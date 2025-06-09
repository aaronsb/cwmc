"""Transcription model registry for managing different transcription clients."""

from typing import Dict, Type, List
from .base import TranscriptionClient


class TranscriptionRegistry:
    """Registry for transcription client classes."""
    
    def __init__(self):
        self._clients: Dict[str, Type[TranscriptionClient]] = {}
    
    def register_client(self, model_name: str, client_class: Type[TranscriptionClient]) -> None:
        """Register a transcription client class for a model.
        
        Args:
            model_name: The model identifier (e.g., 'gpt-4o-transcribe', 'whisper-1')
            client_class: The client class that can handle this model
        """
        self._clients[model_name] = client_class
    
    def get_client_class(self, model_name: str) -> Type[TranscriptionClient]:
        """Get the client class for a model.
        
        Args:
            model_name: The model identifier
            
        Returns:
            The client class for the model
            
        Raises:
            KeyError: If the model is not registered
        """
        if model_name not in self._clients:
            raise KeyError(f"No client registered for model: {model_name}")
        return self._clients[model_name]
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported model names.
        
        Returns:
            List of registered model names
        """
        return list(self._clients.keys())
    
    def is_model_supported(self, model_name: str) -> bool:
        """Check if a model is supported.
        
        Args:
            model_name: The model identifier
            
        Returns:
            True if the model is registered, False otherwise
        """
        return model_name in self._clients