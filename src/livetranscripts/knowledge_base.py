"""Knowledge Base module for storing and managing user-provided documentation."""

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