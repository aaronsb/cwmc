# Live Transcripts - Development Roadmap

## Project Goals

Transform Live Transcripts from a Gemini-only web app into a modular, flexible transcription and AI analysis system with:
1. **Backend flexibility:** Mix-and-match transcription and cognitive AI providers
2. **Local-first option:** GPU-accelerated local models for privacy and cost
3. **Better UI:** Native desktop app or TUI instead of web client-server
4. **Session management:** Persistent markdown logs of all conversations and insights

## Phase 0: Foundation & Planning ✅

**Status:** Complete (Jan 2025)

- [x] Fork project from forayconsulting/cwmc
- [x] Migrate from OpenAI to Gemini for transcription
- [x] Single API key setup (GOOGLE_API_KEY)
- [x] Verify working on Linux with PipeWire
- [x] Reorganize documentation
- [x] Create architecture documents

## Phase 1: Backend Abstraction

**Goal:** Create clean interfaces to support multiple backends

**Tasks:**
- [ ] Design abstract `TranscriptionBackend` interface
- [ ] Design abstract `CognitiveBackend` interface
- [ ] Create backend registry system
- [ ] Refactor existing Gemini code to use new interfaces
  - [ ] `GeminiTranscriptionBackend`
  - [ ] `GeminiCognitiveBackend`
- [ ] Add configuration system for backend selection
- [ ] Update tests to use abstract interfaces
- [ ] Document backend API for contributors

**Success Criteria:**
- Can swap backends via config without code changes
- Existing Gemini functionality unchanged
- Clean separation between transcription and cognitive processing

**Estimated Duration:** 1-2 weeks

## Phase 2: Session Logging System

**Goal:** Persist all conversations and insights as markdown

**Tasks:**
- [ ] Design markdown session format
- [ ] Implement session manager
  - [ ] Auto-create session files
  - [ ] Real-time writing during transcription
  - [ ] Flush/close on session end
- [ ] Add metadata (timestamps, backends used, tags)
- [ ] Implement search/indexing
- [ ] Add token usage tracking
- [ ] Create session viewer/browser
- [ ] Export options (PDF, HTML)
- [ ] Git integration for version control

**Success Criteria:**
- Every meeting automatically logged to markdown
- Searchable across all sessions
- Token/cost tracking visible
- Can resume or reference old sessions

**Estimated Duration:** 1-2 weeks

## Phase 3: OpenAI Backends

**Goal:** Add OpenAI as alternative cloud provider

**Tasks:**
- [ ] Implement `OpenAITranscriptionBackend`
  - [ ] Whisper API integration
  - [ ] Fallback handling
- [ ] Implement `OpenAICognitiveBackend`
  - [ ] GPT-4 integration for Q&A
  - [ ] GPT-4 integration for insights
  - [ ] Streaming support
- [ ] Update config validation
- [ ] Add cost comparison documentation
- [ ] Test mixed backends (e.g., Gemini transcription + OpenAI cognitive)

**Success Criteria:**
- Can use OpenAI for transcription, cognitive, or both
- Can mix Gemini and OpenAI backends
- Proper API key management for multiple providers

**Estimated Duration:** 1 week

## Phase 4: Local Model Research & Selection

**Goal:** Identify best local models for GPU inference

**Tasks:**
- [ ] Research current SOTA transcription models
  - [ ] Benchmark faster-whisper
  - [ ] Test alternatives (distil-whisper, Moonshine, etc.)
  - [ ] Measure WER and RTF on target hardware
- [ ] Research current SOTA local LLMs
  - [ ] Test Qwen2.5/3, Llama 3.1+, others
  - [ ] Benchmark reasoning quality
  - [ ] Test context handling with long transcripts
- [ ] Test inference frameworks
  - [ ] vllm for LLMs
  - [ ] faster-whisper for audio
  - [ ] llama.cpp for flexibility
- [ ] Document findings and recommendations
- [ ] Create performance comparison matrix

**Success Criteria:**
- Identified best transcription model for local GPU
- Identified best LLM for local GPU
- Documented setup and performance metrics
- ROI analysis (cost vs cloud)

