"""SoundDevice backend for cross-platform audio capture."""

import asyncio
import time
from typing import Optional, List, Dict
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from .base import AudioBackend, AudioBackendConfig, AudioChunk, AudioBackendType


class SoundDeviceBackend(AudioBackend):
    """SoundDevice backend for cross-platform audio capture with better latency."""
    
    def __init__(self, config: AudioBackendConfig):
        super().__init__(config)
        self.stream: Optional['sd.InputStream'] = None
        self.device_id: Optional[int] = None
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue(maxsize=100)
    
    @property
    def backend_type(self) -> AudioBackendType:
        return AudioBackendType.SOUNDDEVICE
    
    @property
    def name(self) -> str:
        return "SoundDevice Backend"
    
    async def is_available(self) -> bool:
        """Check if sounddevice is available."""
        return sd is not None
    
    async def get_devices(self) -> List[Dict]:
        """Get list of available audio devices."""
        devices = []
        
        if sd is None:
            return devices
        
        try:
            # Query devices
            device_list = sd.query_devices()
            
            for idx, device in enumerate(device_list):
                # Only include input devices
                if device['max_input_channels'] > 0:
                    name = device['name']
                    
                    # Determine device type
                    device_type = "source"
                    if '.monitor' in name.lower() or 'monitor of' in name.lower():
                        device_type = "monitor"
                    
                    devices.append({
                        "id": str(idx),
                        "name": name,
                        "type": device_type,
                        "channels": device['max_input_channels'],
                        "sample_rate": int(device['default_samplerate']),
                        "hostapi": device['hostapi']
                    })
        
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
        
        # Fallback to default input
        try:
            default_input = sd.default.device[0]
            if default_input is not None:
                return default_input
        except:
            pass
        
        # Fallback to any input device
        if devices:
            return int(devices[0]["id"])
        
        return None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Sounddevice callback for audio data."""
        if status:
            print(f"SoundDevice status: {status}")
        
        try:
            # Copy data (indata is a view)
            audio_data = indata[:, 0].copy() if indata.shape[1] > 1 else indata.flatten().copy()
            
            # Convert to int16 if needed
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Create AudioChunk
            timestamp = time.time()
            duration = len(audio_data) / self.config.sample_rate
            
            chunk = AudioChunk(
                data=audio_data,
                timestamp=timestamp,
                sample_rate=self.config.sample_rate,
                channels=1,  # We convert to mono
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
    
    async def start_capture(self) -> None:
        """Start audio capture."""
        if self._is_capturing:
            return
        
        if sd is None:
            raise RuntimeError("sounddevice not available")
        
        # Find device
        if self.config.device_name:
            # Find device by name
            devices = await self.get_devices()
            for device in devices:
                if self.config.device_name in device["name"]:
                    self.device_id = int(device["id"])
                    break
        else:
            # Auto-select monitor device
            self.device_id = await self._find_monitor_device()
        
        if self.device_id is None:
            raise RuntimeError("No suitable audio device found")
        
        # Set latency based on config
        latency = self.get_latency_hint()
        
        # Create input stream
        self.stream = sd.InputStream(
            device=self.device_id,
            channels=self.config.channels,
            samplerate=self.config.sample_rate,
            blocksize=self.config.chunk_size,
            dtype='int16',
            latency=latency,
            callback=self._audio_callback
        )
        
        self._is_capturing = True
        self._start_time = time.time()
        self.stream.start()
    
    async def stop_capture(self) -> None:
        """Stop audio capture."""
        self._is_capturing = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
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