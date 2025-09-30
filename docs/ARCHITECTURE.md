# Live Transcripts - Architecture

## Project Vision

A modular, real-time audio transcription and AI analysis system with:
- **Pluggable backends** for transcription and cognitive processing
- **Local-first options** for privacy and performance
- **Flexible UI** (web, Qt, TUI, or KDE integration)
- **Session management** with persistent markdown logs

## Current State

### Working Features
- ✅ Gemini 2.0 transcription (cloud-based)
- ✅ Gemini 2.0 Q&A and insights (cloud-based)
- ✅ PipeWire audio capture (Linux)
- ✅ Web-based UI with WebSocket server
- ✅ Real-time transcription with VAD batching
- ✅ Single API key (GOOGLE_API_KEY)

### Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│  (Web UI, Qt App, TUI, or KDE Integration - TBD)       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                Application Controller                    │
│           (Orchestrates audio → AI pipeline)            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────┬──────────────────┬───────────────────┐
│  Audio Capture   │   Transcription  │  Cognitive AI     │
│   (PipeWire)     │     Backend      │     Backend       │
│                  │                  │                   │
│  • Linux         │  • Gemini (✓)    │  • Gemini (✓)     │
│  • macOS         │  • OpenAI (TODO) │  • OpenAI (TODO)  │
│  • Windows       │  • Whisper-GPU   │  • Qwen3 (TODO)   │
│                  │    (TODO)        │                   │
└──────────────────┴──────────────────┴───────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Session & Storage Manager                   │
│   (Markdown logs, conversation history, insights)       │
└─────────────────────────────────────────────────────────┘
```

## Planned Improvements

### 1. Modular Backend System

**Goal:** Decouple transcription and cognitive processing to support mix-and-match configurations.

**Design:**
```python
# Abstract interfaces
class TranscriptionBackend(ABC):
    @abstractmethod
    async def transcribe(self, audio_batch) -> TranscriptionResult:
        pass

class CognitiveBackend(ABC):
    @abstractmethod
    async def generate_insights(self, transcript) -> Insights:
        pass

    @abstractmethod
    async def answer_question(self, question, context) -> Answer:
        pass
```

**Supported Configurations:**
- Gemini + Gemini (current)
- Gemini + OpenAI
- Whisper-GPU + Qwen3 (local-only)
- OpenAI + Gemini
- Mix any transcription with any cognitive backend

**Backend Registry:**
```python
backends = {
    'transcription': {
        'gemini': GeminiTranscriptionBackend,
        'openai': OpenAITranscriptionBackend,
        'whisper-gpu': WhisperGPUBackend,
    },
    'cognitive': {
        'gemini': GeminiCognitiveBackend,
        'openai': OpenAICognitiveBackend,
        'qwen3': Qwen3Backend,
    }
}
```

### 2. Local Backend Support

**Whisper GPU (Transcription):**
- Use `faster-whisper` with CUDA support
- Target: RTX 3060+ or better
- ~100ms latency for real-time transcription
- No API costs, fully private

**Qwen3 (Cognitive):**
- Use `llama.cpp` or `vllm` for local inference
- Qwen2.5-14B-Instruct fits well in 24GB VRAM
- Excellent multilingual support
- Fast inference on modern GPUs

**Benefits:**
- Privacy: No data leaves your machine
- Cost: Zero API fees
- Speed: Lower latency for local GPU
- Offline: Works without internet

### 3. UI Options

**Current: Web UI**
- Pros: Cross-platform, modern, feature-rich
- Cons: Complex (WebSocket server, HTTP server, client-side JS)

**Option A: Qt/PySide6 Desktop App**
```
Pros:
- Native desktop integration
- No server/client architecture
- Better KDE Plasma integration
- System tray support
- Simpler deployment

Cons:
- Need to rewrite UI
- Platform-specific packaging
```

**Option B: Terminal UI (TUI)**
```
Library: textual or rich
Pros:
- Lightweight, fast
- SSH-friendly
- Minimal dependencies
- Great for power users

Cons:
- Limited visual features
- No multimedia support
```

**Option C: KDE Plasma Integration**
```
- Plasmoid/Widget for real-time transcription
- D-Bus integration for system-wide access
- Native notifications
- Krunner plugin for search/Q&A
```

**Recommendation:** Start with Qt app, add TUI as alternative

### 4. Session Logging System

**Goal:** Persist all transcriptions, Q&A, and insights as searchable markdown.

**Design:**
```
sessions/
  2025-01-15/
    morning-standup-0900.md
    client-call-1400.md
  2025-01-16/
    team-sync-1000.md

# Session file format:
---
session_id: abc-123
start_time: 2025-01-15T09:00:00
end_time: 2025-01-15T09:30:00
transcription_backend: gemini-2.0-flash-lite
cognitive_backend: gemini-2.0-flash-lite
tags: [standup, team-meeting]
---

## Transcript

[09:00:15] Alice: Good morning everyone...
[09:00:18] Bob: Hey, ready for standup?

## Q&A

**Q:** What decisions were made?
**A:** The team decided to...

## Insights

- Key topic: Sprint planning
- Action items:
  - Bob to review PR #123
  - Alice to update docs
```

**Features:**
- Full-text search across all sessions
- Export to PDF, HTML, or keep as markdown
- Git-friendly format
- Token usage tracking (local vs cloud)
- Cost analysis for API usage

## Configuration System

```yaml
# config.yaml
audio:
  backend: pipewire
  device: auto

transcription:
  backend: gemini  # or: openai, whisper-gpu
  model: gemini-2.0-flash-lite-transcribe

cognitive:
  backend: gemini  # or: openai, qwen3
  model: gemini-2.0-flash-lite

ui:
  type: qt  # or: web, tui, kde-widget

session:
  auto_save: true
  output_dir: ./sessions
  format: markdown
```

## Migration Path

1. **Phase 1:** Refactor to abstract backend interfaces
2. **Phase 2:** Add OpenAI backends (transcription + cognitive)
3. **Phase 3:** Implement local backends (Whisper-GPU + Qwen3)
4. **Phase 4:** Build Qt desktop UI
5. **Phase 5:** Add session logging and markdown exports
6. **Phase 6:** KDE Plasma widget (optional)

## Development Priorities

1. ✅ **Done:** Gemini integration working
2. **Next:** Backend abstraction layer
3. **Then:** Session logging to markdown
4. **After:** Qt UI prototype
5. **Future:** Local backends (GPU acceleration)