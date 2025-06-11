# Live Transcripts Usage Guide 📖

This guide walks you through using Live Transcripts for real-world scenarios, from your first test to advanced meeting intelligence workflows.

## 🎯 Quick Start Checklist

Before your first session, ensure:

- [x] Virtual environment activated (`source venv/bin/activate`)
- [x] API keys configured in `.env` file
- [x] Audio loopback set up for your platform
- [x] Dependencies installed (`pip install -e ".[dev]"`)

## 🚀 Starting Your First Session

### Step 1: Launch the Application

```bash
# Navigate to project directory
cd livetranscripts

# Activate environment
source venv/bin/activate

# Start the application
./scripts/dev-run.sh
```

**Expected Output:**
```
🎤 Live Transcripts is running!
📡 WebSocket server: ws://localhost:8765
⏸️ Recording starts paused - click Start in web UI
Press Ctrl+C to stop...
```

### Step 2: Open the Web Interface

Navigate to `http://localhost:8765` in your browser. You'll see:

![Web Interface Overview]
```
┌─────────────────────────────────────────────┐
│  🔴 Start Recording    Session Focus: [___] │
├─────────────────────────────────────────────┤
│  Live Transcript                            │
│  (Transcribed text appears here)            │
├─────────────────────────────────────────────┤
│  Ask a Question                             │
│  [___________________________] [Send]       │
│                                             │
│  Suggested Questions:                       │
│  • What was just discussed?                │
│  • Summarize the last 5 minutes            │
├─────────────────────────────────────────────┤
│  Insights & Action Items                    │
│  (Auto-generated every 60 seconds)          │
└─────────────────────────────────────────────┘
```

### Step 3: Configure Your Session

Before starting recording:

1. **Set Session Focus** - Choose or type your meeting intent:
   - "Track action items and decisions"
   - "Identify technical requirements"
   - "Monitor sales objections"
   - Custom: "Find collaboration opportunities"

2. **Upload Knowledge Base** (Optional) - Add reference documents:
   - Click "Knowledge Base" → "Add Files"
   - Upload PDFs, docs, or text files
   - AI will use these for context

3. **Test Audio** - Play a video or speak to verify capture

### Step 4: Start Recording

Click the **Start Recording** button. The system will begin:
- Capturing system audio
- Transcribing in real-time
- Generating contextual questions
- Creating periodic insights

## 💼 Real-World Usage Scenarios

### Team Stand-up Meeting

**Setup:**
- Session Focus: "Track task updates and blockers"
- Knowledge Base: Sprint backlog document

**During the Meeting:**
```
Transcript:
[09:00:15] Sarah: I finished the API integration yesterday.
[09:00:28] Sarah: Today I'm working on the frontend components.
[09:00:41] John: I'm blocked on the database migration issue.

Smart Questions (auto-updated):
• What tasks did Sarah complete?
• Who is blocked and why?
• What are today's priorities?
```

**Ask Custom Questions:**
- "What blockers were mentioned?"
- "Create a task list for today"
- "Who needs help with their work?"

### Client Discovery Call

**Setup:**
- Session Focus: "Identify pain points and requirements"
- Knowledge Base: Product documentation, pricing sheet

**Live Interaction Example:**
```
You: "What specific problems has the client mentioned?"

AI: "The client has mentioned three main problems:
1. Current system is too slow (processing takes 5 minutes)
2. Lack of mobile access for field teams
3. Integration issues with their CRM system

They emphasized that speed is their top priority."
```

### Technical Architecture Review

**Setup:**
- Session Focus: "Capture technical decisions and rationale"
- Knowledge Base: System architecture docs, API specs

**Advanced Usage:**
```javascript
// Connect programmatically for automated logging
const ws = new WebSocket('ws://localhost:8765');

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.type === 'insight' && msg.category === 'DECISION') {
    // Log architectural decisions to your system
    logToConfluence(msg.content);
  }
});
```

## 🎨 Advanced Features

### Dynamic Session Management

Change focus mid-meeting as topics evolve:

1. **Initial Focus**: "General team discussion"
2. **Topic Shifts**: Notice conversation moving to budgets
3. **Update Focus**: Change to "Track financial decisions"
4. **AI Adapts**: Questions and insights now finance-focused

### Knowledge Base Integration

Enhance AI understanding with context:

| Document Type | Use Case | Example |
|--------------|----------|---------|
| Meeting Agendas | Structure tracking | "What agenda items remain?" |
| Technical Specs | Accuracy improvement | "Does this match our API spec?" |
| Previous Minutes | Continuity | "What was decided last week?" |
| Company Policies | Compliance | "Does this follow our process?" |

### Custom Integrations

Build on the WebSocket API:

