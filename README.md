# Live Transcripts 🎤

Transform your meetings with AI-powered real-time transcription and intelligent Q&A. Live Transcripts captures system audio, transcribes it instantly using OpenAI's GPT-4o models, and enables contextual conversations about ongoing discussions—all while your meeting continues.

![Live Transcripts Screenshot](screenshot.jpeg)

## 🌟 Key Features

Live Transcripts combines cutting-edge AI technologies to create a seamless meeting intelligence platform:

| Feature | Description | Technology |
|---------|-------------|------------|
| **Real-time Transcription** | Instant speech-to-text with 30-40% better accuracy | GPT-4o (with Whisper fallback) |
| **Live Q&A** | Ask questions about ongoing discussions | Google Gemini 2.0 |
| **Smart Questions** | Context-aware suggestions updated every 15 seconds | Dynamic AI Analysis |
| **Auto Insights** | Meeting summaries, action items, and follow-ups | Automated every 60 seconds |
| **Knowledge Base** | Integrate reference documents for enhanced context | Local file processing |
| **Session Focus** | Customize AI behavior for specific meeting types | Intent-based adaptation |

## ⚡ Quick Start

Get up and running in under 5 minutes:

```bash
# One-line setup
curl -sSL https://raw.githubusercontent.com/forayconsulting/cwmc/master/scripts/quick-setup.sh | bash

# Or manual setup
git clone https://github.com/forayconsulting/cwmc.git
cd cwmc
./scripts/configure.sh
./scripts/dev-run.sh
```

The setup wizard will guide you through API key configuration, audio device selection, and platform-specific requirements.

## 📋 Prerequisites

Before installation, ensure you have:

