"""Google Gemini API integration for AI insights and Q&A."""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
import google.generativeai as genai


@dataclass
class GeminiConfig:
    """Configuration for Gemini API integration."""
    
    model: str = "gemini-1.5-flash"  # Using 1.5 Flash for stable rate limits
    temperature: float = 0.3
    max_tokens: int = 800  # Balanced for informative yet concise insights
    context_window_minutes: int = 5  # DEPRECATED - we use full transcript now
    insight_interval_seconds: int = 60
    max_conversation_length: int = 20
    use_full_transcript: bool = True  # Always use complete transcript history
    
    def __post_init__(self):
        """Validate configuration."""
        if not 0 <= self.temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        if self.context_window_minutes <= 0:
            raise ValueError("Context window must be positive")
        if self.insight_interval_seconds <= 0:
            raise ValueError("Insight interval must be positive")


class InsightType(Enum):
    """Types of meeting insights."""
    SUMMARY = "summary"
    ACTION_ITEM = "action_item"
    QUESTION = "question"
    DECISION = "decision"
    FOLLOW_UP = "follow_up"


@dataclass
class ChatMessage:
    """Chat message for conversation history."""
    
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate message."""
        if self.role not in ["user", "assistant"]:
            raise ValueError(f"Invalid role: {self.role}")
    
    def is_valid(self) -> bool:
        """Check if message is valid."""
        return len(self.content.strip()) > 0
    
    def to_api_format(self) -> Dict[str, Any]:
        """Convert to Gemini API format."""
        return {
            "role": self.role,
            "parts": [{"text": self.content}]
        }


@dataclass
class MeetingInsight:
    """AI-generated meeting insight."""
    
    type: InsightType
    content: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    context_duration: float = 0.0  # Duration of context used (seconds)
    
    def relevance_score(self) -> float:
        """Calculate relevance score based on recency and confidence."""
        # More recent insights are more relevant
        age_hours = (datetime.now() - self.timestamp).total_seconds() / 3600
        recency_factor = max(0, 1 - (age_hours / 24))  # Decay over 24 hours
        
        return self.confidence * recency_factor


class ContextManager:
    """Manages complete transcript history for AI processing."""
    
    def __init__(self, config: GeminiConfig):
        self.config = config
        self.transcriptions: List = []  # List of TranscriptionResult - stores ENTIRE history
        # Note: We keep the config window for backwards compatibility but don't use it
        self.context_window = timedelta(minutes=config.context_window_minutes)
    
    def add_transcription(self, transcription) -> None:
        """Add transcription to context - keeps full history."""
        self.transcriptions.append(transcription)
        # No pruning - we want the ENTIRE transcript for Gemini's 2M token context
    
    def get_context_text(self) -> str:
        """Get COMPLETE transcript history for AI processing - uses full context."""
        if not self.transcriptions:
            return ""
        
        context_parts = []
        for transcription in self.transcriptions:
            timestamp_str = transcription.timestamp.strftime("%H:%M:%S")
            context_parts.append(f"[{timestamp_str}] {transcription.text}")
        
        full_transcript = "\n".join(context_parts)
        
        # Log context size for monitoring
        word_count = len(full_transcript.split())
        char_count = len(full_transcript)
        print(f"📊 Using FULL transcript context: {word_count} words, {char_count} chars, {len(self.transcriptions)} segments")
        
        return full_transcript
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about current context."""
        if not self.transcriptions:
            return {
                "total_duration": 0.0,
                "transcription_count": 0,
                "average_duration": 0.0,
                "word_count": 0
            }
        
        total_duration = sum(t.duration for t in self.transcriptions)
        word_count = sum(len(t.text.split()) for t in self.transcriptions)
        
        return {
            "total_duration": total_duration,
            "transcription_count": len(self.transcriptions),
            "average_duration": total_duration / len(self.transcriptions),
            "word_count": word_count
        }


