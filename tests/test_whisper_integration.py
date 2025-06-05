"""Test cases for Whisper API integration."""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import io
import wave
from src.livetranscripts.whisper_integration import (
    WhisperClient,
    WhisperConfig,
    TranscriptionResult,
    TranscriptionSegment,
    AudioProcessor,
    RetryManager,
)
from src.livetranscripts.batching import AudioBatch


class TestWhisperConfig:
    """Test Whisper configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WhisperConfig()
        assert config.model == "whisper-1"
        assert config.language is None
        assert config.temperature == 0.0
        assert config.max_retries == 3
        assert config.timeout == 30.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = WhisperConfig(
            model="whisper-1",
            language="en",
            temperature=0.2,
            max_retries=5,
            timeout=60.0
        )
        assert config.model == "whisper-1"
        assert config.language == "en"
        assert config.temperature == 0.2
        assert config.max_retries == 5
        assert config.timeout == 60.0

    def test_invalid_config(self):
        """Test invalid configuration values."""
        with pytest.raises(ValueError, match="Temperature must be between 0 and 1"):
            WhisperConfig(temperature=1.5)
        
        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            WhisperConfig(max_retries=-1)


class TestTranscriptionSegment:
    """Test transcription segment data structure."""

    def test_segment_creation(self):
        """Test creating a transcription segment."""
        segment = TranscriptionSegment(
            text="Hello world",
            start_time=0.0,
            end_time=2.5,
            confidence=0.95
        )
        
        assert segment.text == "Hello world"
        assert segment.start_time == 0.0
        assert segment.end_time == 2.5
        assert segment.confidence == 0.95
        assert segment.duration == 2.5

    def test_segment_validation(self):
        """Test segment validation."""
        # Valid segment
        valid_segment = TranscriptionSegment(
            text="Valid text",
            start_time=0.0,
            end_time=1.0,
            confidence=0.9
        )
        assert valid_segment.is_valid() is True
        
        # Invalid timing
        invalid_timing = TranscriptionSegment(
            text="Invalid",
            start_time=2.0,
            end_time=1.0,  # End before start
            confidence=0.9
        )
        assert invalid_timing.is_valid() is False
        
        # Empty text
        empty_text = TranscriptionSegment(
            text="",
            start_time=0.0,
            end_time=1.0,
            confidence=0.9
        )
        assert empty_text.is_valid() is False


class TestTranscriptionResult:
    """Test transcription result data structure."""

    def test_result_creation(self):
        """Test creating a transcription result."""
        segments = [
            TranscriptionSegment("Hello", 0.0, 1.0, 0.95),
            TranscriptionSegment("world", 1.0, 2.0, 0.90)
        ]
        
        result = TranscriptionResult(
            text="Hello world",
            segments=segments,
            language="en",
            duration=2.0,
            batch_id=1
        )
        
        assert result.text == "Hello world"
        assert len(result.segments) == 2
        assert result.language == "en"
        assert result.duration == 2.0
        assert result.batch_id == 1

    def test_result_aggregation(self):
        """Test aggregating multiple results."""
        result1 = TranscriptionResult(
            text="First part",
            segments=[TranscriptionSegment("First part", 0.0, 1.0, 0.95)],
            language="en",
            duration=1.0,
            batch_id=1
        )
        
        result2 = TranscriptionResult(
            text="Second part",
            segments=[TranscriptionSegment("Second part", 1.0, 2.0, 0.90)],
            language="en",
            duration=1.0,
            batch_id=2
        )
        
        combined = TranscriptionResult.combine([result1, result2])
        
        assert combined.text == "First part Second part"
        assert len(combined.segments) == 2
        assert combined.duration == 2.0

    def test_confidence_calculation(self):
        """Test average confidence calculation."""
        segments = [
            TranscriptionSegment("First", 0.0, 1.0, 0.9),
            TranscriptionSegment("Second", 1.0, 2.0, 0.8),
            TranscriptionSegment("Third", 2.0, 3.0, 1.0)
        ]
        
        result = TranscriptionResult(
            text="First Second Third",
            segments=segments,
            language="en",
            duration=3.0,
            batch_id=1
        )
        
        expected_confidence = (0.9 + 0.8 + 1.0) / 3
        assert abs(result.average_confidence - expected_confidence) < 0.001


class TestAudioProcessor:
    """Test audio processing utilities."""

    def test_audio_to_wav_bytes(self):
        """Test converting audio array to WAV bytes."""
        # Generate test audio
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)  # 1 second
        
        wav_bytes = AudioProcessor.audio_to_wav_bytes(audio_data, sample_rate=16000)
        
        assert isinstance(wav_bytes, bytes)
        assert len(wav_bytes) > 0
        
        # Verify it's a valid WAV file
        with io.BytesIO(wav_bytes) as wav_io:
            with wave.open(wav_io, 'rb') as wav_file:
                assert wav_file.getframerate() == 16000
                assert wav_file.getnchannels() == 1
                assert wav_file.getsampwidth() == 2  # 16-bit
                assert wav_file.getnframes() == 16000

    def test_normalize_audio(self):
        """Test audio normalization."""
        # Test with clipped audio
        clipped_audio = np.array([-32768, -32768, 32767, 32767], dtype=np.int16)
        normalized = AudioProcessor.normalize_audio(clipped_audio)
        
        assert np.max(np.abs(normalized)) <= 32767
        assert normalized.dtype == np.int16
        
        # Test with normal audio (should be unchanged)
        normal_audio = np.array([-1000, 0, 1000], dtype=np.int16)
        normalized_normal = AudioProcessor.normalize_audio(normal_audio)
        np.testing.assert_array_equal(normal_audio, normalized_normal)

    def test_apply_audio_filters(self):
        """Test audio filtering."""
        # Generate noisy audio
        clean_signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000))  # 440Hz tone
        noise = np.random.normal(0, 0.1, 16000)
        noisy_audio = ((clean_signal + noise) * 16384).astype(np.int16)
        
        filtered = AudioProcessor.apply_filters(noisy_audio, sample_rate=16000)
        
        assert filtered.dtype == np.int16
        assert len(filtered) == len(noisy_audio)
        # Filtered audio should have less high-frequency noise
        assert np.std(filtered) <= np.std(noisy_audio)


class TestRetryManager:
    """Test retry management for API calls."""

    def test_retry_manager_creation(self):
        """Test creating a retry manager."""
        retry_manager = RetryManager(max_retries=3, base_delay=1.0)
        assert retry_manager.max_retries == 3
        assert retry_manager.base_delay == 1.0
        assert retry_manager.current_attempt == 0

    def test_should_retry_logic(self):
        """Test retry decision logic."""
        retry_manager = RetryManager(max_retries=3)
        
        # Should retry for first few attempts
        assert retry_manager.should_retry() is True
        retry_manager.current_attempt = 1
        assert retry_manager.should_retry() is True
        retry_manager.current_attempt = 2
        assert retry_manager.should_retry() is True
        
        # Should not retry after max attempts
        retry_manager.current_attempt = 3
        assert retry_manager.should_retry() is False

    def test_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        retry_manager = RetryManager(max_retries=3, base_delay=1.0)
        
        # First retry
        retry_manager.current_attempt = 1
        delay1 = retry_manager.get_delay()
        assert delay1 == 1.0
        
        # Second retry (exponential backoff)
        retry_manager.current_attempt = 2
        delay2 = retry_manager.get_delay()
        assert delay2 == 2.0
        
        # Third retry
        retry_manager.current_attempt = 3
        delay3 = retry_manager.get_delay()
        assert delay3 == 4.0

    @pytest.mark.asyncio
    async def test_async_retry_decorator(self):
        """Test async retry decorator functionality."""
        call_count = 0
        
        @RetryManager.async_retry(max_retries=3, base_delay=0.1)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "Success"
        
        result = await failing_function()
        assert result == "Success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test behavior when retries are exhausted."""
        @RetryManager.async_retry(max_retries=2, base_delay=0.1)
        async def always_failing():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            await always_failing()


