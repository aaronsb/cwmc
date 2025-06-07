"""Audio capture functionality using the backend abstraction layer."""

import asyncio
import platform
from typing import Optional, AsyncIterator
import numpy as np

from .config import get_config, load_config
from .audio_backends import (
    AudioBackend, 
    AudioBackendConfig, 
    AudioChunk,
    get_best_backend,
    get_backend_by_type,
    AudioBackendRegistry,
    AudioBackendType,
    register_backend
)


class AudioCaptureConfig:
    """Configuration for audio capture."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 format: str = "int16",
                 chunk_size: int = 1024,
                 buffer_duration: float = 10.0,
                 backend_preference: Optional[str] = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        self.chunk_size = chunk_size
        self.buffer_duration = buffer_duration
        self.backend_preference = backend_preference


class AudioCapture:
    """Main audio capture class with cross-platform support."""
    
    def __init__(self, config: Optional[AudioCaptureConfig] = None):
        """Initialize audio capture with optional configuration."""
        if config is None:
            config = AudioCaptureConfig()
        
        self.config = config
        self._backend: Optional[AudioBackend] = None
        self._is_initialized = False
        self._capture_task: Optional[asyncio.Task] = None
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
        
        # Register backends on first use
        self._register_backends()
    
    def _register_backends(self):
        """Register all available audio backends."""
        # Import backend implementations
        from .audio_backends.pipewire_backend import PipeWireBackend
        from .audio_backends.pulseaudio_backend import PulseAudioBackend
        from .audio_backends.pyaudio_backend import PyAudioBackend
        from .audio_backends.sounddevice_backend import SoundDeviceBackend
        
        # Register Linux backends
        register_backend(AudioBackendType.PIPEWIRE, PipeWireBackend)
        register_backend(AudioBackendType.PULSEAUDIO, PulseAudioBackend)
        
        # Register cross-platform backends
        register_backend(AudioBackendType.PYAUDIO, PyAudioBackend)
        register_backend(AudioBackendType.SOUNDDEVICE, SoundDeviceBackend)
    
    async def initialize(self) -> None:
        """Initialize the audio capture system."""
        if self._is_initialized:
            return
        
        # Load configuration
        app_config = get_config()
        
        # Create backend config
        backend_config = AudioBackendConfig(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            chunk_size=self.config.chunk_size,
            buffer_duration=self.config.buffer_duration,
            device_name=getattr(app_config.audio, 'device_name', None)
        )
        
        # Determine backend preference
        backend_pref = self.config.backend_preference or app_config.audio.backend_preference
        
        # Convert enum to string if needed
        if hasattr(backend_pref, 'value'):
            backend_pref = backend_pref.value
        
        # Get appropriate backend
        if backend_pref and backend_pref != "auto":
            # Try to get specific backend
            try:
                backend_type = AudioBackendType(backend_pref)
                self._backend = get_backend_by_type(backend_type, backend_config)
            except ValueError:
                print(f"Warning: Unknown backend type '{backend_pref}', falling back to auto-selection")
                self._backend = None
        
        # If no backend yet, use auto-selection
        if not self._backend:
            self._backend = await get_best_backend(backend_config)
        
        if not self._backend:
            raise RuntimeError("No suitable audio backend found for this platform")
        
        print(f"Using audio backend: {self._backend.__class__.__name__}")
        
        # Backend is ready to use
        self._is_initialized = True
    
    async def start_capture(self) -> None:
        """Start capturing audio."""
        if not self._is_initialized:
            await self.initialize()
        
        if self._capture_task and not self._capture_task.done():
            return  # Already capturing
        
        await self._backend.start_capture()
        self._capture_task = asyncio.create_task(self._capture_loop())
    
    async def stop_capture(self) -> None:
        """Stop capturing audio."""
        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None
        
        if self._backend:
            await self._backend.stop_capture()
    
    async def _capture_loop(self) -> None:
        """Internal capture loop."""
        try:
            while True:
                chunk = await self._backend.get_audio_chunk()
                await self._audio_queue.put(chunk)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Error in capture loop: {e}")
            raise
    
    async def get_audio_chunk(self) -> AudioChunk:
        """Get the next audio chunk."""
        return await self._audio_queue.get()
    
    async def stream_audio(self) -> AsyncIterator[AudioChunk]:
        """Stream audio chunks as they become available."""
        while True:
            try:
                chunk = await self.get_audio_chunk()
                yield chunk
            except asyncio.CancelledError:
                break
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.stop_capture()
        
        if self._backend:
            await self._backend.cleanup()
            self._backend = None
        
        self._is_initialized = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


# Platform-specific capture implementations for direct use
class PlatformAudioCapture:
    """Platform-specific audio capture factory."""
    
    @staticmethod
    def create_capture(config: Optional[AudioCaptureConfig] = None) -> AudioCapture:
        """Create the appropriate audio capture for the current platform."""
        return AudioCapture(config)
    
    @staticmethod
    async def test_audio_capture():
        """Test audio capture on the current platform."""
        capture = AudioCapture()
        
        try:
            await capture.initialize()
            await capture.start_capture()
            
            print("Starting audio capture test...")
            print("Capturing 5 seconds of audio...")
            
            start_time = asyncio.get_event_loop().time()
            chunks = []
            
            async for chunk in capture.stream_audio():
                chunks.append(chunk)
                elapsed = asyncio.get_event_loop().time() - start_time
                
                if elapsed >= 5:
                    break
                
                if len(chunks) % 10 == 0:
                    print(f"Captured {len(chunks)} chunks ({elapsed:.1f}s)")
            
            print(f"\nTest complete! Captured {len(chunks)} chunks")
            
            # Calculate statistics
            total_samples = sum(chunk.data.shape[0] for chunk in chunks)
            duration = total_samples / capture.config.sample_rate
            print(f"Total duration: {duration:.2f} seconds")
            print(f"Average chunk size: {total_samples / len(chunks):.0f} samples")
            
        finally:
            await capture.cleanup()


# Make PlatformAudioCapture available at module level
MacOSAudioCapture = PlatformAudioCapture
WindowsAudioCapture = PlatformAudioCapture  
LinuxAudioCapture = PlatformAudioCapture