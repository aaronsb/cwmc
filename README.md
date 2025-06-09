# Live Transcripts 🎤💬

**Transform your meetings with AI-powered live transcription and real-time Q&A**

Live Transcripts captures your meeting audio in real-time, transcribes it instantly using **OpenAI's advanced GPT-4o models**, and lets you ask questions about what's being discussed - all while the meeting is still happening!

## 🚀 **NEW: GPT-4o Transcription Upgrade!**

We've upgraded to **GPT-4o transcription models** for dramatically improved accuracy:

- **🎯 30-40% Better Accuracy** - Significantly fewer transcription errors
- **🔊 Superior Noise Handling** - Excellent performance in noisy environments  
- **🗣️ Enhanced Accent Support** - Better recognition of diverse accents and speech patterns
- **🚫 70% Less Hallucination** - Dramatically reduced fabricated or imagined words
- **💰 Same Cost** - No price increase (~$0.006/minute, identical to Whisper)
- **🔄 Automatic Fallback** - Seamlessly falls back to Whisper if needed
- **⚡ Zero Configuration** - Works immediately with existing setups

## ✨ What Does Live Transcripts Do?

- **🎤 Live Audio Capture**: Automatically captures all system audio from your computer (Zoom, Teams, Google Meet, etc.)
- **📝 Real-Time Transcription**: Converts speech to text instantly using OpenAI's advanced GPT-4o transcription technology
- **💬 Live Q&A**: Ask questions about the meeting content and get instant AI-powered answers
- **🎯 Dynamic Smart Questions**: Contextual quick questions that adapt to your actual meeting topics every 15 seconds
- **💡 Smart Insights**: Automatically generates meeting summaries, action items, and follow-up questions
- **🔄 No Meeting Interruption**: Works silently in the background without disrupting your meetings

## 💼 Key Use Cases

Live Transcripts transforms how you handle different types of conversations by adapting to your specific goals using the **Session Focus** feature:

### 📞 **Sales Calls**
Set your intent to *"Identify objections and buying signals"* and Live Transcripts will:
- Generate questions focused on uncovering customer concerns
- Highlight action items around follow-ups and next steps
- Surface insights about pricing discussions and decision-making timelines
- Help you ask better qualifying questions in real-time

### 🤝 **Relationship Building & Networking**
Use *"Find common interests and collaboration opportunities"* as your focus:
- Questions will center on shared experiences and mutual connections
- Insights emphasize relationship-building moments and future touchpoints
- Action items focus on meaningful follow-up opportunities
- Discover conversation threads that strengthen professional relationships

### 🏛️ **Policy Debates & Decision Making**
Set your intent to *"Track arguments and identify logical gaps"*:
- Questions highlight inconsistencies and areas needing clarification
- Insights focus on pros/cons analysis and decision criteria
- Action items center on research needs and follow-up discussions
- Help identify when consensus is forming or breaking down

### 🎙️ **Interviews & Podcasts**
Focus on *"Find compelling story angles and follow-up questions"*:
- Dynamic questions reveal deeper narrative opportunities
- Insights highlight quotable moments and key themes
- Action items track fact-checking needs and additional topics to explore
- Help maintain conversational flow while capturing content gold

### 📊 **Board Meetings & Executive Sessions**
Use *"Monitor fiduciary responsibilities and strategic risks"*:
- Questions focus on governance issues and strategic implications
- Insights emphasize financial impacts and compliance considerations
- Action items prioritize regulatory requirements and strategic initiatives
- Track decision rationale for accurate board minutes

### 🎓 **Training Sessions & Workshops**
Set your intent to *"Identify learning gaps and engagement opportunities"*:
- Questions highlight areas where participants need clarification
- Insights focus on knowledge transfer effectiveness and engagement levels
- Action items center on follow-up training needs and resource requirements
- Help ensure key learning objectives are being met

**💡 Pro Tip**: Change your Session Focus during the meeting to adapt to evolving conversation dynamics. Start with one intent and switch to another as topics shift!

## 🆘 Quick Start

**One-line setup:**
```bash
curl -sSL https://raw.githubusercontent.com/aaronsb/cwmc/master/scripts/quick-setup.sh | bash
```

**Or manually:**
```bash
# 1. Clone and enter the repository
git clone https://github.com/aaronsb/cwmc.git
cd cwmc

# 2. Run the automated configuration
./scripts/configure.sh

# 3. Start transcribing!
./scripts/dev-run.sh
```