class TestWhisperClient:
    """Test the main Whisper client."""

    @pytest.fixture
    def whisper_config(self):
        """Create Whisper configuration."""
        return WhisperConfig(
            model="whisper-1",
            language="en",
            max_retries=3,
            timeout=30.0
        )

    @pytest.fixture
    def mock_openai_client(self):
        """Create mock OpenAI client."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Hello world"
        mock_response.segments = [
            Mock(text="Hello", start=0.0, end=1.0),
            Mock(text="world", start=1.0, end=2.0)
        ]
        mock_response.language = "en"
        
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
        return mock_client

    @pytest.fixture
    def whisper_client(self, whisper_config, mock_openai_client):
        """Create WhisperClient with mocked dependencies."""
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            client = WhisperClient(whisper_config, api_key="test_key")
            client.client = mock_openai_client
            return client

    def test_client_initialization(self, whisper_client, whisper_config):
        """Test Whisper client initialization."""
        assert whisper_client.config == whisper_config
        assert whisper_client.client is not None

    @pytest.mark.asyncio
    async def test_transcribe_batch_success(self, whisper_client, mock_openai_client):
        """Test successful batch transcription."""
        # Create test audio batch
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=datetime.now(),
            duration=1.0,
            sequence_id=1
        )
        
        result = await whisper_client.transcribe_batch(batch)
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert len(result.segments) == 2
        assert result.batch_id == 1
        mock_openai_client.audio.transcriptions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_batch_with_retry(self, whisper_client, mock_openai_client):
        """Test batch transcription with retry on failure."""
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=datetime.now(),
            duration=1.0,
            sequence_id=1
        )
        
        # First call fails, second succeeds
        mock_openai_client.audio.transcriptions.create.side_effect = [
            Exception("API Error"),
            Mock(text="Retry success", segments=[], language="en")
        ]
        
        result = await whisper_client.transcribe_batch(batch)
        
        assert result.text == "Retry success"
        assert mock_openai_client.audio.transcriptions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_transcribe_batch_failure(self, whisper_client, mock_openai_client):
        """Test batch transcription with persistent failure."""
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=datetime.now(),
            duration=1.0,
            sequence_id=1
        )
        
        # Always fail
        mock_openai_client.audio.transcriptions.create.side_effect = Exception("Persistent error")
        
        with pytest.raises(Exception, match="Persistent error"):
            await whisper_client.transcribe_batch(batch)

    def test_format_request_parameters(self, whisper_client):
        """Test request parameter formatting."""
        params = whisper_client._format_request_parameters()
        
        assert params["model"] == "whisper-1"
        assert params["language"] == "en"
        assert params["temperature"] == 0.0
        assert params["response_format"] == "verbose_json"

    @pytest.mark.asyncio
    async def test_concurrent_transcriptions(self, whisper_client, mock_openai_client):
        """Test concurrent batch transcriptions."""
        # Create multiple batches
        batches = []
        for i in range(3):
            audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
            batch = AudioBatch(
                audio_data=audio_data,
                timestamp=datetime.now(),
                duration=1.0,
                sequence_id=i
            )
            batches.append(batch)
        
        # Mock different responses for each batch
        mock_responses = [
            Mock(text=f"Batch {i}", segments=[], language="en")
            for i in range(3)
        ]
        mock_openai_client.audio.transcriptions.create.side_effect = mock_responses
        
        # Transcribe concurrently
        tasks = [whisper_client.transcribe_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.text == f"Batch {i}"
            assert result.batch_id == i

    def test_audio_preprocessing(self, whisper_client):
        """Test audio preprocessing before transcription."""
        # Test with various audio conditions
        
        # Normal audio
        normal_audio = np.random.randint(-16000, 16000, 16000, dtype=np.int16)
        processed_normal = whisper_client._preprocess_audio(normal_audio)
        assert processed_normal.dtype == np.int16
        assert len(processed_normal) == len(normal_audio)
        
        # Silent audio
        silent_audio = np.zeros(16000, dtype=np.int16)
        processed_silent = whisper_client._preprocess_audio(silent_audio)
        assert len(processed_silent) == len(silent_audio)
        
        # Clipped audio
        clipped_audio = np.full(16000, 32767, dtype=np.int16)
        processed_clipped = whisper_client._preprocess_audio(clipped_audio)
        assert np.max(processed_clipped) <= 32767


class TestWhisperIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def integration_client(self):
        """Create client for integration testing."""
        config = WhisperConfig(
            model="whisper-1",
            language="en",
            max_retries=2,
            timeout=15.0
        )
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            client = WhisperClient(config, api_key="test_key")
            client.client = mock_client
            return client, mock_client

    @pytest.mark.asyncio
    async def test_meeting_transcription_flow(self, integration_client):
        """Test end-to-end meeting transcription flow."""
        client, mock_client = integration_client
        
        # Simulate meeting audio batches
        meeting_phrases = [
            "Good morning everyone",
            "Let's start with the agenda",
            "First item is the budget review",
            "Any questions so far?"
        ]
        
        # Mock responses for each batch
        mock_responses = []
        for i, phrase in enumerate(meeting_phrases):
            mock_response = Mock()
            mock_response.text = phrase
            mock_response.segments = [Mock(text=phrase, start=0.0, end=2.0)]
            mock_response.language = "en"
            mock_responses.append(mock_response)
        
        mock_client.audio.transcriptions.create.side_effect = mock_responses
        
        # Create and transcribe batches
        results = []
        for i, phrase in enumerate(meeting_phrases):
            audio_data = np.random.randint(-16000, 16000, 32000, dtype=np.int16)  # 2 seconds
            batch = AudioBatch(
                audio_data=audio_data,
                timestamp=datetime.now(),
                duration=2.0,
                sequence_id=i
            )
            
            result = await client.transcribe_batch(batch)
            results.append(result)
        
        # Verify results
        assert len(results) == 4
        for i, result in enumerate(results):
            assert result.text == meeting_phrases[i]
            assert result.batch_id == i
            assert result.language == "en"
        
        # Test combining results
        combined = TranscriptionResult.combine(results)
        expected_text = " ".join(meeting_phrases)
        assert combined.text == expected_text

    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, integration_client):
        """Test error recovery in transcription pipeline."""
        client, mock_client = integration_client
        
        # Simulate intermittent API failures
        responses = [
            Exception("Rate limit exceeded"),  # First batch fails
            Mock(text="Second batch success", segments=[], language="en"),  # Second succeeds
            Exception("Temporary server error"),  # Third fails
            Mock(text="Fourth batch success", segments=[], language="en"),  # Fourth succeeds
        ]
        
        mock_client.audio.transcriptions.create.side_effect = responses
        
        # Create batches
        batches = []
        for i in range(4):
            audio_data = np.random.randint(-16000, 16000, 16000, dtype=np.int16)
            batch = AudioBatch(
                audio_data=audio_data,
                timestamp=datetime.now(),
                duration=1.0,
                sequence_id=i
            )
            batches.append(batch)
        
        # Transcribe with error handling
        successful_results = []
        failed_batches = []
        
        for batch in batches:
            try:
                result = await client.transcribe_batch(batch)
                successful_results.append(result)
            except Exception:
                failed_batches.append(batch)
        
        # Should have 2 successful results and 2 failed batches
        assert len(successful_results) == 2
        assert len(failed_batches) == 2
        
        # Successful results should have correct content
        assert successful_results[0].text == "Second batch success"
        assert successful_results[1].text == "Fourth batch success"