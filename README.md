# Live Transcripts 🎤💬

**Transform your meetings with AI-powered live transcription and real-time Q&A**

Live Transcripts captures your meeting audio in real-time, transcribes it instantly, and lets you ask questions about what's being discussed - all while the meeting is still happening!

## ✨ What Does Live Transcripts Do?

- **🎤 Live Audio Capture**: Automatically captures all system audio from your computer (Zoom, Teams, Google Meet, etc.)
- **📝 Real-Time Transcription**: Converts speech to text instantly using OpenAI's advanced Whisper technology
- **💬 Live Q&A**: Ask questions about the meeting content and get instant AI-powered answers
- **💡 Smart Insights**: Automatically generates meeting summaries, action items, and follow-up questions
- **🔄 No Meeting Interruption**: Works silently in the background without disrupting your meetings

## 🚀 Quick Start Guide

### Prerequisites

You'll need:
1. **OpenAI API Key** (for transcription) - [Get one here](https://platform.openai.com/api-keys)
2. **Google AI API Key** (for Q&A and insights) - [Get one here](https://aistudio.google.com/app/apikey)
3. **Python 3.9+** installed on your computer
4. **Audio loopback setup** (instructions below for your operating system)

### Step 1: Download and Setup

1. **Download the project** to your computer
2. **Open Terminal/Command Prompt** and navigate to the project folder
3. **Install the software**:
   ```bash
   # Create a virtual environment
   python3 -m venv venv
   
   # Activate it (Mac/Linux)
   source venv/bin/activate
   
   # Activate it (Windows)
   venv\Scripts\activate
   
   # Install dependencies
   pip install -e ".[dev]"
   ```

### Step 2: Add Your API Keys

1. **Copy the example configuration**:
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file** and add your real API keys:
   ```
   OPENAI_API_KEY=sk-your-actual-openai-key-here
   GOOGLE_API_KEY=your-actual-google-key-here
   ```

### Step 3: Set Up Audio Capture

Choose your operating system:

#### 🍎 **macOS Users**
1. **Install BlackHole** (free virtual audio driver):
   ```bash
   brew install blackhole-2ch
   ```
   Or download from: https://github.com/ExistentialAudio/BlackHole

2. **Create Multi-Output Device** (Critical Step):
   - Open **Audio MIDI Setup** (Cmd+Space, search "Audio MIDI Setup")
   - Click the **"+"** button → **"Create Multi-Output Device"**
   - **Check BOTH boxes**:
     - ✅ **BlackHole 2ch** 
     - ✅ **MacBook Pro Speakers** (or your preferred speakers)
   - **Name it**: "Live Transcripts Setup"
   - **Set Master Device** to your speakers (not BlackHole)

3. **Set System Audio Output**:
   - Open **System Preferences → Sound → Output**
   - **Select**: "Live Transcripts Setup" (your new multi-output device)
   - **Test**: Play music - you should hear it AND Live Transcripts should capture it

4. **Verify Setup**:
   - Play a YouTube video with clear speech
   - Run Live Transcripts
   - You should see **actual transcriptions**, not just "you"

#### 🪟 **Windows Users**
No additional setup needed! Windows has built-in audio loopback support.

#### 🐧 **Linux Users**
Install PulseAudio development files:
```bash
sudo apt-get install portaudio19-dev pulseaudio
```

### Step 4: Run Live Transcripts

1. **Start the application**:
   ```bash
   python -m src.livetranscripts.main
   ```

2. **You'll see startup messages**:
   ```
   ✓ Audio capture initialized
   ✓ Batch processor initialized
   ✓ Whisper integration initialized
   ✓ Gemini integration initialized
   🎤 Live Transcripts is running!
   📡 WebSocket server: ws://localhost:8765
   📝 Real-time transcription and Q&A active
   💡 Automated insights every 60 seconds
   ```

3. **Start your meeting** (Zoom, Teams, Google Meet, etc.) and begin speaking!

## 📱 How to Use During Meetings

### Real-Time Transcription
- **Automatic**: Just start talking! Transcriptions appear in your terminal in real-time
- **Example Output**:
  ```
  [14:30:15] Good morning everyone, let's start today's quarterly review
  [14:30:28] Our revenue increased by 15% this quarter
  [14:30:45] John, can you prepare the budget analysis by Friday?
  ```

### Live Q&A
Connect to the Q&A interface at `http://localhost:8765` in your web browser, or use any WebSocket client to ask questions:

**Example Questions You Can Ask:**
- "What was the main topic discussed so far?"
- "Who is responsible for the budget analysis?"
- "What are the key action items from this meeting?"
- "Can you summarize what Sarah said about the project timeline?"

### Automated Insights
Every 60 seconds, the system automatically generates:

- **📄 Meeting Summaries**: Key discussion points
- **✅ Action Items**: Tasks and assignments with deadlines
- **❓ Clarifying Questions**: Suggested follow-up questions

## 🎯 Real-World Usage Examples

### **Scenario 1: Project Status Meeting**
```
🎤 Meeting Audio: "The website redesign is 80% complete. Sarah will finish the mobile version by Thursday. We need to schedule user testing next week."

💬 Your Q&A: "When is the website redesign due?"
🤖 AI Response: "The website redesign is 80% complete, with Sarah finishing the mobile version by Thursday."

💡 Auto Insight: 
ACTION ITEMS:
• Sarah: Complete mobile version by Thursday
• Team: Schedule user testing for next week
```

### **Scenario 2: Budget Review**
```
🎤 Meeting Audio: "Q3 revenue exceeded targets by 12%. Marketing spend was $50K under budget. John will prepare the Q4 forecast."

💬 Your Q&A: "How did we perform against budget this quarter?"
🤖 AI Response: "Q3 performance was strong - revenue exceeded targets by 12% and marketing spend was $50K under budget."

💡 Auto Insight:
SUMMARY: Strong Q3 performance with revenue 12% above target and marketing under budget by $50K.
```

## ⚙️ Configuration Options

You can customize the system by editing your `.env` file:

```bash
# Audio Settings
SAMPLE_RATE=16000          # Audio quality (16kHz recommended)
CHUNK_SIZE=1024           # Processing chunk size

# Transcription Settings
WHISPER_MODEL=whisper-1   # OpenAI model to use
MIN_BATCH_DURATION=3      # Minimum seconds before transcribing
MAX_BATCH_DURATION=30     # Maximum seconds to wait

# Q&A Settings
GEMINI_MODEL=gemini-2.0-flash-exp  # Google AI model (latest)
INSIGHT_INTERVAL=60            # Seconds between auto-insights

# Server Settings
SERVER_HOST=localhost     # Server address
SERVER_PORT=8765         # Server port
```

## 🔒 Privacy & Security

- **Local Processing**: All audio processing happens on your computer
- **API Calls Only**: Only sends audio to OpenAI for transcription and text to Google for Q&A
- **No Storage**: Audio is not saved to disk (transcriptions are kept in memory only)
- **Secure Keys**: Your API keys are stored locally in your `.env` file

## 🆘 Troubleshooting

### **"No audio being captured"**
- **macOS**: Ensure BlackHole is installed and set as your audio output
- **Windows**: Check that applications are playing audio through your default output device
- **All platforms**: Verify the system audio is working by playing music

### **"API key errors"**
- Verify your API keys are correctly copied to the `.env` file
- Ensure OpenAI key starts with `sk-`
- Test your Google AI key at https://aistudio.google.com/

### **"WebSocket connection failed"**
- Make sure the application is running
- Check that port 8765 isn't being used by another application
- Try changing the port in your `.env` file

### **"Poor transcription quality"**
- Ensure good audio quality (minimize background noise)
- Check that your microphone levels are appropriate
- Verify the correct audio device is being captured

## 🏢 Business Use Cases

- **📊 Executive Briefings**: Automatically capture key decisions and action items
- **🤝 Client Meetings**: Generate instant summaries and follow-up tasks
- **🎓 Training Sessions**: Ask questions about training content in real-time
- **💼 Board Meetings**: Create comprehensive meeting records with Q&A
- **🔍 Research Interviews**: Extract insights and themes from conversations
- **📈 Sales Calls**: Identify key customer concerns and requirements

## 💰 Cost Considerations

**OpenAI Whisper API**: ~$0.006 per minute of audio
**Google AI (Gemini)**: ~$0.001 per 1K characters for Q&A

*Example: A 1-hour meeting costs approximately $0.36 for transcription + ~$0.10 for Q&A = **$0.46 total***

## 📞 Support

- **Issues**: Report problems at [GitHub Issues](https://github.com/your-repo/issues)
- **Feature Requests**: Submit ideas for new features
- **Documentation**: Full technical docs available in the `/docs` folder

## 🎉 Ready to Transform Your Meetings?

Live Transcripts turns every meeting into an interactive, searchable, and actionable experience. Start capturing insights from your conversations today!

---

*Built with ❤️ for teams who want to get more value from their meetings*