"""Base classes for audio backend abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, AsyncIterator
import numpy as np
import asyncio


class AudioBackendType(Enum):
    """Supported audio backend types."""
    PIPEWIRE = "pipewire"
    PULSEAUDIO = "pulseaudio"
    PYAUDIO = "pyaudio"
    SOUNDDEVICE = "sounddevice"
    WASAPI = "wasapi"
    COREAUDIO = "coreaudio"
    BLACKHOLE = "blackhole"
    JACK = "jack"
    ALSA = "alsa"


@dataclass
class AudioBackendConfig:
    """Configuration for audio backends."""
    
    sample_rate: int = 16000
    channels: int = 1
    format: str = "int16"
    chunk_size: int = 1024
    buffer_duration: float = 10.0
    device_name: Optional[str] = None
    latency_mode: str = "low"  # "low", "normal", "high"
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if self.channels not in [1, 2]:
            raise ValueError("Channels must be 1 or 2")
        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if self.buffer_duration <= 0:
            raise ValueError("Buffer duration must be positive")
        if self.latency_mode not in ["low", "normal", "high"]:
            raise ValueError("Latency mode must be 'low', 'normal', or 'high'")


@dataclass
class AudioChunk:
    """Container for audio data with metadata."""
    
    data: np.ndarray
    timestamp: float
    sample_rate: int
    channels: int
    duration: float
    
    @property
    def samples(self) -> int:
        """Number of samples in this chunk."""
        return len(self.data) // self.channels
    
    def to_mono(self) -> np.ndarray:
        """Convert to mono if stereo."""
        if self.channels == 1:
            return self.data
        # Average stereo channels
        return self.data.reshape(-1, 2).mean(axis=1).astype(self.data.dtype)


class AudioBackend(ABC):
    """Abstract base class for audio capture backends."""
    
    def __init__(self, config: AudioBackendConfig):
        self.config = config
        self._is_capturing = False
        self._start_time: Optional[float] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
    
    @property
    @abstractmethod
    def backend_type(self) -> AudioBackendType:
        """Return the backend type."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the backend."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this backend is available on the current system."""
        pass
    
    @abstractmethod
    async def get_devices(self) -> list[dict]:
        """Get list of available audio devices.
        
        Returns:
            List of device info dicts with at least 'name' and 'id' keys
        """
        pass
    
    @abstractmethod
    async def start_capture(self) -> None:
        """Start audio capture."""
        pass
    
    @abstractmethod
    async def stop_capture(self) -> None:
        """Stop audio capture."""
        pass
    
    @abstractmethod
    async def get_audio_chunk(self) -> AudioChunk:
        """Get next audio chunk.
        
        Returns:
            AudioChunk with audio data and metadata
        """
        pass
    
    async def capture_stream(self) -> AsyncIterator[AudioChunk]:
        """Async iterator for continuous audio capture.
        
        Yields:
            AudioChunk objects as they become available
        """
        if not self._is_capturing:
            await self.start_capture()
        
        try:
            while self._is_capturing:
                try:
                    chunk = await self.get_audio_chunk()
                    yield chunk
                except Exception as e:
                    if self._error_callback:
                        self._error_callback(e)
                    else:
                        raise
        finally:
            await self.stop_capture()
    
    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Set callback for handling errors during capture."""
        self._error_callback = callback
    
    @property
    def is_capturing(self) -> bool:
        """Check if currently capturing audio."""
        return self._is_capturing
    
    def get_latency_hint(self) -> float:
        """Get suggested latency in seconds based on config."""
        latency_map = {
            "low": 0.01,     # 10ms
            "normal": 0.05,  # 50ms
            "high": 0.1      # 100ms
        }
        return latency_map.get(self.config.latency_mode, 0.05)