"""Base transcription interface and shared types."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from ..whisper_integration import TranscriptionResult
from ..config import TranscriptionConfig


class TranscriptionClient(ABC):
    """Abstract base class for transcription clients."""
    
    def __init__(self, config: TranscriptionConfig, api_key: str):
        self.config = config
        self.api_key = api_key
    
    @abstractmethod
    async def transcribe_batch(self, batch) -> TranscriptionResult:
        """Transcribe an audio batch.
        
        Args:
            batch: Audio batch to transcribe
            
        Returns:
            TranscriptionResult containing transcribed text and metadata
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get transcription statistics.
        
        Returns:
            Dictionary containing statistics about transcription performance
        """
        pass