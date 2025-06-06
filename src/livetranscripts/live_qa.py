"""Live Q&A WebSocket server for real-time meeting interaction."""

import asyncio
import json
import time
import uuid
import warnings
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
import websockets
from websockets.exceptions import ConnectionClosed, InvalidMessage
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
from pathlib import Path


class MessageType(Enum):
    """WebSocket message types."""
    QUESTION = "question"
    ANSWER = "answer"
    ERROR = "error"
    STATUS = "status"
    TRANSCRIPT = "transcript"
    INSIGHT = "insight"
    SUGGESTED_QUESTIONS = "suggested_questions"
    INTENT = "intent"
    RECORDING_CONTROL = "recording_control"
    RECORDING_STATUS = "recording_status"
    STATUS_REQUEST = "status_request"


class ConnectionState(Enum):
    """Connection states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class QARequest:
    """Q&A request from client."""
    
    question: str
    session_id: str
    timestamp: datetime
    request_id: str
    
    def is_valid(self) -> bool:
        """Check if request is valid."""
        return (len(self.question.strip()) > 0 and 
                len(self.session_id.strip()) > 0 and
                len(self.request_id.strip()) > 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "question": self.question,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QARequest':
        """Create from dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
        return cls(
            question=data["question"],
            session_id=data["session_id"],
            request_id=data["request_id"],
            timestamp=timestamp
        )


@dataclass
class QAResponse:
    """Q&A response to client."""
    
    answer: str
    request_id: str
    confidence: float
    processing_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_valid(self) -> bool:
        """Check if response is valid."""
        return len(self.answer.strip()) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "answer": self.answer,
            "request_id": self.request_id,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class QASession:
    """Q&A session for a client connection."""
    
    session_id: str
    user_id: str
    created_at: datetime
    state: ConnectionState = ConnectionState.CONNECTED
    qa_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history_length: int = 50
    
    def add_qa_pair(self, request: QARequest, response: QAResponse) -> None:
        """Add Q&A pair to session history."""
        qa_pair = {
            "request": request,
            "response": response,
            "timestamp": datetime.now()
        }
        self.qa_history.append(qa_pair)
        
        # Prune history if too long
        if len(self.qa_history) > self.max_history_length:
            self.qa_history = self.qa_history[-self.max_history_length:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        if not self.qa_history:
            return {
                "total_questions": 0,
                "average_confidence": 0.0,
                "average_processing_time": 0.0,
                "session_duration": 0.0
            }
        
        total_questions = len(self.qa_history)
        confidences = [pair["response"].confidence for pair in self.qa_history]
        processing_times = [pair["response"].processing_time for pair in self.qa_history]
        
        session_duration = (datetime.now() - self.created_at).total_seconds()
        
        return {
            "total_questions": total_questions,
            "average_confidence": sum(confidences) / len(confidences),
            "average_processing_time": sum(processing_times) / len(processing_times),
            "session_duration": session_duration
        }


class SessionManager:
    """Manages client sessions for Q&A."""
    
    def __init__(self, max_sessions: int = 100, session_timeout_minutes: int = 60):
        self.max_sessions = max_sessions
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.sessions: Dict[str, QASession] = {}
    
    def create_session(self, user_id: str) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        
        # Check if we need to remove old sessions
        if len(self.sessions) >= self.max_sessions:
            self._remove_oldest_session()
        
        session = QASession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now()
        )
        
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[QASession]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def close_session(self, session_id: str) -> None:
        """Close a session."""
        if session_id in self.sessions:
            self.sessions[session_id].state = ConnectionState.DISCONNECTED
    
    def cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        cutoff_time = datetime.now() - self.session_timeout
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.created_at < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
    
    def _remove_oldest_session(self) -> None:
        """Remove the oldest session to make room for new one."""
        if not self.sessions:
            return
        
        oldest_session_id = min(
            self.sessions.keys(),
            key=lambda sid: self.sessions[sid].created_at
        )
        del self.sessions[oldest_session_id]


