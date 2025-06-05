# 📋 Step-by-Step Usage Guide

## 🚀 Your First Live Transcription Session

### Before You Start
✅ API keys are set in your `.env` file  
✅ Virtual environment is activated (`source venv/bin/activate`)  
✅ Audio loopback is configured for your system  
✅ Dependencies are installed (`pip install -e ".[dev]"`)

---

## 🎯 Step 1: Start Live Transcripts

1. **Open your terminal** and navigate to the Live Transcripts folder
2. **Activate the environment**:
   ```bash
   source venv/bin/activate
   ```
3. **Start the application**:
   ```bash
   python -m src.livetranscripts.main
   ```

### ✅ What You Should See:
```
Initializing Live Transcripts...
✓ Audio capture initialized
✓ Batch processor initialized
✓ Whisper integration initialized
✓ Gemini integration initialized
✓ Q&A server initialized
✓ All components initialized successfully

🎤 Live Transcripts is running!
📡 WebSocket server: ws://localhost:8765
📝 Real-time transcription and Q&A active
💡 Automated insights every 60 seconds

Press Ctrl+C to stop...
```

## 🎤 Step 2: Test Your Audio Setup

1. **Play some music** or **speak into your microphone**
2. **Check that audio is being captured**:
   - You should see audio processing messages in the terminal
   - If you don't see anything, check your audio loopback setup

### 🔧 Audio Troubleshooting:
- **macOS**: Ensure your system output is set to BlackHole or Multi-Output Device
- **Windows**: Make sure applications are using your default audio device
- **Test**: Play a YouTube video and see if Live Transcripts detects the audio

## 💬 Step 3: Start a Test Meeting

### Option A: Join a Real Meeting
1. **Open Zoom/Teams/Google Meet** and join any meeting
2. **Start speaking** or let others talk
3. **Watch the transcriptions** appear in your terminal in real-time

### Option B: Create a Test Scenario
1. **Play a podcast or video** with clear speech
2. **Or speak directly** into your microphone
3. **Watch the system** process and transcribe the audio

### ✅ What You Should See:
```
[14:30:15] Good morning everyone, welcome to today's meeting
[14:30:28] Let's start with our quarterly review
[14:30:45] Revenue has increased by fifteen percent this quarter

💡 [14:31:00] SUMMARY: Meeting discussion about quarterly review and revenue performance...
```

## 🤖 Step 4: Test Live Q&A

### Method 1: Using a WebSocket Client
1. **Install a WebSocket testing tool** like [WebSocket King](https://websocketking.com/)
2. **Connect to**: `ws://localhost:8765`
3. **Send a question**:
   ```json
   {
     "type": "question",
     "question": "What was discussed about revenue?",
     "request_id": "test_123"
   }
   ```

### Method 2: Using curl (Advanced)
```bash
# In a new terminal window
curl -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: $(echo -n test | base64)" \
     -H "Sec-WebSocket-Version: 13" \
     http://localhost:8765/
```

### ✅ Expected Response:
```json
{
  "type": "answer",
  "answer": "The discussion mentioned that revenue has increased by fifteen percent this quarter.",
  "request_id": "test_123",
  "confidence": 0.85,
  "processing_time": 1.2
}
```

## 📊 Step 5: Monitor Automated Insights

Every 60 seconds, you'll see automated insights like:

```
💡 [14:31:00] SUMMARY: Quarterly review meeting discussing revenue growth and performance metrics...

💡 [14:32:00] ACTION_ITEM: 
• Team: Review quarterly performance data
• John: Prepare detailed revenue analysis

💡 [14:33:00] QUESTION: 
• What factors contributed to the 15% revenue increase?
• Are there any risks to maintaining this growth rate?
```

## 🎯 Step 6: Real Meeting Usage

### During Your Next Meeting:

1. **Start Live Transcripts** 5 minutes before the meeting
2. **Join your meeting** (Zoom, Teams, etc.) as normal  
3. **Let the system run** in the background
4. **Ask questions** via WebSocket as needed:
   - "What action items have been mentioned?"
   - "Can you summarize what John said about the budget?"
   - "What are the key decisions from this meeting?"

### Best Practices:
- **Keep the terminal visible** to monitor transcription quality
- **Test audio levels** before important meetings
- **Have a WebSocket client ready** for Q&A
- **Review insights** every few minutes

## 🛑 Step 7: Stopping the System

1. **Press `Ctrl+C`** in the terminal running Live Transcripts
2. **Wait for graceful shutdown**:
   ```
   Stopping Live Transcripts...
   ✓ Q&A server stopped
   ✓ Automated insights stopped
   ✓ Transcription processing stopped
   ✓ Batch processing stopped
   ✓ Audio capture stopped
   ✓ Live Transcripts stopped successfully
   ```

## 📈 Advanced Usage Tips

### Customizing for Your Needs

**For Longer Meetings** (2+ hours):
```bash
# Edit .env file
MAX_BATCH_DURATION=45
INSIGHT_INTERVAL=120
```

**For High-Volume Meetings**:
```bash
# Edit .env file  
MIN_BATCH_DURATION=2
SILENCE_THRESHOLD=300
```

**For Better Privacy**:
```bash
# Run Q&A server only (no audio capture)
python -m src.livetranscripts.server
```

### Integration Ideas

- **Meeting Notes**: Copy/paste insights into your note-taking app
- **CRM Updates**: Use Q&A to extract client requirements
- **Project Management**: Convert action items into task tickets
- **Training**: Ask clarifying questions during training sessions

## 🚨 Common Issues & Solutions

### Issue: "No transcriptions appearing"
**Solution**: Check audio setup - play music and verify system audio is captured

### Issue: "WebSocket connection refused"  
**Solution**: Ensure Live Transcripts is running and port 8765 is available

### Issue: "Poor transcription quality"
**Solution**: Improve audio quality - reduce background noise, adjust volume levels

### Issue: "Slow API responses"
**Solution**: Check internet connection; consider upgrading API plans for higher rate limits

## 🎉 You're Ready!

You now have a complete AI-powered meeting assistant that:
- 📝 **Transcribes everything** in real-time
- 💬 **Answers questions** about meeting content  
- 💡 **Generates insights** automatically
- 🔄 **Works with any meeting platform**

Start your next meeting with Live Transcripts and experience the difference! 🚀