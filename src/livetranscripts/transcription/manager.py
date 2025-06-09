"""Enhanced transcription manager with model fallback support."""

import asyncio
from typing import List, Optional, Dict, Any
import logging

from .registry import TranscriptionRegistry
from .gpt4o_client import GPT4oClient
from ..whisper_integration import WhisperClient, TranscriptionResult
from ..config import TranscriptionConfig

logger = logging.getLogger(__name__)


class TranscriptionManager:
    """Manages transcription with model fallback support."""
    
    def __init__(self, config: TranscriptionConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        self.registry = TranscriptionRegistry()
        self._setup_registry()
        self._clients: Dict[str, Any] = {}
        
    def _setup_registry(self) -> None:
        """Set up the transcription model registry."""
        # Register available models
        self.registry.register_client("gpt-4o-transcribe", GPT4oClient)
        self.registry.register_client("gpt-4o-mini-transcribe", GPT4oClient)
        self.registry.register_client("whisper-1", WhisperClient)
    
    def _get_client(self, model_name: str):
        """Get or create a client for the specified model."""
        if model_name not in self._clients:
            client_class = self.registry.get_client_class(model_name)
            
            # Create appropriate config for the client
            if model_name.startswith("gpt-4o"):
                # Use TranscriptionConfig for GPT-4o clients
                client_config = TranscriptionConfig(
                    transcription_model=model_name,
                    whisper_language=self.config.whisper_language,
                    api_timeout=self.config.api_timeout,
                    max_retries=self.config.max_retries,
                    retry_delay=self.config.retry_delay
                )
                self._clients[model_name] = client_class(client_config, self.api_key)
            else:
                # Use WhisperConfig for Whisper clients
                from ..whisper_integration import WhisperConfig
                whisper_config = WhisperConfig(
                    model=model_name,
                    language=self.config.whisper_language,
                    max_retries=self.config.max_retries,
                    timeout=self.config.api_timeout
                )
                self._clients[model_name] = client_class(whisper_config, self.api_key)
        
        return self._clients[model_name]
    
    async def transcribe_batch_with_fallback(self, batch) -> TranscriptionResult:
        """Transcribe batch with automatic fallback on failure."""
        models_to_try = [self.config.transcription_model] + self.config.model_fallback
        last_exception = None
        
        for model_name in models_to_try:
            try:
                logger.debug(f"Attempting transcription with {model_name}")
                client = self._get_client(model_name)
                result = await client.transcribe_batch(batch)
                logger.debug(f"Transcription successful with {model_name}")
                return result
                
            except Exception as e:
                logger.warning(f"Transcription failed with {model_name}: {e}")
                last_exception = e
                continue
        
        # If all models failed, raise the last exception
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("No transcription models available")
    
    async def transcribe_batch(self, batch) -> TranscriptionResult:
        """Transcribe batch using primary model only (backward compatibility)."""
        client = self._get_client(self.config.transcription_model)
        return await client.transcribe_batch(batch)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics from all clients."""
        stats = {
            'models_used': list(self._clients.keys()),
            'primary_model': self.config.transcription_model,
            'fallback_models': self.config.model_fallback,
            'client_stats': {}
        }
        
        for model_name, client in self._clients.items():
            stats['client_stats'][model_name] = client.get_statistics()
        
        return stats
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported transcription models."""
        return self.registry.get_supported_models()