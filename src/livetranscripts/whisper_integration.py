"""OpenAI Whisper API integration for audio transcription."""

import asyncio
import io
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import numpy as np
import openai


@dataclass
class WhisperConfig:
    """Configuration for Whisper API integration."""
    
    model: str = "whisper-1"
    language: Optional[str] = None
    temperature: float = 0.0
    max_retries: int = 3
    timeout: float = 30.0
    response_format: str = "verbose_json"
    
    def __post_init__(self):
        """Validate configuration."""
        if not 0 <= self.temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class TranscriptionSegment:
    """Individual transcription segment with timing."""
    
    text: str
    start_time: float
    end_time: float
    confidence: float = 0.0
    
    @property
    def duration(self) -> float:
        """Get segment duration."""
        return self.end_time - self.start_time
    
    def is_valid(self) -> bool:
        """Check if segment is valid."""
        return (len(self.text.strip()) > 0 and 
                self.end_time > self.start_time and
                self.start_time >= 0)


@dataclass
class TranscriptionResult:
    """Complete transcription result with metadata."""
    
    text: str
    segments: List[TranscriptionSegment]
    language: str
    duration: float
    batch_id: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across segments."""
        if not self.segments:
            return 0.0
        confidences = [seg.confidence for seg in self.segments if seg.confidence > 0]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def is_valid(self) -> bool:
        """Check if transcription result is valid."""
        return (len(self.text.strip()) > 0 and 
                self.duration > 0 and
                all(seg.is_valid() for seg in self.segments))
    
    @staticmethod
    def combine(results: List['TranscriptionResult']) -> 'TranscriptionResult':
        """Combine multiple transcription results."""
        if not results:
            raise ValueError("Cannot combine empty results list")
        
        combined_text = " ".join(result.text for result in results)
        combined_segments = []
        time_offset = 0.0
        
        for result in results:
            for segment in result.segments:
                adjusted_segment = TranscriptionSegment(
                    text=segment.text,
                    start_time=segment.start_time + time_offset,
                    end_time=segment.end_time + time_offset,
                    confidence=segment.confidence
                )
                combined_segments.append(adjusted_segment)
            time_offset += result.duration
        
        return TranscriptionResult(
            text=combined_text,
            segments=combined_segments,
            language=results[0].language,
            duration=sum(r.duration for r in results),
            batch_id=results[0].batch_id,
            timestamp=results[0].timestamp
        )


class AudioProcessor:
    """Utilities for audio processing before transcription."""
    
    @staticmethod
    def audio_to_wav_bytes(audio_data: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        return wav_buffer.getvalue()
    
    @staticmethod
    def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio to prevent clipping."""
        if len(audio_data) == 0:
            return audio_data
        
        max_val = np.max(np.abs(audio_data))
        if max_val > 32767:
            # Scale down to prevent clipping
            scale_factor = 32767 / max_val
            return (audio_data * scale_factor).astype(np.int16)
        
        return audio_data
    
    @staticmethod
    def apply_filters(audio_data: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """Apply basic audio filters to improve transcription quality."""
        # Simple high-pass filter to remove low-frequency noise
        if len(audio_data) < 100:
            return audio_data
        
        # Calculate a simple moving average for noise reduction
        window_size = min(5, len(audio_data) // 10)
        if window_size > 1:
            # Apply simple smoothing
            filtered = np.convolve(audio_data, np.ones(window_size)/window_size, mode='same')
            return filtered.astype(np.int16)
        
        return audio_data


class RetryManager:
    """Manages retry logic for API calls."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.current_attempt = 0
    
    def should_retry(self) -> bool:
        """Check if should retry based on current attempt."""
        return self.current_attempt < self.max_retries
    
    def get_delay(self) -> float:
        """Get delay for current retry (exponential backoff)."""
        return self.base_delay * (2 ** (self.current_attempt - 1))
    
    async def wait(self) -> None:
        """Wait for retry delay."""
        if self.current_attempt > 0:
            delay = self.get_delay()
            await asyncio.sleep(delay)
    
    @staticmethod
    def async_retry(max_retries: int = 3, base_delay: float = 1.0):
        """Decorator for async functions with retry logic."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                retry_manager = RetryManager(max_retries, base_delay)
                last_exception = None
                
                while retry_manager.should_retry():
                    try:
                        await retry_manager.wait()
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        last_exception = e
                        retry_manager.current_attempt += 1
                        if not retry_manager.should_retry():
                            break
                
                raise last_exception
            return wrapper
        return decorator


class WhisperClient:
    """OpenAI Whisper API client for transcription."""
    
    def __init__(self, config: WhisperConfig, api_key: str):
        self.config = config
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_audio_duration': 0.0,
            'total_processing_time': 0.0
        }
    
    async def transcribe_batch(self, batch) -> TranscriptionResult:
        """Transcribe an audio batch."""
        from .batching import AudioBatch  # Import here to avoid circular import
        
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
        """Format parameters for Whisper API request."""
        params = {
            "model": self.config.model,
            "response_format": self.config.response_format,
            "temperature": self.config.temperature,
        }
        
        if self.config.language:
            params["language"] = self.config.language
        
        return params
    
    @RetryManager.async_retry(max_retries=3, base_delay=1.0)
    async def _make_transcription_request(self, audio_file: io.BytesIO, params: Dict[str, Any]):
        """Make the actual transcription request with retry."""
        return await self.client.audio.transcriptions.create(
            file=audio_file,
            **params
        )
    
    def _process_response(self, response, batch) -> TranscriptionResult:
        """Process Whisper API response into TranscriptionResult."""
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


class TranscriptionManager:
    """Manages the transcription pipeline."""
    
    def __init__(self, whisper_client: WhisperClient):
        self.whisper_client = whisper_client
        self.transcription_history: List[TranscriptionResult] = []
        self.is_processing = False
        self._processing_queue = asyncio.Queue()
        self._result_callbacks = []
    
    async def start_processing(self) -> None:
        """Start the transcription processing pipeline."""
        self.is_processing = True
        asyncio.create_task(self._process_queue())
    
    async def stop_processing(self) -> None:
        """Stop the transcription processing pipeline."""
        self.is_processing = False
    
    async def transcribe_batch(self, batch) -> None:
        """Queue a batch for transcription."""
        if self.is_processing:
            await self._processing_queue.put(batch)
    
    async def _process_queue(self) -> None:
        """Process batches from the queue."""
        while self.is_processing:
            try:
                # Wait for batch with timeout
                batch = await asyncio.wait_for(
                    self._processing_queue.get(), 
                    timeout=1.0
                )
                
                # Transcribe batch
                result = await self.whisper_client.transcribe_batch(batch)
                
                # Store result
                self.transcription_history.append(result)
                
                # Notify callbacks
                for callback in self._result_callbacks:
                    try:
                        await callback(result)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
            except asyncio.TimeoutError:
                # No batch available, continue
                continue
            except Exception as e:
                print(f"Transcription error: {e}")
    
    def add_result_callback(self, callback) -> None:
        """Add callback for transcription results."""
        self._result_callbacks.append(callback)
    
    def get_recent_transcriptions(self, count: int = 10) -> List[TranscriptionResult]:
        """Get recent transcription results."""
        return self.transcription_history[-count:] if self.transcription_history else []
    
    def get_full_transcript(self) -> str:
        """Get full transcript text."""
        return " ".join(result.text for result in self.transcription_history)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transcription statistics."""
        base_stats = self.whisper_client.get_statistics()
        
        total_duration = sum(r.duration for r in self.transcription_history)
        avg_confidence = (
            sum(r.average_confidence for r in self.transcription_history) / 
            len(self.transcription_history)
        ) if self.transcription_history else 0.0
        
        base_stats.update({
            'total_transcribed_duration': total_duration,
            'transcription_count': len(self.transcription_history),
            'average_confidence': avg_confidence,
            'queue_size': self._processing_queue.qsize()
        })
        
        return base_stats