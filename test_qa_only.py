#!/usr/bin/env python3
"""Test script for Q&A functionality only."""

import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

async def test_qa_client():
    """Test WebSocket Q&A client."""
    print("🧪 Testing Q&A WebSocket Connection...")
    
    try:
        # Connect to Q&A server
        uri = "ws://localhost:8766"
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Q&A server")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"📨 Server: {welcome_data}")
            
            # Test questions
            test_questions = [
                "What is the purpose of this system?",
                "How does live transcription work?",
                "Can you explain voice activity detection?"
            ]
            
            for i, question in enumerate(test_questions, 1):
                print(f"\n❓ Question {i}: {question}")
                
                # Send question
                request = {
                    "type": "question",
                    "question": question,
                    "request_id": f"test_{i}"
                }
                await websocket.send(json.dumps(request))
                
                # Get response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                if response_data["type"] == "answer":
                    print(f"💬 Answer: {response_data['answer'][:100]}...")
                    print(f"⏱️  Processing time: {response_data['processing_time']:.2f}s")
                else:
                    print(f"❌ Error: {response_data}")
                
                await asyncio.sleep(1)  # Be nice to the API
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure the Q&A server is running!")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_qa_client())