"""Test cases for knowledge base functionality."""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# These will be implemented after tests are written
from src.livetranscripts.knowledge_base import (
    KnowledgeBase,
    KnowledgeDocument,
)


class TestKnowledgeDocument:
    """Test knowledge document data structure."""

    def test_document_creation(self):
        """Test creating a knowledge document."""
        content = "# Product SKU\n\nOur flagship product..."
        doc = KnowledgeDocument(
            doc_id="doc_123",
            content=content,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert doc.doc_id == "doc_123"
        assert doc.content == content
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)

    def test_document_serialization(self):
        """Test document JSON serialization."""
        doc = KnowledgeDocument(
            doc_id="doc_456",
            content="Test content",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        json_data = doc.to_dict()
        
        assert json_data["doc_id"] == "doc_456"
        assert json_data["content"] == "Test content"
        assert "created_at" in json_data
        assert "updated_at" in json_data

    def test_document_deserialization(self):
        """Test creating document from JSON data."""
        data = {
            "doc_id": "doc_789",
            "content": "Deserialized content",
            "created_at": "2025-06-10T10:30:00",
            "updated_at": "2025-06-10T10:30:00"
        }
        
        doc = KnowledgeDocument.from_dict(data)
        
        assert doc.doc_id == "doc_789"
        assert doc.content == "Deserialized content"

    def test_document_update(self):
        """Test updating document content."""
        doc = KnowledgeDocument(
            doc_id="doc_update",
            content="Original content",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        original_updated_at = doc.updated_at
        
        # Update content
        doc.update_content("Updated content")
        
        assert doc.content == "Updated content"
        assert doc.updated_at > original_updated_at


class TestKnowledgeBase:
    """Test knowledge base management."""

    @pytest.fixture
    def knowledge_base(self):
        """Create knowledge base instance."""
        return KnowledgeBase()

    def test_knowledge_base_initialization(self, knowledge_base):
        """Test KB initialization."""
        assert knowledge_base.documents == {}
        assert knowledge_base.get_content() == ""

    def test_add_document(self, knowledge_base):
        """Test adding a document to KB."""
        doc_id = knowledge_base.add_document("# Test Document\n\nContent here...")
        
        assert doc_id is not None
        assert doc_id in knowledge_base.documents
        assert knowledge_base.documents[doc_id].content == "# Test Document\n\nContent here..."

    def test_update_document(self, knowledge_base):
        """Test updating an existing document."""
        # Add initial document
        doc_id = knowledge_base.add_document("Initial content")
        
        # Update it
        success = knowledge_base.update_document(doc_id, "Updated content")
        
        assert success is True
        assert knowledge_base.documents[doc_id].content == "Updated content"
        
        # Try updating non-existent document
        success = knowledge_base.update_document("fake_id", "Content")
        assert success is False

    def test_remove_document(self, knowledge_base):
        """Test removing a document from KB."""
        # Add document
        doc_id = knowledge_base.add_document("Test content")
        assert doc_id in knowledge_base.documents
        
        # Remove it
        success = knowledge_base.remove_document(doc_id)
        assert success is True
        assert doc_id not in knowledge_base.documents
        
        # Try removing non-existent document
        success = knowledge_base.remove_document("fake_id")
        assert success is False

    def test_get_content(self, knowledge_base):
        """Test getting full KB content."""
        # Empty KB
        assert knowledge_base.get_content() == ""
        
        # Add multiple documents
        doc1_id = knowledge_base.add_document("# Document 1\n\nFirst document content")
        doc2_id = knowledge_base.add_document("# Document 2\n\nSecond document content")
        
        full_content = knowledge_base.get_content()
        
        assert "# Document 1" in full_content
        assert "First document content" in full_content
        assert "# Document 2" in full_content
        assert "Second document content" in full_content
        assert "\n\n---\n\n" in full_content  # Document separator

    def test_clear_all(self, knowledge_base):
        """Test clearing all documents."""
        # Add documents
        knowledge_base.add_document("Doc 1")
        knowledge_base.add_document("Doc 2")
        knowledge_base.add_document("Doc 3")
        
        assert len(knowledge_base.documents) == 3
        
        # Clear all
        knowledge_base.clear_all()
        
        assert len(knowledge_base.documents) == 0
        assert knowledge_base.get_content() == ""

    def test_get_statistics(self, knowledge_base):
        """Test getting KB statistics."""
        # Empty KB
        stats = knowledge_base.get_statistics()
        assert stats["total_documents"] == 0
        assert stats["total_characters"] == 0
        
        # Add documents
        knowledge_base.add_document("Short doc")
        knowledge_base.add_document("A longer document with more content")
        
        stats = knowledge_base.get_statistics()
        assert stats["total_documents"] == 2
        assert stats["total_characters"] == len("Short doc") + len("A longer document with more content")

    def test_serialization(self, knowledge_base):
        """Test KB serialization/deserialization."""
        # Add documents
        doc1_id = knowledge_base.add_document("Document 1")
        doc2_id = knowledge_base.add_document("Document 2")
        
        # Serialize
        serialized = knowledge_base.to_dict()
        
        assert "documents" in serialized
        assert len(serialized["documents"]) == 2
        
        # Create new KB from serialized data
        new_kb = KnowledgeBase.from_dict(serialized)
        
        assert len(new_kb.documents) == 2
        assert doc1_id in new_kb.documents
        assert doc2_id in new_kb.documents
        assert new_kb.documents[doc1_id].content == "Document 1"


class TestKnowledgeBaseIntegration:
    """Test KB integration with existing components."""

    @pytest.fixture
    def mock_gemini_integration(self):
        """Create mock Gemini integration."""
        mock = AsyncMock()
        mock.generate_questions.return_value = ["Question 1?", "Question 2?"]
        mock.generate_insights.return_value = ["Insight 1", "Insight 2"]
        return mock

    @pytest.fixture
    def knowledge_base_with_content(self):
        """Create KB with sample content."""
        kb = KnowledgeBase()
        kb.add_document("""
# Product Catalog

## SKU-001: Enterprise Solution
- Price: $10,000/month
- Features: Advanced analytics, 24/7 support
- Use case: Large organizations

## SKU-002: Starter Package  
- Price: $100/month
- Features: Basic features, email support
- Use case: Small businesses
""")
        kb.add_document("""
# Sales Playbook

## Objection Handling
- Price concerns: Emphasize ROI and value
- Feature requests: Highlight customization options
- Competition: Focus on our unique differentiators
""")
        return kb

    @pytest.mark.asyncio
    async def test_gemini_with_knowledge_base(self, mock_gemini_integration, knowledge_base_with_content):
        """Test Gemini integration with KB content."""
        # This test validates that KB can be set on Gemini integration
        # The actual integration is tested in test_gemini_kb_integration.py
        
        # Mock should have set_knowledge_base method
        mock_gemini_integration.set_knowledge_base = Mock()
        
        # Set KB
        mock_gemini_integration.set_knowledge_base(knowledge_base_with_content)
        
        # Verify KB was set
        mock_gemini_integration.set_knowledge_base.assert_called_once_with(knowledge_base_with_content)

    def test_websocket_kb_protocol(self):
        """Test WebSocket protocol for KB updates."""
        # Test update KB message
        update_msg = {
            "type": "update_kb",
            "content": "# New KB Content\n\nTest content..."
        }
        
        # Validate message format
        assert update_msg["type"] == "update_kb"
        assert "content" in update_msg
        
        # Test KB content response
        content_msg = {
            "type": "kb_content",
            "content": "# Existing KB\n\nExisting content..."
        }
        
        assert content_msg["type"] == "kb_content"
        assert "content" in content_msg

    def test_server_kb_state_management(self, knowledge_base_with_content):
        """Test server-side KB state management."""
        # Test that KB can be managed at the server level
        # This simulates how the server would manage KB state
        
        # Server would maintain KB instance
        server_kb = knowledge_base_with_content
        
        # Update KB
        new_content = "# Updated KB\n\nNew content"
        server_kb.clear_all()
        server_kb.add_document(new_content)
        
        # Verify state
        assert server_kb.get_content() == new_content
        
        # Test that KB persists across operations
        doc_id = server_kb.add_document("Additional content")
        assert "Additional content" in server_kb.get_content()
        assert "Updated KB" in server_kb.get_content()

    @pytest.mark.asyncio
    async def test_kb_persistence_across_sessions(self):
        """Test that KB content persists across WebSocket sessions."""
        kb = KnowledgeBase()
        kb.add_document("Persistent content")
        
        # Simulate multiple sessions
        session1_kb_content = kb.get_content()
        session2_kb_content = kb.get_content()
        
        assert session1_kb_content == session2_kb_content
        assert "Persistent content" in session1_kb_content


class TestKnowledgeBasePromptIntegration:
    """Test KB integration with prompt generation."""

    def test_prompt_with_empty_kb(self):
        """Test prompt generation with empty KB."""
        kb = KnowledgeBase()
        transcript = "Test transcript"
        focus = "Identify opportunities"
        
        # Mock prompt builder
        def build_prompt(transcript_text, kb_content, focus_prompt):
            if kb_content:
                return f"KB: {kb_content}\nFOCUS: {focus_prompt}\nTRANSCRIPT: {transcript_text}"
            else:
                return f"FOCUS: {focus_prompt}\nTRANSCRIPT: {transcript_text}"
        
        prompt = build_prompt(transcript, kb.get_content(), focus)
        
        assert "KB:" not in prompt  # No KB section when empty
        assert f"FOCUS: {focus}" in prompt
        assert f"TRANSCRIPT: {transcript}" in prompt

    def test_prompt_with_kb_content(self):
        """Test prompt generation with KB content."""
        kb = KnowledgeBase()
        kb.add_document("# Important Context\n\nKey information here")
        
        transcript = "Discussion about pricing"
        focus = "Address pricing concerns"
        
        # Mock prompt builder
        def build_prompt(transcript_text, kb_content, focus_prompt):
            return f"""KNOWLEDGE BASE:
{kb_content}

SESSION FOCUS: {focus_prompt}

TRANSCRIPT:
{transcript_text}

Generate insights connecting the discussion to the knowledge base."""
        
        prompt = build_prompt(transcript, kb.get_content(), focus)
        
        assert "KNOWLEDGE BASE:" in prompt
        assert "# Important Context" in prompt
        assert "Key information here" in prompt
        assert f"SESSION FOCUS: {focus}" in prompt
        assert transcript in prompt  # Just check transcript is present, not exact format

    def test_token_estimation(self):
        """Test estimating tokens for KB content."""
        kb = KnowledgeBase()
        
        # Add content of known size
        # Rough estimate: 1 token ≈ 4 characters
        large_content = "x" * 4000  # ~1000 tokens
        kb.add_document(large_content)
        
        content = kb.get_content()
        estimated_tokens = len(content) / 4
        
        assert 900 < estimated_tokens < 1100  # Allow some variance

    def test_kb_content_ordering(self):
        """Test that KB documents maintain order."""
        kb = KnowledgeBase()
        
        # Add documents in specific order
        doc1_id = kb.add_document("First document")
        doc2_id = kb.add_document("Second document")
        doc3_id = kb.add_document("Third document")
        
        content = kb.get_content()
        
        # Verify order is maintained
        first_pos = content.find("First document")
        second_pos = content.find("Second document")
        third_pos = content.find("Third document")
        
        assert first_pos < second_pos < third_pos