class GeminiClient:
    """Google Gemini API client."""
    
    def __init__(self, config: GeminiConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(config.model)
    
    async def generate_content(self, prompt: str) -> str:
        """Generate content using Gemini API."""
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self._get_generation_config(),
                safety_settings=self._get_safety_settings()
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    async def generate_with_context(self, prompt: str, conversation: List[ChatMessage]) -> str:
        """Generate content with conversation context."""
        # Format conversation for Gemini
        messages = []
        for msg in conversation:
            messages.append(msg.to_api_format())
        
        # Add new prompt
        messages.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        try:
            response = await self.model.generate_content_async(
                messages,
                generation_config=self._get_generation_config(),
                safety_settings=self._get_safety_settings()
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    def _get_generation_config(self):
        """Get generation configuration."""
        return genai.types.GenerationConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
            top_p=0.8,
            top_k=40
        )
    
    def _get_safety_settings(self):
        """Get safety settings for content generation."""
        return [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH", 
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]


class InsightGenerator:
    """Generates automated meeting insights."""
    
    def __init__(self, config: GeminiConfig, context_manager: ContextManager):
        self.config = config
        self.context_manager = context_manager
        self.client = None  # Will be set by main app - ensures same client instance
        self.is_running = False
        self._insight_callbacks: List[Callable] = []
        self.session_intent: str = ""  # User's session focus/intent
    
    async def generate_summary(self) -> MeetingInsight:
        """Generate meeting summary insight."""
        if not self.client:
            raise RuntimeError("Insight generator client not initialized")
            
        context_text = self.context_manager.get_context_text()
        if not context_text:
            raise ValueError("No context available for summary")
        
        prompt = self._build_summary_prompt(context_text)
        content = await self.client.generate_content(prompt)
        
        return MeetingInsight(
            type=InsightType.SUMMARY,
            content=content,
            confidence=0.8,  # Default confidence for summaries
            context_duration=sum(t.duration for t in self.context_manager.transcriptions)
        )
    
    async def generate_action_items(self) -> MeetingInsight:
        """Generate key themes and notable moments insight."""
        if not self.client:
            raise RuntimeError("Insight generator client not initialized")
            
        context_text = self.context_manager.get_context_text()
        if not context_text:
            raise ValueError("No context available for insights")
        
        prompt = self._build_action_items_prompt(context_text)
        content = await self.client.generate_content(prompt)
        
        return MeetingInsight(
            type=InsightType.SUMMARY,  # Changed to SUMMARY since it's about themes/moments
            content=content,
            confidence=0.85,
            context_duration=sum(t.duration for t in self.context_manager.transcriptions)
        )
    
    async def generate_questions(self) -> MeetingInsight:
        """Generate clarifying questions insight."""
        if not self.client:
            raise RuntimeError("Insight generator client not initialized")
            
        context_text = self.context_manager.get_context_text()
        if not context_text:
            raise ValueError("No context available for questions")
        
        prompt = self._build_questions_prompt(context_text)
        content = await self.client.generate_content(prompt)
        
        return MeetingInsight(
            type=InsightType.QUESTION,
            content=content,
            confidence=0.7,  # Lower confidence for questions
            context_duration=sum(t.duration for t in self.context_manager.transcriptions)
        )
    
    async def start_automated_insights(self, callback: Callable[[MeetingInsight], None]) -> None:
        """Start automated insight generation."""
        self.is_running = True
        self._insight_callbacks.append(callback)
        
        while self.is_running:
            try:
                await asyncio.sleep(self.config.insight_interval_seconds)
                
                if self.context_manager.transcriptions:
                    # Generate different types of insights on rotation
                    current_time = int(time.time())
                    insight_type_index = (current_time // self.config.insight_interval_seconds) % 2
                    
                    if insight_type_index == 0:
                        insight = await self.generate_summary()
                    else:
                        insight = await self.generate_action_items()
                    
                    # Notify callbacks
                    for cb in self._insight_callbacks:
                        try:
                            cb(insight)
                        except Exception as e:
                            print(f"Insight callback error: {e}")
                            
            except Exception as e:
                print(f"Automated insight generation error: {e}")
    
    def stop_automated_insights(self) -> None:
        """Stop automated insight generation."""
        self.is_running = False
    
    def set_session_intent(self, intent: str) -> None:
        """Set the session intent for focused insights."""
        self.session_intent = intent
        print(f"📌 Insight generator intent updated: '{intent}'")
    
    def _build_summary_prompt(self, context_text: str) -> str:
        """Build prompt for summary generation."""
        intent_prefix = ""
        if self.session_intent:
            intent_prefix = f"The user's goal for this session is: '{self.session_intent}'\n\n"
        
        return f"""{intent_prefix}Based on the meeting transcript, provide an insightful observation about what's happening in the conversation (2-3 sentences, ~400 characters).

Complete Meeting Transcript:
{context_text}

Share an interesting insight, pattern, or notable point from the discussion{f", especially related to {self.session_intent}" if self.session_intent else ""}. Make it a statement, not a question:"""
    
    def _build_action_items_prompt(self, context_text: str) -> str:
        """Build prompt for action items generation."""
        intent_prefix = ""
        if self.session_intent:
            intent_prefix = f"The user's goal for this session is: '{self.session_intent}'\n\n"
        
        return f"""{intent_prefix}From the meeting transcript, extract key themes, decisions, or noteworthy moments (2-3 sentences, ~400 characters).

Complete Meeting Transcript:
{context_text}

Identify what's most interesting or important about the conversation so far{f", particularly regarding {self.session_intent}" if self.session_intent else ""}. Focus on patterns, decisions, or notable developments:"""
    
    def _build_questions_prompt(self, context_text: str) -> str:
        """Build prompt for questions generation."""
        intent_prefix = ""
        if self.session_intent:
            intent_prefix = f"The user's goal for this session is: '{self.session_intent}'\n\n"
        
        return f"""{intent_prefix}Based on the meeting discussion, suggest 2-3 thoughtful clarifying questions (aim for ~400 characters).

Complete Meeting Transcript:
{context_text}

Identify key gaps or areas needing clarification{f" regarding {self.session_intent}" if self.session_intent else ""}. 
Format each question on a new line. Make them specific and actionable:"""


class QAHandler:
    """Handles live Q&A during meetings."""
    
    def __init__(self, config: GeminiConfig, context_manager: ContextManager):
        self.config = config
        self.context_manager = context_manager
        self.client = None  # Will be set by main app - ensures same client instance
        self.conversation_history: List[ChatMessage] = []
        self.max_conversation_length = config.max_conversation_length
        self.session_intent: str = ""  # User's session focus/intent
    
    async def answer_question(self, question: str) -> str:
        """Answer a question based on meeting context."""
        if not self.client:
            raise RuntimeError("QA handler client not initialized")
            
        # Add question to conversation history
        user_message = ChatMessage(role="user", content=question)
        self.conversation_history.append(user_message)
        
        # Build prompt with context
        prompt = self._build_qa_prompt(question)
        
        # Generate answer using simple generate_content (more reliable than generate_with_context)
        answer = await self.client.generate_content(prompt)
        
        # Add answer to conversation history
        assistant_message = ChatMessage(role="assistant", content=answer)
        self.conversation_history.append(assistant_message)
        
        # Prune conversation history
        self._prune_conversation_history()
        
        return answer
    
    def _build_qa_prompt(self, question: str) -> str:
        """Build prompt for Q&A with COMPLETE meeting context."""
        context_text = self.context_manager.get_context_text()
        
        prompt = f"""You are an AI assistant with access to the COMPLETE meeting transcript from beginning to end. Please answer the following question using ANY information from the ENTIRE meeting.

Complete Meeting Transcript (everything from start to now):
{context_text if context_text else "No meeting context available yet."}

Question: {question}

Please provide a comprehensive answer based on the ENTIRE meeting transcript. You have access to everything that has been said from the beginning of the meeting. If the answer requires information from earlier in the meeting, please include it.

Answer:"""
        
        return prompt
    
    async def generate_contextual_questions(self) -> List[str]:
        """Generate contextual questions based on recent meeting content."""
        if not self.client:
            print("⚠️  QA handler client not initialized")
            return []
            
        context_text = self.context_manager.get_context_text()
        
        # Check for any context (even small amounts are fine with full transcript)
        if not context_text:
            print(f"📊 No context available yet for questions")
            return []
        
        word_count = len(context_text.split())
        print(f"📄 Full transcript context for questions: {word_count} words, {len(context_text)} chars")
        
        intent_prefix = ""
        if self.session_intent:
            intent_prefix = f"The user's goal for this session is: '{self.session_intent}'\n\n"
        
        prompt = f"""{intent_prefix}Based on the COMPLETE meeting transcript from beginning to end, generate exactly 4 specific questions that attendees might want to ask. These should be relevant to ANY topics discussed throughout the ENTIRE meeting, not just recent parts.

Complete Meeting Transcript (entire history):
{context_text}

Considering ALL topics and discussions from the ENTIRE meeting{f", with special focus on {self.session_intent}" if self.session_intent else ""}, list exactly 4 questions, one per line, without numbering or bullet points. Each question should end with a question mark."""
        
        try:
            response = await self.client.generate_content(prompt)
            print(f"🤖 Gemini raw response: {response[:200]}...")  # First 200 chars
            
            # Split response into lines and clean up
            lines = response.strip().split('\n')
            questions = []
            
            for line in lines:
                line = line.strip()
                # Skip empty lines
                if not line:
                    continue
                    
                # Remove common prefixes (numbers, bullets, etc.)
                line = line.lstrip('0123456789.-*•● ')
                
                # Only keep lines that look like questions
                if line and '?' in line:
                    questions.append(line)
            
            # If we got fewer than 4 questions, use default fallbacks
            default_questions = [
                "What are the key technical details mentioned?",
                "What are the next steps or action items?",
                "Who is responsible for each task?",
                "What timeline was discussed?"
            ]
            
            # Fill in with defaults if needed
            while len(questions) < 4 and default_questions:
                questions.append(default_questions.pop(0))
            
            # Return exactly 4 questions
            return questions[:4]
            
        except Exception as e:
            print(f"Error generating contextual questions: {e}")
            # Return default questions on error
            return [
                "What are the main topics being discussed?",
                "What decisions have been made so far?",
                "Are there any action items or next steps?",
                "What questions or concerns were raised?"
            ]
    
    def set_session_intent(self, intent: str) -> None:
        """Set the session intent for focused Q&A and questions."""
        self.session_intent = intent
        print(f"📌 QA handler intent updated: '{intent}'")
    
    def _prune_conversation_history(self) -> None:
        """Prune conversation history to stay within limits."""
        if len(self.conversation_history) > self.max_conversation_length:
            # Keep the most recent messages
            self.conversation_history = self.conversation_history[-self.max_conversation_length:]
    
    def get_conversation_summary(self) -> str:
        """Get summary of Q&A conversation."""
        if not self.conversation_history:
            return "No Q&A conversation yet."
        
        qa_pairs = []
        for i in range(0, len(self.conversation_history), 2):
            if i + 1 < len(self.conversation_history):
                question = self.conversation_history[i].content
                answer = self.conversation_history[i + 1].content
                qa_pairs.append(f"Q: {question}\nA: {answer}")
        
        return "\n\n".join(qa_pairs)
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []


class MeetingAnalyzer:
    """Analyzes meeting patterns and provides advanced insights."""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.insights_history: List[MeetingInsight] = []
    
    def analyze_speaking_patterns(self) -> Dict[str, Any]:
        """Analyze speaking patterns in the meeting."""
        transcriptions = self.context_manager.transcriptions
        if not transcriptions:
            return {"error": "No transcriptions available"}
        
        total_duration = sum(t.duration for t in transcriptions)
        segment_count = sum(len(t.segments) for t in transcriptions)
        avg_segment_duration = total_duration / segment_count if segment_count > 0 else 0
        
        return {
            "total_speaking_time": total_duration,
            "segment_count": segment_count,
            "average_segment_duration": avg_segment_duration,
            "speech_density": segment_count / total_duration if total_duration > 0 else 0
        }
    
    def analyze_meeting_pace(self) -> Dict[str, Any]:
        """Analyze the pace and flow of the meeting."""
        transcriptions = self.context_manager.transcriptions
        if len(transcriptions) < 2:
            return {"error": "Insufficient data for pace analysis"}
        
        # Calculate gaps between transcriptions
        gaps = []
        for i in range(1, len(transcriptions)):
            gap = (transcriptions[i].timestamp - transcriptions[i-1].timestamp).total_seconds()
            gaps.append(gap)
        
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        
        return {
            "average_gap_between_segments": avg_gap,
            "total_gaps": len(gaps),
            "meeting_flow": "fast" if avg_gap < 2 else "moderate" if avg_gap < 5 else "slow"
        }
    
    def get_meeting_statistics(self) -> Dict[str, Any]:
        """Get comprehensive meeting statistics."""
        context_stats = self.context_manager.get_context_stats()
        speaking_patterns = self.analyze_speaking_patterns()
        pace_analysis = self.analyze_meeting_pace()
        
        return {
            "context": context_stats,
            "speaking_patterns": speaking_patterns,
            "pace_analysis": pace_analysis,
            "insights_generated": len(self.insights_history)
        }