- **Python 3.9+** installed
- **OpenAI API Key** for transcription ([Get one here](https://platform.openai.com/api-keys))
- **Google AI API Key** for Q&A ([Get one here](https://aistudio.google.com/app/apikey))
- **Audio capture** configured for your OS (detailed below)

## 🔧 Platform Setup

### macOS Configuration

macOS requires BlackHole for system audio capture. Here's the complete setup:

1. **Install BlackHole**
   ```bash
   brew install blackhole-2ch
   ```

2. **Create Multi-Output Device**
   - Open **Audio MIDI Setup** (Spotlight → "Audio MIDI Setup")
   - Click **"+"** → **"Create Multi-Output Device"**
   - Check boxes for:
     - ✅ BlackHole 2ch (required)
     - ✅ Your speakers/headphones
   - Name it "Live Transcripts"
   - Set your preferred device as Master (not BlackHole)

3. **Set System Output**
   - System Preferences → Sound → Output
   - Select "Live Transcripts" multi-output device
   - This routes audio to both your speakers and transcription

### Windows Configuration

Windows includes built-in WASAPI loopback support—no additional setup required! The application automatically captures system audio.

### Linux Configuration

Linux supports multiple audio backends with automatic detection:

```bash
# Install dependencies (choose based on your distro)
# Ubuntu/Debian:
sudo apt-get install portaudio19-dev pulseaudio

# Fedora:
sudo dnf install portaudio-devel pulseaudio

# Configure audio backend
./scripts/configure-linux.sh
```

Supported backends: PipeWire (recommended), PulseAudio, ALSA, JACK

## 💡 Usage Scenarios

Live Transcripts adapts to your specific needs through customizable Session Focus settings:

### Business Meetings

**Focus**: *"Identify action items and decisions"*

The AI will:
- Highlight assignments with owners and deadlines
- Track key decisions and their rationale
- Generate follow-up questions about implementation
- Surface risks and dependencies

### Sales Calls

**Focus**: *"Track objections and buying signals"*

Automatically:
- Identifies customer pain points and concerns
- Highlights positive buying indicators
- Suggests qualifying questions in real-time
- Tracks pricing discussions and next steps

### Technical Discussions

**Focus**: *"Capture technical details and architecture decisions"*

Features:
- Accurate transcription of technical terminology
- Tracking of design decisions and trade-offs
- Integration points and dependencies
- Action items for technical implementation

### Training & Education

**Focus**: *"Monitor comprehension and engagement"*

Provides:
- Questions that check understanding
- Identification of topics needing clarification
- Engagement metrics and participation tracking
- Summary of key learning points

## 🚀 Running Live Transcripts

### Starting the Application

```bash
# Development mode (recommended - shows all logs)
./scripts/dev-run.sh

# Or using make
make dev

# Direct Python execution
python -m src.livetranscripts.main
```

You'll see the startup confirmation:
```
✓ Audio capture initialized
✓ Batch processor initialized  
✓ GPT-4o transcription initialized
✓ Gemini integration initialized
🎤 Live Transcripts is running!
📡 WebSocket server: ws://localhost:8765
⏸️ Recording starts paused - click Start in web UI
```

### Web Interface

Open `http://localhost:8765` in your browser to access:

- **Recording Control**: Start/stop transcription
- **Session Focus**: Set meeting intent
- **Live Transcripts**: Real-time speech-to-text
- **Smart Q&A**: Ask questions with suggested prompts
- **Insights Panel**: Auto-generated summaries
- **Knowledge Base**: Upload reference documents

### API Integration

Connect via WebSocket for programmatic access:

```javascript
const ws = new WebSocket('ws://localhost:8765');

// Ask a question
ws.send(JSON.stringify({
  type: 'question',
  question: 'What were the main decisions?',
  request_id: 'q123'
}));

// Receive structured response
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response.answer);
};
```

## 📊 Advanced Configuration

Customize behavior through environment variables:

```bash
# Transcription
TRANSCRIPTION_MODEL=gpt-4o-transcribe  # or gpt-4o-mini-transcribe, whisper-1
MODEL_FALLBACK=whisper-1                # Automatic fallback model

# Processing
MIN_BATCH_DURATION=3   # Minimum seconds before transcription
MAX_BATCH_DURATION=30  # Maximum batch size
SILENCE_THRESHOLD=500  # Milliseconds of silence to trigger batch

# AI Models
GEMINI_MODEL=gemini-2.0-flash-lite  # Optimized for rate limits
INSIGHT_INTERVAL=60                 # Seconds between auto-insights

# Server
SERVER_HOST=localhost
SERVER_PORT=8765
```

## 🔒 Privacy & Security

Your data remains secure through multiple layers of protection:

- **Local Processing**: Audio analysis happens on your device
- **No Storage**: Audio is never saved to disk
- **API-Only**: Only transcribed text sent to cloud services
- **Encrypted Keys**: API credentials stored locally in `.env`
- **Session Isolation**: Each session's context is independent

## 💰 Cost Analysis

Typical usage costs per hour:

| Component | Model | Rate | Hourly Cost |
|-----------|-------|------|-------------|
| Transcription | GPT-4o | $0.006/min | $0.36 |
| Q&A & Insights | Gemini 2.0 | ~$0.001/1K chars | ~$0.10 |
| **Total** | | | **~$0.46/hour** |

*Note: Costs scale with speaking time, not meeting duration*

## 🛠️ Troubleshooting

### Common Issues

**No Audio Capture**
- macOS: Verify "Live Transcripts" is selected as system output
- Windows: Check default audio device in Sound settings
- Linux: Run `./scripts/list-audio-devices.sh` to verify device

**Poor Transcription Quality**
- Ensure clear audio without echo/feedback
- Check microphone levels aren't clipping
- Minimize background noise
- Verify correct audio device selected

**API Errors**
- Confirm API keys in `.env` file
- Check rate limits in provider dashboards
- Verify internet connectivity
- Review error logs for specifics

### Performance Optimization

For large meetings or multiple speakers:

```bash
# Increase batch size for stability
MAX_BATCH_DURATION=45

# Reduce insight frequency  
INSIGHT_INTERVAL=120

# Adjust silence detection
SILENCE_THRESHOLD=750
```

## 📚 Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Audio Capture  │────▶│  VAD Batching    │────▶│ GPT-4o/Whisper  │
│  (Platform API) │     │  (Smart Chunks)  │     │ (Transcription) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Web UI/API    │◀────│  Gemini Q&A      │◀────│ Context Manager │
│  (WebSocket)    │     │  (Insights)      │     │  (Full History) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 🤝 Contributing

We welcome contributions! Key areas for enhancement:

- Additional audio backend support
- Enhanced language support
- Custom insight generators
- Integration plugins
- UI improvements

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

Built with ❤️ by teams who believe every conversation holds valuable insights.