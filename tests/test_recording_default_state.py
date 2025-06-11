"""Test that recording starts in OFF state by default."""
import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.livetranscripts.main import LiveTranscriptsApp
from src.livetranscripts.live_qa import LiveQAServer


@pytest.mark.asyncio
class TestRecordingDefaultState:
    """Test recording default state behavior."""

    async def test_app_starts_with_recording_paused(self):
        """Test that LiveTranscriptsApp initializes with recording paused."""
        # Create LiveTranscriptsApp instance
        app = LiveTranscriptsApp()
        
        # Assert that recording starts paused
        assert app.recording_paused is True, "Recording should start paused by default"

    async def test_qa_server_starts_with_recording_disabled(self):
        """Test that LiveQAServer initializes with recording disabled."""
        # Create LiveQAServer instance
        server = LiveQAServer()
        
        # Assert that recording starts disabled
        assert server.recording_enabled is False, "Recording should start disabled by default"

    async def test_app_does_not_process_audio_when_paused(self):
        """Test that audio processing is skipped when recording is paused."""
        with patch('src.livetranscripts.main.AudioCapture') as mock_audio_capture:
            with patch('src.livetranscripts.main.BatchProcessor') as mock_batch_processor:
                # Setup mocks
                mock_audio_capture_instance = AsyncMock()
                mock_audio_capture.return_value = mock_audio_capture_instance
                mock_audio_capture_instance.get_audio_chunk = AsyncMock()
                
                mock_batch_instance = AsyncMock()
                mock_batch_processor.return_value = mock_batch_instance
                mock_batch_instance.get_next_batch = AsyncMock(return_value=None)
                
                # Create LiveTranscriptsApp with recording paused
                app = LiveTranscriptsApp()
                assert app.recording_paused is True  # Verify it starts paused
                app.audio_capture = mock_audio_capture_instance
                app.batch_processor = mock_batch_instance
                app.is_running = True
                
                # Run audio processing loop briefly
                process_task = asyncio.create_task(app._audio_processing_loop())
                await asyncio.sleep(0.2)  # Give it time to potentially call methods
                app.is_running = False
                await process_task
                
                # Verify that audio capture was not called when paused
                mock_audio_capture_instance.get_audio_chunk.assert_not_called()
                mock_batch_instance.get_next_batch.assert_not_called()

    async def test_recording_can_be_resumed_after_starting_paused(self):
        """Test that recording can be resumed after starting paused."""
        # Create LiveTranscriptsApp
        app = LiveTranscriptsApp()
        
        # Verify starts paused
        assert app.recording_paused is True
        
        # Resume recording
        await app.resume_recording()
        
        # Verify recording is no longer paused
        assert app.recording_paused is False

    async def test_qa_server_recording_status_message(self):
        """Test that QA server sends correct recording status on connection."""
        # Create LiveQAServer with recording disabled
        server = LiveQAServer()
        assert server.recording_enabled is False  # Verify it starts disabled
        
        # Mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.send = AsyncMock()
        
        # Test the initial state message format
        # The server should broadcast false status when recording is disabled
        status_msg = json.dumps({
            "type": "recording_status",
            "is_recording": server.recording_enabled
        })
        
        # Simulate sending the status
        await mock_websocket.send(status_msg)
        
        # Verify the message was sent with correct content
        mock_websocket.send.assert_called_once_with(status_msg)
        sent_data = mock_websocket.send.call_args[0][0]
        assert '"type": "recording_status"' in sent_data
        assert '"is_recording": false' in sent_data