**Estimated Duration:** 1-2 weeks (research + testing)

## Phase 5: Local Backend Implementation

**Goal:** Full local GPU inference support

**Tasks:**
- [ ] Implement `WhisperGPUBackend`
  - [ ] faster-whisper integration
  - [ ] CUDA optimization
  - [ ] Batching strategy
- [ ] Implement `Qwen3Backend` (or chosen LLM)
  - [ ] vllm or llama.cpp integration
  - [ ] Context window management
  - [ ] Streaming inference
- [ ] Add model downloading/management
- [ ] VRAM monitoring and warnings
- [ ] Performance tuning
- [ ] Fallback to cloud if local unavailable
- [ ] Document hardware requirements

**Success Criteria:**
- Fully local transcription + Q&A working
- Real-time performance on target GPU
- No cloud dependencies when local mode enabled
- Graceful degradation if GPU unavailable

**Estimated Duration:** 2-3 weeks

## Phase 6: UI Modernization

**Goal:** Replace web UI with native desktop app

**Tasks:**
- [ ] Evaluate UI frameworks
  - [ ] PySide6/Qt prototype
  - [ ] Rich/Textual TUI prototype
  - [ ] KDE Plasma integration research
- [ ] Design new UI architecture
  - [ ] No WebSocket server needed
  - [ ] Direct Python integration
  - [ ] System tray support
- [ ] Implement Qt prototype
  - [ ] Main window with transcript view
  - [ ] Q&A panel
  - [ ] Settings dialog
  - [ ] Session browser
- [ ] KDE integration
  - [ ] D-Bus service for IPC
  - [ ] Krunner plugin for search
  - [ ] Optional Plasmoid widget
- [ ] Migrate all features from web UI
- [ ] Package for distribution

**Success Criteria:**
- Native desktop app with all features
- Better integration with desktop environment
- Simpler architecture (no client-server split)
- Optional: TUI alternative for terminal users

**Estimated Duration:** 3-4 weeks

## Phase 7: Polish & Documentation

**Goal:** Production-ready release

**Tasks:**
- [ ] Comprehensive user documentation
- [ ] Developer guide for adding backends
- [ ] Performance optimization
- [ ] Extensive testing
  - [ ] All backend combinations
  - [ ] Long-running sessions
  - [ ] GPU memory management
- [ ] Packaging and distribution
  - [ ] Python package (PyPI)
  - [ ] Flatpak
  - [ ] AppImage
  - [ ] AUR package for Arch Linux
- [ ] Example configurations
- [ ] Video tutorials
- [ ] Community setup (issues, discussions, wiki)

**Estimated Duration:** 2 weeks

## Future Ideas (Backlog)

- [ ] Multi-language transcription and translation
- [ ] Speaker diarization (who said what)
- [ ] Meeting summaries and action item extraction
- [ ] Calendar integration (auto-start for meetings)
- [ ] Slack/Discord bot integration
- [ ] API for third-party integrations
- [ ] Mobile companion app (view transcripts on phone)
- [ ] RAG integration (search across all past sessions)
- [ ] Custom model fine-tuning on your meeting style
- [ ] Screen recording + transcript sync
- [ ] Live collaborative note-taking

## Timeline Estimate

**Aggressive:** 3-4 months
**Realistic:** 5-6 months
**Conservative:** 6-9 months

Factors:
- Full-time vs part-time development
- Complexity of local model integration
- UI design iterations
- Testing and polish time

## Success Metrics

1. **Functionality:** All features from web version work in new UI
2. **Performance:** Local backends match or beat cloud latency
3. **Cost:** Local mode eliminates API costs for power users
4. **Privacy:** Fully local mode = zero data leaves machine
5. **UX:** Native UI feels better than web interface
6. **Adoption:** Community contributions and feedback

## Next Steps

1. Review and approve this roadmap
2. Begin Phase 1 (backend abstraction)
3. Set up project board for task tracking
4. Create development branch structure
5. Start building!