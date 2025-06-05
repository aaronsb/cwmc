"""Test cases for VAD-based audio batching system."""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from src.livetranscripts.batching import (
    AudioBatch,
    BatchingConfig,
    VADAudioBatcher,
    SilenceDetector,
    BatchQueue,
)


class TestAudioBatch:
    """Test AudioBatch data structure."""

    def test_audio_batch_creation(self):
        """Test creating an AudioBatch."""
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        timestamp = datetime.now()
        
        batch = AudioBatch(
            audio_data=audio_data,
            timestamp=timestamp,
            duration=1.0,
            sequence_id=1
        )
        
        assert np.array_equal(batch.audio_data, audio_data)
        assert batch.timestamp == timestamp
        assert batch.duration == 1.0
        assert batch.sequence_id == 1
        assert batch.is_final is False

    def test_batch_size_calculation(self):
        """Test batch size calculation in bytes."""
        audio_data = np.random.randint(-32768, 32767, 1000, dtype=np.int16)
        batch = AudioBatch(audio_data=audio_data, timestamp=datetime.now())
        
        expected_size = 1000 * 2  # 1000 samples * 2 bytes per int16
        assert batch.size_bytes == expected_size

    def test_batch_validation(self):
        """Test batch data validation."""
        # Valid batch
        valid_data = np.random.randint(-32768, 32767, 1000, dtype=np.int16)
        batch = AudioBatch(audio_data=valid_data, timestamp=datetime.now())
        assert batch.is_valid() is True
        
        # Empty batch
        empty_batch = AudioBatch(audio_data=np.array([], dtype=np.int16), timestamp=datetime.now())
        assert empty_batch.is_valid() is False
        
        # Wrong dtype
        float_data = np.random.random(1000).astype(np.float32)
        float_batch = AudioBatch(audio_data=float_data, timestamp=datetime.now())
        assert float_batch.is_valid() is False


