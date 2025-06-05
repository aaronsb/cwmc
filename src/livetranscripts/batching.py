"""VAD-based audio batching system for intelligent transcription batching."""

import asyncio
import time
import warnings
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Deque
import numpy as np


@dataclass
class AudioBatch:
    """Audio batch data structure."""
    
    audio_data: np.ndarray
    timestamp: datetime
    duration: float = 0.0
    sequence_id: int = 0
    is_final: bool = False
    
    def __post_init__(self):
        """Calculate duration if not provided."""
        if self.duration == 0.0 and len(self.audio_data) > 0:
            # Assume 16kHz sample rate
            self.duration = len(self.audio_data) / 16000.0
    
    @property
    def size_bytes(self) -> int:
        """Get batch size in bytes."""
        return self.audio_data.nbytes
    
    def is_valid(self) -> bool:
        """Check if batch is valid."""
        return (len(self.audio_data) > 0 and 
                self.audio_data.dtype == np.int16 and
                self.duration > 0)


@dataclass
class BatchingConfig:
    """Configuration for audio batching."""
    
    min_batch_duration: float = 3.0
    max_batch_duration: float = 30.0
    silence_threshold: int = 500  # milliseconds
    sample_rate: int = 16000
    overlap_duration: float = 0.5
    energy_threshold: float = 1000.0  # RMS energy threshold for speech detection
    
    def __post_init__(self):
        """Validate configuration."""
        if self.min_batch_duration <= 0:
            raise ValueError("min_batch_duration must be positive")
        if self.max_batch_duration <= self.min_batch_duration:
            raise ValueError("max_batch_duration must be greater than min_batch_duration")
        if self.silence_threshold <= 0:
            raise ValueError("silence_threshold must be positive")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")


class SilenceDetector:
    """Voice Activity Detection (VAD) for silence detection."""
    
    def __init__(self, config: BatchingConfig):
        self.config = config
        self.energy_threshold = config.energy_threshold
        self.silence_start_time = None
        self.last_speech_time = time.time()
    
    def is_silence(self, audio_chunk: np.ndarray) -> bool:
        """Detect if audio chunk contains silence."""
        energy = self._calculate_rms_energy(audio_chunk)
        current_time = time.time()
        
        if energy > self.energy_threshold:
            # Speech detected
            self.last_speech_time = current_time
            self.silence_start_time = None
            return False
        else:
            # Silence detected
            if self.silence_start_time is None:
                self.silence_start_time = current_time
            return True
    
    def get_silence_duration(self) -> int:
        """Get current silence duration in milliseconds."""
        if self.silence_start_time is None:
            return 0
        return int((time.time() - self.silence_start_time) * 1000)
    
    def _calculate_rms_energy(self, audio_chunk: np.ndarray) -> float:
        """Calculate RMS energy of audio chunk."""
        if len(audio_chunk) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio_chunk.astype(np.float64) ** 2)))


