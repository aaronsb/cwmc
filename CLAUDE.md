# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Live Transcripts is a real-time meeting transcription and AI-powered Q&A system that captures system audio, transcribes it using OpenAI's Whisper API, and provides live interaction capabilities through Google's Gemini API. The system features cross-platform support (macOS, Windows, Linux) with a focus on real-time processing and user interaction.

### Recent Updates (June 2025)

- **Audio Backend Abstraction Layer**: Implemented a clean abstraction layer for audio capture with support for multiple backends:
  - Linux: PipeWire (recommended), PulseAudio, SoundDevice, PyAudio
  - macOS: BlackHole, CoreAudio, SoundDevice, PyAudio  
  - Windows: WASAPI, SoundDevice, PyAudio
- **Profile-Based Configuration**: Simplified configuration system with OS-specific profiles (macos, linux, windows)
- **Enhanced Setup Scripts**: Comprehensive `configure.sh` with OS-specific sub-configurators for Linux audio backend selection
- **Fixed Dependencies**: Added PyYAML to dependencies for configuration support

## Common Development Commands

### Build & Setup
```bash
make install-dev       # Install with development dependencies
make dev-setup         # Complete development environment setup
```

### Testing
```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-coverage     # Tests with coverage report
make test-audio        # Audio-specific tests
```

### Code Quality
```bash
make format            # Format code with black and isort
make lint              # Run flake8 linting
make type-check        # Run mypy type checking
make check             # Run all quality checks (format, lint, type-check, test-unit)
```

### Running the Application
```bash
make run               # Run full application (python -m src.livetranscripts.main)
make run-server        # Run Q&A server only (python -m src.livetranscripts.server)
```

## High-Level Architecture

The system follows a pipeline architecture:

```
Audio Capture → VAD Batching → Whisper API → Context Manager → 
→ [Gemini Q&A | Automated Insights | Dynamic Questions] → WebSocket Clients
```

### Core Components

1. **Audio Capture Layer** (`audio_capture.py`)
   - Platform-specific implementations for macOS (BlackHole), Windows (WASAPI), Linux (PulseAudio)
   - 16kHz mono audio capture optimized for speech recognition
   - Ring buffer for resilient streaming

2. **Intelligent Batching** (`batching.py`)
   - Voice Activity Detection (VAD) with silence detection
   - Variable batch sizing (3-30 seconds) triggered by 500ms silence
   - Preserves word boundaries for accurate transcription

3. **Transcription** (`whisper_integration.py`)
   - OpenAI Whisper API integration with retry logic
   - Async processing for non-blocking operation
   - Context preservation across batches

4. **AI Integration** (`gemini_integration.py`)
   - Google Gemini API (2.0 Flash-Lite model) for Q&A and insights
   - Full transcript context (2M token window) - no rolling window
   - Dynamic contextual questions generated every 15 seconds
   - Session focus/intent customization

5. **Real-time Interface** (`live_qa.py`, `web_interface.html`)
   - WebSocket server for live Q&A
   - Modern, glassified UI design
   - Pinned Q&A cards feature
   - Session management

### Key Architectural Decisions

1. **Local-First Processing:** All audio processing happens on-device; only API calls go to cloud services
2. **Full Context Window:** Gemini uses complete transcript history (not rolling window) for comprehensive understanding
3. **Modular Design:** Clear separation between audio capture, transcription, AI processing, and UI layers
4. **Async Architecture:** Non-blocking async operations throughout for real-time performance
5. **Cross-Platform Support:** Abstract base classes with platform-specific implementations
6. **WebSocket Communication:** Real-time bidirectional communication between server and web clients
7. **Session-Based Focus:** Users can set meeting intent/focus to customize AI behavior dynamically

## Development Context

### API Requirements
- `OPENAI_API_KEY` - Required for Whisper transcription
- `GOOGLE_API_KEY` - Required for Gemini Q&A and insights
- Uses Gemini 2.0 Flash-Lite (gemini-2.0-flash-lite) for optimized rate limits

### Platform-Specific Setup
- **macOS**: Requires BlackHole virtual audio driver for system audio capture
- **Windows**: Uses built-in WASAPI loopback
- **Linux**: Requires PulseAudio

### Test-Driven Development
The project follows TDD with comprehensive test coverage. Tests use mocked external dependencies for unit testing and include categories: unit, integration, slow, api, audio.

### Entry Points
- `main.py` - Full system with audio capture
- `server.py` - Standalone Q&A server mode (no audio capture)

## Implementation Status

The system is fully implemented and tested. All core modules are complete:
- Cross-platform audio capture
- VAD-based intelligent batching
- Whisper and Gemini API integrations
- WebSocket server for real-time Q&A
- Dynamic contextual questions
- Modern UI with pinned Q&A cards

Run `make test` to verify the implementation and `make run` to start the application.