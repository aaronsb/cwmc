"""PulseAudio backend for systems without PipeWire."""

import asyncio
import subprocess
import time
from typing import Optional, List, Dict
import numpy as np

from .base import AudioBackend, AudioBackendConfig, AudioChunk, AudioBackendType


class PulseAudioBackend(AudioBackend):
    """PulseAudio backend using parec for audio capture."""
    
    def __init__(self, config: AudioBackendConfig):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._capture_task: Optional[asyncio.Task] = None
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue(maxsize=100)
        self._monitor_source: Optional[str] = None
    
    @property
    def backend_type(self) -> AudioBackendType:
        return AudioBackendType.PULSEAUDIO
    
    @property
    def name(self) -> str:
        return "PulseAudio Backend"
    
    async def is_available(self) -> bool:
        """Check if PulseAudio is available."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pactl", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            return result.returncode == 0 and b"Server Name" in stdout
        except (FileNotFoundError, OSError):
            return False
    
    async def get_devices(self) -> List[Dict]:
        """Get list of available audio sources from PulseAudio."""
        devices = []
        
        try:
            # List all sources
            result = await asyncio.create_subprocess_exec(
                "pactl", "list", "sources", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                for line in lines:
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            source_id = parts[0]
                            source_name = parts[1]
                            
                            # Get more info about the source
                            is_monitor = ".monitor" in source_name
                            
                            devices.append({
                                "id": source_name,
                                "name": source_name,
                                "type": "monitor" if is_monitor else "source",
                                "index": source_id
                            })
            
        except Exception:
            pass
        
        return devices
    
    async def _find_default_monitor(self) -> Optional[str]:
        """Find the default audio output monitor."""
        try:
            # Get default sink monitor
            result = await asyncio.create_subprocess_exec(
                "pactl", "get-default-sink",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                default_sink = stdout.decode().strip()
                return f"{default_sink}.monitor"
            
        except Exception:
            pass
        
        # Fallback: find any monitor
        devices = await self.get_devices()
        monitors = [d for d in devices if d["type"] == "monitor"]
        
        if monitors:
            return monitors[0]["id"]
        
        return None
    
    async def start_capture(self) -> None:
        """Start audio capture using parec."""
        if self._is_capturing:
            return
        
        # Find monitor source if not specified
        if not self._monitor_source:
            if self.config.device_name:
                self._monitor_source = self.config.device_name
            else:
                self._monitor_source = await self._find_default_monitor()
        
        if not self._monitor_source:
            raise RuntimeError("No audio monitor source found")
        
        # Build parec command
        format_map = {
            "int16": "s16le",
            "float32": "float32le"
        }
        audio_format = format_map.get(self.config.format, "s16le")
        
        cmd = [
            "parec",
            "--device", self._monitor_source,
            "--rate", str(self.config.sample_rate),
            "--channels", str(self.config.channels),
            "--format", audio_format,
            "--latency-msec", str(int(self.get_latency_hint() * 1000))
        ]
        
        # Start parec process
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        self._is_capturing = True
        self._start_time = time.time()
        
        # Start capture task
        self._capture_task = asyncio.create_task(self._capture_loop())
    
    async def _capture_loop(self) -> None:
        """Read audio data from parec process."""
        if not self._process or not self._process.stdout:
            return
        
        bytes_per_sample = 2 if self.config.format == "int16" else 4
        chunk_bytes = self.config.chunk_size * self.config.channels * bytes_per_sample
        
        try:
            while self._is_capturing and self._process.returncode is None:
                # Read chunk of audio data
                data = await self._process.stdout.read(chunk_bytes)
                
                if not data:
                    break
                
                # Convert to numpy array
                dtype = np.int16 if self.config.format == "int16" else np.float32
                audio_data = np.frombuffer(data, dtype=dtype)
                
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
                
                # Put in queue
                try:
                    self._audio_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    # Drop oldest chunk
                    try:
                        self._audio_queue.get_nowait()
                        self._audio_queue.put_nowait(chunk)
                    except asyncio.QueueEmpty:
                        pass
        
        except Exception as e:
            if self._error_callback:
                self._error_callback(e)
    
    async def stop_capture(self) -> None:
        """Stop audio capture."""
        self._is_capturing = False
        
        # Stop the process
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None
        
        # Cancel capture task
        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None
        
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