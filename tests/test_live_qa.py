"""Test cases for live Q&A handler and WebSocket integration."""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import websockets
from src.livetranscripts.live_qa import (
    LiveQAServer,
    WebSocketHandler,
    QASession,
    QARequest,
    QAResponse,
    SessionManager,
    MessageType,
    ConnectionState,
)
from src.livetranscripts.gemini_integration import QAHandler, GeminiConfig, ContextManager


class TestQARequest:
    """Test Q&A request data structure."""

    def test_request_creation(self):
        """Test creating a Q&A request."""
        request = QARequest(
            question="What was discussed about the budget?",
            session_id="session_123",
            timestamp=datetime.now(),
            request_id="req_456"
        )
        
        assert request.question == "What was discussed about the budget?"
        assert request.session_id == "session_123"
        assert request.request_id == "req_456"
        assert isinstance(request.timestamp, datetime)

    def test_request_validation(self):
        """Test request validation."""
        # Valid request
        valid_request = QARequest(
            question="Valid question?",
            session_id="valid_session",
            timestamp=datetime.now(),
            request_id="req_1"
        )
        assert valid_request.is_valid() is True
        
        # Empty question
        empty_question = QARequest(
            question="",
            session_id="session",
            timestamp=datetime.now(),
            request_id="req_2"
        )
        assert empty_question.is_valid() is False
        
        # Missing session ID
        no_session = QARequest(
            question="Test?",
            session_id="",
            timestamp=datetime.now(),
            request_id="req_3"
        )
        assert no_session.is_valid() is False

    def test_request_serialization(self):
        """Test request JSON serialization."""
        timestamp = datetime.now()
        request = QARequest(
            question="Test question?",
            session_id="session_123",
            timestamp=timestamp,
            request_id="req_456"
        )
        
        json_data = request.to_dict()
        
        assert json_data["question"] == "Test question?"
        assert json_data["session_id"] == "session_123"
        assert json_data["request_id"] == "req_456"
        assert "timestamp" in json_data

    def test_request_deserialization(self):
        """Test creating request from JSON data."""
        data = {
            "question": "Deserialized question?",
            "session_id": "session_789",
            "request_id": "req_101",
            "timestamp": "2025-06-05T10:30:00"
        }
        
        request = QARequest.from_dict(data)
        
        assert request.question == "Deserialized question?"
        assert request.session_id == "session_789"
        assert request.request_id == "req_101"


class TestQAResponse:
    """Test Q&A response data structure."""

    def test_response_creation(self):
        """Test creating a Q&A response."""
        response = QAResponse(
            answer="The budget was approved for Q2 with 10% increase",
            request_id="req_456",
            confidence=0.92,
            processing_time=1.5,
            timestamp=datetime.now()
        )
        
        assert "budget was approved" in response.answer
        assert response.request_id == "req_456"
        assert response.confidence == 0.92
        assert response.processing_time == 1.5

    def test_response_validation(self):
        """Test response validation."""
        # Valid response
        valid_response = QAResponse(
            answer="Valid answer",
            request_id="req_1",
            confidence=0.8,
            processing_time=1.0,
            timestamp=datetime.now()
        )
        assert valid_response.is_valid() is True
        
        # Empty answer
        empty_answer = QAResponse(
            answer="",
            request_id="req_2",
            confidence=0.8,
            processing_time=1.0,
            timestamp=datetime.now()
        )
        assert empty_answer.is_valid() is False

    def test_response_serialization(self):
        """Test response JSON serialization."""
        response = QAResponse(
            answer="Test answer",
            request_id="req_123",
            confidence=0.85,
            processing_time=2.3,
            timestamp=datetime.now()
        )
        
        json_data = response.to_dict()
        
        assert json_data["answer"] == "Test answer"
        assert json_data["request_id"] == "req_123"
        assert json_data["confidence"] == 0.85
        assert json_data["processing_time"] == 2.3


