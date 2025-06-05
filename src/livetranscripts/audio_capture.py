"""Audio capture functionality for live meeting transcription."""

import asyncio
import platform
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union
import numpy as np


@dataclass
class AudioCaptureConfig:
    """Configuration for audio capture."""
    
    sample_rate: int = 16000
    channels: int = 1
    format: str = "int16"
    chunk_size: int = 1024
    buffer_duration: float = 10.0
    
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


class PlatformAudioCapture(ABC):
    """Abstract base class for platform-specific audio capture."""
    
    def __init__(self, config: AudioCaptureConfig):
        self.config = config
        self._is_capturing = False
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if audio capture is available on this platform."""
        pass
    
    @abstractmethod
    def start_capture(self) -> None:
        """Start audio capture."""
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """Stop audio capture."""
        pass
    
    @abstractmethod
    def get_audio_chunk(self) -> np.ndarray:
        """Get the next audio chunk."""
        pass


class MacOSAudioCapture(PlatformAudioCapture):
    """macOS-specific audio capture using BlackHole loopback."""
    
    def __init__(self, config: AudioCaptureConfig):
        super().__init__(config)
        self.pa = None
        self.stream = None
        self.device_index = None
        
    def is_available(self) -> bool:
        """Check if PyAudio and BlackHole are available."""
        try:
            import pyaudio
            self.pa = pyaudio.PyAudio()
            self.device_index = self._find_loopback_device()
            return True
        except (ImportError, RuntimeError):
            return False
    
    def _find_loopback_device(self) -> int:
        """Find BlackHole or other loopback device."""
        if not self.pa:
            raise RuntimeError("PyAudio not initialized")
        
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            device_name = device_info.get('name', '').lower()
            
            # Look for BlackHole or other loopback devices
            if ('blackhole' in device_name or 
                'loopback' in device_name or
                'soundflower' in device_name):
                if device_info.get('maxInputChannels', 0) > 0:
                    return i
        
        raise RuntimeError("No loopback audio device found. Please install BlackHole.")
    
    def start_capture(self) -> None:
        """Start audio capture from loopback device."""
        if not self.pa or self.device_index is None:
            if not self.is_available():
                raise RuntimeError("Audio capture not available")
        
        import pyaudio
        
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.config.chunk_size
        )
        self._is_capturing = True
    
    def stop_capture(self) -> None:
        """Stop audio capture."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.pa:
            self.pa.terminate()
            self.pa = None
        self._is_capturing = False
    
    def get_audio_chunk(self) -> np.ndarray:
        """Get audio chunk from stream."""
        if not self.stream or not self._is_capturing:
            raise RuntimeError("Audio capture not started")
        
        try:
            data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
            return np.frombuffer(data, dtype=np.int16)
        except Exception as e:
            if "overflow" in str(e).lower():
                raise BufferError("Buffer overflow")
            raise


