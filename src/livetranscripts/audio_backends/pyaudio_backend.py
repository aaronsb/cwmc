"""PyAudio backend for fallback audio capture."""

import asyncio
import time
import warnings
from typing import Optional, List, Dict
import numpy as np

try:
    import pyaudio
except ImportError:
    pyaudio = None

from .base import AudioBackend, AudioBackendConfig, AudioChunk, AudioBackendType


class PyAudioBackend(AudioBackend):
    """PyAudio backend for cross-platform audio capture."""
    
    def __init__(self, config: AudioBackendConfig):
        super().__init__(config)
        self.pa: Optional['pyaudio.PyAudio'] = None
        self.stream = None
        self.device_index: Optional[int] = None
        self._capture_task: Optional[asyncio.Task] = None
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue(maxsize=100)
    
    @property
    def backend_type(self) -> AudioBackendType:
        return AudioBackendType.PYAUDIO
    
    @property
    def name(self) -> str:
        return "PyAudio Backend"
    
    async def is_available(self) -> bool:
        """Check if PyAudio is available."""
        if pyaudio is None:
            return False
        
        try:
            # Suppress ALSA warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pa = pyaudio.PyAudio()
                pa.terminate()
            return True
        except Exception:
            return False
    
    async def get_devices(self) -> List[Dict]:
        """Get list of available audio devices."""
        devices = []
        
        if pyaudio is None:
            return devices
        
        try:
            # Suppress ALSA warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                if not self.pa:
                    self.pa = pyaudio.PyAudio()
                
                for i in range(self.pa.get_device_count()):
                    try:
                        device_info = self.pa.get_device_info_by_index(i)
                        
                        # Only include input devices
                        if device_info.get('maxInputChannels', 0) > 0:
                            name = device_info.get('name', '')
                            
                            # Determine device type
                            device_type = "source"
                            if '.monitor' in name.lower() or 'loopback' in name.lower():
                                device_type = "monitor"
                            
                            devices.append({
                                "id": str(i),
                                "name": name,
                                "type": device_type,
                                "channels": device_info.get('maxInputChannels', 0),
                                "sample_rate": int(device_info.get('defaultSampleRate', 0))
                            })
                    except Exception:
                        continue
        
        except Exception:
            pass
        
        return devices
    
    async def _find_monitor_device(self) -> Optional[int]:
        """Find a suitable monitor/loopback device."""
        devices = await self.get_devices()
        
        # Prefer monitor devices
        monitors = [d for d in devices if d["type"] == "monitor"]
        if monitors:
            return int(monitors[0]["id"])
        
        # Fallback to any input device
        if devices:
            return int(devices[0]["id"])
        
        return None
    
    async def start_capture(self) -> None:
        """Start audio capture."""
        if self._is_capturing:
            return
        
        if pyaudio is None:
            raise RuntimeError("PyAudio not available")
        
        # Initialize PyAudio
        if not self.pa:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.pa = pyaudio.PyAudio()
        
        # Find device
        if self.config.device_name:
            # Find device by name
            devices = await self.get_devices()
            for device in devices:
                if self.config.device_name in device["name"]:
                    self.device_index = int(device["id"])
                    break
        else:
            # Auto-select monitor device
            self.device_index = await self._find_monitor_device()
        
        if self.device_index is None:
            raise RuntimeError("No suitable audio device found")
        
        # Get device info
        device_info = self.pa.get_device_info_by_index(self.device_index)
        
        # Open stream with device's native sample rate if possible
        device_rate = int(device_info.get('defaultSampleRate', self.config.sample_rate))
        
        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback
            )
        except Exception:
            # Try with device's native rate
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=device_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback
            )
        
        self._is_capturing = True
        self._start_time = time.time()
        self.stream.start_stream()
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for audio data."""
        if status:
            print(f"PyAudio status: {status}")
        
        try:
            # Convert to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Create AudioChunk
            timestamp = time.time()
            duration = len(audio_data) / (self.config.sample_rate * self.config.channels)
            
            chunk = AudioChunk(
                data=audio_data,
                timestamp=timestamp,
                sample_rate=self.config.sample_rate,
                channels=self.config.channels,
                duration=duration
            )
            
            # Put in queue (non-blocking)
            try:
                self._audio_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                # Drop oldest chunk
                try:
                    self._audio_queue.get_nowait()
                    self._audio_queue.put_nowait(chunk)
                except:
                    pass
        
        except Exception as e:
            if self._error_callback:
                self._error_callback(e)
        
        return (None, pyaudio.paContinue)
    
    async def stop_capture(self) -> None:
        """Stop audio capture."""
        self._is_capturing = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self.pa:
            self.pa.terminate()
            self.pa = None
        
        # Clear queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    async def get_audio_chunk(self) -> AudioChunk:
        """Get next audio chunk from the queue."""
        if not self._is_capturing:
            raise RuntimeError("Audio capture not started")
        
        # Wait for audio chunk with timeout
        try:
            chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=1.0)
            return chunk
        except asyncio.TimeoutError:
            raise RuntimeError("No audio data available")