class TestQASession:
    """Test Q&A session management."""

    def test_session_creation(self):
        """Test creating a Q&A session."""
        session = QASession(
            session_id="session_123",
            user_id="user_456",
            created_at=datetime.now()
        )
        
        assert session.session_id == "session_123"
        assert session.user_id == "user_456"
        assert session.state == ConnectionState.CONNECTED
        assert len(session.qa_history) == 0

    def test_add_qa_pair(self):
        """Test adding Q&A pair to session history."""
        session = QASession("session_1", "user_1", datetime.now())
        
        request = QARequest(
            question="Test question?",
            session_id="session_1",
            timestamp=datetime.now(),
            request_id="req_1"
        )
        
        response = QAResponse(
            answer="Test answer",
            request_id="req_1",
            confidence=0.9,
            processing_time=1.0,
            timestamp=datetime.now()
        )
        
        session.add_qa_pair(request, response)
        
        assert len(session.qa_history) == 1
        assert session.qa_history[0]["request"] == request
        assert session.qa_history[0]["response"] == response

    def test_session_statistics(self):
        """Test session statistics calculation."""
        session = QASession("session_1", "user_1", datetime.now())
        
        # Add multiple Q&A pairs
        for i in range(3):
            request = QARequest(f"Question {i}?", "session_1", datetime.now(), f"req_{i}")
            response = QAResponse(f"Answer {i}", f"req_{i}", 0.8 + i * 0.05, 1.0 + i * 0.5, datetime.now())
            session.add_qa_pair(request, response)
        
        stats = session.get_statistics()
        
        assert stats["total_questions"] == 3
        assert stats["average_confidence"] == 0.85  # (0.8 + 0.85 + 0.9) / 3
        assert stats["average_processing_time"] == 1.5  # (1.0 + 1.5 + 2.0) / 3

    def test_session_history_pruning(self):
        """Test pruning of old session history."""
        session = QASession("session_1", "user_1", datetime.now())
        session.max_history_length = 5
        
        # Add more than max history
        for i in range(8):
            request = QARequest(f"Question {i}?", "session_1", datetime.now(), f"req_{i}")
            response = QAResponse(f"Answer {i}", f"req_{i}", 0.9, 1.0, datetime.now())
            session.add_qa_pair(request, response)
        
        # Should be pruned to max length
        assert len(session.qa_history) == 5
        # Should keep the most recent ones
        assert session.qa_history[0]["request"].question == "Question 3?"
        assert session.qa_history[-1]["request"].question == "Question 7?"


class TestSessionManager:
    """Test session management functionality."""

    @pytest.fixture
    def session_manager(self):
        """Create session manager."""
        return SessionManager(max_sessions=10, session_timeout_minutes=30)

    def test_create_session(self, session_manager):
        """Test creating a new session."""
        session_id = session_manager.create_session("user_123")
        
        assert session_id is not None
        assert session_id in session_manager.sessions
        assert session_manager.sessions[session_id].user_id == "user_123"

    def test_get_session(self, session_manager):
        """Test retrieving a session."""
        session_id = session_manager.create_session("user_456")
        
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        
        # Non-existent session
        non_existent = session_manager.get_session("fake_session")
        assert non_existent is None

    def test_close_session(self, session_manager):
        """Test closing a session."""
        session_id = session_manager.create_session("user_789")
        
        session_manager.close_session(session_id)
        
        session = session_manager.get_session(session_id)
        assert session.state == ConnectionState.DISCONNECTED

    def test_session_timeout_cleanup(self, session_manager):
        """Test cleanup of timed-out sessions."""
        # Create sessions with different ages
        recent_session = session_manager.create_session("user_recent")
        old_session = session_manager.create_session("user_old")
        
        # Manually set old session timestamp
        session_manager.sessions[old_session].created_at = datetime.now() - session_manager.session_timeout
        
        # Run cleanup
        session_manager.cleanup_expired_sessions()
        
        # Recent session should remain, old should be removed
        assert recent_session in session_manager.sessions
        assert old_session not in session_manager.sessions

    def test_max_sessions_limit(self, session_manager):
        """Test enforcement of maximum sessions limit."""
        # Create sessions up to limit
        session_ids = []
        for i in range(10):  # max_sessions = 10
            session_id = session_manager.create_session(f"user_{i}")
            session_ids.append(session_id)
        
        assert len(session_manager.sessions) == 10
        
        # Try to create one more (should remove oldest)
        new_session = session_manager.create_session("user_overflow")
        
        assert len(session_manager.sessions) == 10
        assert new_session in session_manager.sessions
        assert session_ids[0] not in session_manager.sessions  # Oldest removed


