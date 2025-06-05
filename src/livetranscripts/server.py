"""Standalone server entry point for Live Q&A functionality."""

import asyncio
import os
import sys
import argparse
from dotenv import load_dotenv
from .gemini_integration import GeminiClient, GeminiConfig, ContextManager, QAHandler
from .live_qa import run_qa_server


async def main():
    """Run the Q&A server in standalone mode."""
    parser = argparse.ArgumentParser(description='Live Q&A Server - Standalone WebSocket Q&A server')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8765, help='Server port')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Check for required API key
    google_key = os.getenv('GOOGLE_API_KEY')
    if not google_key:
        print("Error: GOOGLE_API_KEY environment variable required")
        print("Set with: export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Initialize Gemini components
    try:
        config = GeminiConfig()
        context_manager = ContextManager(config)
        gemini_client = GeminiClient(config, google_key)
        qa_handler = QAHandler(config, context_manager)
        qa_handler.client = gemini_client
        
        print("✓ Q&A components initialized")
        
        # Run server
        print(f"Starting Q&A server on {args.host}:{args.port}")
        print("Note: This is standalone mode - no live transcription")
        print("You can ask questions via WebSocket connection")
        print("\nPress Ctrl+C to stop...")
        
        await run_qa_server(qa_handler, args.host, args.port)
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    asyncio.run(main())