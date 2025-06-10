"""Test cases for multi-record Knowledge Base functionality."""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock
import websockets

from src.livetranscripts.knowledge_base import KnowledgeBase, KnowledgeDocument
from src.livetranscripts.live_qa import MessageType, WebSocketHandler


class TestMultiRecordKnowledgeBase:
    """Test Knowledge Base multi-record management."""
    
    def test_create_kb_record(self):
        """Test creating a new KB record with title."""
        kb = KnowledgeBase()
        
        # Create a record with title and content
        doc_id = kb.add_document("# Product Overview\n\nOur main product is...")
        
        assert doc_id is not None
        assert doc_id in kb.documents
        assert kb.documents[doc_id].content == "# Product Overview\n\nOur main product is..."
    
    def test_list_kb_records(self):
        """Test listing all KB records with metadata."""
        kb = KnowledgeBase()
        
        # Add multiple records
        doc1_id = kb.add_document("# Sales Process\n\nOur sales process...")
        doc2_id = kb.add_document("# Technical Specs\n\nTechnical details...")
        doc3_id = kb.add_document("# FAQ\n\nFrequently asked questions...")
        
        # Get all records
        records = kb.list_documents()
        
        assert len(records) == 3
        assert all('doc_id' in r for r in records)
        assert all('title' in r for r in records)
        assert all('created_at' in r for r in records)
        assert all('updated_at' in r for r in records)
        
        # Check titles are extracted from markdown headers
        titles = [r['title'] for r in records]
        assert "Sales Process" in titles
        assert "Technical Specs" in titles
        assert "FAQ" in titles
    
    def test_extract_title_from_content(self):
        """Test extracting title from markdown content."""
        kb = KnowledgeBase()
        
        # Test with H1 header
        assert kb._extract_title("# My Title\n\nContent") == "My Title"
        
        # Test with H2 header
        assert kb._extract_title("## Another Title\n\nContent") == "Another Title"
        
        # Test with no header (uses first line)
        assert kb._extract_title("Just some content") == "Just some content"
        
        # Test with multiple headers (should use first)
        assert kb._extract_title("# First\n\n## Second") == "First"
        
        # Test with empty content
        assert kb._extract_title("") == "Untitled Document"
        
        # Test with only whitespace
        assert kb._extract_title("   \n\n   ") == "Untitled Document"
    
    def test_update_kb_record(self):
        """Test updating an existing KB record."""
        kb = KnowledgeBase()
        
        # Create a record
        doc_id = kb.add_document("# Original Title\n\nOriginal content")
        original_updated_at = kb.documents[doc_id].updated_at
        
        # Update it
        success = kb.update_document(doc_id, "# Updated Title\n\nUpdated content")
        
        assert success is True
        assert kb.documents[doc_id].content == "# Updated Title\n\nUpdated content"
        assert kb.documents[doc_id].updated_at > original_updated_at
    
    def test_delete_kb_record(self):
        """Test deleting a KB record."""
        kb = KnowledgeBase()
        
        # Create records
        doc1_id = kb.add_document("# Record 1")
        doc2_id = kb.add_document("# Record 2")
        
        # Delete one
        success = kb.remove_document(doc1_id)
        
        assert success is True
        assert doc1_id not in kb.documents
        assert doc2_id in kb.documents
        assert len(kb.documents) == 1


class TestKBWebSocketProtocol:
    """Test WebSocket protocol for KB multi-record operations."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.remote_address = ("127.0.0.1", 12345)
        return mock_ws
    
    @pytest.fixture
    def websocket_handler(self):
        """Create WebSocket handler with KB."""
        session_manager = Mock()
        qa_handler = Mock()
        server = Mock()
        
        # Create KB with test data
        kb = KnowledgeBase()
        kb.add_document("# Test Doc 1\n\nContent 1")
        kb.add_document("# Test Doc 2\n\nContent 2")
        
        server.knowledge_base = kb
        
        handler = WebSocketHandler(session_manager, qa_handler, server)
        handler.knowledge_base = kb
        handler.current_session_id = "test_session"
        return handler
    
    @pytest.mark.asyncio
    async def test_list_kb_records_message(self, websocket_handler, mock_websocket):
        """Test handling LIST_KB_RECORDS message."""
        message = {
            "type": "list_kb_records"
        }
        
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should send list of records
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "kb_records_list"
        assert "records" in sent_data
        assert len(sent_data["records"]) == 2
        assert all("title" in r for r in sent_data["records"])
    
    @pytest.mark.asyncio
    async def test_create_kb_record_message(self, websocket_handler, mock_websocket):
        """Test handling CREATE_KB_RECORD message."""
        message = {
            "type": "create_kb_record",
            "content": "# New Record\n\nNew content here"
        }
        
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should send success response with new record ID
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "kb_record_created"
        assert sent_data["success"] is True
        assert "doc_id" in sent_data
        assert "title" in sent_data
        assert sent_data["title"] == "New Record"
    
    @pytest.mark.asyncio
    async def test_update_kb_record_message(self, websocket_handler, mock_websocket):
        """Test handling UPDATE_KB_RECORD message."""
        # Get existing doc ID
        records = websocket_handler.knowledge_base.list_documents()
        doc_id = records[0]['doc_id']
        
        message = {
            "type": "update_kb_record",
            "doc_id": doc_id,
            "content": "# Updated Content\n\nThis is updated"
        }
        
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should send success response
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "kb_record_updated"
        assert sent_data["success"] is True
        assert sent_data["doc_id"] == doc_id
    
    @pytest.mark.asyncio
    async def test_delete_kb_record_message(self, websocket_handler, mock_websocket):
        """Test handling DELETE_KB_RECORD message."""
        # Get existing doc ID
        records = websocket_handler.knowledge_base.list_documents()
        doc_id = records[0]['doc_id']
        
        message = {
            "type": "delete_kb_record",
            "doc_id": doc_id
        }
        
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should send success response
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "kb_record_deleted"
        assert sent_data["success"] is True
        assert sent_data["doc_id"] == doc_id
    
    @pytest.mark.asyncio
    async def test_get_kb_record_message(self, websocket_handler, mock_websocket):
        """Test handling GET_KB_RECORD message."""
        # Get existing doc ID
        records = websocket_handler.knowledge_base.list_documents()
        doc_id = records[0]['doc_id']
        
        message = {
            "type": "get_kb_record",
            "doc_id": doc_id
        }
        
        await websocket_handler._process_message(mock_websocket, json.dumps(message))
        
        # Should send record content
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        
        assert sent_data["type"] == "kb_record_content"
        assert sent_data["doc_id"] == doc_id
        assert "content" in sent_data
        assert "title" in sent_data


class TestMessageTypes:
    """Test that new message types are defined."""
    
    def test_kb_message_types_exist(self):
        """Test that KB multi-record message types exist."""
        assert hasattr(MessageType, 'LIST_KB_RECORDS')
        assert hasattr(MessageType, 'CREATE_KB_RECORD')
        assert hasattr(MessageType, 'UPDATE_KB_RECORD')
        assert hasattr(MessageType, 'DELETE_KB_RECORD')
        assert hasattr(MessageType, 'GET_KB_RECORD')
        assert hasattr(MessageType, 'KB_RECORDS_LIST')
        assert hasattr(MessageType, 'KB_RECORD_CREATED')
        assert hasattr(MessageType, 'KB_RECORD_UPDATED')
        assert hasattr(MessageType, 'KB_RECORD_DELETED')
        assert hasattr(MessageType, 'KB_RECORD_CONTENT')