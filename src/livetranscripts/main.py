"""Main application entry point for Live Transcripts."""

import asyncio
import os
import signal
import sys
from typing import Optional
import argparse
from datetime import datetime
from dotenv import load_dotenv

from .audio_capture import AudioCapture, AudioCaptureConfig
from .batching import BatchProcessor, BatchingConfig
from .whisper_integration import WhisperClient, WhisperConfig, TranscriptionManager
from .gemini_integration import (
    GeminiClient, GeminiConfig, ContextManager, 
    QAHandler, InsightGenerator
)
from .live_qa import LiveQAServer, run_qa_server


class LiveTranscriptsApp:
    """Main application class for Live Transcripts."""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.is_running = False
        
        # Components
        self.audio_capture: Optional[AudioCapture] = None
        self.batch_processor: Optional[BatchProcessor] = None
        self.whisper_client: Optional[WhisperClient] = None
        self.transcription_manager: Optional[TranscriptionManager] = None
        self.gemini_client: Optional[GeminiClient] = None
        self.context_manager: Optional[ContextManager] = None
        self.qa_handler: Optional[QAHandler] = None
        self.insight_generator: Optional[InsightGenerator] = None
        self.qa_server: Optional[LiveQAServer] = None
        
        # Tasks
        self.tasks = []
        
        # Recording state
        self.recording_paused: bool = False
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.stats = {
            'audio_chunks_processed': 0,
            'batches_created': 0,
            'transcriptions_completed': 0,
            'questions_answered': 0,
            'insights_generated': 0
        }
    
    def initialize(self) -> None:
        """Initialize all components."""
        print("Initializing Live Transcripts...")
        
        # Get API keys
        openai_key = os.getenv('OPENAI_API_KEY')
        google_key = os.getenv('GOOGLE_API_KEY')
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable required")
        if not google_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")
        
        # Initialize configurations
        audio_config = AudioCaptureConfig(
            sample_rate=self.config.get('sample_rate', 16000),
            channels=1,
            chunk_size=self.config.get('chunk_size', 1024),
            buffer_duration=self.config.get('buffer_duration', 10.0)
        )
        
        batching_config = BatchingConfig(
            min_batch_duration=self.config.get('min_batch_duration', 4.5),
            max_batch_duration=self.config.get('max_batch_duration', 45.0),
            silence_threshold=self.config.get('silence_threshold', 500),
            sample_rate=audio_config.sample_rate
        )
        
        whisper_config = WhisperConfig(
            model=self.config.get('whisper_model', 'whisper-1'),
            language=self.config.get('language'),
            temperature=self.config.get('whisper_temperature', 0.0)
        )
        
        gemini_config = GeminiConfig(
            model=self.config.get('gemini_model', 'gemini-1.5-flash'),
            temperature=self.config.get('gemini_temperature', 0.3),
            context_window_minutes=self.config.get('context_window_minutes', 5),
            insight_interval_seconds=self.config.get('insight_interval_seconds', 60)
        )
        
        # Initialize components
        try:
            self.audio_capture = AudioCapture(audio_config)
            print("✓ Audio capture initialized")
            
            self.batch_processor = BatchProcessor(batching_config)
            print("✓ Batch processor initialized")
            
            self.whisper_client = WhisperClient(whisper_config, openai_key)
            self.transcription_manager = TranscriptionManager(self.whisper_client)
            print("✓ Whisper integration initialized")
            
            self.gemini_client = GeminiClient(gemini_config, google_key)
            self.context_manager = ContextManager(gemini_config)
            self.qa_handler = QAHandler(gemini_config, self.context_manager)
            self.insight_generator = InsightGenerator(gemini_config, self.context_manager)
            print("✓ Gemini integration initialized")
            
            # Set up API clients for handlers
            self.qa_handler.client = self.gemini_client
            self.insight_generator.client = self.gemini_client
            
            # Ensure all components use the correct model
            self.qa_handler.config = gemini_config
            self.insight_generator.config = gemini_config
            
            self.qa_server = LiveQAServer(
                host=self.config.get('server_host', 'localhost'),
                port=self.config.get('server_port', 8765),
                http_port=self.config.get('http_port', 8766),
                qa_handler=self.qa_handler
            )
            print("✓ Q&A server initialized")
            
            # Set up callbacks
            self.transcription_manager.add_result_callback(self._on_transcription_result)
            
            print("✓ All components initialized successfully")
            
        except Exception as e:
            print(f"✗ Initialization failed: {e}")
            raise
    
    async def start(self) -> None:
        """Start the application."""
        if not self.audio_capture:
            raise RuntimeError("Application not initialized")
        
        print("Starting Live Transcripts application...")
        self.is_running = True
        self.start_time = datetime.now()
        
        # Start components
        try:
            # Initialize and start audio capture
            await self.audio_capture.initialize()
            await self.audio_capture.start_capture()
            print("✓ Audio capture started")
            
            # Start batch processing
            await self.batch_processor.start_processing()
            print("✓ Batch processing started")
            
            # Start transcription processing
            await self.transcription_manager.start_processing()
            print("✓ Transcription processing started")
            
            # Start automated insights
            insight_callback = self._on_insight_generated
            insight_task = asyncio.create_task(
                self.insight_generator.start_automated_insights(insight_callback)
            )
            self.tasks.append(insight_task)
            print("✓ Automated insights started")
            
            # Set up recording control connection
            self.qa_server.set_main_app(self)
            
            # Start Q&A server
            server_task = asyncio.create_task(self.qa_server.start())
            self.tasks.append(server_task)
            print("✓ Q&A server started")
            
            # Start audio processing loop
            audio_task = asyncio.create_task(self._audio_processing_loop())
            self.tasks.append(audio_task)
            print("✓ Audio processing loop started")
            
            # Start intent synchronization task
            intent_task = asyncio.create_task(self._intent_sync_loop())
            self.tasks.append(intent_task)
            print("✓ Intent synchronization started")
            
            print(f"\n🎤 Live Transcripts is running!")
            print(f"📡 WebSocket server: ws://localhost:{self.qa_server.port}")
            print(f"🌐 Web interface: http://localhost:{self.qa_server.http_port}")
            print("📝 Real-time transcription and Q&A active")
            print("💡 Automated insights every 60 seconds")
            print(f"\n👉 Open http://localhost:{self.qa_server.http_port} in your browser for Q&A!")
            print("\nPress Ctrl+C to stop...")
            
            # Wait for all tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            print(f"✗ Runtime error: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the application gracefully."""
        print("\nStopping Live Transcripts...")
        self.is_running = False
        
        # Stop components in reverse order
        if self.qa_server:
            self.qa_server.stop()
            print("✓ Q&A server stopped")
        
        if self.insight_generator:
            self.insight_generator.stop_automated_insights()
            print("✓ Automated insights stopped")
        
        if self.transcription_manager:
            await self.transcription_manager.stop_processing()
            print("✓ Transcription processing stopped")
        
        if self.batch_processor:
            await self.batch_processor.stop_processing()
            print("✓ Batch processing stopped")
        
        if self.audio_capture:
            await self.audio_capture.stop_capture()
            print("✓ Audio capture stopped")
        
        # Cancel remaining tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        print("✓ Live Transcripts stopped successfully")
    
    async def _audio_processing_loop(self) -> None:
        """Main audio processing loop."""
        try:
            while self.is_running:
                # Skip processing if recording is paused
                if self.recording_paused:
                    await asyncio.sleep(0.1)  # Longer delay when paused
                    continue
                
                # Get audio data
                try:
                    audio_chunk = await asyncio.wait_for(
                        self.audio_capture.get_audio_chunk(),
                        timeout=0.1
                    )
                    # Process through batching system
                    await self.batch_processor.process_audio_chunk(audio_chunk.data)
                except asyncio.TimeoutError:
                    # No audio available, continue
                    await asyncio.sleep(0.01)
                    self.stats['audio_chunks_processed'] += 1
                    
                    # Check for new batches
                    batch = await self.batch_processor.get_next_batch()
                    if batch:
                        # Send for transcription
                        await self.transcription_manager.transcribe_batch(batch)
                        self.stats['batches_created'] += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)  # 10ms
                
        except Exception as e:
            print(f"Audio processing error: {e}")
            self.is_running = False
    
    async def _intent_sync_loop(self) -> None:
        """Synchronize intent between Q&A server and insight generator."""
        try:
            while self.is_running:
                # Check if Q&A server has a current intent
                if (self.qa_server and hasattr(self.qa_server, 'current_intent') and 
                    self.insight_generator and hasattr(self.insight_generator, 'session_intent')):
                    
                    current_intent = self.qa_server.current_intent
                    if self.insight_generator.session_intent != current_intent:
                        self.insight_generator.set_session_intent(current_intent)
                
                # Check every 5 seconds
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"Intent sync error: {e}")
    
    async def pause_recording(self) -> None:
        """Pause audio recording and processing."""
        self.recording_paused = True
        print("⏸️ Recording paused - audio processing stopped")
    
    async def resume_recording(self) -> None:
        """Resume audio recording and processing."""
        self.recording_paused = False
        print("▶️ Recording resumed - audio processing active")
    
    async def _on_transcription_result(self, result) -> None:
        """Handle new transcription result."""
        try:
            # Add to context
            self.context_manager.add_transcription(result)
            self.stats['transcriptions_completed'] += 1
            
            # Broadcast to connected clients
            if self.qa_server:
                await self.qa_server.broadcast_transcript(result)
            
            # Print to console
            timestamp = result.timestamp.strftime("%H:%M:%S")
            print(f"[{timestamp}] {result.text}")
            
        except Exception as e:
            print(f"Transcription callback error: {e}")
    
    def _on_insight_generated(self, insight) -> None:
        """Handle new insight generation."""
        try:
            self.stats['insights_generated'] += 1
            
            # Broadcast to connected clients
            if self.qa_server:
                asyncio.create_task(self.qa_server.broadcast_insight(insight))
            
            # Print to console
            timestamp = insight.timestamp.strftime("%H:%M:%S")
            print(f"\n💡 [{timestamp}] {insight.type.value.upper()}: {insight.content}\n")
            
        except Exception as e:
            print(f"Insight callback error: {e}")
    
    def get_statistics(self) -> dict:
        """Get application statistics."""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        base_stats = {
            'uptime_seconds': uptime,
            'is_running': self.is_running,
            **self.stats
        }
        
        # Add component statistics
        if self.batch_processor:
            base_stats['batching'] = self.batch_processor.get_statistics()
        
        if self.transcription_manager:
            base_stats['transcription'] = self.transcription_manager.get_statistics()
        
        if self.qa_server:
            base_stats['qa_server'] = self.qa_server.get_statistics()
        
        if self.context_manager:
            base_stats['context'] = self.context_manager.get_context_stats()
        
        return base_stats


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Live Transcripts - Real-time meeting transcription and Q&A')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--host', default='localhost', help='WebSocket server host')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket server port')
    parser.add_argument('--http-port', type=int, default=8766, help='HTTP server port for web interface')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        'server_host': args.host,
        'server_port': args.port,
        'http_port': args.http_port
    }
    
    # Create and initialize app
    app = LiveTranscriptsApp(config)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler():
        print("\nReceived shutdown signal...")
        asyncio.create_task(app.stop())
    
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, signal_handler)
    
    try:
        # Initialize and start
        app.initialize()
        await app.start()
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)
    finally:
        if app.is_running:
            await app.stop()


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for required environment variables
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable required")
        print("Options:")
        print("1. Set with: export OPENAI_API_KEY='your-api-key'")
        print("2. Create .env file with: OPENAI_API_KEY=your-api-key")
        sys.exit(1)
    
    if not os.getenv('GOOGLE_API_KEY'):
        print("Error: GOOGLE_API_KEY environment variable required")
        print("Options:")
        print("1. Set with: export GOOGLE_API_KEY='your-api-key'")
        print("2. Create .env file with: GOOGLE_API_KEY=your-api-key")
        sys.exit(1)
    
    # Run the application
    asyncio.run(main())