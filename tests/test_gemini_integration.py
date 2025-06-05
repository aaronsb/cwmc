"""Test cases for Gemini API integration."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from src.livetranscripts.gemini_integration import (
    GeminiClient,
    GeminiConfig,
    ContextManager,
    InsightGenerator,
    QAHandler,
    InsightType,
    ChatMessage,
    MeetingInsight,
)
from src.livetranscripts.whisper_integration import TranscriptionResult, TranscriptionSegment


class TestGeminiConfig:
    """Test Gemini configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GeminiConfig()
        assert config.model == "gemini-1.5-flash"
        assert config.temperature == 0.3
        assert config.max_tokens == 2048
        assert config.context_window_minutes == 5
        assert config.insight_interval_seconds == 60

    def test_custom_config(self):
        """Test custom configuration values."""
        config = GeminiConfig(
            model="gemini-pro-vision",
            temperature=0.7,
            max_tokens=4096,
            context_window_minutes=10,
            insight_interval_seconds=30
        )
        assert config.model == "gemini-pro-vision"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.context_window_minutes == 10
        assert config.insight_interval_seconds == 30

    def test_invalid_config(self):
        """Test invalid configuration values."""
        with pytest.raises(ValueError, match="Temperature must be between 0 and 1"):
            GeminiConfig(temperature=1.5)
        
        with pytest.raises(ValueError, match="Context window must be positive"):
            GeminiConfig(context_window_minutes=0)


class TestChatMessage:
    """Test chat message data structure."""

    def test_message_creation(self):
        """Test creating a chat message."""
        message = ChatMessage(
            role="user",
            content="What was discussed about the budget?",
            timestamp=datetime.now()
        )
        
        assert message.role == "user"
        assert message.content == "What was discussed about the budget?"
        assert isinstance(message.timestamp, datetime)

    def test_message_validation(self):
        """Test message validation."""
        # Valid message
        valid_message = ChatMessage(
            role="user",
            content="Valid question",
            timestamp=datetime.now()
        )
        assert valid_message.is_valid() is True
        
        # Invalid role
        with pytest.raises(ValueError, match="Invalid role"):
            ChatMessage(role="invalid", content="Test", timestamp=datetime.now())
        
        # Empty content
        empty_message = ChatMessage(
            role="user",
            content="",
            timestamp=datetime.now()
        )
        assert empty_message.is_valid() is False

    def test_message_formatting(self):
        """Test message formatting for API."""
        message = ChatMessage(
            role="user",
            content="Test question",
            timestamp=datetime.now()
        )
        
        formatted = message.to_api_format()
        assert formatted["role"] == "user"
        assert formatted["parts"] == [{"text": "Test question"}]


class TestMeetingInsight:
    """Test meeting insight data structure."""

    def test_insight_creation(self):
        """Test creating a meeting insight."""
        insight = MeetingInsight(
            type=InsightType.SUMMARY,
            content="Key discussion points: budget, timeline, resources",
            confidence=0.85,
            timestamp=datetime.now(),
            context_duration=300  # 5 minutes
        )
        
        assert insight.type == InsightType.SUMMARY
        assert "budget" in insight.content
        assert insight.confidence == 0.85
        assert insight.context_duration == 300

    def test_insight_relevance_score(self):
        """Test calculating insight relevance score."""
        recent_insight = MeetingInsight(
            type=InsightType.ACTION_ITEM,
            content="Follow up on budget approval",
            confidence=0.9,
            timestamp=datetime.now(),
            context_duration=60
        )
        
        old_insight = MeetingInsight(
            type=InsightType.SUMMARY,
            content="Old summary",
            confidence=0.8,
            timestamp=datetime.now() - timedelta(hours=1),
            context_duration=120
        )
        
        # Recent insight should have higher relevance
        assert recent_insight.relevance_score() > old_insight.relevance_score()

    def test_insight_types(self):
        """Test different insight types."""
        types = [
            InsightType.SUMMARY,
            InsightType.ACTION_ITEM,
            InsightType.QUESTION,
            InsightType.DECISION,
            InsightType.FOLLOW_UP
        ]
        
        for insight_type in types:
            insight = MeetingInsight(
                type=insight_type,
                content=f"Test {insight_type.value}",
                confidence=0.8,
                timestamp=datetime.now()
            )
            assert insight.type == insight_type


