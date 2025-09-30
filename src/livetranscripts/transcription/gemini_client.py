"""Gemini transcription client."""

import asyncio
import io
import time
import wave
from typing import Dict, Any
import numpy as np
import google.generativeai as genai

from .base import TranscriptionClient
from ..whisper_integration import (
    TranscriptionResult,
    TranscriptionSegment,
    AudioProcessor,
    RetryManager
)
from ..config import TranscriptionConfig


class GeminiClient(TranscriptionClient):
    """Google Gemini transcription client."""

    def __init__(self, config: TranscriptionConfig, api_key: str):
        super().__init__(config, api_key)
        genai.configure(api_key=api_key)

        # Extract model name from config (e.g., "gemini-2.0-flash" from "gemini-2.0-flash-transcribe")
        model_name = self.config.transcription_model.replace("-transcribe", "")
        self.model = genai.GenerativeModel(model_name)

        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_audio_duration': 0.0,
            'total_processing_time': 0.0
        }

    async def transcribe_batch(self, batch) -> TranscriptionResult:
        """Transcribe an audio batch using Gemini."""
        from ..batching import AudioBatch  # Import here to avoid circular import

        start_time = time.time()
        self._stats['total_requests'] += 1
        self._stats['total_audio_duration'] += batch.duration

        try:
            # Preprocess audio
            processed_audio = self._preprocess_audio(batch.audio_data)

            # Convert to WAV bytes
            wav_bytes = AudioProcessor.audio_to_wav_bytes(processed_audio)

            # Make API call with retry logic
            response = await self._make_transcription_request(wav_bytes, batch)

            # Process response
            result = self._process_response(response, batch)

            self._stats['successful_requests'] += 1
            self._stats['total_processing_time'] += time.time() - start_time

            return result

        except Exception as e:
            self._stats['failed_requests'] += 1
            raise e

    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Preprocess audio before transcription."""
        if len(audio_data) == 0:
            return audio_data

        # Normalize to prevent clipping
        processed = AudioProcessor.normalize_audio(audio_data)

        # Apply basic filters
        processed = AudioProcessor.apply_filters(processed)

        return processed

    @RetryManager.async_retry(max_retries=3, base_delay=1.0)
    async def _make_transcription_request(self, wav_bytes: bytes, batch):
        """Make the actual transcription request with retry."""
        import tempfile
        import os as os_module

        # Gemini requires a file path, so write to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_file.write(wav_bytes)
            tmp_path = tmp_file.name

        try:
            # Upload audio file to Gemini
            loop = asyncio.get_event_loop()
            audio_file = await loop.run_in_executor(
                None,
                lambda: genai.upload_file(path=tmp_path, mime_type="audio/wav")
            )

            # Create transcription prompt
            prompt = "Transcribe this audio accurately. Provide only the transcription text without any additional commentary."

            # Add language hint if specified
            if self.config.whisper_language:
                prompt = f"Transcribe this audio in {self.config.whisper_language}. Provide only the transcription text without any additional commentary."

            # Generate transcription (run in executor since it's synchronous)
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content([prompt, audio_file])
            )

            return response

        finally:
            # Clean up temp file
            if os_module.path.exists(tmp_path):
                os_module.unlink(tmp_path)

    def _process_response(self, response, batch) -> TranscriptionResult:
        """Process Gemini API response into TranscriptionResult."""
        # Extract transcription text
        transcription_text = response.text.strip()

        # Create single segment (Gemini doesn't provide word-level timestamps by default)
        segments = [TranscriptionSegment(
            text=transcription_text,
            start_time=0.0,
            end_time=batch.duration,
            confidence=0.0  # Gemini doesn't provide confidence scores
        )]

        return TranscriptionResult(
            text=transcription_text,
            segments=segments,
            language=self.config.whisper_language or 'unknown',
            duration=batch.duration,
            batch_id=batch.sequence_id,
            timestamp=batch.timestamp
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get transcription statistics."""
        stats = self._stats.copy()

        if stats['successful_requests'] > 0:
            stats['average_processing_time'] = (
                stats['total_processing_time'] / stats['successful_requests']
            )
            stats['success_rate'] = (
                stats['successful_requests'] / stats['total_requests']
            )
        else:
            stats['average_processing_time'] = 0.0
            stats['success_rate'] = 0.0

        return stats