class TestWebSocketHandler:
    """Test WebSocket message handling."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.remote_address = ("127.0.0.1", 12345)
        return mock_ws

    @pytest.fixture
    def mock_qa_handler(self):
        """Create mock Q&A handler."""
        mock_handler = AsyncMock()
        mock_handler.answer_question.return_value = "Mock answer to the question"
        return mock_handler

    @pytest.fixture
    def websocket_handler(self, mock_qa_handler):
        """Create WebSocket handler with dependencies."""
        session_manager = SessionManager()
        return WebSocketHandler(session_manager, mock_qa_handler)

    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_handler, mock_websocket):
        """Test WebSocket connection handling."""
        # Simulate connection
        await websocket_handler.handle_connection(mock_websocket)
        
        # Should create a session
        assert len(websocket_handler.session_manager.sessions) == 1

    @pytest.mark.asyncio
    async def test_message_processing(self, websocket_handler, mock_websocket, mock_qa_handler):
        """Test processing of Q&A messages."""
        # Set up session
        session_id = websocket_handler.session_manager.create_session("test_user")
        websocket_handler.current_session_id = session_id
        
        # Mock incoming message
        incoming_message = {
            "type": "question",
            "question": "What was discussed?",
            "request_id": "req_123"
        }
        
        mock_websocket.recv.return_value = json.dumps(incoming_message)
        mock_websocket.recv.side_effect = [json.dumps(incoming_message), websockets.exceptions.ConnectionClosed(None, None)]
        
        # Process message
        await websocket_handler.handle_connection(mock_websocket)
        
        # Should have called Q&A handler
        mock_qa_handler.answer_question.assert_called_once_with("What was discussed?")
        
        # Should have sent response
        mock_websocket.send.assert_called()

    @pytest.mark.asyncio
    async def test_invalid_message_handling(self, websocket_handler, mock_websocket):
        """Test handling of invalid messages."""
        # Set up session
        session_id = websocket_handler.session_manager.create_session("test_user")
        websocket_handler.current_session_id = session_id
        
        # Mock invalid message
        invalid_message = "not json"
        
        mock_websocket.recv.side_effect = [invalid_message, websockets.exceptions.ConnectionClosed(None, None)]
        
        # Should handle gracefully
        await websocket_handler.handle_connection(mock_websocket)
        
        # Should send error response
        mock_websocket.send.assert_called()
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_message["type"] == "error"

    def test_message_validation(self, websocket_handler):
        """Test message format validation."""
        # Valid message
        valid_msg = {
            "type": "question",
            "question": "Valid question?",
            "request_id": "req_123"
        }
        assert websocket_handler._validate_message(valid_msg) is True
        
        # Missing required field
        invalid_msg = {
            "type": "question",
            "request_id": "req_456"
            # Missing question
        }
        assert websocket_handler._validate_message(invalid_msg) is False
        
        # Unknown message type
        unknown_type = {
            "type": "unknown",
            "question": "Test?",
            "request_id": "req_789"
        }
        assert websocket_handler._validate_message(unknown_type) is False

    def test_response_formatting(self, websocket_handler):
        """Test response message formatting."""
        response = QAResponse(
            answer="Test answer",
            request_id="req_123",
            confidence=0.85,
            processing_time=1.5,
            timestamp=datetime.now()
        )
        
        formatted = websocket_handler._format_response(response)
        
        assert formatted["type"] == "answer"
        assert formatted["answer"] == "Test answer"
        assert formatted["request_id"] == "req_123"
        assert formatted["confidence"] == 0.85
        assert formatted["processing_time"] == 1.5

    @pytest.mark.asyncio
    async def test_kb_update_message_handling(self, websocket_handler, mock_websocket):
        """Test handling of KB update messages."""
        # Set up session
        session_id = websocket_handler.session_manager.create_session("test_user")
        websocket_handler.current_session_id = session_id
        
        # Create a mock knowledge base
        from src.livetranscripts.knowledge_base import KnowledgeBase
        websocket_handler.knowledge_base = KnowledgeBase()
        
        # Mock KB update message
        kb_update_message = {
            "type": "update_kb",
            "content": "# Test KB Content\n\nThis is test knowledge base content."
        }
        
        # Process the message directly
        await websocket_handler._process_message(mock_websocket, json.dumps(kb_update_message))
        
        # Should have sent acknowledgment
        mock_websocket.send.assert_called()
        # Get the last sent message (should be kb_updated)
        sent_message = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_message["type"] == "kb_updated"
        assert sent_message["success"] is True

    @pytest.mark.asyncio
    async def test_kb_content_sync_on_connect(self, websocket_handler, mock_websocket):
        """Test that KB content is sent to client on connection."""
        # Set up initial KB content
        websocket_handler.knowledge_base = Mock()
        websocket_handler.knowledge_base.get_content.return_value = "# Existing KB\n\nExisting content"
        
        # Simulate connection and immediate close
        mock_websocket.recv.side_effect = websockets.exceptions.ConnectionClosed(None, None)
        
        # Handle connection
        await websocket_handler.handle_connection(mock_websocket)
        
        # Should have sent KB content on connect
        mock_websocket.send.assert_called()
        sent_messages = [json.loads(call[0][0]) for call in mock_websocket.send.call_args_list]
        
        # Find KB content message
        kb_content_msg = next((msg for msg in sent_messages if msg.get("type") == "kb_content"), None)
        assert kb_content_msg is not None
        assert kb_content_msg["content"] == "# Existing KB\n\nExisting content"


class TestLiveQAServer:
    """Test the main Live Q&A server."""

    @pytest.fixture
    def mock_qa_handler(self):
        """Create mock Q&A handler."""
        mock_handler = AsyncMock()
        mock_handler.answer_question.return_value = "Server mock answer"
        return mock_handler

    @pytest.fixture
    def qa_server(self, mock_qa_handler):
        """Create Live Q&A server."""
        return LiveQAServer(
            host="localhost",
            port=8765,
            qa_handler=mock_qa_handler
        )

    def test_server_initialization(self, qa_server, mock_qa_handler):
        """Test server initialization."""
        assert qa_server.host == "localhost"
        assert qa_server.port == 8765
        assert qa_server.qa_handler == mock_qa_handler
        assert qa_server.is_running is False

    @pytest.mark.asyncio
    async def test_server_start_stop(self, qa_server):
        """Test server start and stop functionality."""
        # Start server
        server_task = asyncio.create_task(qa_server.start())
        await asyncio.sleep(0.1)  # Let server start
        
        assert qa_server.is_running is True
        
        # Stop server
        qa_server.stop()
        await asyncio.sleep(0.1)  # Let server stop
        
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, qa_server):
        """Test health check functionality."""
        health_status = qa_server.get_health_status()
        
        assert "status" in health_status
        assert "active_sessions" in health_status
        assert "uptime" in health_status
        assert health_status["status"] in ["healthy", "unhealthy"]

    def test_server_statistics(self, qa_server):
        """Test server statistics collection."""
        # Simulate some activity
        qa_server.session_manager.create_session("user_1")
        qa_server.session_manager.create_session("user_2")
        
        stats = qa_server.get_statistics()
        
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 2
        assert "questions_processed" in stats
        assert "average_response_time" in stats


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def integration_setup(self):
        """Set up complete integration environment."""
        # Mock Gemini Q&A handler
        config = GeminiConfig()
        context_manager = ContextManager(config)
        qa_handler = QAHandler(config, context_manager)
        
        # Mock the Gemini client
        mock_client = AsyncMock()
        mock_client.generate_content.return_value = "Integration test answer"
        qa_handler.client = mock_client
        
        # Create server
        server = LiveQAServer(
            host="localhost",
            port=8766,
            qa_handler=qa_handler
        )
        
        return {
            "server": server,
            "qa_handler": qa_handler,
            "context_manager": context_manager,
            "mock_client": mock_client
        }

    @pytest.mark.asyncio
    async def test_full_qa_flow(self, integration_setup):
        """Test complete Q&A flow from WebSocket to response."""
        components = integration_setup
        server = components["server"]
        context_manager = components["context_manager"]
        
        # Add meeting context
        from src.livetranscripts.whisper_integration import TranscriptionResult, TranscriptionSegment
        
        transcript = TranscriptionResult(
            text="We discussed the budget approval for next quarter",
            segments=[TranscriptionSegment("We discussed the budget approval for next quarter", 0.0, 3.0, 0.9)],
            language="en",
            duration=3.0,
            batch_id=1
        )
        context_manager.add_transcription(transcript)
        
        # Create mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ("127.0.0.1", 12345)
        
        # Simulate Q&A exchange
        question_message = {
            "type": "question",
            "question": "What was discussed about the budget?",
            "request_id": "req_integration_test"
        }
        
        mock_websocket.recv.side_effect = [
            json.dumps(question_message),
            websockets.exceptions.ConnectionClosed(None, None)
        ]
        
        # Handle the connection
        websocket_handler = WebSocketHandler(server.session_manager, server.qa_handler)
        await websocket_handler.handle_connection(mock_websocket)
        
        # Verify response was sent
        mock_websocket.send.assert_called()
        response_json = mock_websocket.send.call_args[0][0]
        response_data = json.loads(response_json)
        
        assert response_data["type"] == "answer"
        assert response_data["request_id"] == "req_integration_test"
        assert "answer" in response_data

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, integration_setup):
        """Test handling multiple concurrent Q&A sessions."""
        components = integration_setup
        server = components["server"]
        
        # Create multiple mock WebSocket connections
        num_sessions = 3
        mock_websockets = []
        
        for i in range(num_sessions):
            mock_ws = AsyncMock()
            mock_ws.remote_address = ("127.0.0.1", 12345 + i)
            mock_websockets.append(mock_ws)
        
        # Set up different questions for each session
        questions = [
            "What was the budget decision?",
            "Who is responsible for implementation?",
            "What is the timeline?"
        ]
        
        # Configure WebSocket mocks
        for i, (mock_ws, question) in enumerate(zip(mock_websockets, questions)):
            question_msg = {
                "type": "question",
                "question": question,
                "request_id": f"req_{i}"
            }
            mock_ws.recv.side_effect = [
                json.dumps(question_msg),
                websockets.exceptions.ConnectionClosed(None, None)
            ]
        
        # Handle all connections concurrently
        websocket_handler = WebSocketHandler(server.session_manager, server.qa_handler)
        tasks = [
            websocket_handler.handle_connection(mock_ws)
            for mock_ws in mock_websockets
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all sessions were handled
        assert len(server.session_manager.sessions) == num_sessions
        
        # Verify all WebSockets received responses
        for mock_ws in mock_websockets:
            mock_ws.send.assert_called()

    @pytest.mark.asyncio
    async def test_error_resilience(self, integration_setup):
        """Test system resilience to various error conditions."""
        components = integration_setup
        server = components["server"]
        mock_client = components["mock_client"]
        
        # Test API error handling
        mock_client.generate_content.side_effect = Exception("API temporarily unavailable")
        
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ("127.0.0.1", 12345)
        
        error_question = {
            "type": "question",
            "question": "This will cause an error",
            "request_id": "req_error_test"
        }
        
        mock_websocket.recv.side_effect = [
            json.dumps(error_question),
            websockets.exceptions.ConnectionClosed(None, None)
        ]
        
        # Handle connection with error
        websocket_handler = WebSocketHandler(server.session_manager, server.qa_handler)
        await websocket_handler.handle_connection(mock_websocket)
        
        # Should send error response instead of crashing
        mock_websocket.send.assert_called()
        response_json = mock_websocket.send.call_args[0][0]
        response_data = json.loads(response_json)
        
        assert response_data["type"] == "error"
        assert response_data["request_id"] == "req_error_test"