The configuration script will:
- ✅ Check Python version and dependencies
- ✅ Set up virtual environment
- ✅ Install all required packages
- ✅ Configure API keys
- ✅ Set up audio backend (with device selection on Linux)
- ✅ Create platform-specific configuration

## 🚀 Detailed Setup Guide

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
   - **Check ALL boxes for devices you want to hear audio from**:
     - ✅ **BlackHole 2ch** (REQUIRED for transcription)
     - ✅ **MacBook Pro Speakers** (for built-in speakers)
     - ✅ **Your Headphones/AirPods** (if you use them)
   - **Name it**: "Live Transcripts Setup"
   - **Set Master Device** to your preferred audio device (NOT BlackHole)

3. **Set System Audio Output** (CRITICAL STEP):
   - Open **System Preferences → Sound → Output**
   - **Select**: "Live Transcripts Setup" (your new multi-output device)
   - **IMPORTANT**: This must ALWAYS be your system output when using Live Transcripts
   - **Test**: Play music - you should hear it AND Live Transcripts should capture it

4. **Using with Headphones/AirPods**:
   - **DO**: Keep "Live Transcripts Setup" as system output
   - **DO**: Your headphones/AirPods will still work - audio goes to both
   - **DON'T**: Switch output directly to headphones/AirPods (breaks transcription)
   - **WHY**: System audio must flow through the multi-output device for capture

5. **Verify Setup**:
   - Play a YouTube video with clear speech
   - Run Live Transcripts
   - You should see **actual transcriptions**, not just silence
   - If wearing headphones, you should hear audio AND see transcriptions

#### 🪟 **Windows Users**
No additional setup needed! Windows has built-in audio loopback support.

#### 🐧 **Linux Users**
Install audio dependencies:
```bash
# For Debian/Ubuntu:
sudo apt-get install portaudio19-dev pulseaudio

# For Arch Linux:
sudo pacman -S portaudio pulseaudio

# For Fedora:
sudo dnf install portaudio-devel pulseaudio
```

**Configure Audio Device** (optional):
```bash
# List available audio devices
./scripts/list-audio-devices.sh

# Select a specific device for capture
./scripts/configure-audio-device.sh
```

💡 **Tip**: For meeting transcription, select a `.monitor` device to capture system audio.

### Step 4: Run Live Transcripts

1. **Start the application**:
   ```bash
   # For development (recommended - shows all logs)
   ./scripts/dev-run.sh
   
   # Or use make
   make dev
   
   # Or run directly
   python -m src.livetranscripts.main
   ```

2. **You'll see startup messages**:
   ```
   ✓ Audio capture initialized
   ✓ Batch processor initialized
   ✓ GPT-4o transcription initialized
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

**🎯 Smart Quick Questions:**
The interface features **dynamic contextual questions** that automatically adapt to your meeting content:
- **"Summarize recent discussion"** - Always available
- **4 contextual questions** - Update every 15 seconds based on actual meeting topics
- Questions become more relevant as your meeting progresses
- No more generic prompts - get questions tailored to what's actually being discussed!

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

## 🚀 GPT-4o Transcription (New!)

Live Transcripts now uses OpenAI's latest GPT-4o transcription models by default, providing:

- **🎯 30-40% Better Accuracy** - Lower word error rates across all scenarios
- **🔊 Superior Noise Handling** - Excellent performance in noisy environments  
- **🗣️ Enhanced Accent Support** - Better recognition of diverse accents and speech patterns
- **🚫 Reduced Hallucination** - 70% less likely to fabricate or imagine words
- **💰 Same Cost** - ~$0.006/minute (identical to Whisper pricing)
- **🔄 Automatic Fallback** - Falls back to Whisper if GPT-4o is unavailable

### Transcription Model Options
- **`gpt-4o-transcribe`** (default) - Best accuracy for critical use cases
- **`gpt-4o-mini-transcribe`** - Faster, lighter alternative 
- **`whisper-1`** - Original Whisper model (automatically used as fallback)

### Real-World Quality Improvements

**Before (Whisper)**: "Um, the Q4 budget is looking really good. We should consider, uh, increasing our investment in the new product line."

**After (GPT-4o)**: "The Q4 budget is looking really good. We should consider increasing our investment in the new product line."

Notice how GPT-4o:
- ✅ Removes filler words ("Um", "uh") more intelligently
- ✅ Maintains natural sentence flow
- ✅ Better handles interrupted speech patterns
- ✅ More accurate punctuation and capitalization

## ⚙️ Configuration Options

You can customize the system by editing your `.env` file:

```bash
# Audio Settings
SAMPLE_RATE=16000          # Audio quality (16kHz recommended)
CHUNK_SIZE=1024           # Processing chunk size

