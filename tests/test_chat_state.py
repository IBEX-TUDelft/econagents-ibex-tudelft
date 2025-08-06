import pytest

from econagents_ibex_tudelft.core.state.chat import (
    ChatHistory,
    ChatMessage,
    ChatState,
    msg,
)


class TestChatState:
    @pytest.fixture
    def chat_state(self):
        """Create a fresh ChatState for each test"""
        return ChatState()

    def test_initial_state(self, chat_state):
        """Test that ChatState initializes with empty messages"""
        assert chat_state.messages == {}
        assert isinstance(chat_state.messages, dict)

    def test_add_single_message(self, chat_state):
        """Test adding a single message to ChatState"""
        msg_data = {
            "number": 1,
            "sender": 100,
            "to": [200, 300],
            "text": "Hello world",
            "time": 1234567890,
        }

        chat_state.process_event("message-received", msg_data)

        assert 1 in chat_state.messages
        assert chat_state.messages[1].sender == 100
        assert chat_state.messages[1].to == [200, 300]
        assert chat_state.messages[1].text == "Hello world"
        assert chat_state.messages[1].time == 1234567890

    def test_add_multiple_messages(self, chat_state):
        """Test adding multiple messages to ChatState"""
        messages = [
            {"number": 1, "sender": 100, "text": "First message", "time": 1000},
            {"number": 2, "sender": 200, "text": "Second message", "time": 2000},
            {"number": 3, "sender": 300, "text": "Third message", "time": 3000},
        ]

        for msg_data in messages:
            chat_state.process_event("message-received", msg_data)

        assert len(chat_state.messages) == 3
        assert chat_state.messages[1].text == "First message"
        assert chat_state.messages[2].text == "Second message"
        assert chat_state.messages[3].text == "Third message"

    def test_message_with_optional_fields(self, chat_state):
        """Test message with optional 'to' field"""
        msg_data = {
            "number": 1,
            "sender": 100,
            "text": "Broadcast message",
            "time": 1234567890,
        }

        chat_state.process_event("message-received", msg_data)

        assert chat_state.messages[1].to == []

    def test_process_non_message_event(self, chat_state):
        """Test that non-message events are ignored"""
        initial_count = len(chat_state.messages)

        chat_state.process_event("other-event", {"data": "some data"})

        assert len(chat_state.messages) == initial_count

    def test_message_overwrite(self, chat_state):
        """Test that messages with the same ID are overwritten"""
        msg_data1 = {
            "number": 1,
            "sender": 100,
            "text": "Original message",
            "time": 1000,
        }
        msg_data2 = {
            "number": 1,
            "sender": 200,
            "text": "Updated message",
            "time": 2000,
        }

        chat_state.process_event("message-received", msg_data1)
        chat_state.process_event("message-received", msg_data2)

        assert len(chat_state.messages) == 1
        assert chat_state.messages[1].text == "Updated message"
        assert chat_state.messages[1].sender == 200


class TestMsg:
    def test_msg_creation(self):
        """Test creating a msg object"""
        message = msg(
            sender=100,
            to=[200, 300],
            number=1,
            text="Test message",
            time=1234567890,
        )

        assert message.sender == 100
        assert message.to == [200, 300]
        assert message.number == 1
        assert message.text == "Test message"
        assert message.time == 1234567890

    def test_msg_optional_number(self):
        """Test msg with optional number field"""
        message = msg(
            sender=100,
            to=[200],
            number=None,
            text="Test message",
            time=1234567890,
        )

        assert message.number is None


class TestChatMessage:
    def test_chat_message_creation(self):
        """Test creating a ChatMessage object"""
        message = ChatMessage(
            sender_id=100,
            sender_name="Alice",
            message="Hello everyone!",
            timestamp="2024-01-15 10:30:00",
        )

        assert message.sender_id == 100
        assert message.sender_name == "Alice"
        assert message.message == "Hello everyone!"
        assert message.timestamp == "2024-01-15 10:30:00"
        assert message.is_system is False

    def test_system_message(self):
        """Test creating a system message"""
        message = ChatMessage(
            sender_id=0,
            sender_name="System",
            message="Game started",
            timestamp="2024-01-15 10:00:00",
            is_system=True,
        )

        assert message.is_system is True


class TestChatHistory:
    @pytest.fixture
    def chat_history(self):
        """Create a fresh ChatHistory for each test"""
        return ChatHistory()

    def test_initial_state(self, chat_history):
        """Test that ChatHistory initializes with empty messages"""
        assert chat_history.messages == []
        assert isinstance(chat_history.messages, list)

    def test_add_message(self, chat_history):
        """Test adding messages to ChatHistory"""
        message = ChatMessage(
            sender_id=100,
            sender_name="Alice",
            message="Hello!",
            timestamp="2024-01-15 10:30:00",
        )

        chat_history.add_message(message)

        assert len(chat_history.messages) == 1
        assert chat_history.messages[0] == message

    def test_formatted_history(self, chat_history):
        """Test the formatted_history computed field"""
        messages = [
            ChatMessage(
                sender_id=100,
                sender_name="Alice",
                message="Hello everyone!",
                timestamp="2024-01-15 10:30:00",
            ),
            ChatMessage(
                sender_id=200,
                sender_name="Bob",
                message="Hi Alice!",
                timestamp="2024-01-15 10:31:00",
            ),
            ChatMessage(
                sender_id=0,
                sender_name="System",
                message="Round 1 started",
                timestamp="2024-01-15 10:32:00",
                is_system=True,
            ),
        ]

        for m in messages:
            chat_history.add_message(m)

        expected = "[Alice] Hello everyone!\n[Bob] Hi Alice!\n[System] Round 1 started"
        assert chat_history.formatted_history == expected

    def test_empty_formatted_history(self, chat_history):
        """Test formatted_history with no messages"""
        assert chat_history.formatted_history == ""
