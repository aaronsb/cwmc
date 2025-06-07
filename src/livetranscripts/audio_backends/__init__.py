"""Audio backend abstraction layer for Live Transcripts.

This module provides a unified interface for different audio capture backends,
allowing the system to use the best available option on each platform.
"""

from .base import AudioBackend, AudioBackendConfig, AudioChunk, AudioBackendType
from .registry import (
    AudioBackendRegistry, 
    get_best_backend,
    get_backend_by_type,
    register_backend,
    get_available_backends
)

__all__ = [
    "AudioBackend",
    "AudioBackendConfig", 
    "AudioChunk",
    "AudioBackendType",
    "AudioBackendRegistry",
    "get_best_backend",
    "get_backend_by_type",
    "register_backend",
    "get_available_backends",
]