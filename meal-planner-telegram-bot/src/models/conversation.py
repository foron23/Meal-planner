"""
Conversation models for the Meal Planner Bot.

This module defines models for conversation messages and state.
Note: Actual conversation persistence is handled by LangGraph checkpoints.
These models are used for typing and data transfer.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConversationMessage(BaseModel):
    """
    Represents a single message in a conversation.
    
    Attributes:
        role: The sender role (user or assistant)
        content: Message text content
        timestamp: When the message was sent
    """
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)


class ConversationState(BaseModel):
    """
    Represents the current state of a conversation.
    
    This is primarily used for API responses and debugging.
    Actual state management is handled by LangGraph.
    
    Attributes:
        thread_id: Unique identifier for this conversation thread
        user_id: Telegram user ID
        messages: List of messages in the conversation
        is_active: Whether the conversation is currently active
        created_at: When the conversation started
        last_activity: Last message timestamp
    """
    thread_id: str
    user_id: int
    messages: List[ConversationMessage] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)
    
    def add_message(self, role: Literal["user", "assistant"], content: str) -> None:
        """
        Add a message to the conversation.
        
        Args:
            role: Message sender role
            content: Message text
        """
        message = ConversationMessage(role=role, content=content)
        self.messages.append(message)
        self.last_activity = message.timestamp
    
    def get_last_n_messages(self, n: int) -> List[ConversationMessage]:
        """
        Get the last N messages from the conversation.
        
        Args:
            n: Number of messages to retrieve
            
        Returns:
            List of the most recent messages
        """
        return self.messages[-n:] if len(self.messages) >= n else self.messages
    
    def clear(self) -> None:
        """Clear all messages from the conversation."""
        self.messages = []
        self.last_activity = datetime.utcnow()
    
    @property
    def message_count(self) -> int:
        """Get the total number of messages."""
        return len(self.messages)