```python
import websocket
import json

class MeetingBot:
    def __init__(self):
        self.ws = websocket.WebSocket()
        self.ws.connect("ws://localhost:8765")
    
    def ask_question(self, question):
        self.ws.send(json.dumps({
            "type": "question",
            "question": question,
            "request_id": "bot_001"
        }))
        response = json.loads(self.ws.recv())
        return response["answer"]
    
    def monitor_insights(self):
        while True:
            msg = json.loads(self.ws.recv())
            if msg["type"] == "insight":
                self.process_insight(msg)
```

## 🔧 Optimization Tips

### For Long Meetings (2+ hours)

Edit `.env` for better stability:
```bash
MAX_BATCH_DURATION=45      # Larger chunks
INSIGHT_INTERVAL=120       # Less frequent insights
SILENCE_THRESHOLD=1000     # Longer pause detection
```

### For Fast-Paced Discussions

Optimize for rapid speakers:
```bash
MIN_BATCH_DURATION=2       # Faster processing
SILENCE_THRESHOLD=300      # Quick batch triggers
INSIGHT_INTERVAL=45        # More frequent updates
```

### For Noisy Environments

Improve accuracy in challenging audio:
```bash
TRANSCRIPTION_MODEL=gpt-4o-transcribe  # Best noise handling
AUDIO_GAIN=1.5                         # Boost audio input
NOISE_REDUCTION=true                   # Enable filtering
```

## 📊 Monitoring & Metrics

### Session Statistics

Track performance in real-time:
```
Session Duration: 45:23
Words Transcribed: 8,432
Questions Asked: 12
Insights Generated: 15
API Cost Estimate: $0.34
```

### Quality Indicators

Watch for these signals:
- **Green**: Clear transcription, minimal corrections
- **Yellow**: Some missed words, background noise
- **Red**: Poor audio quality, consider adjusting setup

## 🆘 Troubleshooting Guide

### Issue: Transcription Lag

**Symptoms**: Text appears 10+ seconds after speech

**Solutions**:
1. Check internet connection speed
2. Reduce `MAX_BATCH_DURATION` to 20
3. Ensure CPU isn't overloaded
4. Try `gpt-4o-mini-transcribe` model

### Issue: Missing Speaker Audio

**Symptoms**: Only hearing one side of conversation

**Platform-Specific Fixes**:
- **macOS**: Verify multi-output device includes all sources
- **Windows**: Check "Listen to this device" settings
- **Linux**: Confirm `.monitor` device selected

### Issue: Questions Not Contextual

**Symptoms**: Generic questions despite rich discussion

**Solutions**:
1. Set specific Session Focus
2. Add relevant Knowledge Base docs
3. Ensure sufficient conversation history (5+ minutes)
4. Check Gemini API isn't rate limited

## 🎯 Best Practices

### Before Important Meetings

1. **Test Run**: Do a 5-minute test with similar audio setup
2. **Clear Context**: Start fresh session (restart app)
3. **Prepare Knowledge Base**: Upload relevant documents
4. **Set Intent**: Choose specific, actionable focus
5. **Check APIs**: Verify rate limits and quotas

### During Meetings

- **Monitor Quality**: Watch transcription accuracy
- **Ask Clarifying Questions**: "What did John mean by X?"
- **Pin Important Insights**: Mark critical action items
- **Adjust Focus**: Update intent as topics change
- **Take Screenshots**: Capture important moments

### After Meetings

1. **Export Transcript**: Save full text record
2. **Review Insights**: Compile action items
3. **Share Summary**: Distribute AI-generated summary
4. **Update Systems**: Log decisions in project tools
5. **Analyze Metrics**: Review session statistics

## 🚀 Power User Tips

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Toggle recording |
| `Ctrl+Q` | Quick question |
| `Ctrl+I` | Force insight generation |
| `Ctrl+S` | Save transcript |
| `Ctrl+K` | Clear context |

### Command Line Options

```bash
# Start with custom port
python -m src.livetranscripts.main --port 9000

# Use specific audio device
python -m src.livetranscripts.main --device "BlackHole 2ch"

# Enable debug logging
python -m src.livetranscripts.main --debug

# Start in server-only mode (no audio)
python -m src.livetranscripts.server
```

### Integration Recipes

**Slack Integration**:
```bash
# Post insights to Slack
curl -X POST https://hooks.slack.com/YOUR_WEBHOOK \
  -d "{'text': '$(python get_insights.py)'}"
```

**Email Summaries**:
```python
# Auto-email meeting summaries
import smtplib
from livetranscripts import get_summary

summary = get_summary()
send_email(recipient, subject="Meeting Summary", body=summary)
```

## 🎉 You're Ready!

With Live Transcripts running, you now have:

- 🎤 **Real-time transcription** of any audio source
- 💬 **Intelligent Q&A** about ongoing discussions  
- 🎯 **Contextual insights** tailored to your goals
- 📊 **Actionable intelligence** from every conversation

Start transforming your meetings into structured, searchable, and actionable knowledge today!