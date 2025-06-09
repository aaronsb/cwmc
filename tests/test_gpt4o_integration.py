"""Test cases for GPT-4o transcription integration."""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import io

from src.livetranscripts.batching import AudioBatch


class TestGPT4oConfig:
    """Test GPT-4o configuration support."""

    def test_transcription_config_supports_gpt4o(self):
        """Test that TranscriptionConfig supports GPT-4o model selection."""
        from src.livetranscripts.config import TranscriptionConfig
        
        config = TranscriptionConfig(
            transcription_model="gpt-4o-transcribe",
            model_fallback=["gpt-4o-mini-transcribe", "whisper-1"]
        )
        
        assert config.transcription_model == "gpt-4o-transcribe"
        assert config.model_fallback == ["gpt-4o-mini-transcribe", "whisper-1"]

    def test_transcription_config_validates_models(self):
        """Test that TranscriptionConfig validates supported models."""
        from src.livetranscripts.config import TranscriptionConfig
        
        # Valid models should work
        valid_models = ["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"]
        for model in valid_models:
            config = TranscriptionConfig(transcription_model=model)
            assert config.transcription_model == model
        
        # Invalid model should raise error
        with pytest.raises(ValueError, match="Unsupported transcription model"):
            TranscriptionConfig(transcription_model="invalid-model")


class TestGPT4oClient:
    """Test GPT-4o transcription client."""

    def test_gpt4o_client_creation(self):
        """Test creating a GPT-4o client."""
        from src.livetranscripts.transcription import GPT4oClient, TranscriptionConfig
        
        config = TranscriptionConfig(transcription_model="gpt-4o-transcribe")
        client = GPT4oClient(config, api_key="test_key")
        
        assert client.config.transcription_model == "gpt-4o-transcribe"
        assert client.client is not None

    def test_gpt4o_client_interface_compatibility(self):
        """Test that GPT4oClient has same interface as WhisperClient."""
        from src.livetranscripts.transcription import GPT4oClient, TranscriptionConfig
        from src.livetranscripts.whisper_integration import WhisperClient, WhisperConfig
        
        # Both clients should have the same public methods
        gpt4o_config = TranscriptionConfig(transcription_model="gpt-4o-transcribe")
        gpt4o_client = GPT4oClient(gpt4o_config, api_key="test_key")
        
        whisper_config = WhisperConfig()
        whisper_client = WhisperClient(whisper_config, api_key="test_key")
        
        # Check key methods exist
        assert hasattr(gpt4o_client, 'transcribe_batch')
        assert hasattr(gpt4o_client, 'get_statistics')
        assert hasattr(whisper_client, 'transcribe_batch')
        assert hasattr(whisper_client, 'get_statistics')

    @pytest.mark.asyncio
    async def test_gpt4o_transcribe_batch(self):
        """Test GPT-4o batch transcription."""
        from src.livetranscripts.transcription import GPT4oClient, TranscriptionConfig
        from src.livetranscripts.whisper_integration import TranscriptionResult
        
        config = TranscriptionConfig(transcription_model="gpt-4o-transcribe")
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "Hello world from GPT-4o"
            mock_response.segments = [
                Mock(text="Hello world from GPT-4o", start=0.0, end=2.0)
            ]
            mock_response.language = "en"
            
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            client = GPT4oClient(config, api_key="test_key")
            
            # Create test audio batch
            audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
            batch = AudioBatch(
                audio_data=audio_data,
                timestamp=datetime.now(),
                duration=1.0,
                sequence_id=1
            )
            
            result = await client.transcribe_batch(batch)
            
            assert isinstance(result, TranscriptionResult)
            assert result.text == "Hello world from GPT-4o"
            assert result.batch_id == 1
            mock_client.audio.transcriptions.create.assert_called_once()


class TestTranscriptionRegistry:
    """Test transcription model registry."""

    def test_registry_creation(self):
        """Test creating a transcription registry."""
        from src.livetranscripts.transcription import TranscriptionRegistry
        
        registry = TranscriptionRegistry()
        assert registry is not None

    def test_register_and_get_client(self):
        """Test registering and retrieving transcription clients."""
        from src.livetranscripts.transcription import TranscriptionRegistry, GPT4oClient
        from src.livetranscripts.whisper_integration import WhisperClient
        
        registry = TranscriptionRegistry()
        
        # Register clients
        registry.register_client("gpt-4o-transcribe", GPT4oClient)
        registry.register_client("whisper-1", WhisperClient)
        
        # Retrieve clients
        gpt4o_class = registry.get_client_class("gpt-4o-transcribe")
        whisper_class = registry.get_client_class("whisper-1")
        
        assert gpt4o_class == GPT4oClient
        assert whisper_class == WhisperClient

    def test_get_supported_models(self):
        """Test getting list of supported models."""
        from src.livetranscripts.transcription import TranscriptionRegistry, GPT4oClient
        from src.livetranscripts.whisper_integration import WhisperClient
        
        registry = TranscriptionRegistry()
        registry.register_client("gpt-4o-transcribe", GPT4oClient)
        registry.register_client("whisper-1", WhisperClient)
        
        models = registry.get_supported_models()
        assert "gpt-4o-transcribe" in models
        assert "whisper-1" in models