class WindowsAudioCapture(PlatformAudioCapture):
    """Windows-specific audio capture using WASAPI loopback."""
    
    def __init__(self, config: AudioCaptureConfig):
        super().__init__(config)
        self.pa = None
        self.stream = None
        self.wasapi_info = None
    
    def is_available(self) -> bool:
        """Check if PyAudio with WASAPI is available."""
        try:
            import pyaudio
            self.pa = pyaudio.PyAudio()
            self.wasapi_info = self._get_wasapi_loopback()
            return self.wasapi_info is not None
        except (ImportError, RuntimeError):
            return False
    
    def _get_wasapi_loopback(self):
        """Get WASAPI loopback device info."""
        if not self.pa:
            return None
        
        try:
            # Look for WASAPI loopback devices
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                if (device_info.get('name', '').endswith('(Loopback)') and
                    device_info.get('maxInputChannels', 0) > 0):
                    return device_info
        except Exception:
            pass
        return None
    
    def start_capture(self) -> None:
        """Start WASAPI loopback capture."""
        if not self.pa or not self.wasapi_info:
            if not self.is_available():
                raise RuntimeError("WASAPI loopback not available")
        
        import pyaudio
        
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            input=True,
            input_device_index=self.wasapi_info['index'],
            frames_per_buffer=self.config.chunk_size
        )
        self._is_capturing = True
    
    def stop_capture(self) -> None:
        """Stop audio capture."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.pa:
            self.pa.terminate()
            self.pa = None
        self._is_capturing = False
    
    def get_audio_chunk(self) -> np.ndarray:
        """Get audio chunk from WASAPI stream."""
        if not self.stream or not self._is_capturing:
            raise RuntimeError("Audio capture not started")
        
        try:
            data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
            return np.frombuffer(data, dtype=np.int16)
        except Exception as e:
            if "overflow" in str(e).lower():
                raise BufferError("Buffer overflow")
            raise


class LinuxAudioCapture(PlatformAudioCapture):
    """Linux-specific audio capture using PulseAudio loopback."""
    
    def __init__(self, config: AudioCaptureConfig):
        super().__init__(config)
        self.pa = None
        self.stream = None
        self.monitor_device = None
    
    def is_available(self) -> bool:
        """Check if PyAudio and PulseAudio are available."""
        try:
            import pyaudio
            self.pa = pyaudio.PyAudio()
            self.monitor_device = self._find_monitor_device()
            return True
        except (ImportError, RuntimeError):
            return False
    
    def _find_monitor_device(self) -> Optional[int]:
        """Find PulseAudio monitor device for system audio."""
        if not self.pa:
            return None
        
        try:
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                device_name = device_info.get('name', '').lower()
                
                # Look for monitor devices (system audio output monitors)
                if ('.monitor' in device_name or 
                    'monitor' in device_name):
                    if device_info.get('maxInputChannels', 0) > 0:
                        return i
        except Exception:
            pass
        return None
    
    def start_capture(self) -> None:
        """Start PulseAudio monitor capture."""
        if not self.pa or self.monitor_device is None:
            if not self.is_available():
                raise RuntimeError("PulseAudio monitor not available")
        
        import pyaudio
        
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            input=True,
            input_device_index=self.monitor_device,
            frames_per_buffer=self.config.chunk_size
        )
        self._is_capturing = True
    
    def stop_capture(self) -> None:
        """Stop audio capture."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.pa:
            self.pa.terminate()
            self.pa = None
        self._is_capturing = False
    
    def get_audio_chunk(self) -> np.ndarray:
        """Get audio chunk from monitor stream."""
        if not self.stream or not self._is_capturing:
            raise RuntimeError("Audio capture not started")
        
        try:
            data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
            return np.frombuffer(data, dtype=np.int16)
        except Exception as e:
            if "overflow" in str(e).lower():
                raise BufferError("Buffer overflow")
            raise


def get_platform_capture(config: Optional[AudioCaptureConfig] = None) -> PlatformAudioCapture:
    """Get platform-specific audio capture implementation."""
    if config is None:
        config = AudioCaptureConfig()
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        capture = MacOSAudioCapture(config)
    elif system == "Windows":
        capture = WindowsAudioCapture(config)
    elif system == "Linux":
        capture = LinuxAudioCapture(config)
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
    
    if not capture.is_available():
        raise RuntimeError(f"Audio capture not available on {system}")
    
    return capture