class WebSocketHandler:
    """Handles individual WebSocket connections."""
    
    def __init__(self, session_manager: SessionManager, qa_handler, server=None):
        self.session_manager = session_manager
        self.qa_handler = qa_handler
        self.server = server  # Reference to LiveQAServer
        self.current_session_id: Optional[str] = None
        self.current_intent: str = ""  # Store user's session intent
    
    async def handle_connection(self, websocket) -> None:
        """Handle a WebSocket connection."""
        print(f"🔗 New WebSocket connection from {websocket.remote_address}")
        try:
            # Create session
            user_id = f"user_{int(time.time())}"  # Simple user ID generation
            self.current_session_id = self.session_manager.create_session(user_id)
            print(f"📝 Created session: {self.current_session_id}")
            
            # Send welcome message
            welcome_msg = {
                "type": "status",
                "message": "Connected to Live Q&A",
                "session_id": self.current_session_id
            }
            await websocket.send(json.dumps(welcome_msg))
            print(f"👋 Sent welcome message to {self.current_session_id}")
            
            # Handle messages
            print(f"👂 Listening for messages from {self.current_session_id}")
            async for message in websocket:
                print(f"📨 Received message: {message}")
                await self._process_message(websocket, message)
                
        except ConnectionClosed:
            print(f"📦 WebSocket connection closed normally")
            pass
        except Exception as e:
            print(f"💥 WebSocket error in handle_connection: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up session
            if self.current_session_id:
                self.session_manager.close_session(self.current_session_id)
                print(f"🧹 Cleaned up session: {self.current_session_id}")
    
    async def _process_message(self, websocket, message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            if not self._validate_message(data):
                await self._send_error(websocket, "Invalid message format", None)
                return
            
            message_type = data.get("type")
            
            if message_type == MessageType.QUESTION.value:
                await self._handle_question(websocket, data)
            elif message_type == MessageType.INTENT.value:
                await self._handle_intent(websocket, data)
            elif message_type == MessageType.RECORDING_CONTROL.value:
                await self._handle_recording_control(websocket, data)
            elif message_type == MessageType.STATUS_REQUEST.value:
                await self._handle_status_request(websocket, data)
            else:
                await self._send_error(websocket, f"Unknown message type: {message_type}", data.get("request_id"))
                
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON format", None)
        except Exception as e:
            await self._send_error(websocket, f"Processing error: {e}", None)
    
    async def _handle_question(self, websocket, data: Dict[str, Any]) -> None:
        """Handle a question message."""
        try:
            request = QARequest(
                question=data["content"],
                session_id=self.current_session_id or "",
                timestamp=datetime.now(),
                request_id=data.get("request_id", str(uuid.uuid4()))
            )
            
            if not request.is_valid():
                await self._send_error(websocket, "Invalid question request", request.request_id)
                return
            
            # Store question for response
            self._last_question = request.question
            
            # Process question
            print(f"🤔 Processing question: {request.question}")
            start_time = time.time()
            try:
                answer = await self.qa_handler.answer_question(request.question)
                processing_time = time.time() - start_time
                print(f"✅ Generated answer in {processing_time:.2f}s: {answer[:100]}...")
            except Exception as e:
                processing_time = time.time() - start_time
                print(f"💥 Error generating answer: {e}")
                answer = f"Sorry, I encountered an error processing your question: {e}"
            
            # Create response
            response = QAResponse(
                answer=answer,
                request_id=request.request_id,
                confidence=0.8,  # Default confidence
                processing_time=processing_time
            )
            
            # Store in session
            session = self.session_manager.get_session(self.current_session_id)
            if session:
                session.add_qa_pair(request, response)
            
            # Send response
            await self._send_response(websocket, response)
            
        except Exception as e:
            await self._send_error(
                websocket, 
                f"Failed to process question: {e}", 
                data.get("request_id")
            )
    
    async def _send_response(self, websocket, response: QAResponse) -> None:
        """Send Q&A response to client."""
        # Get the original question from the request
        request_question = getattr(self, '_last_question', 'Unknown question')
        
        message = {
            "type": MessageType.ANSWER.value,
            "question": request_question,
            "content": response.answer,
            **response.to_dict()
        }
        await websocket.send(json.dumps(message))
    
    async def _handle_intent(self, websocket, data: Dict[str, Any]) -> None:
        """Handle intent update from client."""
        try:
            self.current_intent = data.get("content", "").strip()
            print(f"🎯 Session intent updated: '{self.current_intent}' for session {self.current_session_id}")
            
            # Store intent in qa_handler if it exists
            if self.qa_handler and hasattr(self.qa_handler, 'set_session_intent'):
                self.qa_handler.set_session_intent(self.current_intent)
            
            # Update the server's global intent
            if self.server:
                self.server.current_intent = self.current_intent
                print(f"📍 Updated server intent: '{self.current_intent}'")
            
            # Send confirmation
            confirmation = {
                "type": MessageType.STATUS.value,
                "message": f"Session focus updated: {self.current_intent if self.current_intent else 'Default'}",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(confirmation))
            
        except Exception as e:
            await self._send_error(websocket, f"Failed to update intent: {e}", None)
    
    async def _handle_recording_control(self, websocket, data: Dict[str, Any]) -> None:
        """Handle recording control from client."""
        try:
            action = data.get("content", {}).get("action", "").strip()
            print(f"🎙️ Recording control request: '{action}' for session {self.current_session_id}")
            
            if action not in ["start", "stop"]:
                await self._send_error(websocket, f"Invalid recording action: {action}", None)
                return
            
            # Forward the request to the server for handling
            if self.server and hasattr(self.server, 'handle_recording_control'):
                success = await self.server.handle_recording_control(action)
                
                # Send status update
                status_msg = {
                    "type": MessageType.STATUS.value,
                    "message": f"Recording {'started' if action == 'start' else 'stopped'}",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send(json.dumps(status_msg))
                
                # Broadcast recording status to all clients
                recording_status = {
                    "type": MessageType.RECORDING_STATUS.value,
                    "content": {
                        "recording": action == "start",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await self.server.broadcast_message(recording_status)
                
            else:
                await self._send_error(websocket, "Recording control not available", None)
                
        except Exception as e:
            await self._send_error(websocket, f"Failed to control recording: {e}", None)
    
    async def _handle_status_request(self, websocket, data: Dict[str, Any]) -> None:
        """Handle status request from client."""
        try:
            request_type = data.get("content", "")
            
            if request_type == "recording_status":
                # Send current recording status
                recording_status = {
                    "type": MessageType.RECORDING_STATUS.value,
                    "content": {
                        "recording": self.server.recording_enabled if self.server else True,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await websocket.send(json.dumps(recording_status))
                print(f"📤 Sent recording status: {self.server.recording_enabled if self.server else True}")
            
        except Exception as e:
            await self._send_error(websocket, f"Failed to handle status request: {e}", None)
    
    async def _send_error(self, websocket, error_message: str, request_id: Optional[str]) -> None:
        """Send error message to client."""
        message = {
            "type": MessageType.ERROR.value,
            "error": error_message,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(message))
    
    def _validate_message(self, data: Dict[str, Any]) -> bool:
        """Validate incoming message format."""
        if not isinstance(data, dict):
            return False
        
        message_type = data.get("type")
        if message_type not in [mt.value for mt in MessageType]:
            return False
        
        if message_type == MessageType.QUESTION.value:
            required_fields = ["content"]
            return all(field in data and data[field] for field in required_fields)
        
        if message_type == MessageType.INTENT.value:
            return "content" in data  # Intent can be empty string to clear
        
        if message_type == MessageType.RECORDING_CONTROL.value:
            return ("content" in data and 
                    isinstance(data["content"], dict) and 
                    "action" in data["content"])
        
        if message_type == MessageType.STATUS_REQUEST.value:
            return "content" in data  # Status request content can be any string
        
        return True
    
    def _format_response(self, response: QAResponse) -> Dict[str, Any]:
        """Format response for WebSocket transmission."""
        return {
            "type": MessageType.ANSWER.value,
            **response.to_dict()
        }


class WebInterfaceHandler(SimpleHTTPRequestHandler):
    """HTTP handler for serving the web interface."""
    
    def __init__(self, *args, interface_file_path=None, **kwargs):
        self.interface_file_path = interface_file_path
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/" or self.path == "/index.html":
            self.serve_web_interface()
        else:
            self.send_error(404, "Not Found")
    
    def serve_web_interface(self):
        """Serve the web interface HTML file."""
        try:
            if self.interface_file_path and os.path.exists(self.interface_file_path):
                with open(self.interface_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Content-length', len(content.encode('utf-8')))
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(404, "Web interface file not found")
        except Exception as e:
            self.send_error(500, f"Server error: {e}")
    
    def log_message(self, format, *args):
        """Override to reduce logging noise."""
        pass


class HTTPServerThread(threading.Thread):
    """Thread for running the HTTP server."""
    
    def __init__(self, host: str, port: int, interface_file_path: str):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.interface_file_path = interface_file_path
        self.httpd = None
        self.running = False
    
    def run(self):
        """Run the HTTP server."""
        try:
            def handler_factory(*args, **kwargs):
                return WebInterfaceHandler(*args, interface_file_path=self.interface_file_path, **kwargs)
            
            self.httpd = HTTPServer((self.host, self.port), handler_factory)
            self.running = True
            print(f"Web interface available at: http://{self.host}:{self.port}")
            self.httpd.serve_forever()
        except Exception as e:
            print(f"HTTP server error: {e}")
        finally:
            self.running = False
    
    def stop(self):
        """Stop the HTTP server."""
        self.running = False
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


class LiveQAServer:
    """Main live Q&A WebSocket server with web interface."""
    
    def __init__(self, host: str = "localhost", port: int = 8765, qa_handler=None, http_port: int = 8766):
        self.host = host
        self.port = port
        self.http_port = http_port
        self.qa_handler = qa_handler
        self.session_manager = SessionManager()
        self.is_running = False
        self.server = None
        self.http_server = None
        self.start_time: Optional[datetime] = None
        self.active_connections: Set = set()
        self.current_intent: str = ""  # Global intent for all sessions
        self.recording_enabled: bool = True  # Recording state
        self.main_app = None  # Reference to main application
        
        # Find the web interface file
        self.interface_file_path = self._find_web_interface_file()
    
    def _find_web_interface_file(self) -> Optional[str]:
        """Find the web interface HTML file."""
        # Look for the file relative to this module
        current_dir = Path(__file__).parent
        interface_path = current_dir / "web_interface.html"
        
        if interface_path.exists():
            return str(interface_path)
        
        # Alternative locations
        alternative_paths = [
            current_dir.parent / "web_interface.html",
            Path.cwd() / "web_interface.html",
            Path.cwd() / "src" / "livetranscripts" / "web_interface.html"
        ]
        
        for path in alternative_paths:
            if path.exists():
                return str(path)
        
        print("⚠️  Web interface file not found. Web interface will not be available.")
        return None
    
    async def start(self) -> None:
        """Start both WebSocket and HTTP servers."""
        self.is_running = True
        self.start_time = datetime.now()
        
        # Start HTTP server for web interface
        if self.interface_file_path:
            self.http_server = HTTPServerThread(self.host, self.http_port, self.interface_file_path)
            self.http_server.start()
        
        # Start background tasks
        self._background_tasks = []
        cleanup_task = asyncio.create_task(self.cleanup_task())
        self._background_tasks.append(cleanup_task)
        
        questions_task = asyncio.create_task(self.contextual_questions_task())
        self._background_tasks.append(questions_task)
        
        async def connection_handler(websocket):
            print(f"🌐 WebSocket connection attempt from {websocket.remote_address}")
            self.active_connections.add(websocket)
            try:
                print(f"🔧 Creating WebSocket handler for {websocket.remote_address}")
                if self.qa_handler is None:
                    print("❌ ERROR: qa_handler is None!")
                    await websocket.close(code=1011, reason="Server not ready")
                    return
                
                handler = WebSocketHandler(self.session_manager, self.qa_handler, self)
                print(f"✅ WebSocket handler created, starting connection handling...")
                await handler.handle_connection(websocket)
            except Exception as e:
                print(f"💥 ERROR in connection_handler: {e}")
                import traceback
                traceback.print_exc()
                try:
                    await websocket.close(code=1011, reason="Server error")
                except:
                    pass
            finally:
                self.active_connections.discard(websocket)
                print(f"🧹 Connection handler cleanup complete for {websocket.remote_address}")
        
        print(f"Starting Live Q&A server on {self.host}:{self.port}")
        try:
            self.server = await websockets.serve(connection_handler, self.host, self.port)
            print(f"✅ WebSocket server successfully bound to {self.host}:{self.port}")
            print(f"🔄 WebSocket server waiting for connections...")
            
            # Keep server running
            await self.server.wait_closed()
        except Exception as e:
            print(f"💥 Failed to start WebSocket server: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def stop(self) -> None:
        """Stop both WebSocket and HTTP servers."""
        self.is_running = False
        if self.server:
            self.server.close()
        if self.http_server:
            self.http_server.stop()
        
        # Cancel background tasks
        if hasattr(self, '_background_tasks'):
            for task in self._background_tasks:
                task.cancel()
    
    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for websocket in self.active_connections:
            try:
                await websocket.send(message_json)
            except ConnectionClosed:
                disconnected.add(websocket)
            except Exception as e:
                print(f"Broadcast error: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.active_connections -= disconnected
    
    async def broadcast_transcript(self, transcription) -> None:
        """Broadcast new transcription to all clients."""
        message = {
            "type": MessageType.TRANSCRIPT.value,
            "content": {
                "text": transcription.text,
                "timestamp": transcription.timestamp.isoformat(),
                "batch_id": transcription.batch_id
            }
        }
        await self.broadcast_message(message)
    
    async def broadcast_insight(self, insight) -> None:
        """Broadcast new insight to all clients."""
        message = {
            "type": MessageType.INSIGHT.value,
            "content": {
                "type": insight.type.value,
                "content": insight.content,
                "confidence": insight.confidence,
                "timestamp": insight.timestamp.isoformat()
            }
        }
        await self.broadcast_message(message)
    
    async def broadcast_suggested_questions(self, questions: List[str]) -> None:
        """Broadcast suggested questions to all clients."""
        message = {
            "type": MessageType.SUGGESTED_QUESTIONS.value,
            "content": {
                "questions": questions,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.broadcast_message(message)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get server health status."""
        if not self.is_running:
            return {"status": "stopped"}
        
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            "status": "healthy" if self.is_running else "unhealthy",
            "uptime": uptime,
            "active_connections": len(self.active_connections),
            "active_sessions": len(self.session_manager.sessions),
            "host": self.host,
            "port": self.port
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get server statistics."""
        total_sessions = len(self.session_manager.sessions)
        active_sessions = sum(
            1 for session in self.session_manager.sessions.values()
            if session.state == ConnectionState.CONNECTED
        )
        
        total_questions = sum(
            len(session.qa_history) 
            for session in self.session_manager.sessions.values()
        )
        
        if total_questions > 0:
            all_processing_times = []
            for session in self.session_manager.sessions.values():
                for qa_pair in session.qa_history:
                    all_processing_times.append(qa_pair["response"].processing_time)
            
            avg_response_time = sum(all_processing_times) / len(all_processing_times)
        else:
            avg_response_time = 0.0
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "active_connections": len(self.active_connections),
            "questions_processed": total_questions,
            "average_response_time": avg_response_time,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }
    
    async def cleanup_task(self) -> None:
        """Periodic cleanup task."""
        while self.is_running:
            try:
                self.session_manager.cleanup_expired_sessions()
                await asyncio.sleep(300)  # Cleanup every 5 minutes
            except Exception as e:
                print(f"Cleanup error: {e}")
    
    async def contextual_questions_task(self) -> None:
        """Generate and broadcast contextual questions every 15 seconds."""
        await asyncio.sleep(10)  # Initial delay to let some transcripts accumulate
        
        while self.is_running:
            try:
                if self.qa_handler and hasattr(self.qa_handler, 'generate_contextual_questions'):
                    # Update QA handler with current intent if it has changed
                    if hasattr(self.qa_handler, 'session_intent') and self.qa_handler.session_intent != self.current_intent:
                        self.qa_handler.set_session_intent(self.current_intent)
                    
                    print("🔄 Generating contextual questions...")
                    questions = await self.qa_handler.generate_contextual_questions()
                    if questions:
                        print(f"📝 Generated questions: {questions}")
                        await self.broadcast_suggested_questions(questions)
                        print(f"🎯 Broadcast {len(questions)} contextual questions")
                    else:
                        print("⚠️  No questions generated")
                else:
                    print("⚠️  QA handler not available or missing method")
                
                await asyncio.sleep(15)  # Generate new questions every 15 seconds
            except Exception as e:
                print(f"💥 Contextual questions generation error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(15)  # Continue after error
    
    async def handle_recording_control(self, action: str) -> bool:
        """Handle recording control requests from web interface."""
        try:
            if action == "start":
                if self.recording_enabled:
                    print("⚠️  Recording is already enabled")
                    return True
                
                self.recording_enabled = True
                print("🎙️ Recording enabled via web interface")
                
                # Notify main app to resume processing if available
                if self.main_app and hasattr(self.main_app, 'resume_recording'):
                    await self.main_app.resume_recording()
                
                return True
                
            elif action == "stop":
                if not self.recording_enabled:
                    print("⚠️  Recording is already disabled")
                    return True
                
                self.recording_enabled = False
                print("🛑 Recording disabled via web interface")
                
                # Notify main app to pause processing if available
                if self.main_app and hasattr(self.main_app, 'pause_recording'):
                    await self.main_app.pause_recording()
                
                return True
            
            else:
                print(f"❌ Invalid recording action: {action}")
                return False
                
        except Exception as e:
            print(f"💥 Error handling recording control: {e}")
            return False
    
    def set_main_app(self, main_app) -> None:
        """Set reference to main application for recording control."""
        self.main_app = main_app
        print("🔗 Main app reference set for recording control")


# Utility functions
def create_qa_server(qa_handler, host: str = "localhost", port: int = 8765) -> LiveQAServer:
    """Create and configure a Live Q&A server."""
    return LiveQAServer(host=host, port=port, qa_handler=qa_handler)


async def run_qa_server(qa_handler, host: str = "localhost", port: int = 8765) -> None:
    """Run the Live Q&A server."""
    server = create_qa_server(qa_handler, host, port)
    
    # Start background tasks
    cleanup_task = asyncio.create_task(server.cleanup_task())
    questions_task = asyncio.create_task(server.contextual_questions_task())
    
    try:
        await server.start()
    finally:
        # Cancel background tasks
        cleanup_task.cancel()
        questions_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        try:
            await questions_task
        except asyncio.CancelledError:
            pass