class TestBatchingConfig:
    """Test batching configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BatchingConfig()
        assert config.min_batch_duration == 3.0
        assert config.max_batch_duration == 30.0
        assert config.silence_threshold == 500  # ms
        assert config.sample_rate == 16000
        assert config.overlap_duration == 0.5

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BatchingConfig(
            min_batch_duration=5.0,
            max_batch_duration=20.0,
            silence_threshold=1000,
            overlap_duration=1.0
        )
        assert config.min_batch_duration == 5.0
        assert config.max_batch_duration == 20.0
        assert config.silence_threshold == 1000
        assert config.overlap_duration == 1.0

    def test_invalid_config(self):
        """Test invalid configuration values."""
        with pytest.raises(ValueError, match="min_batch_duration must be positive"):
            BatchingConfig(min_batch_duration=0)
        
        with pytest.raises(ValueError, match="max_batch_duration must be greater than min_batch_duration"):
            BatchingConfig(min_batch_duration=10, max_batch_duration=5)


class TestSilenceDetector:
    """Test silence detection functionality."""

    @pytest.fixture
    def silence_detector(self):
        """Create SilenceDetector instance."""
        config = BatchingConfig(silence_threshold=500, sample_rate=16000)
        return SilenceDetector(config)

    def test_silence_detection_quiet(self, silence_detector):
        """Test detection of silence in quiet audio."""
        # Generate quiet audio (noise floor)
        quiet_audio = np.random.randint(-100, 100, 8000, dtype=np.int16)  # 0.5 seconds
        
        is_silence = silence_detector.is_silence(quiet_audio)
        assert is_silence is True

    def test_silence_detection_loud(self, silence_detector):
        """Test detection of speech in loud audio."""
        # Generate loud audio (speech-like)
        loud_audio = np.random.randint(-16000, 16000, 8000, dtype=np.int16)  # 0.5 seconds
        
        is_silence = silence_detector.is_silence(loud_audio)
        assert is_silence is False

    def test_silence_duration_tracking(self, silence_detector):
        """Test tracking of silence duration."""
        quiet_audio = np.random.randint(-50, 50, 8000, dtype=np.int16)  # 0.5 seconds of quiet
        
        # First call should not trigger (need sustained silence)
        silence_detector.is_silence(quiet_audio)
        assert silence_detector.get_silence_duration() < 500
        
        # Second call should accumulate
        silence_detector.is_silence(quiet_audio)
        assert silence_detector.get_silence_duration() >= 500

    def test_silence_reset_on_speech(self, silence_detector):
        """Test silence duration reset when speech is detected."""
        quiet_audio = np.random.randint(-50, 50, 8000, dtype=np.int16)
        loud_audio = np.random.randint(-16000, 16000, 8000, dtype=np.int16)
        
        # Build up silence
        silence_detector.is_silence(quiet_audio)
        silence_detector.is_silence(quiet_audio)
        assert silence_detector.get_silence_duration() >= 500
        
        # Speech should reset
        silence_detector.is_silence(loud_audio)
        assert silence_detector.get_silence_duration() == 0

    def test_energy_calculation(self, silence_detector):
        """Test RMS energy calculation."""
        # High energy signal
        high_energy = np.full(1000, 16000, dtype=np.int16)
        energy_high = silence_detector._calculate_rms_energy(high_energy)
        
        # Low energy signal
        low_energy = np.full(1000, 100, dtype=np.int16)
        energy_low = silence_detector._calculate_rms_energy(low_energy)
        
        assert energy_high > energy_low
        assert energy_high > silence_detector.energy_threshold
        assert energy_low < silence_detector.energy_threshold


class TestBatchQueue:
    """Test the batch queue management."""

    @pytest.fixture
    def batch_queue(self):
        """Create BatchQueue instance."""
        return BatchQueue(max_size=10)

    def test_queue_operations(self, batch_queue):
        """Test basic queue operations."""
        audio_data = np.random.randint(-32768, 32767, 1000, dtype=np.int16)
        batch = AudioBatch(audio_data=audio_data, timestamp=datetime.now())
        
        # Test empty queue
        assert batch_queue.size() == 0
        assert batch_queue.is_empty() is True
        
        # Test adding batch
        batch_queue.put(batch)
        assert batch_queue.size() == 1
        assert batch_queue.is_empty() is False
        
        # Test getting batch
        retrieved_batch = batch_queue.get()
        assert retrieved_batch == batch
        assert batch_queue.size() == 0

    def test_queue_overflow(self, batch_queue):
        """Test queue overflow handling."""
        # Fill queue to capacity
        for i in range(10):
            audio_data = np.random.randint(-32768, 32767, 1000, dtype=np.int16)
            batch = AudioBatch(audio_data=audio_data, timestamp=datetime.now(), sequence_id=i)
            batch_queue.put(batch)
        
        assert batch_queue.size() == 10
        
        # Try to add one more (should drop oldest)
        overflow_batch = AudioBatch(
            audio_data=np.random.randint(-32768, 32767, 1000, dtype=np.int16),
            timestamp=datetime.now(),
            sequence_id=10
        )
        
        with pytest.warns(UserWarning, match="Batch queue overflow"):
            batch_queue.put(overflow_batch)
        
        assert batch_queue.size() == 10
        # First batch should be the one with sequence_id=1 (oldest was dropped)
        first_batch = batch_queue.get()
        assert first_batch.sequence_id == 1

    @pytest.mark.asyncio
    async def test_async_queue_operations(self, batch_queue):
        """Test asynchronous queue operations."""
        audio_data = np.random.randint(-32768, 32767, 1000, dtype=np.int16)
        batch = AudioBatch(audio_data=audio_data, timestamp=datetime.now())
        
        # Test async put/get
        await batch_queue.put_async(batch)
        assert batch_queue.size() == 1
        
        retrieved_batch = await batch_queue.get_async()
        assert retrieved_batch == batch
        assert batch_queue.size() == 0


class TestVADAudioBatcher:
    """Test the main VAD-based audio batcher."""

    @pytest.fixture
    def batcher_config(self):
        """Create batching configuration."""
        return BatchingConfig(
            min_batch_duration=3.0,
            max_batch_duration=10.0,
            silence_threshold=500,
            sample_rate=16000
        )

    @pytest.fixture
    def vad_batcher(self, batcher_config):
        """Create VADAudioBatcher instance."""
        return VADAudioBatcher(batcher_config)

    def test_batcher_initialization(self, vad_batcher, batcher_config):
        """Test batcher initialization."""
        assert vad_batcher.config == batcher_config
        assert vad_batcher.current_batch == []
        assert vad_batcher.sequence_id == 0
        assert vad_batcher.is_processing is False

    @pytest.mark.asyncio
    async def test_add_audio_chunk(self, vad_batcher):
        """Test adding audio chunks to batcher."""
        audio_chunk = np.random.randint(-32768, 32767, 8000, dtype=np.int16)  # 0.5 seconds
        
        # Add chunk - should not trigger batch yet (below min duration)
        batch = await vad_batcher.add_audio_chunk(audio_chunk)
        assert batch is None
        assert len(vad_batcher.current_batch) == 8000

    @pytest.mark.asyncio
    async def test_force_batch_on_max_duration(self, vad_batcher):
        """Test forced batching when max duration is reached."""
        # Add enough audio to exceed max duration (10 seconds = 160,000 samples)
        chunk_size = 16000  # 1 second chunks
        total_chunks = 11  # 11 seconds total
        
        batch = None
        for i in range(total_chunks):
            audio_chunk = np.random.randint(-100, 100, chunk_size, dtype=np.int16)  # Quiet audio
            batch = await vad_batcher.add_audio_chunk(audio_chunk)
            
            if batch is not None:
                break
        
        # Should have triggered a batch due to max duration
        assert batch is not None
        assert batch.duration >= vad_batcher.config.max_batch_duration

    @pytest.mark.asyncio
    async def test_silence_triggered_batch(self, vad_batcher):
        """Test batching triggered by silence detection."""
        # Add minimum duration of audio (speech-like)
        speech_chunks = []
        for i in range(4):  # 4 seconds of speech
            speech_chunk = np.random.randint(-16000, 16000, 16000, dtype=np.int16)
            speech_chunks.append(speech_chunk)
            await vad_batcher.add_audio_chunk(speech_chunk)
        
        # Add silence that should trigger batch
        silence_chunks = []
        batch = None
        for i in range(2):  # Add enough silence chunks to exceed threshold
            silence_chunk = np.random.randint(-50, 50, 8000, dtype=np.int16)  # 0.5 sec quiet
            silence_chunks.append(silence_chunk)
            batch = await vad_batcher.add_audio_chunk(silence_chunk)
            
            if batch is not None:
                break
        
        # Should have triggered a batch due to silence
        assert batch is not None
        assert batch.duration >= vad_batcher.config.min_batch_duration

    def test_calculate_overlap(self, vad_batcher):
        """Test overlap calculation between batches."""
        # Simulate previous batch
        previous_audio = np.random.randint(-32768, 32767, 32000, dtype=np.int16)  # 2 seconds
        vad_batcher.previous_batch_audio = previous_audio
        
        # Calculate overlap (should be 0.5 seconds = 8000 samples)
        overlap = vad_batcher._calculate_overlap()
        expected_samples = int(vad_batcher.config.overlap_duration * vad_batcher.config.sample_rate)
        
        assert len(overlap) == expected_samples
        np.testing.assert_array_equal(overlap, previous_audio[-expected_samples:])

    def test_sequence_id_increment(self, vad_batcher):
        """Test that sequence IDs increment correctly."""
        initial_id = vad_batcher.sequence_id
        
        # Create a batch
        audio_data = np.random.randint(-32768, 32767, 48000, dtype=np.int16)  # 3 seconds
        vad_batcher.current_batch = audio_data.tolist()
        vad_batcher.batch_start_time = datetime.now()
        
        batch = vad_batcher._create_batch()
        
        assert batch.sequence_id == initial_id
        assert vad_batcher.sequence_id == initial_id + 1

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, vad_batcher):
        """Test that batcher handles concurrent audio chunk additions."""
        async def add_chunks():
            batches = []
            for i in range(5):
                chunk = np.random.randint(-16000, 16000, 16000, dtype=np.int16)
                batch = await vad_batcher.add_audio_chunk(chunk)
                if batch:
                    batches.append(batch)
            return batches
        
        # Run multiple concurrent tasks
        tasks = [add_chunks() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Verify that processing occurred without race conditions
        all_batches = [batch for result in results for batch in result]
        sequence_ids = [batch.sequence_id for batch in all_batches]
        
        # Sequence IDs should be unique and incrementing
        assert len(sequence_ids) == len(set(sequence_ids))
        assert sequence_ids == sorted(sequence_ids)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def realistic_batcher(self):
        """Create batcher with realistic configuration."""
        config = BatchingConfig(
            min_batch_duration=3.0,
            max_batch_duration=30.0,
            silence_threshold=500,
            sample_rate=16000,
            overlap_duration=0.5
        )
        return VADAudioBatcher(config)

    @pytest.mark.asyncio
    async def test_meeting_scenario(self, realistic_batcher):
        """Test a realistic meeting scenario with speech and pauses."""
        batches = []
        
        # Simulate meeting audio pattern
        # 1. Initial silence (people joining)
        for _ in range(5):  # 2.5 seconds of silence
            silence = np.random.randint(-30, 30, 8000, dtype=np.int16)
            batch = await realistic_batcher.add_audio_chunk(silence)
            if batch:
                batches.append(batch)
        
        # 2. Speaker 1 talking (5 seconds)
        for _ in range(10):  # 5 seconds of speech
            speech = np.random.randint(-15000, 15000, 8000, dtype=np.int16)
            batch = await realistic_batcher.add_audio_chunk(speech)
            if batch:
                batches.append(batch)
        
        # 3. Brief pause
        for _ in range(2):  # 1 second pause
            pause = np.random.randint(-50, 50, 8000, dtype=np.int16)
            batch = await realistic_batcher.add_audio_chunk(pause)
            if batch:
                batches.append(batch)
        
        # 4. Speaker 2 talking (7 seconds)
        for _ in range(14):  # 7 seconds of speech
            speech = np.random.randint(-12000, 12000, 8000, dtype=np.int16)
            batch = await realistic_batcher.add_audio_chunk(speech)
            if batch:
                batches.append(batch)
        
        # 5. Longer pause (should trigger batch)
        for _ in range(3):  # 1.5 seconds pause
            pause = np.random.randint(-40, 40, 8000, dtype=np.int16)
            batch = await realistic_batcher.add_audio_chunk(pause)
            if batch:
                batches.append(batch)
        
        # Should have generated at least one batch
        assert len(batches) > 0
        
        # All batches should meet duration requirements
        for batch in batches:
            assert batch.duration >= realistic_batcher.config.min_batch_duration
            assert batch.duration <= realistic_batcher.config.max_batch_duration
            assert batch.is_valid()

    @pytest.mark.asyncio
    async def test_continuous_speech_scenario(self, realistic_batcher):
        """Test scenario with continuous speech (should batch on max duration)."""
        batches = []
        
        # Simulate 35 seconds of continuous speech (exceeds max duration)
        for i in range(70):  # 35 seconds of 0.5-second chunks
            speech = np.random.randint(-14000, 14000, 8000, dtype=np.int16)
            batch = await realistic_batcher.add_audio_chunk(speech)
            if batch:
                batches.append(batch)
        
        # Should have generated at least one batch due to max duration
        assert len(batches) > 0
        
        # First batch should be close to max duration
        first_batch = batches[0]
        assert first_batch.duration >= realistic_batcher.config.max_batch_duration - 1.0