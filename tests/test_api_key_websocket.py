"""Test cases for WebSocket API key management protocol."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
import websockets

from src.livetranscripts.live_qa import MessageType, WebSocketHandler


class TestAPIKeyWebSocketProtocol:
    """Test WebSocket protocol for API key management."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.remote_address = ("127.0.0.1", 12345)
        return mock_ws

    @pytest.fixture
    def mock_api_key_manager(self):
        """Create mock API key manager."""
        mock_manager = Mock()
        mock_manager.get_api_keys.return_value = {
            'openai_key': 'sk-test1234567890abcdefghijklmnopqrstuvwxyz',
            'gemini_key': 'AIzaSyD-test1234567890abcdefghijklmnopqr'
        }
        return mock_manager

    @pytest.fixture
    def websocket_handler(self, mock_api_key_manager):
        """Create WebSocket handler with API key manager."""
        session_manager = Mock()
        qa_handler = Mock()
        server = Mock()
        server.api_key_manager = mock_api_key_manager
        
        handler = WebSocketHandler(session_manager, qa_handler, server)
        handler.current_session_id = "test_session"
        return handler

    @pytest.mark.asyncio
    async def test_get_api_keys_message(self, websocket_handler, mock_websocket, mock_api_key_manager):
        """Test handling GET_API_KEYS message."""
        # Mock the manager to return masked keys
        mock_api_key_manager.get_api_keys.return_value = {
            'openai_key': 'sk-...vwxyz',
            'gemini_key': 'AIza...nopqr'
        }
        
        # Send GET_API_KEYS message
        message = {
            "type": "get_api_keys"
        }
        
        # Process message
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should call get_api_keys with masked=True
        mock_api_key_manager.get_api_keys.assert_called_once_with(masked=True)
        
        # Should send response
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "api_keys"
        assert sent_data["openai_key"] == "sk-...vwxyz"
        assert sent_data["gemini_key"] == "AIza...nopqr"

    @pytest.mark.asyncio
    async def test_set_api_keys_valid(self, websocket_handler, mock_websocket, mock_api_key_manager):
        """Test handling SET_API_KEYS message with valid keys."""
        # Send SET_API_KEYS message
        message = {
            "type": "set_api_keys",
            "openai_key": "sk-new1234567890abcdefghijklmnopqrstuvwxyz",
            "gemini_key": "AIzaSyD-new1234567890abcdefghijklmnopqrs"
        }
        
        # Process message
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should call set_api_keys
        mock_api_key_manager.set_api_keys.assert_called_once_with(
            openai_key="sk-new1234567890abcdefghijklmnopqrstuvwxyz",
            gemini_key="AIzaSyD-new1234567890abcdefghijklmnopqrs"
        )
        
        # Should call reload_environment
        mock_api_key_manager.reload_environment.assert_called_once()
        
        # Should send success response
        mock_websocket.send.assert_called()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "api_keys_updated"
        assert sent_data["success"] is True
        assert "API keys updated successfully" in sent_data["message"]

    @pytest.mark.asyncio
    async def test_set_api_keys_invalid(self, websocket_handler, mock_websocket, mock_api_key_manager):
        """Test handling SET_API_KEYS message with invalid keys."""
        from src.livetranscripts.api_key_manager import APIKeyValidationError
        
        # Mock validation error
        mock_api_key_manager.set_api_keys.side_effect = APIKeyValidationError("Invalid OpenAI API key format")
        
        # Send SET_API_KEYS message with invalid key
        message = {
            "type": "set_api_keys",
            "openai_key": "invalid-key",
            "gemini_key": ""
        }
        
        # Process message
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should send error response
        mock_websocket.send.assert_called()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "api_keys_updated"
        assert sent_data["success"] is False
        assert "Invalid OpenAI API key format" in sent_data["message"]

    @pytest.mark.asyncio
    async def test_set_partial_api_keys(self, websocket_handler, mock_websocket, mock_api_key_manager):
        """Test setting only one API key."""
        # Send message with only OpenAI key
        message = {
            "type": "set_api_keys",
            "openai_key": "sk-partial1234567890abcdefghijklmnopqrstuv",
            "gemini_key": ""
        }
        
        # Process message
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should call set_api_keys with both values
        mock_api_key_manager.set_api_keys.assert_called_once_with(
            openai_key="sk-partial1234567890abcdefghijklmnopqrstuv",
            gemini_key=""
        )

    @pytest.mark.asyncio
    async def test_clear_api_keys(self, websocket_handler, mock_websocket, mock_api_key_manager):
        """Test clearing API keys."""
        # Send message with empty keys
        message = {
            "type": "set_api_keys",
            "openai_key": "",
            "gemini_key": ""
        }
        
        # Process message
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should call set_api_keys with empty values
        mock_api_key_manager.set_api_keys.assert_called_once_with(
            openai_key="",
            gemini_key=""
        )
        
        # Should still reload environment
        mock_api_key_manager.reload_environment.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_keys_on_connection(self, mock_websocket, mock_api_key_manager):
        """Test that API keys status is sent on connection."""
        # Create handler
        session_manager = Mock()
        session_manager.create_session.return_value = "new_session"
        qa_handler = Mock()
        server = Mock()
        server.api_key_manager = mock_api_key_manager
        
        handler = WebSocketHandler(session_manager, qa_handler, server)
        
        # Mock get_api_keys to return keys
        mock_api_key_manager.get_api_keys.return_value = {
            'openai_key': 'sk-...vwxyz',
            'gemini_key': 'AIza...nopqr'
        }
        
        # Simulate connection and immediate close
        mock_websocket.recv.side_effect = websockets.exceptions.ConnectionClosed(None, None)
        
        # Handle connection
        await handler.handle_connection(mock_websocket)
        
        # Should have sent API keys status
        sent_messages = [json.loads(call[0][0]) for call in mock_websocket.send.call_args_list]
        
        # Find API keys message
        api_keys_msg = next((msg for msg in sent_messages if msg.get("type") == "api_keys_status"), None)
        assert api_keys_msg is not None
        assert api_keys_msg["has_openai_key"] is True
        assert api_keys_msg["has_gemini_key"] is True

    @pytest.mark.asyncio
    async def test_unauthorized_api_key_access(self, websocket_handler, mock_websocket):
        """Test that non-admin users cannot access API key functions."""
        # For MVP, we'll allow all users. In production, add admin check here.
        # This test is a placeholder for future authorization
        
        message = {
            "type": "get_api_keys"
        }
        
        # Should work for now (no auth in MVP)
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should have sent response (not error)
        mock_websocket.send.assert_called()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["type"] == "api_keys"

    def test_message_type_enum_includes_api_keys(self):
        """Test that MessageType enum includes API key message types."""
        # These should be added to the MessageType enum
        assert hasattr(MessageType, 'GET_API_KEYS')
        assert hasattr(MessageType, 'SET_API_KEYS')
        assert hasattr(MessageType, 'API_KEYS')
        assert hasattr(MessageType, 'API_KEYS_UPDATED')
        assert hasattr(MessageType, 'API_KEYS_STATUS')