class TestContextManager:
    """Test context management for rolling window."""

    @pytest.fixture
    def context_manager(self):
        """Create context manager with 5-minute window."""
        config = GeminiConfig(context_window_minutes=5)
        return ContextManager(config)

    def test_add_transcription(self, context_manager):
        """Test adding transcription to context."""
        transcription = TranscriptionResult(
            text="This is a test transcription",
            segments=[
                TranscriptionSegment("This is a test", 0.0, 2.0, 0.9),
                TranscriptionSegment("transcription", 2.0, 3.5, 0.95)
            ],
            language="en",
            duration=3.5,
            batch_id=1
        )
        
        context_manager.add_transcription(transcription)
        
        assert len(context_manager.transcriptions) == 1
        assert context_manager.transcriptions[0] == transcription

    def test_context_window_pruning(self, context_manager):
        """Test that old transcriptions are pruned from context."""
        # Add transcriptions with timestamps spread over time
        old_time = datetime.now() - timedelta(minutes=10)
        recent_time = datetime.now() - timedelta(minutes=2)
        current_time = datetime.now()
        
        transcriptions = [
            TranscriptionResult("Old text", [], "en", 1.0, 1, timestamp=old_time),
            TranscriptionResult("Recent text", [], "en", 1.0, 2, timestamp=recent_time),
            TranscriptionResult("Current text", [], "en", 1.0, 3, timestamp=current_time)
        ]
        
        for transcript in transcriptions:
            context_manager.add_transcription(transcript)
        
        # Prune old context
        context_manager.prune_old_context()
        
        # Should only have recent and current transcriptions
        assert len(context_manager.transcriptions) == 2
        assert context_manager.transcriptions[0].batch_id == 2
        assert context_manager.transcriptions[1].batch_id == 3

    def test_get_context_text(self, context_manager):
        """Test getting formatted context text."""
        transcriptions = [
            TranscriptionResult("First part", [], "en", 1.0, 1),
            TranscriptionResult("Second part", [], "en", 1.0, 2),
            TranscriptionResult("Third part", [], "en", 1.0, 3)
        ]
        
        for transcript in transcriptions:
            context_manager.add_transcription(transcript)
        
        context_text = context_manager.get_context_text()
        
        assert "First part" in context_text
        assert "Second part" in context_text
        assert "Third part" in context_text

    def test_context_statistics(self, context_manager):
        """Test context statistics calculation."""
        transcriptions = [
            TranscriptionResult("Short", [], "en", 1.0, 1),
            TranscriptionResult("Medium length text", [], "en", 2.0, 2),
            TranscriptionResult("This is a much longer transcription text", [], "en", 3.0, 3)
        ]
        
        for transcript in transcriptions:
            context_manager.add_transcription(transcript)
        
        stats = context_manager.get_context_stats()
        
        assert stats["total_duration"] == 6.0
        assert stats["transcription_count"] == 3
        assert stats["average_duration"] == 2.0
        assert "word_count" in stats


