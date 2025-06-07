"""Registry for audio backends with automatic selection."""

import platform
import asyncio
from typing import Optional, Type, Dict, List
from .base import AudioBackend, AudioBackendConfig, AudioBackendType


class AudioBackendRegistry:
    """Registry for managing audio backends."""
    
    def __init__(self):
        self._backends: Dict[AudioBackendType, Type[AudioBackend]] = {}
        self._priority_map = self._get_platform_priorities()
    
    def register(self, backend_type: AudioBackendType, backend_class: Type[AudioBackend]) -> None:
        """Register a new audio backend."""
        self._backends[backend_type] = backend_class
    
    def _get_platform_priorities(self) -> List[AudioBackendType]:
        """Get backend priorities for current platform."""
        system = platform.system()
        
        if system == "Linux":
            return [
                AudioBackendType.PIPEWIRE,
                AudioBackendType.PULSEAUDIO,
                AudioBackendType.JACK,
                AudioBackendType.SOUNDDEVICE,
                AudioBackendType.PYAUDIO,
                AudioBackendType.ALSA,
            ]
        elif system == "Darwin":  # macOS
            return [
                AudioBackendType.BLACKHOLE,
                AudioBackendType.COREAUDIO,
                AudioBackendType.SOUNDDEVICE,
                AudioBackendType.PYAUDIO,
            ]
        elif system == "Windows":
            return [
                AudioBackendType.WASAPI,
                AudioBackendType.SOUNDDEVICE,
                AudioBackendType.PYAUDIO,
            ]
        else:
            # Fallback for unknown systems
            return [
                AudioBackendType.SOUNDDEVICE,
                AudioBackendType.PYAUDIO,
            ]
    
    async def get_available_backends(self) -> List[tuple[AudioBackendType, Type[AudioBackend]]]:
        """Get list of available backends in priority order."""
        available = []
        
        for backend_type in self._priority_map:
            if backend_type in self._backends:
                backend_class = self._backends[backend_type]
                try:
                    # Test if backend is available
                    test_backend = backend_class(AudioBackendConfig())
                    if await test_backend.is_available():
                        available.append((backend_type, backend_class))
                except Exception:
                    # Backend not available or failed to initialize
                    continue
        
        return available
    
    async def get_best_backend(self, config: Optional[AudioBackendConfig] = None) -> Optional[AudioBackend]:
        """Get the best available backend for the current platform."""
        if config is None:
            config = AudioBackendConfig()
        
        available = await self.get_available_backends()
        
        if not available:
            return None
        
        # Return instance of the highest priority available backend
        backend_type, backend_class = available[0]
        return backend_class(config)
    
    def get_backend_by_type(self, backend_type: AudioBackendType, config: Optional[AudioBackendConfig] = None) -> Optional[AudioBackend]:
        """Get a specific backend by type."""
        if backend_type not in self._backends:
            return None
        
        if config is None:
            config = AudioBackendConfig()
        
        backend_class = self._backends[backend_type]
        return backend_class(config)


# Global registry instance
_registry = AudioBackendRegistry()


def register_backend(backend_type: AudioBackendType, backend_class: Type[AudioBackend]) -> None:
    """Register a backend with the global registry."""
    _registry.register(backend_type, backend_class)


async def get_best_backend(config: Optional[AudioBackendConfig] = None) -> Optional[AudioBackend]:
    """Get the best available backend for the current platform."""
    return await _registry.get_best_backend(config)


async def get_available_backends() -> List[tuple[AudioBackendType, Type[AudioBackend]]]:
    """Get list of available backends."""
    return await _registry.get_available_backends()


def get_backend_by_type(backend_type: AudioBackendType, config: Optional[AudioBackendConfig] = None) -> Optional[AudioBackend]:
    """Get a specific backend by type."""
    return _registry.get_backend_by_type(backend_type, config)