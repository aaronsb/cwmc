# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a live meeting transcription and interaction system that:
- Captures system audio in real-time from meetings/calls
- Uses OpenAI Whisper API for transcription with intelligent batching
- Integrates with Gemini API for live Q&A and automated insights
- Provides true real-time interaction capabilities during ongoing meetings

## Architecture

**Core Components:**
- Audio capture layer with platform-specific system audio loopback
- VAD-based intelligent batching (silence detection to preserve word boundaries)
- Async Whisper API integration with context preservation
- Gemini API integration for live Q&A and batch insights
- WebSocket-based real-time UI

**Key Design Principles:**
- Local-first architecture (all processing on-device except API calls)
- Variable batch sizing triggered by silence detection (3-30 second range)
- Rolling context window for AI processing
- Cross-platform compatibility (macOS, Windows, Linux)

## Development Workflow

### Test-Driven Development (TDD)
This project follows TDD principles with comprehensive test coverage:

**Test Structure:**
- `tests/test_audio_capture.py` - Cross-platform audio capture and VAD testing
- `tests/test_batching.py` - Intelligent batching with silence detection
- `tests/test_whisper_integration.py` - OpenAI Whisper API integration
- `tests/test_gemini_integration.py` - Google Gemini API and context management
- `tests/test_live_qa.py` - WebSocket Q&A server and session management
- `tests/conftest.py` - Shared fixtures and test utilities

**Running Tests:**
```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-coverage     # Tests with coverage report
make test-audio        # Audio-specific tests
```

### Code Quality
```bash
make format      # Format code with black and isort
make lint        # Run flake8 linting
make type-check  # Run mypy type checking
make check       # Run all quality checks
```

### Development Setup
```bash
make install-dev    # Install with development dependencies
make dev-setup      # Complete development environment setup
```

### Implementation Guidelines

**Module Structure:**
- `src/livetranscripts/audio_capture.py` - AudioCapture, PlatformAudioCapture classes
- `src/livetranscripts/batching.py` - VADAudioBatcher, SilenceDetector, BatchQueue
- `src/livetranscripts/whisper_integration.py` - WhisperClient, TranscriptionResult
- `src/livetranscripts/gemini_integration.py` - GeminiClient, QAHandler, ContextManager
- `src/livetranscripts/live_qa.py` - LiveQAServer, WebSocketHandler, SessionManager

**Key Classes to Implement:**
1. `AudioCapture` with platform-specific implementations (macOS/Windows/Linux)
2. `VADAudioBatcher` with silence detection and variable batch sizing
3. `WhisperClient` with retry logic and async processing
4. `QAHandler` with rolling context window management
5. `LiveQAServer` with WebSocket support for real-time Q&A

**Testing Approach:**
- All classes have corresponding test files with comprehensive coverage
- Mock external APIs (OpenAI, Google) for unit tests
- Use realistic audio data and meeting scenarios in tests
- Test error conditions, timeouts, and edge cases
- Verify cross-platform compatibility

### API Dependencies
- OpenAI API key required for Whisper transcription
- Google AI API key required for Gemini Q&A and insights
- Uses Gemini 2.0 Flash-Lite (gemini-2.0-flash-lite) for optimized rate limits and fast responses
- Set via environment variables: `OPENAI_API_KEY`, `GOOGLE_API_KEY`

### Platform-Specific Notes
- **macOS**: Requires BlackHole virtual audio driver for system audio capture
- **Windows**: Uses WASAPI loopback mode (built-in)
- **Linux**: Requires PulseAudio for system audio capture

### Audio Processing Requirements
- 16kHz sample rate (optimized for Whisper)
- Mono audio (single channel)
- VAD threshold: 500ms silence detection
- Batch range: 3-30 seconds with 0.5s overlap
- Ring buffer: 10 seconds for resilient streaming

## Implementation Status