class TestInsightGenerator:
    """Test automated insight generation."""

    @pytest.fixture
    def mock_gemini_client(self):
        """Create mock Gemini client."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Generated insight about the meeting"
        mock_client.generate_content_async = AsyncMock(return_value=mock_response)
        return mock_client

    @pytest.fixture
    def insight_generator(self, mock_gemini_client):
        """Create insight generator with mock client."""
        config = GeminiConfig(insight_interval_seconds=30)
        context_manager = ContextManager(config)
        
        generator = InsightGenerator(config, context_manager)
        generator.client = mock_gemini_client
        return generator, mock_gemini_client

    @pytest.mark.asyncio
    async def test_generate_summary(self, insight_generator):
        """Test generating meeting summary."""
        generator, mock_client = insight_generator
        
        # Add some context
        transcriptions = [
            TranscriptionResult("We discussed the quarterly budget", [], "en", 2.0, 1),
            TranscriptionResult("The timeline needs to be adjusted", [], "en", 2.0, 2),
            TranscriptionResult("Let's schedule a follow-up meeting", [], "en", 2.0, 3)
        ]
        
        for transcript in transcriptions:
            generator.context_manager.add_transcription(transcript)
        
        insight = await generator.generate_summary()
        
        assert isinstance(insight, MeetingInsight)
        assert insight.type == InsightType.SUMMARY
        assert insight.content == "Generated insight about the meeting"
        mock_client.generate_content_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_action_items(self, insight_generator):
        """Test generating action items."""
        generator, mock_client = insight_generator
        
        # Mock response with action items
        mock_response = Mock()
        mock_response.text = "1. Review budget proposal\n2. Schedule follow-up meeting\n3. Update timeline"
        mock_client.generate_content_async.return_value = mock_response
        
        transcriptions = [
            TranscriptionResult("John will review the budget proposal", [], "en", 2.0, 1),
            TranscriptionResult("We need to schedule a follow-up", [], "en", 2.0, 2),
            TranscriptionResult("Sarah will update the timeline", [], "en", 2.0, 3)
        ]
        
        for transcript in transcriptions:
            generator.context_manager.add_transcription(transcript)
        
        insight = await generator.generate_action_items()
        
        assert insight.type == InsightType.ACTION_ITEM
        assert "Review budget proposal" in insight.content
        assert "Schedule follow-up meeting" in insight.content

    @pytest.mark.asyncio
    async def test_insight_scheduling(self, insight_generator):
        """Test automated insight generation scheduling."""
        generator, mock_client = insight_generator
        
        # Mock different responses for different calls
        responses = [
            Mock(text="First automated insight"),
            Mock(text="Second automated insight")
        ]
        mock_client.generate_content_async.side_effect = responses
        
        # Add context
        transcription = TranscriptionResult("Meeting content", [], "en", 2.0, 1)
        generator.context_manager.add_transcription(transcription)
        
        # Start automated insights with short interval for testing
        generator.config.insight_interval_seconds = 0.1
        
        insights = []
        def insight_callback(insight):
            insights.append(insight)
        
        # Run for a short time to collect insights
        task = asyncio.create_task(generator.start_automated_insights(insight_callback))
        await asyncio.sleep(0.3)  # Let it run for 300ms
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should have generated at least one insight
        assert len(insights) >= 1
        assert insights[0].content == "First automated insight"

    def test_prompt_construction(self, insight_generator):
        """Test construction of prompts for different insight types."""
        generator, _ = insight_generator
        
        context_text = "We discussed the budget and timeline for the project."
        
        # Test summary prompt
        summary_prompt = generator._build_summary_prompt(context_text)
        assert "summary" in summary_prompt.lower()
        assert context_text in summary_prompt
        
        # Test action items prompt
        action_prompt = generator._build_action_items_prompt(context_text)
        assert "action" in action_prompt.lower()
        assert context_text in action_prompt
        
        # Test questions prompt
        questions_prompt = generator._build_questions_prompt(context_text)
        assert "question" in questions_prompt.lower()
        assert context_text in questions_prompt


class TestQAHandler:
    """Test live Q&A functionality."""

    @pytest.fixture
    def mock_gemini_client(self):
        """Create mock Gemini client for Q&A."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Based on the meeting discussion, the budget was approved for Q2."
        mock_client.generate_content_async = AsyncMock(return_value=mock_response)
        return mock_client

    @pytest.fixture
    def qa_handler(self, mock_gemini_client):
        """Create Q&A handler with mock client."""
        config = GeminiConfig()
        context_manager = ContextManager(config)
        
        handler = QAHandler(config, context_manager)
        handler.client = mock_gemini_client
        return handler, mock_gemini_client

    @pytest.mark.asyncio
    async def test_answer_question(self, qa_handler):
        """Test answering a user question."""
        handler, mock_client = qa_handler
        
        # Add meeting context
        transcriptions = [
            TranscriptionResult("The Q2 budget was discussed", [], "en", 2.0, 1),
            TranscriptionResult("We approved the 50K allocation", [], "en", 2.0, 2),
            TranscriptionResult("Next steps include procurement", [], "en", 2.0, 3)
        ]
        
        for transcript in transcriptions:
            handler.context_manager.add_transcription(transcript)
        
        question = "What was decided about the budget?"
        answer = await handler.answer_question(question)
        
        assert answer == "Based on the meeting discussion, the budget was approved for Q2."
        mock_client.generate_content_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_conversation_history(self, qa_handler):
        """Test maintaining conversation history."""
        handler, mock_client = qa_handler
        
        # Add initial context
        transcription = TranscriptionResult("We discussed project timeline", [], "en", 2.0, 1)
        handler.context_manager.add_transcription(transcription)
        
        # Ask first question
        await handler.answer_question("What was discussed?")
        
        # Mock second response
        mock_response2 = Mock()
        mock_response2.text = "The timeline is 6 months based on previous discussion."
        mock_client.generate_content_async.return_value = mock_response2
        
        # Ask follow-up question
        answer2 = await handler.answer_question("How long is the timeline?")
        
        assert len(handler.conversation_history) == 4  # 2 questions + 2 answers
        assert answer2 == "The timeline is 6 months based on previous discussion."

    def test_conversation_pruning(self, qa_handler):
        """Test pruning of old conversation history."""
        handler, _ = qa_handler
        
        # Add many messages to exceed limit
        for i in range(25):  # Exceed default limit of 20
            handler.conversation_history.append(
                ChatMessage(
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Message {i}",
                    timestamp=datetime.now()
                )
            )
        
        handler._prune_conversation_history()
        
        # Should be pruned to max limit
        assert len(handler.conversation_history) <= handler.max_conversation_length

    def test_context_aware_prompting(self, qa_handler):
        """Test that prompts include meeting context."""
        handler, _ = qa_handler
        
        # Add meeting context
        transcription = TranscriptionResult(
            "John mentioned the deadline is next Friday",
            [],
            "en",
            2.0,
            1
        )
        handler.context_manager.add_transcription(transcription)
        
        question = "When is the deadline?"
        prompt = handler._build_qa_prompt(question)
        
        assert "John mentioned the deadline is next Friday" in prompt
        assert question in prompt
        assert "meeting context" in prompt.lower()

    @pytest.mark.asyncio
    async def test_error_handling(self, qa_handler):
        """Test error handling in Q&A."""
        handler, mock_client = qa_handler
        
        # Mock API error
        mock_client.generate_content_async.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await handler.answer_question("Test question")

    @pytest.mark.asyncio
    async def test_concurrent_questions(self, qa_handler):
        """Test handling concurrent questions."""
        handler, mock_client = qa_handler
        
        # Add context
        transcription = TranscriptionResult("Meeting about new features", [], "en", 2.0, 1)
        handler.context_manager.add_transcription(transcription)
        
        # Mock different responses
        responses = [
            Mock(text="Answer 1"),
            Mock(text="Answer 2"),
            Mock(text="Answer 3")
        ]
        mock_client.generate_content_async.side_effect = responses
        
        # Ask concurrent questions
        questions = [
            "What features were discussed?",
            "Who is responsible for implementation?",
            "What is the timeline?"
        ]
        
        tasks = [handler.answer_question(q) for q in questions]
        answers = await asyncio.gather(*tasks)
        
        assert len(answers) == 3
        assert answers[0] == "Answer 1"
        assert answers[1] == "Answer 2"
        assert answers[2] == "Answer 3"


