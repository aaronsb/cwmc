# 🔧 Fixing macOS Audio Setup for Live Transcripts

## The Problem
You're currently set up to capture **microphone input** instead of **system audio**. Live Transcripts needs to "hear" what your computer is playing (Zoom, YouTube, etc.), not just your microphone.

## The Solution: Set Up Proper Audio Loopback

### Step 1: Create a Multi-Output Device
1. **Open Audio MIDI Setup** (search in Spotlight)
2. **Click the "+" button** → **Create Multi-Output Device**
3. **Check the boxes** for:
   - ✅ **BlackHole 2ch**
   - ✅ **MacBook Pro Speakers** (or your preferred speakers)
4. **Name it**: "Live Transcripts Output"
5. **Set the master device** to your speakers (not BlackHole)

### Step 2: Set System Audio Output
1. **Open System Preferences** → **Sound** → **Output**
2. **Select**: "Live Transcripts Output" (the multi-output device you just created)
3. **Test**: Play some music - you should hear it through your speakers

### Step 3: Configure Live Transcripts Input
The system should automatically detect BlackHole as an input source for capturing the looped audio.

### Step 4: Test the Setup
1. **Play a YouTube video** or **join a Zoom meeting**
2. **Start Live Transcripts**
3. **You should see actual transcriptions** instead of just "you"

## Alternative: Use Existing Multi-Output Device
If you already have a Multi-Output Device:
1. **System Preferences** → **Sound** → **Output**
2. **Select your Multi-Output Device** that includes BlackHole
3. **Make sure BlackHole is checked** in the device configuration

## Quick Test
To verify your setup is working:
1. **Play this test video**: https://www.youtube.com/watch?v=dQw4w9WgXcQ
2. **The transcription should show the actual spoken words**, not just "you"

## Why This Fixes It
- **Current setup**: Microphone → Live Transcripts (only hears ambient room audio)
- **Correct setup**: System Audio → BlackHole → Live Transcripts (hears all computer audio)