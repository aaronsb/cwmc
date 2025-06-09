"""GPT-4o transcription client."""

import asyncio
import io
import time
import wave
from typing import Dict, Any
import numpy as np
import openai

from .base import TranscriptionClient
from ..whisper_integration import (
    TranscriptionResult,
    TranscriptionSegment,
    AudioProcessor,
    RetryManager
)
from ..config import TranscriptionConfig


class GPT4oClient(TranscriptionClient):
    """OpenAI GPT-4o transcription client."""
    
    def __init__(self, config: TranscriptionConfig, api_key: str):
        super().__init__(config, api_key)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_audio_duration': 0.0,
            'total_processing_time': 0.0
        }
    
    async def transcribe_batch(self, batch) -> TranscriptionResult:
        """Transcribe an audio batch using GPT-4o."""
        from ..batching import AudioBatch  # Import here to avoid circular import
        
        start_time = time.time()
        self._stats['total_requests'] += 1
        self._stats['total_audio_duration'] += batch.duration
        
        try:
            # Preprocess audio
            processed_audio = self._preprocess_audio(batch.audio_data)
            
            # Convert to WAV bytes
            wav_bytes = AudioProcessor.audio_to_wav_bytes(processed_audio)
            
            # Create file-like object
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = f"batch_{batch.sequence_id}.wav"
            
            # Prepare request parameters
            params = self._format_request_parameters()
            
            # Make API call with retry logic
            response = await self._make_transcription_request(audio_file, params)
            
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
    
    def _format_request_parameters(self) -> Dict[str, Any]:
        """Format parameters for GPT-4o transcription API request."""
        params = {
            "model": self.config.transcription_model,
            "response_format": "verbose_json",
            "temperature": 0.0,  # Use deterministic output for transcription
        }
        
        # Use whisper_language if set (for backward compatibility)
        if self.config.whisper_language:
            params["language"] = self.config.whisper_language
        
        return params
    
    @RetryManager.async_retry(max_retries=3, base_delay=1.0)
    async def _make_transcription_request(self, audio_file: io.BytesIO, params: Dict[str, Any]):
        """Make the actual transcription request with retry."""
        return await self.client.audio.transcriptions.create(
            file=audio_file,
            **params
        )
    
    def _process_response(self, response, batch) -> TranscriptionResult:
        """Process GPT-4o API response into TranscriptionResult."""
        # Extract segments if available
        segments = []
        if hasattr(response, 'segments') and response.segments:
            for seg in response.segments:
                segment = TranscriptionSegment(
                    text=seg.text.strip(),
                    start_time=float(seg.start),
                    end_time=float(seg.end),
                    confidence=getattr(seg, 'confidence', 0.0)
                )
                segments.append(segment)
        else:
            # Create single segment if no segments provided
            segments = [TranscriptionSegment(
                text=response.text.strip(),
                start_time=0.0,
                end_time=batch.duration,
                confidence=0.0
            )]
        
        return TranscriptionResult(
            text=response.text.strip(),
            segments=segments,
            language=getattr(response, 'language', 'unknown'),
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