class TestGeminiClient:
    """Test the main Gemini client."""

    @pytest.fixture
    def gemini_config(self):
        """Create Gemini configuration."""
        return GeminiConfig(
            model="gemini-1.5-flash",
            temperature=0.3,
            max_tokens=2048
        )

    @pytest.fixture
    def mock_genai(self):
        """Create mock Google GenerativeAI."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Generated response"
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        
        with patch('google.generativeai.GenerativeModel') as mock_genai:
            mock_genai.return_value = mock_model
            yield mock_model

    @pytest.fixture
    def gemini_client(self, gemini_config, mock_genai):
        """Create GeminiClient with mocked dependencies."""
        with patch('google.generativeai.configure') as mock_configure:
            client = GeminiClient(gemini_config, api_key="test_key")
            client.model = mock_genai
            return client

    def test_client_initialization(self, gemini_client, gemini_config):
        """Test Gemini client initialization."""
        assert gemini_client.config == gemini_config

    @pytest.mark.asyncio
    async def test_generate_content(self, gemini_client, mock_genai):
        """Test content generation."""
        prompt = "Summarize this meeting content"
        
        response = await gemini_client.generate_content(prompt)
        
        assert response == "Generated response"
        mock_genai.generate_content_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_context(self, gemini_client, mock_genai):
        """Test content generation with conversation context."""
        conversation = [
            ChatMessage("user", "What was discussed?", datetime.now()),
            ChatMessage("assistant", "Budget and timeline", datetime.now())
        ]
        
        new_question = "What about the timeline specifically?"
        
        response = await gemini_client.generate_with_context(new_question, conversation)
        
        assert response == "Generated response"
        # Verify that context was included in the call
        call_args = mock_genai.generate_content_async.call_args
        assert "Budget and timeline" in str(call_args)

    def test_safety_settings(self, gemini_client):
        """Test that safety settings are properly configured."""
        safety_settings = gemini_client._get_safety_settings()
        
        assert len(safety_settings) > 0
        # Should have settings for various harm categories
        categories = [setting.category for setting in safety_settings]
        assert len(categories) > 0

    def test_generation_config(self, gemini_client):
        """Test generation configuration."""
        config = gemini_client._get_generation_config()
        
        assert config.temperature == 0.3
        assert config.max_output_tokens == 2048
        assert hasattr(config, 'top_p')
        assert hasattr(config, 'top_k')


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def integration_setup(self):
        """Set up components for integration testing."""
        config = GeminiConfig(
            insight_interval_seconds=1,  # Fast for testing
            context_window_minutes=10
        )
        
        context_manager = ContextManager(config)
        
        # Mock Gemini client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Integration test response"
        mock_client.generate_content_async = AsyncMock(return_value=mock_response)
        
        insight_generator = InsightGenerator(config, context_manager)
        insight_generator.client = mock_client
        
        qa_handler = QAHandler(config, context_manager)
        qa_handler.client = mock_client
        
        return {
            "context_manager": context_manager,
            "insight_generator": insight_generator,
            "qa_handler": qa_handler,
            "mock_client": mock_client
        }

    @pytest.mark.asyncio
    async def test_end_to_end_meeting_flow(self, integration_setup):
        """Test complete meeting flow with insights and Q&A."""
        components = integration_setup
        context_manager = components["context_manager"]
        insight_generator = components["insight_generator"]
        qa_handler = components["qa_handler"]
        
        # Simulate meeting progression
        meeting_transcripts = [
            "Welcome everyone to today's quarterly review",
            "First item is the budget performance",
            "We exceeded targets by 15 percent this quarter",
            "Next quarter we need to focus on cost optimization",
            "Action item: John will prepare cost analysis by Friday"
        ]
        
        # Add transcripts progressively
        for i, text in enumerate(meeting_transcripts):
            transcript = TranscriptionResult(
                text=text,
                segments=[TranscriptionSegment(text, 0.0, 2.0, 0.9)],
                language="en",
                duration=2.0,
                batch_id=i
            )
            context_manager.add_transcription(transcript)
        
        # Generate insights
        summary_insight = await insight_generator.generate_summary()
        action_insight = await insight_generator.generate_action_items()
        
        # Test Q&A
        questions = [
            "What was the budget performance?",
            "Who is responsible for the cost analysis?",
            "When is the deadline for the analysis?"
        ]
        
        answers = []
        for question in questions:
            answer = await qa_handler.answer_question(question)
            answers.append(answer)
        
        # Verify results
        assert summary_insight.type == InsightType.SUMMARY
        assert action_insight.type == InsightType.ACTION_ITEM
        assert len(answers) == 3
        
        # Context should contain all transcripts
        context_text = context_manager.get_context_text()
        for transcript_text in meeting_transcripts:
            assert transcript_text in context_text