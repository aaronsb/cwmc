# 🎤 Adding Microphone Support to Live Transcripts

## The Problem
Live Transcripts currently captures system audio (YouTube, Zoom) perfectly, but when YOU speak directly, it only shows "you" because your voice goes to the microphone, not through the system audio path.

## The Solution: Aggregate Device

Create an **Aggregate Device** that combines both BlackHole (system audio) AND your microphone into one input stream.

### Step 1: Create Aggregate Device

1. **Open Audio MIDI Setup** (Cmd+Space → "Audio MIDI Setup")

2. **Click "+" → "Create Aggregate Device"**

3. **Configure the Aggregate Device**:
   - ✅ Check **BlackHole 2ch** 
   - ✅ Check **MacBook Pro Microphone**
   - **Name it**: "Live Transcripts Complete"
   - **Set Clock Source**: BlackHole 2ch (usually)

4. **Set Channel Layout**:
   - BlackHole: Channels 1-2 (system audio)
   - Microphone: Channels 3-4 (your voice)

### Step 2: Update Audio Capture Code

We need to modify Live Transcripts to use the Aggregate Device instead of just BlackHole.

### Step 3: Test the Setup

1. **Play YouTube video** (should transcribe the video)
2. **Speak while video is paused** (should transcribe your voice)
3. **Both together** (should transcribe both sources)

## Alternative: Software Solution

If hardware setup is too complex, we can modify the code to:
1. Capture system audio (BlackHole) 
2. Capture microphone separately
3. Mix both audio streams in software
4. Send combined stream to Whisper

This requires code changes but is more reliable across different setups.