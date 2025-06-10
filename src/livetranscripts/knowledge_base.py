"""Knowledge Base module for storing and managing user-provided documentation."""

import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any


class KnowledgeDocument:
    """Represents a single document in the knowledge base."""
    
    def __init__(self, doc_id: str, content: str, created_at: datetime, updated_at: datetime):
        """Initialize a knowledge document.
        
        Args:
            doc_id: Unique identifier for the document
            content: The markdown content of the document
            created_at: When the document was created
            updated_at: When the document was last updated
        """
        self.doc_id = doc_id
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at
    
    def update_content(self, new_content: str) -> None:
        """Update the document content and timestamp.
        
        Args:
            new_content: The new content for the document
        """
        self.content = new_content
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary for serialization.
        
        Returns:
            Dictionary representation of the document
        """
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeDocument":
        """Create document from dictionary.
        
        Args:
            data: Dictionary containing document data
            
        Returns:
            KnowledgeDocument instance
        """
        return cls(
            doc_id=data["doc_id"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


class KnowledgeBase:
    """Manages a collection of knowledge documents."""
    
    def __init__(self):
        """Initialize an empty knowledge base."""
        self.documents: Dict[str, KnowledgeDocument] = {}
    
    def add_document(self, content: str) -> str:
        """Add a new document to the knowledge base.
        
        Args:
            content: The markdown content to add
            
        Returns:
            The ID of the created document
        """
        doc_id = str(uuid.uuid4())
        now = datetime.now()
        doc = KnowledgeDocument(doc_id, content, now, now)
        self.documents[doc_id] = doc
        return doc_id
    
    def update_document(self, doc_id: str, content: str) -> bool:
        """Update an existing document.
        
        Args:
            doc_id: The ID of the document to update
            content: The new content
            
        Returns:
            True if update successful, False if document not found
        """
        if doc_id not in self.documents:
            return False
        
        self.documents[doc_id].update_content(content)
        return True
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the knowledge base.
        
        Args:
            doc_id: The ID of the document to remove
            
        Returns:
            True if removal successful, False if document not found
        """
        if doc_id not in self.documents:
            return False
        
        del self.documents[doc_id]
        return True
    
    def get_content(self) -> str:
        """Get all knowledge base content as a single string.
        
        Returns:
            All document contents concatenated with separators
        """
        if not self.documents:
            return ""
        
        # Sort by creation time to maintain consistent order
        sorted_docs = sorted(
            self.documents.values(),
            key=lambda d: d.created_at
        )
        
        # Join documents with separator
        contents = []
        for doc in sorted_docs:
            contents.append(doc.content)
        
        return "\n\n---\n\n".join(contents)
    
    def clear_all(self) -> None:
        """Remove all documents from the knowledge base."""
        self.documents.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base.
        
        Returns:
            Dictionary with statistics
        """
        total_chars = sum(len(doc.content) for doc in self.documents.values())
        
        return {
            "total_documents": len(self.documents),
            "total_characters": total_chars
        }
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents with metadata.
        
        Returns:
            List of document metadata dictionaries
        """
        # Sort by creation time
        sorted_docs = sorted(
            self.documents.values(),
            key=lambda d: d.created_at
        )
        
        records = []
        for doc in sorted_docs:
            records.append({
                "doc_id": doc.doc_id,
                "title": self._extract_title(doc.content),
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
                "char_count": len(doc.content)
            })
        
        return records
    
    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            Extracted title or "Untitled Document"
        """
        if not content:
            return "Untitled Document"
        
        # Look for markdown headers (# or ##)
        lines = content.strip().split('\n')
        for line in lines:
            # Match H1 header
            match = re.match(r'^#\s+(.+)$', line.strip())
            if match:
                return match.group(1).strip()
            
            # Match H2 header if no H1 found
            match = re.match(r'^##\s+(.+)$', line.strip())
            if match:
                return match.group(1).strip()
        
        # If no headers found, use first non-empty line truncated
        for line in lines:
            if line.strip():
                title = line.strip()
                if len(title) > 50:
                    return title[:47] + "..."
                return title
        
        return "Untitled Document"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert knowledge base to dictionary for serialization.
        
        Returns:
            Dictionary representation of the knowledge base
        """
        return {
            "documents": [doc.to_dict() for doc in self.documents.values()]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeBase":
        """Create knowledge base from dictionary.
        
        Args:
            data: Dictionary containing knowledge base data
            
        Returns:
            KnowledgeBase instance
        """
        kb = cls()
        for doc_data in data["documents"]:
            doc = KnowledgeDocument.from_dict(doc_data)
            kb.documents[doc.doc_id] = doc
        return kb