# Transcription Settings
TRANSCRIPTION_MODEL=gpt-4o-transcribe  # OpenAI model to use (gpt-4o-transcribe, whisper-1)
MODEL_FALLBACK=whisper-1               # Fallback model if primary fails
MIN_BATCH_DURATION=3                   # Minimum seconds before transcribing
MAX_BATCH_DURATION=30                  # Maximum seconds to wait

# Q&A Settings
GEMINI_MODEL=gemini-2.0-flash-lite  # Google AI model (optimized rate limits)
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
- **macOS**: 
  - Ensure BlackHole is installed and "Live Transcripts Setup" is your system output
  - **Common Issue**: If using headphones/AirPods, audio MUST go through multi-output device
  - Go to System Preferences → Sound → Output → Select "Live Transcripts Setup"
- **Windows**: Check that applications are playing audio through your default output device
- **All platforms**: Verify the system audio is working by playing music

### **"API key errors"**
- Verify your API keys are correctly copied to the `.env` file
- Ensure OpenAI key starts with `sk-`
- Test your Google AI key at https://aistudio.google.com/

### **"Rate limit errors from Gemini API"**
- Live Transcripts uses Gemini 2.5 Pro for higher rate limits
- If you still hit limits, consider reducing `INSIGHT_INTERVAL` in your `.env` file
- Free tier: 2 requests per minute | Paid tier: 1000 requests per minute
- Monitor usage at https://aistudio.google.com/

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

**OpenAI GPT-4o Transcription**: ~$0.006 per minute of audio (same cost as Whisper with better accuracy)
**Google AI (Gemini)**: ~$0.001 per 1K characters for Q&A

*Example: A 1-hour meeting costs approximately $0.36 for transcription + ~$0.10 for Q&A = **$0.46 total***

## ❓ Frequently Asked Questions

### **Why don't I see transcriptions when using headphones/AirPods?**
On macOS, you MUST keep "Live Transcripts Setup" as your system output device. When you switch directly to headphones/AirPods, audio bypasses BlackHole and can't be captured. The multi-output device sends audio to BOTH your headphones AND BlackHole for transcription.

### **Can I use this with Bluetooth headphones?**
Yes! Just make sure to:
1. Add your Bluetooth device to the multi-output device in Audio MIDI Setup
2. Keep "Live Transcripts Setup" as your system output
3. Set your Bluetooth device as the "Master Device" in the multi-output configuration

### **Do I need to change audio settings every time?**
No, once configured, just leave "Live Transcripts Setup" as your default output. It works for all scenarios - speakers, wired headphones, or Bluetooth devices.

## 🛠️ Available Scripts

The project includes several helpful scripts in the `scripts/` directory:

### Configuration Scripts
- **`configure.sh`** - Main setup script that handles everything
- **`configure-linux.sh`** - Linux-specific audio backend configuration
- **`configure-windows.sh`** - Windows-specific setup
- **`configure-macos.sh`** - macOS-specific setup (placeholder)
- **`configure-audio-device.sh`** - Select specific audio input/output devices

### Running Scripts  
- **`dev-run.sh`** - Run in development mode with full logging (recommended)
- **`run.sh`** - Alias for dev-run.sh
- **`start.sh`** - Start the service in background
- **`stop.sh`** - Stop the background service

### Utility Scripts
- **`list-audio-devices.sh`** - List all available audio devices
- **`check-env.sh`** - Verify environment and dependencies

### Usage Examples
```bash
# Initial setup
./scripts/configure.sh

# Run with live logs (Ctrl+C to stop)
./scripts/dev-run.sh

# List audio devices
./scripts/list-audio-devices.sh

# Change audio device
./scripts/configure-audio-device.sh
```

## 📞 Support

- **Issues**: Report problems at [GitHub Issues](https://github.com/your-repo/issues)
- **Feature Requests**: Submit ideas for new features
- **Documentation**: Full technical docs available in the `/docs` folder

## 🎉 Ready to Transform Your Meetings?

Live Transcripts turns every meeting into an interactive, searchable, and actionable experience. Start capturing insights from your conversations today!

---

*Built with ❤️ for teams who want to get more value from their meetings*