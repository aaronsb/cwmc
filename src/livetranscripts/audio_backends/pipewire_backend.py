"""PipeWire audio backend for Linux systems."""

import asyncio
import subprocess
import json
import time
from typing import Optional, List, Dict
import numpy as np

from .base import AudioBackend, AudioBackendConfig, AudioChunk, AudioBackendType


class PipeWireBackend(AudioBackend):
    """PipeWire audio backend using pw-record for low-latency capture."""
    
    def __init__(self, config: AudioBackendConfig):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._capture_task: Optional[asyncio.Task] = None
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue(maxsize=100)
        self._monitor_source: Optional[str] = None
    
    @property
    def backend_type(self) -> AudioBackendType:
        return AudioBackendType.PIPEWIRE
    
    @property
    def name(self) -> str:
        return "PipeWire Audio Backend"
    
    async def is_available(self) -> bool:
        """Check if PipeWire is available."""
        try:
            # Check if pw-cli is available
            result = await asyncio.create_subprocess_exec(
                "pw-cli", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False
    
    async def get_devices(self) -> List[Dict]:
        """Get list of available audio devices from PipeWire."""
        devices = []
        
        try:
            # Use pw-dump to get all nodes
            result = await asyncio.create_subprocess_exec(
                "pw-dump",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                nodes = json.loads(stdout.decode())
                
                for node in nodes:
                    # Look for audio sinks and their monitors
                    if node.get("type") == "PipeWire:Interface:Node":
                        props = node.get("info", {}).get("props", {})
                        
                        # Check if it's an audio sink monitor
                        if (props.get("media.class") == "Audio/Source" and 
                            ".monitor" in props.get("node.name", "")):
                            
                            devices.append({
                                "id": props.get("node.name"),
                                "name": props.get("node.description", props.get("node.name")),
                                "type": "monitor",
                                "node_id": node.get("id")
                            })
                        
                        # Also include regular audio sources
                        elif props.get("media.class") == "Audio/Source":
                            devices.append({
                                "id": props.get("node.name"),
                                "name": props.get("node.description", props.get("node.name")),
                                "type": "source",
                                "node_id": node.get("id")
                            })
            
        except Exception:
            pass
        
        return devices
    
    async def _find_default_monitor(self) -> Optional[str]:
        """Find the default audio output monitor."""
        try:
            # Get default sink name using pactl (PipeWire provides PulseAudio compatibility)
            result = await asyncio.create_subprocess_exec(
                "pactl", "get-default-sink",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                default_sink = stdout.decode().strip()
                # Monitor source is typically sink_name.monitor
                return f"{default_sink}.monitor"
            
        except Exception:
            pass
        
        # Fallback: try to find any monitor
        devices = await self.get_devices()
        monitors = [d for d in devices if d["type"] == "monitor"]
        
        if monitors:
            return monitors[0]["id"]
        
        return None
    
    async def start_capture(self) -> None:
        """Start audio capture using pw-record."""
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
        
        # Build pw-record command
        cmd = [
            "pw-record",
            "--target", self._monitor_source,
            "--rate", str(self.config.sample_rate),
            "--channels", str(self.config.channels),
            "--format", "s16",  # 16-bit signed integer
            "--latency", f"{int(self.get_latency_hint() * 1000)}ms",
            "-"  # Output to stdout
        ]
        
        # Start pw-record process
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
        """Read audio data from pw-record process."""
        if not self._process or not self._process.stdout:
            return
        
        bytes_per_sample = 2  # 16-bit = 2 bytes
        chunk_bytes = self.config.chunk_size * self.config.channels * bytes_per_sample
        
        try:
            while self._is_capturing and self._process.returncode is None:
                # Read chunk of audio data
                data = await self._process.stdout.read(chunk_bytes)
                
                if not data:
                    break
                
                # Convert to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)
                
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
                
                # Put in queue (drop if full)
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