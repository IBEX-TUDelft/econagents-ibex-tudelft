from typing import Any, List, Optional

from pydantic import BaseModel, Field, computed_field


class msg(BaseModel):
    sender: int
    to: list[int]
    number: Optional[int]
    text: str
    time: int


class ChatState(BaseModel):
    """
    Represents the current state of the chat:
    - History of messages
    """

    messages: dict[int, msg] = Field(default_factory=dict)

    def _on_add_msg(self, msg_data: dict):
        """
        The server is telling us a new msg has been received.
        We'll store it in self.messages .
        """
        msg_id = msg_data["number"]
        new_msg = msg(
            sender=msg_data["sender"],
            to=msg_data.get("to", []),
            number=msg_data.get("number"),
            text=msg_data["text"],
            time=msg_data["time"],
        )
        self.messages[msg_id] = new_msg

    def process_event(self, event_type: str, data: dict):
        """
        Update the ChatState based on the eventType and
        event data from the server.
        """
        if event_type == "message-received":
            self._on_add_msg(data)


class ChatMessage(BaseModel):
    """Represents a single chat message in the game."""

    sender_id: int
    sender_name: str
    message: str
    timestamp: str
    is_system: bool = False


class ChatHistory(BaseModel):
    """Manages a collection of chat messages."""

    messages: List[ChatMessage] = Field(default_factory=list)

    def add_message(self, message: ChatMessage) -> None:
        """Add a new message to the chat history."""
        self.messages.append(message)

    @computed_field
    def formatted_history(self) -> str:
        """Return a formatted string representation of the chat history."""
        result = []
        for msg in self.messages:
            prefix = f"[{msg.sender_name}]"
            result.append(f"{prefix} {msg.message}")
        return "\n".join(result)
