#!/usr/bin/env python3
"""Test script for full system with simulated audio."""

import asyncio
import numpy as np
import os
from datetime import datetime
from dotenv import load_dotenv

async def test_full_pipeline():
    """Test the complete transcription pipeline with simulated audio."""
    print("🧪 Testing Full System Pipeline...")
    
    try:
        from src.livetranscripts.batching import VADAudioBatcher, BatchingConfig
        from src.livetranscripts.whisper_integration import WhisperClient, WhisperConfig
        from src.livetranscripts.gemini_integration import GeminiClient, GeminiConfig, ContextManager
        
        # Initialize components
        print("🔧 Initializing components...")
        
        # Configs
        batch_config = BatchingConfig(min_batch_duration=1.0, max_batch_duration=5.0)  # Shorter for testing
        whisper_config = WhisperConfig()
        gemini_config = GeminiConfig()
        
        # Components
        batcher = VADAudioBatcher(batch_config)
        
        openai_key = os.getenv('OPENAI_API_KEY')
        google_key = os.getenv('GOOGLE_API_KEY')
        
        if openai_key and not openai_key.startswith('your-'):
            whisper_client = WhisperClient(whisper_config, openai_key)
            print("✅ Whisper client ready")
        else:
            print("⚠️  Whisper client disabled (no API key)")
            whisper_client = None
            
        if google_key and not google_key.startswith('your-'):
            gemini_client = GeminiClient(gemini_config, google_key)
            context_manager = ContextManager(gemini_config)
            print("✅ Gemini client ready")
        else:
            print("⚠️  Gemini client disabled (no API key)")
            gemini_client = None
        
        # Test 1: Audio batching with simulated data
        print("\n📊 Testing Audio Batching...")
        
        # Simulate speech audio chunks
        for i in range(10):
            # Generate realistic audio (speech-like)
            chunk_size = 8000  # 0.5 seconds at 16kHz
            if i % 3 == 0:  # Every 3rd chunk is silence
                audio_chunk = np.random.randint(-50, 50, chunk_size, dtype=np.int16)
                print(f"🔇 Chunk {i+1}: Silence")
            else:
                audio_chunk = np.random.randint(-12000, 12000, chunk_size, dtype=np.int16)
                print(f"🗣️  Chunk {i+1}: Speech")
            
            batch = await batcher.add_audio_chunk(audio_chunk)
            
            if batch:
                print(f"📦 Batch created: {batch.duration:.1f}s, sequence {batch.sequence_id}")
                
                # Test 2: Transcription (if available)
                if whisper_client:
                    try:
                        print("🎤 Sending to Whisper...")
                        result = await whisper_client.transcribe_batch(batch)
                        print(f"📝 Transcription: {result.text}")
                        
                        # Test 3: Add to context and Q&A (if available)
                        if gemini_client:
                            context_manager.add_transcription(result)
                            print("🧠 Added to context")
                            
                    except Exception as e:
                        print(f"⚠️  Transcription error: {e}")
                        
                break  # Just test one batch
        
        # Force remaining batch
        final_batch = await batcher.force_batch()
        if final_batch:
            print(f"📦 Final batch: {final_batch.duration:.1f}s")
        
        print("\n✅ Pipeline test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_full_pipeline())