✅ **COMPLETED MODULES** (Ready for testing):
- `audio_capture.py` - Cross-platform audio capture with macOS/Windows/Linux support
- `batching.py` - VAD-based intelligent batching with silence detection
- `whisper_integration.py` - OpenAI Whisper API client with retry logic
- `gemini_integration.py` - Google Gemini API integration with context management
- `live_qa.py` - WebSocket server for real-time Q&A
- `main.py` - Complete application orchestration
- `server.py` - Standalone Q&A server mode

🧪 **TESTING STATUS**: 
- ✅ Comprehensive test suite implemented (TDD approach)
- ✅ Full system tested and verified working
- ✅ Both OpenAI and Google APIs tested successfully
- ✅ Audio processing pipeline validated
- ✅ Q&A and insights generation working
- ✅ WebSocket server functional
- ✅ Complete user workflow tested
- 🔄 Run `make test` to execute full test suite against implementations

🚀 **READY TO RUN**:
```bash
# Set up environment
export OPENAI_API_KEY="your-openai-key"
export GOOGLE_API_KEY="your-google-key"

# Install dependencies
make install-dev

# Run full application
python -m src.livetranscripts.main

# Or run Q&A server only
python -m src.livetranscripts.server
```

## Implementation Details

**Key Features Implemented:**
- ✅ Real-time system audio capture (BlackHole/WASAPI/PulseAudio)
- ✅ Intelligent VAD-based batching (3-30s with silence detection)
- ✅ Async Whisper API integration with retry logic
- ✅ Rolling context window for Gemini AI processing
- ✅ WebSocket server for live Q&A
- ✅ **Dynamic contextual questions** - AI-generated questions that adapt to meeting content every 15 seconds
- ✅ Automated insight generation (summaries, action items, questions)
- ✅ Modern, sleek UI inspired by Atlassian design system
- ✅ Session management and error handling
- ✅ Cross-platform compatibility

**Architecture Flow:**
```
Audio Capture → VAD Batching → Whisper API → Context Manager → 
→ [Gemini Q&A | Automated Insights | Dynamic Questions] → WebSocket Clients
```

**Full Transcript Context System:**
- **ALL Gemini API calls use the COMPLETE transcript from meeting start**
- No rolling window - leverages Gemini's 2M token context window
- Context accumulates throughout the meeting for comprehensive understanding
- Q&A can reference any part of the meeting, not just recent discussion
- Insights generated with full meeting context for better accuracy
- Contextual questions consider all topics discussed, not just recent ones

**Dynamic Questions System:**
- Background task generates contextual questions every 15 seconds
- Uses FULL transcript history (not just recent context) via Gemini API
- WebSocket broadcasts `suggested_questions` message type
- Client-side rotation updates one question slot at a time
- Smooth fade-out/fade-in animations for seamless UX
- "Summarize recent discussion" always remains available

**Entry Points:**
- `main.py` - Full live transcription system
- `server.py` - Standalone Q&A server (no audio capture)

**Configuration Options:**
- Audio: sample rate, chunk size, buffer duration
- Batching: min/max duration, silence threshold, overlap
- APIs: model selection, temperature, timeouts
- Server: host, port, session limits

## Next Steps for Development

🔧 **Testing & Validation:**
1. Run test suite: `make test`
2. Fix any implementation issues revealed by tests
3. Test with real audio input
4. Validate API integrations

📊 **Monitoring & Observability:**
- Application provides real-time statistics
- Health checks for all components
- Error handling and recovery mechanisms

🎛️ **Configuration & Deployment:**
- Environment-based configuration
- Docker containerization (optional)
- Platform-specific audio driver setup

## Development Context

- When doing searches, remember that the current month is June 2025.
- Focus on minimum viable design principles
- Prioritize robust, resilient, portable architecture
- Implementation complete - now in testing/refinement phase
- Follow existing patterns when adding new functionality

## Development Guidance

- Make sure that you always update your claude.md after every major milestone is passed