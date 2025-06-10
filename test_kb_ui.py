#!/usr/bin/env python3
"""Quick test to verify KB editor UI integration."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from livetranscripts.live_qa import LiveQAServer
from livetranscripts.gemini_integration import GeminiConfig, GeminiIntegration
from livetranscripts.knowledge_base import KnowledgeBase


async def test_kb_ui():
    """Test the KB editor UI integration."""
    print("🚀 Starting KB editor UI test...")
    
    # Create Gemini integration
    config = GeminiConfig(focus_prompt="Test KB integration")
    gemini = GeminiIntegration(config)
    
    # Create knowledge base with initial content
    kb = KnowledgeBase()
    kb.add_document("""# Test Knowledge Base

## Product Information
- Product A: $100
- Product B: $200

## Company Policies
- Policy 1: Customer first
- Policy 2: Quality matters
""")
    
    # Set KB on Gemini integration
    gemini.set_knowledge_base(kb)
    
    # Create Q&A server
    server = LiveQAServer(
        host="localhost",
        port=8765,
        qa_handler=gemini.qa_handler,
        http_port=8766
    )
    
    # Set KB on server
    server.set_knowledge_base(kb)
    
    print("📚 Knowledge base initialized with test content")
    print("🌐 Starting server...")
    print("=" * 60)
    print("🔗 WebSocket: ws://localhost:8765")
    print("🌐 Web UI: http://localhost:8766")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Open http://localhost:8766 in your browser")
    print("2. Click on the 'Knowledge Base' tab")
    print("3. You should see the test KB content loaded")
    print("4. Try editing and saving the KB")
    print("5. Switch back to 'Ask Questions' and ask about the products")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(test_kb_ui())
    except KeyboardInterrupt:
        print("\n✅ Test completed!")