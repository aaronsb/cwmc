"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
import numpy as np
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.livetranscripts.batching import AudioBatch, BatchingConfig
from src.livetranscripts.whisper_integration import TranscriptionResult, TranscriptionSegment
from src.livetranscripts.gemini_integration import GeminiConfig, ContextManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for testing."""
    # Generate 1 second of 16kHz audio (speech-like pattern)
    duration = 1.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    
    # Create a more realistic audio pattern (sine wave with noise)
    t = np.linspace(0, duration, samples)
    frequency = 440  # A4 note
    signal = np.sin(2 * np.pi * frequency * t)
    noise = np.random.normal(0, 0.1, samples)
    audio = ((signal + noise) * 16384).astype(np.int16)
    
    return audio


@pytest.fixture
def sample_audio_batch(sample_audio_data):
    """Create a sample audio batch for testing."""
    return AudioBatch(
        audio_data=sample_audio_data,
        timestamp=datetime.now(),
        duration=1.0,
        sequence_id=1
    )


@pytest.fixture
def sample_transcription_result():
    """Create a sample transcription result for testing."""
    segments = [
        TranscriptionSegment("Hello", 0.0, 1.0, 0.95),
        TranscriptionSegment("world", 1.0, 2.0, 0.90),
        TranscriptionSegment("this is a test", 2.0, 4.0, 0.88)
    ]
    
    return TranscriptionResult(
        text="Hello world this is a test",
        segments=segments,
        language="en",
        duration=4.0,
        batch_id=1,
        timestamp=datetime.now()
    )


@pytest.fixture
def batching_config():
    """Create a standard batching configuration for testing."""
    return BatchingConfig(
        min_batch_duration=3.0,
        max_batch_duration=30.0,
        silence_threshold=500,
        sample_rate=16000,
        overlap_duration=0.5
    )


@pytest.fixture
def gemini_config():
    """Create a standard Gemini configuration for testing."""
    return GeminiConfig(
        model="gemini-1.5-flash",
        temperature=0.3,
        max_tokens=2048,
        context_window_minutes=5,
        insight_interval_seconds=60
    )


@pytest.fixture
def context_manager(gemini_config):
    """Create a context manager for testing."""
    return ContextManager(gemini_config)


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for Whisper API testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "Mock transcription result"
    mock_response.segments = [
        Mock(text="Mock", start=0.0, end=1.0),
        Mock(text="transcription", start=1.0, end=2.5),
        Mock(text="result", start=2.5, end=3.0)
    ]
    mock_response.language = "en"
    
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "Mock Gemini response"
    mock_client.generate_content_async = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def silence_audio():
    """Generate silence audio for testing."""
    duration = 1.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    # Very quiet audio (background noise level)
    return np.random.randint(-50, 50, samples, dtype=np.int16)


@pytest.fixture
def speech_audio():
    """Generate speech-like audio for testing."""
    duration = 1.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    # Louder audio simulating speech
    return np.random.randint(-12000, 12000, samples, dtype=np.int16)


@pytest.fixture
def meeting_transcripts():
    """Create a series of meeting transcripts for testing."""
    return [
        TranscriptionResult(
            "Good morning everyone, let's start today's meeting",
            [TranscriptionSegment("Good morning everyone, let's start today's meeting", 0.0, 3.0, 0.92)],
            "en", 3.0, 1, datetime.now()
        ),
        TranscriptionResult(
            "First agenda item is the quarterly budget review",
            [TranscriptionSegment("First agenda item is the quarterly budget review", 0.0, 3.5, 0.88)],
            "en", 3.5, 2, datetime.now()
        ),
        TranscriptionResult(
            "We've exceeded our targets by fifteen percent this quarter",
            [TranscriptionSegment("We've exceeded our targets by fifteen percent this quarter", 0.0, 4.0, 0.95)],
            "en", 4.0, 3, datetime.now()
        ),
        TranscriptionResult(
            "John will prepare the detailed analysis by Friday",
            [TranscriptionSegment("John will prepare the detailed analysis by Friday", 0.0, 3.2, 0.90)],
            "en", 3.2, 4, datetime.now()
        ),
        TranscriptionResult(
            "Any questions before we move to the next item?",
            [TranscriptionSegment("Any questions before we move to the next item?", 0.0, 2.8, 0.87)],
            "en", 2.8, 5, datetime.now()
        )
    ]


@pytest.fixture
def async_mock():
    """Create an AsyncMock for testing async functions."""
    return AsyncMock()


# Pytest markers for different test categories
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests") 
    config.addinivalue_line("markers", "slow: Slow tests that may take longer to run")
    config.addinivalue_line("markers", "api: Tests that require API access")
    config.addinivalue_line("markers", "audio: Tests involving audio processing")


# Async test utilities
class AsyncTestHelper:
    """Helper class for async testing."""
    
    @staticmethod
    async def run_with_timeout(coro, timeout=5.0):
        """Run coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)
    
    @staticmethod
    async def collect_async_results(async_generator, max_items=10):
        """Collect results from async generator."""
        results = []
        async for item in async_generator:
            results.append(item)
            if len(results) >= max_items:
                break
        return results


@pytest.fixture
def async_helper():
    """Provide async test helper."""
    return AsyncTestHelper()


# Mock environment variables for testing
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key")
    monkeypatch.setenv("TESTING", "true")


# Audio test utilities
class AudioTestUtils:
    """Utilities for audio testing."""
    
    @staticmethod
    def generate_tone(frequency, duration, sample_rate=16000, amplitude=0.5):
        """Generate a pure tone for testing."""
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples)
        tone = amplitude * np.sin(2 * np.pi * frequency * t)
        return (tone * 32767).astype(np.int16)
    
    @staticmethod
    def add_noise(audio, noise_level=0.1):
        """Add noise to audio signal."""
        noise = np.random.normal(0, noise_level, len(audio))
        noisy = audio + (noise * 32767).astype(np.int16)
        return np.clip(noisy, -32768, 32767).astype(np.int16)
    
    @staticmethod
    def calculate_rms(audio):
        """Calculate RMS energy of audio signal."""
        return np.sqrt(np.mean(audio.astype(np.float64) ** 2))


@pytest.fixture
def audio_utils():
    """Provide audio test utilities."""
    return AudioTestUtils()