class BatchQueue:
    """Thread-safe queue for audio batches."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._queue: Deque[AudioBatch] = deque()
        self._lock = asyncio.Lock()
    
    def put(self, batch: AudioBatch) -> None:
        """Add batch to queue (sync version)."""
        if len(self._queue) >= self.max_size:
            warnings.warn("Batch queue overflow, dropping oldest batch", UserWarning)
            self._queue.popleft()
        self._queue.append(batch)
    
    async def put_async(self, batch: AudioBatch) -> None:
        """Add batch to queue (async version)."""
        async with self._lock:
            self.put(batch)
    
    def get(self) -> Optional[AudioBatch]:
        """Get batch from queue (sync version)."""
        if self._queue:
            return self._queue.popleft()
        return None
    
    async def get_async(self) -> Optional[AudioBatch]:
        """Get batch from queue (async version)."""
        async with self._lock:
            return self.get()
    
    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0


class VADAudioBatcher:
    """Main VAD-based audio batcher."""
    
    def __init__(self, config: BatchingConfig):
        self.config = config
        self.silence_detector = SilenceDetector(config)
        self.current_batch: List[int] = []
        self.batch_start_time: Optional[datetime] = None
        self.sequence_id = 0
        self.is_processing = False
        self.previous_batch_audio: Optional[np.ndarray] = None
        self._lock = asyncio.Lock()
    
    async def add_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[AudioBatch]:
        """Add audio chunk and return batch if ready."""
        async with self._lock:
            return await self._process_audio_chunk(audio_chunk)
    
    async def _process_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[AudioBatch]:
        """Process audio chunk and determine if batch should be created."""
        if self.batch_start_time is None:
            self.batch_start_time = datetime.now()
        
        # Add chunk to current batch
        self.current_batch.extend(audio_chunk.tolist())
        
        # Calculate current batch duration
        current_duration = len(self.current_batch) / self.config.sample_rate
        
        # Check for silence
        is_silence = self.silence_detector.is_silence(audio_chunk)
        silence_duration = self.silence_detector.get_silence_duration()
        
        # Determine if we should create a batch
        should_batch = False
        
        # Force batch on max duration
        if current_duration >= self.config.max_batch_duration:
            should_batch = True
        
        # Batch on silence after minimum duration
        elif (current_duration >= self.config.min_batch_duration and 
              is_silence and 
              silence_duration >= self.config.silence_threshold):
            should_batch = True
        
        if should_batch:
            batch = self._create_batch()
            self._reset_batch()
            return batch
        
        return None
    
    def _create_batch(self) -> AudioBatch:
        """Create an AudioBatch from current data."""
        audio_data = np.array(self.current_batch, dtype=np.int16)
        
        # Add overlap from previous batch if available
        overlap = self._calculate_overlap()
        if overlap is not None and len(overlap) > 0:
            audio_data = np.concatenate([overlap, audio_data])
        
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=self.batch_start_time or datetime.now(),
            sequence_id=self.sequence_id
        )
        
        # Store audio for next batch overlap
        self.previous_batch_audio = audio_data.copy()
        self.sequence_id += 1
        
        return batch
    
    def _calculate_overlap(self) -> Optional[np.ndarray]:
        """Calculate overlap from previous batch."""
        if self.previous_batch_audio is None:
            return None
        
        overlap_samples = int(self.config.overlap_duration * self.config.sample_rate)
        if len(self.previous_batch_audio) < overlap_samples:
            return self.previous_batch_audio.copy()
        
        return self.previous_batch_audio[-overlap_samples:].copy()
    
    def _reset_batch(self) -> None:
        """Reset current batch state."""
        self.current_batch = []
        self.batch_start_time = None
    
    async def force_batch(self) -> Optional[AudioBatch]:
        """Force creation of batch from current data."""
        async with self._lock:
            if len(self.current_batch) > 0:
                batch = self._create_batch()
                self._reset_batch()
                return batch
            return None


class BatchProcessor:
    """Processes batches and manages the batching pipeline."""
    
    def __init__(self, config: BatchingConfig):
        self.config = config
        self.batcher = VADAudioBatcher(config)
        self.batch_queue = BatchQueue()
        self.is_running = False
        self._stats = {
            'batches_created': 0,
            'total_audio_duration': 0.0,
            'average_batch_duration': 0.0
        }
    
    async def start_processing(self) -> None:
        """Start the batch processing pipeline."""
        self.is_running = True
    
    async def stop_processing(self) -> None:
        """Stop the batch processing pipeline."""
        self.is_running = False
        
        # Force final batch if needed
        final_batch = await self.batcher.force_batch()
        if final_batch:
            await self.batch_queue.put_async(final_batch)
    
    async def process_audio_chunk(self, audio_chunk: np.ndarray) -> None:
        """Process an audio chunk through the batching system."""
        if not self.is_running:
            return
        
        batch = await self.batcher.add_audio_chunk(audio_chunk)
        if batch:
            await self.batch_queue.put_async(batch)
            self._update_stats(batch)
    
    async def get_next_batch(self) -> Optional[AudioBatch]:
        """Get the next available batch."""
        return await self.batch_queue.get_async()
    
    def _update_stats(self, batch: AudioBatch) -> None:
        """Update processing statistics."""
        self._stats['batches_created'] += 1
        self._stats['total_audio_duration'] += batch.duration
        self._stats['average_batch_duration'] = (
            self._stats['total_audio_duration'] / self._stats['batches_created']
        )
    
    def get_statistics(self) -> dict:
        """Get processing statistics."""
        return self._stats.copy()
    
    def get_queue_status(self) -> dict:
        """Get queue status information."""
        return {
            'queue_size': self.batch_queue.size(),
            'is_empty': self.batch_queue.is_empty(),
            'max_size': self.batch_queue.max_size
        }


# Utility functions
def calculate_audio_duration(audio_data: np.ndarray, sample_rate: int = 16000) -> float:
    """Calculate duration of audio data in seconds."""
    return len(audio_data) / sample_rate


def merge_audio_batches(batches: List[AudioBatch]) -> AudioBatch:
    """Merge multiple audio batches into one."""
    if not batches:
        raise ValueError("Cannot merge empty batch list")
    
    # Concatenate all audio data
    audio_arrays = [batch.audio_data for batch in batches]
    merged_audio = np.concatenate(audio_arrays)
    
    # Use timestamp from first batch
    timestamp = batches[0].timestamp
    
    # Calculate total duration
    total_duration = sum(batch.duration for batch in batches)
    
    return AudioBatch(
        audio_data=merged_audio,
        timestamp=timestamp,
        duration=total_duration,
        sequence_id=batches[0].sequence_id,
        is_final=True
    )


def validate_batch_sequence(batches: List[AudioBatch]) -> bool:
    """Validate that batches are in correct sequence order."""
    if len(batches) <= 1:
        return True
    
    for i in range(1, len(batches)):
        if batches[i].sequence_id <= batches[i-1].sequence_id:
            return False
    
    return True