class AudioCapture:
    """Main audio capture class with cross-platform support."""
    
    def __init__(self, config: Optional[AudioCaptureConfig] = None):
        self.config = config or AudioCaptureConfig()
        self.platform_capture = get_platform_capture(self.config)
        self.microphone_capture = None
        self.is_capturing = False
        
        # Try to set up microphone capture for dual-source audio
        try:
            self.microphone_capture = self._setup_microphone_capture()
        except Exception as e:
            print(f"⚠️  Microphone capture not available: {e}")
            print("   Live Transcripts will work with system audio only")
    
    def _setup_microphone_capture(self):
        """Set up microphone capture for dual-source audio."""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            
            # Find default microphone
            default_mic = None
            for i in range(pa.get_device_count()):
                device_info = pa.get_device_info_by_index(i)
                if (device_info.get('maxInputChannels', 0) > 0 and
                    'microphone' in device_info.get('name', '').lower() and
                    'blackhole' not in device_info.get('name', '').lower()):
                    default_mic = i
                    break
            
            if default_mic is not None:
                return {
                    'pa': pa,
                    'device_index': default_mic,
                    'stream': None
                }
            else:
                pa.terminate()
                return None
                
        except Exception as e:
            return None
    
    def start_capture(self) -> None:
        """Start audio capture."""
        self.platform_capture.start_capture()
        
        # Start microphone capture if available
        if self.microphone_capture:
            try:
                import pyaudio
                pa = self.microphone_capture['pa']
                self.microphone_capture['stream'] = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.config.sample_rate,
                    input=True,
                    input_device_index=self.microphone_capture['device_index'],
                    frames_per_buffer=self.config.chunk_size
                )
                print("✅ Dual-source audio: System + Microphone")
            except Exception as e:
                print(f"⚠️  Microphone start failed: {e}")
                self.microphone_capture = None
        
        self.is_capturing = True
    
    def stop_capture(self) -> None:
        """Stop audio capture."""
        self.platform_capture.stop_capture()
        
        # Stop microphone capture
        if self.microphone_capture and self.microphone_capture.get('stream'):
            try:
                self.microphone_capture['stream'].stop_stream()
                self.microphone_capture['stream'].close()
                self.microphone_capture['pa'].terminate()
            except Exception as e:
                print(f"⚠️  Microphone stop error: {e}")
        
        self.is_capturing = False
    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """Get audio data, mixing system audio and microphone if available."""
        try:
            # Get system audio (BlackHole)
            system_audio = self.platform_capture.get_audio_chunk()
            
            # Get microphone audio if available
            if (self.microphone_capture and 
                self.microphone_capture.get('stream') and
                self.is_capturing):
                try:
                    mic_data = self.microphone_capture['stream'].read(
                        self.config.chunk_size, 
                        exception_on_overflow=False
                    )
                    mic_audio = np.frombuffer(mic_data, dtype=np.int16)
                    
                    # Mix system audio and microphone (simple addition with clipping protection)
                    if len(mic_audio) == len(system_audio):
                        # Mix at 70% system + 30% microphone to prevent overwhelming
                        mixed_audio = (system_audio * 0.7 + mic_audio * 0.3).astype(np.int16)
                        # Prevent clipping
                        mixed_audio = np.clip(mixed_audio, -32768, 32767)
                        return mixed_audio
                    
                except Exception:
                    # If microphone fails, fall back to system audio only
                    pass
            
            return system_audio
            
        except BufferError:
            warnings.warn("Audio buffer overflow detected", UserWarning)
            return None
    
    def __enter__(self):
        """Context manager entry."""
        self.start_capture()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_capture()


# Audio processing utilities
def normalize_audio_data(audio_data: np.ndarray) -> np.ndarray:
    """Normalize int16 audio data to float32 [-1, 1] range."""
    return audio_data.astype(np.float32) / 32768.0


def validate_audio_format(
    audio_data: np.ndarray, 
    expected_length: Optional[int] = None,
    expected_dtype: Optional[np.dtype] = None
) -> bool:
    """Validate audio data format."""
    if expected_length is not None and len(audio_data) != expected_length:
        return False
    
    if expected_dtype is not None and audio_data.dtype != expected_dtype:
        return False
    
    return True


def detect_clipping(audio_data: np.ndarray, threshold: float = 0.95) -> bool:
    """Detect audio clipping in int16 data."""
    if audio_data.dtype != np.int16:
        return False
    
    max_val = 32767 * threshold
    min_val = -32768 * threshold
    
    clipped_samples = np.sum((audio_data >= max_val) | (audio_data <= min_val))
    clipping_ratio = clipped_samples / len(audio_data)
    
    return clipping_ratio > 0.01  # More than 1% clipped samples