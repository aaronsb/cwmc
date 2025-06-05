"""Test cases for audio capture functionality."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.livetranscripts.audio_capture import (
    AudioCapture,
    AudioCaptureConfig,
    PlatformAudioCapture,
    MacOSAudioCapture,
    WindowsAudioCapture,
    LinuxAudioCapture,
)


class TestAudioCaptureConfig:
    """Test audio capture configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AudioCaptureConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.format == "int16"
        assert config.chunk_size == 1024
        assert config.buffer_duration == 10.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AudioCaptureConfig(
            sample_rate=44100,
            channels=2,
            chunk_size=2048,
            buffer_duration=5.0
        )
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.chunk_size == 2048
        assert config.buffer_duration == 5.0

    def test_invalid_sample_rate(self):
        """Test that invalid sample rates raise ValueError."""
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            AudioCaptureConfig(sample_rate=0)

    def test_invalid_channels(self):
        """Test that invalid channel counts raise ValueError."""
        with pytest.raises(ValueError, match="Channels must be 1 or 2"):
            AudioCaptureConfig(channels=3)


class TestAudioCapture:
    """Test the main AudioCapture class."""

    @pytest.fixture
    def mock_platform_capture(self):
        """Create a mock platform-specific audio capture."""
        mock = Mock(spec=PlatformAudioCapture)
        mock.is_available.return_value = True
        mock.start_capture = Mock()
        mock.stop_capture = Mock()
        mock.get_audio_chunk = Mock(return_value=np.zeros(1024, dtype=np.int16))
        return mock

    @pytest.fixture
    def audio_capture(self, mock_platform_capture):
        """Create AudioCapture instance with mocked platform capture."""
        with patch('src.livetranscripts.audio_capture.get_platform_capture') as mock_get:
            mock_get.return_value = mock_platform_capture
            capture = AudioCapture()
            return capture

    def test_initialization(self, audio_capture, mock_platform_capture):
        """Test AudioCapture initialization."""
        assert audio_capture.config.sample_rate == 16000
        assert audio_capture.is_capturing is False
        mock_platform_capture.is_available.assert_called_once()

    def test_start_capture(self, audio_capture, mock_platform_capture):
        """Test starting audio capture."""
        audio_capture.start_capture()
        assert audio_capture.is_capturing is True
        mock_platform_capture.start_capture.assert_called_once()

    def test_stop_capture(self, audio_capture, mock_platform_capture):
        """Test stopping audio capture."""
        audio_capture.start_capture()
        audio_capture.stop_capture()
        assert audio_capture.is_capturing is False
        mock_platform_capture.stop_capture.assert_called_once()

    def test_get_audio_data(self, audio_capture, mock_platform_capture):
        """Test getting audio data."""
        test_data = np.random.randint(-32768, 32767, 1024, dtype=np.int16)
        mock_platform_capture.get_audio_chunk.return_value = test_data
        
        audio_capture.start_capture()
        data = audio_capture.get_audio_data()
        
        assert isinstance(data, np.ndarray)
        assert data.dtype == np.int16
        assert len(data) == 1024
        np.testing.assert_array_equal(data, test_data)

    def test_context_manager(self, audio_capture, mock_platform_capture):
        """Test using AudioCapture as context manager."""
        with audio_capture as capture:
            assert capture.is_capturing is True
            mock_platform_capture.start_capture.assert_called_once()
        
        assert audio_capture.is_capturing is False
        mock_platform_capture.stop_capture.assert_called_once()

    def test_buffer_overflow_handling(self, audio_capture, mock_platform_capture):
        """Test handling of audio buffer overflow."""
        audio_capture.start_capture()
        
        # Simulate buffer overflow
        mock_platform_capture.get_audio_chunk.side_effect = BufferError("Buffer overflow")
        
        with pytest.warns(UserWarning, match="Audio buffer overflow"):
            data = audio_capture.get_audio_data()
            assert data is None


