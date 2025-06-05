#!/usr/bin/env python3
"""
Setup verification script for Live Transcripts
Run this before your first meeting to ensure everything is working!
"""

import os
import sys
from dotenv import load_dotenv

def check_setup():
    """Check if Live Transcripts is ready to run."""
    print("🔍 Live Transcripts Setup Verification")
    print("=" * 45)
    
    all_good = True
    
    # Check 1: Python version
    print("1️⃣  Checking Python version...")
    if sys.version_info >= (3, 9):
        print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor} (Good!)")
    else:
        print(f"   ❌ Python {sys.version_info.major}.{sys.version_info.minor} (Need 3.9+)")
        all_good = False
    
    # Check 2: Dependencies
    print("\n2️⃣  Checking dependencies...")
    try:
        import numpy
        import openai
        import websockets
        import google.generativeai
        print("   ✅ All required packages installed")
    except ImportError as e:
        print(f"   ❌ Missing package: {e}")
        print("   💡 Run: pip install -e \".[dev]\"")
        all_good = False
    
    # Check 3: API Keys
    print("\n3️⃣  Checking API keys...")
    load_dotenv()
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key and openai_key.startswith('sk-'):
        print("   ✅ OpenAI API key found")
    else:
        print("   ❌ OpenAI API key missing or invalid")
        print("   💡 Add OPENAI_API_KEY=sk-your-key to .env file")
        all_good = False
    
    google_key = os.getenv('GOOGLE_API_KEY')
    if google_key and len(google_key) > 30:
        print("   ✅ Google AI API key found")
    else:
        print("   ❌ Google AI API key missing or invalid")
        print("   💡 Add GOOGLE_API_KEY=your-key to .env file")
        all_good = False
    
    # Check 4: Core components
    print("\n4️⃣  Checking Live Transcripts components...")
    try:
        from src.livetranscripts.main import LiveTranscriptsApp
        print("   ✅ Core application ready")
        
        from src.livetranscripts.audio_capture import AudioCapture
        print("   ✅ Audio capture ready")
        
        from src.livetranscripts.whisper_integration import WhisperClient
        print("   ✅ Whisper integration ready")
        
        from src.livetranscripts.gemini_integration import GeminiClient
        print("   ✅ Gemini integration ready")
        
        from src.livetranscripts.live_qa import LiveQAServer
        print("   ✅ Q&A server ready")
        
    except ImportError as e:
        print(f"   ❌ Component error: {e}")
        all_good = False
    
    # Check 5: Audio system (basic check)
    print("\n5️⃣  Checking audio system...")
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        device_count = pa.get_device_count()
        pa.terminate()
        print(f"   ✅ Audio system ready ({device_count} devices found)")
    except Exception as e:
        print(f"   ⚠️  Audio system warning: {e}")
        print("   💡 You may need to set up audio loopback (see README)")
    
    # Final verdict
    print("\n" + "=" * 45)
    if all_good:
        print("🎉 SETUP COMPLETE! Live Transcripts is ready to use!")
        print("\n🚀 To start your first session:")
        print("   python -m src.livetranscripts.main")
        print("\n📖 Need help? Check USAGE_GUIDE.md")
    else:
        print("⚠️  SETUP INCOMPLETE - Please fix the issues above")
        print("\n📚 For help, see:")
        print("   • README.md for setup instructions")
        print("   • USAGE_GUIDE.md for step-by-step usage")
    
    return all_good

if __name__ == "__main__":
    check_setup()