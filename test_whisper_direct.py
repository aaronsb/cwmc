#!/usr/bin/env python3
"""Direct Whisper API test with real audio file."""

import asyncio
import numpy as np
import os
from datetime import datetime
from dotenv import load_dotenv

async def test_whisper_with_audio():
    """Test Whisper with generated audio that sounds like speech."""
    print("🎤 Testing Whisper API with Audio...")
    
    try:
        from src.livetranscripts.whisper_integration import WhisperClient, WhisperConfig
        from src.livetranscripts.batching import AudioBatch
        
        # Initialize Whisper client
        config = WhisperConfig()
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key or api_key.startswith('your-'):
            print("❌ OpenAI API key not set properly")
            return
            
        client = WhisperClient(config, api_key)
        print("✅ Whisper client initialized")
        
        # Generate more realistic audio data
        print("🔊 Generating test audio...")
        
        # Create a 3-second audio clip with some pattern (like speech)
        sample_rate = 16000
        duration = 3.0
        samples = int(duration * sample_rate)
        
        # Generate a mix of tones that might resemble speech patterns
        t = np.linspace(0, duration, samples)
        
        # Create speech-like audio with multiple frequencies
        audio = np.zeros(samples)
        freqs = [200, 400, 800, 1200]  # Speech-like frequencies
        for freq in freqs:
            audio += 0.25 * np.sin(2 * np.pi * freq * t)
        
        # Add some noise and variation
        noise = np.random.normal(0, 0.1, samples)
        audio += noise
        
        # Convert to int16
        audio_int16 = (audio * 16384).astype(np.int16)
        
        # Create audio batch
        batch = AudioBatch(
            audio_data=audio_int16,
            timestamp=datetime.now(),
            duration=duration,
            sequence_id=1
        )
        
        print(f"📦 Created audio batch: {batch.size_bytes} bytes, {batch.duration}s")
        
        # Test transcription
        print("🚀 Sending to Whisper API...")
        result = await client.transcribe_batch(batch)
        
        print("✅ Transcription completed!")
        print(f"📝 Text: '{result.text}'")
        print(f"🗣️  Language: {result.language}")
        print(f"⏱️  Duration: {result.duration}s")
        print(f"🎯 Confidence: {result.average_confidence:.2f}")
        print(f"📊 Segments: {len(result.segments)}")
        
        for i, segment in enumerate(result.segments):
            print(f"   Segment {i+1}: '{segment.text}' ({segment.start_time:.1f}s-{segment.end_time:.1f}s)")
        
        # Test client statistics
        stats = client.get_statistics()
        print(f"\\n📈 Client Stats:")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Success rate: {stats['success_rate']:.1%}")
        print(f"   Avg processing time: {stats['average_processing_time']:.2f}s")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_whisper_with_audio())