class TestPlatformDetection:
    """Test platform-specific audio capture detection."""

    @patch('platform.system')
    def test_macos_detection(self, mock_system):
        """Test macOS platform detection."""
        mock_system.return_value = "Darwin"
        from src.livetranscripts.audio_capture import get_platform_capture
        
        with patch('src.livetranscripts.audio_capture.MacOSAudioCapture') as mock_macos:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_macos.return_value = mock_instance
            
            capture = get_platform_capture()
            assert isinstance(capture, type(mock_instance))

    @patch('platform.system')
    def test_windows_detection(self, mock_system):
        """Test Windows platform detection."""
        mock_system.return_value = "Windows"
        from src.livetranscripts.audio_capture import get_platform_capture
        
        with patch('src.livetranscripts.audio_capture.WindowsAudioCapture') as mock_windows:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_windows.return_value = mock_instance
            
            capture = get_platform_capture()
            assert isinstance(capture, type(mock_instance))

    @patch('platform.system')
    def test_linux_detection(self, mock_system):
        """Test Linux platform detection."""
        mock_system.return_value = "Linux"
        from src.livetranscripts.audio_capture import get_platform_capture
        
        with patch('src.livetranscripts.audio_capture.LinuxAudioCapture') as mock_linux:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_linux.return_value = mock_instance
            
            capture = get_platform_capture()
            assert isinstance(capture, type(mock_instance))

    @patch('platform.system')
    def test_unsupported_platform(self, mock_system):
        """Test handling of unsupported platforms."""
        mock_system.return_value = "FreeBSD"
        from src.livetranscripts.audio_capture import get_platform_capture
        
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            get_platform_capture()


class TestMacOSAudioCapture:
    """Test macOS-specific audio capture."""

    @pytest.fixture
    def macos_capture(self):
        """Create MacOSAudioCapture instance with mocked dependencies."""
        with patch('pyaudiowpatch.PyAudio') as mock_pyaudio:
            mock_pa_instance = Mock()
            mock_pyaudio.return_value = mock_pa_instance
            mock_pa_instance.get_device_count.return_value = 2
            mock_pa_instance.get_device_info_by_index.side_effect = [
                {"name": "Built-in Microphone", "maxInputChannels": 2},
                {"name": "BlackHole 2ch", "maxInputChannels": 2}
            ]
            
            capture = MacOSAudioCapture()
            capture.pa = mock_pa_instance
            return capture

    def test_find_loopback_device(self, macos_capture):
        """Test finding BlackHole loopback device."""
        device_index = macos_capture._find_loopback_device()
        assert device_index == 1  # BlackHole device

    def test_no_loopback_device(self, macos_capture):
        """Test handling when no loopback device is found."""
        macos_capture.pa.get_device_info_by_index.side_effect = [
            {"name": "Built-in Microphone", "maxInputChannels": 2},
            {"name": "Built-in Speaker", "maxInputChannels": 0}
        ]
        
        with pytest.raises(RuntimeError, match="No loopback audio device found"):
            macos_capture._find_loopback_device()

    def test_is_available(self, macos_capture):
        """Test availability check."""
        assert macos_capture.is_available() is True

    @patch('pyaudiowpatch.PyAudio')
    def test_unavailable_when_no_pyaudio(self, mock_pyaudio):
        """Test unavailable when PyAudio is not available."""
        mock_pyaudio.side_effect = ImportError("No module named pyaudiowpatch")
        
        capture = MacOSAudioCapture()
        assert capture.is_available() is False


class TestAudioDataValidation:
    """Test audio data validation and processing."""

    def test_normalize_audio_data(self):
        """Test audio data normalization."""
        from src.livetranscripts.audio_capture import normalize_audio_data
        
        # Test int16 data
        int16_data = np.array([-32768, 0, 32767], dtype=np.int16)
        normalized = normalize_audio_data(int16_data)
        expected = np.array([-1.0, 0.0, 0.999969482421875], dtype=np.float32)
        np.testing.assert_array_almost_equal(normalized, expected, decimal=5)

    def test_validate_audio_format(self):
        """Test audio format validation."""
        from src.livetranscripts.audio_capture import validate_audio_format
        
        # Valid data
        valid_data = np.random.randint(-32768, 32767, 1024, dtype=np.int16)
        assert validate_audio_format(valid_data, expected_length=1024) is True
        
        # Invalid length
        assert validate_audio_format(valid_data, expected_length=512) is False
        
        # Invalid dtype
        float_data = valid_data.astype(np.float32)
        assert validate_audio_format(float_data, expected_dtype=np.int16) is False

    def test_detect_audio_clipping(self):
        """Test audio clipping detection."""
        from src.livetranscripts.audio_capture import detect_clipping
        
        # No clipping
        normal_data = np.random.randint(-16384, 16383, 1000, dtype=np.int16)
        assert detect_clipping(normal_data) is False
        
        # With clipping
        clipped_data = np.array([-32768, -32768, 32767, 32767] * 250, dtype=np.int16)
        assert detect_clipping(clipped_data) is True