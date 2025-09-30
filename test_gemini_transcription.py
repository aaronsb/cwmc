#!/usr/bin/env python3
"""Quick test of Gemini transcription functionality."""

import asyncio
import os
import numpy as np
from dotenv import load_dotenv

from src.livetranscripts.config import TranscriptionConfig
from src.livetranscripts.transcription import TranscriptionManager, GeminiClient
from src.livetranscripts.batching import AudioBatch
from src.livetranscripts.whisper_integration import AudioProcessor

# Load environment
load_dotenv()

async def test_gemini_transcription():
    """Test Gemini transcription with synthetic audio."""
    print("🧪 Testing Gemini Transcription Integration\n")

    # Check API key
    google_key = os.getenv('GOOGLE_API_KEY')
    if not google_key:
        print("❌ GOOGLE_API_KEY not found in environment")
        return

    print(f"✓ GOOGLE_API_KEY found (ends with: ...{google_key[-4:]})")

    # Create config
    config = TranscriptionConfig(
        transcription_model="gemini-2.0-flash-lite-transcribe",
        model_fallback=["gemini-2.0-flash-transcribe"]
    )
    print(f"✓ Config created: {config.transcription_model}")

    # Create manager
    manager = TranscriptionManager(config, google_key)
    print(f"✓ Manager created")
    print(f"  Supported models: {manager.get_supported_models()}")

    # Create test audio batch (simple sine wave)
    sample_rate = 16000
    duration = 2.0  # 2 seconds
    frequency = 440  # A4 note

    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    # Create batch
    from datetime import datetime
    batch = AudioBatch(
        audio_data=audio_data,
        duration=duration,
        timestamp=datetime.now(),
        sequence_id=1
    )
    print(f"✓ Test batch created: {duration}s of {frequency}Hz sine wave")

    # Test transcription
    print("\n📝 Testing transcription...")
    try:
        result = await manager.transcribe_batch_with_fallback(batch)
        print(f"✓ Transcription successful!")
        print(f"  Text: {result.text}")
        print(f"  Duration: {result.duration}s")
        print(f"  Language: {result.language}")
        print(f"  Batch ID: {result.batch_id}")
        print(f"  Segments: {len(result.segments)}")
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get statistics
    stats = manager.get_statistics()
    print(f"\n📊 Manager Statistics:")
    print(f"  Models used: {stats['models_used']}")
    print(f"  Primary model: {stats['primary_model']}")
    print(f"  Client stats: {stats['client_stats']}")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_gemini_transcription())