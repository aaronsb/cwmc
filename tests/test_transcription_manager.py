"""Test cases for enhanced transcription manager with model fallback."""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.livetranscripts.batching import AudioBatch
from src.livetranscripts.config import TranscriptionConfig


class TestTranscriptionManagerFallback:
    """Test fallback mechanism in transcription manager."""

    @pytest.mark.asyncio
    async def test_fallback_on_primary_model_failure(self):
        """Test that manager falls back to secondary model on primary failure."""
        from src.livetranscripts.transcription import TranscriptionManager
        
        config = TranscriptionConfig(
            transcription_model="gpt-4o-transcribe",
            model_fallback=["whisper-1"]
        )
        
        manager = TranscriptionManager(config, api_key="test_key")
        
        # Create test batch
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=datetime.now(),
            duration=1.0,
            sequence_id=1
        )
        
        # Mock primary client to fail, secondary to succeed
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            # First call (GPT-4o) fails
            mock_client.audio.transcriptions.create.side_effect = [
                Exception("GPT-4o service unavailable"),
                Mock(text="Fallback success", segments=[], language="en")
            ]
            mock_openai.return_value = mock_client
            
            result = await manager.transcribe_batch_with_fallback(batch)
            
            # Should succeed with fallback
            assert result.text == "Fallback success"
            # Should have made 2 API calls (primary + fallback)
            assert mock_client.audio.transcriptions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_no_fallback_when_primary_succeeds(self):
        """Test that fallback is not used when primary model succeeds."""
        from src.livetranscripts.transcription import TranscriptionManager
        
        config = TranscriptionConfig(
            transcription_model="gpt-4o-transcribe",
            model_fallback=["whisper-1"]
        )
        
        manager = TranscriptionManager(config, api_key="test_key")
        
        # Create test batch
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=datetime.now(),
            duration=1.0,
            sequence_id=1
        )
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            # Primary succeeds immediately
            mock_client.audio.transcriptions.create.return_value = Mock(
                text="Primary success", segments=[], language="en"
            )
            mock_openai.return_value = mock_client
            
            result = await manager.transcribe_batch_with_fallback(batch)
            
            # Should succeed with primary
            assert result.text == "Primary success"
            # Should have made only 1 API call
            assert mock_client.audio.transcriptions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_fallback_models(self):
        """Test fallback through multiple models."""
        from src.livetranscripts.transcription import TranscriptionManager
        
        config = TranscriptionConfig(
            transcription_model="gpt-4o-transcribe",
            model_fallback=["gpt-4o-mini-transcribe", "whisper-1"]
        )
        
        manager = TranscriptionManager(config, api_key="test_key")
        
        # Create test batch
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=datetime.now(),
            duration=1.0,
            sequence_id=1
        )
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            # First two fail, third succeeds
            mock_client.audio.transcriptions.create.side_effect = [
                Exception("GPT-4o unavailable"),
                Exception("GPT-4o-mini unavailable"),
                Mock(text="Final fallback success", segments=[], language="en")
            ]
            mock_openai.return_value = mock_client
            
            result = await manager.transcribe_batch_with_fallback(batch)
            
            # Should succeed with final fallback
            assert result.text == "Final fallback success"
            # Should have made 3 API calls (primary + 2 fallbacks)
            assert mock_client.audio.transcriptions.create.call_count == 3