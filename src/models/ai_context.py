"""AI Context SQLAlchemy model."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Index, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class AIContext(Base):
    """
    AI Context model for conversation history and contextual information.

    Maintains AI assistant interaction history, terminal context, user preferences,
    and token usage statistics for intelligent assistance within terminal sessions.
    """
    __tablename__ = "ai_contexts"

    # Primary fields
    context_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the AI context"
    )
    session_id = Column(
        String(36),
        ForeignKey("terminal_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the terminal session"
    )
    user_id = Column(
        String(36),
        ForeignKey("user_profiles.user_id"),
        nullable=False,
        index=True,
        comment="Reference to the user"
    )

    # Conversation data
    conversation_history = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Array of AI conversation messages"
    )
    terminal_context = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "recentCommands": [],
            "currentDirectory": "/",
            "environmentInfo": {},
            "activeProcesses": [],
            "fileSystemContext": []
        },
        comment="Recent terminal commands and output"
    )
    user_preferences = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="User AI preferences"
    )

    # AI model configuration
    model_provider = Column(
        String(50),
        nullable=False,
        default="openai",
        comment="AI model provider (openai, anthropic, local)"
    )
    model_name = Column(
        String(100),
        nullable=False,
        default="gpt-4",
        comment="Specific model name"
    )
    context_window = Column(
        Integer,
        nullable=False,
        default=8192,
        comment="Maximum context window size"
    )
    temperature = Column(
        Float,
        nullable=False,
        default=0.7,
        comment="AI response randomness (0-1)"
    )
    max_tokens = Column(
        Integer,
        nullable=False,
        default=1000,
        comment="Maximum response length"
    )
    system_prompt = Column(
        Text,
        nullable=False,
        default="You are a helpful AI assistant integrated into a terminal environment.",
        comment="System prompt for AI behavior"
    )

    # Timestamps
    last_interaction_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Last AI interaction timestamp"
    )

    # Usage statistics
    token_usage = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "request_count": 0,
            "average_response_time": 0.0
        },
        comment="Token usage statistics"
    )

    # Additional settings
    settings = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional AI settings"
    )
    extra_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional context metadata"
    )

    # Relationships
    terminal_session = relationship(
        "TerminalSession",
        back_populates="ai_contexts"
    )
    user_profile = relationship(
        "UserProfile",
        back_populates="ai_contexts"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_ai_contexts_user_session", "user_id", "session_id"),
        Index("idx_ai_contexts_last_interaction", "last_interaction_at"),
        Index("idx_ai_contexts_provider_model", "model_provider", "model_name"),
    )

    @validates('model_provider')
    def validate_model_provider(self, key: str, value: str) -> str:
        """Validate model provider."""
        valid_providers = ["openai", "anthropic", "local", "huggingface", "cohere"]
        if value not in valid_providers:
            raise ValueError(f"Invalid model provider: {value}. Must be one of: {valid_providers}")
        return value

    @validates('temperature')
    def validate_temperature(self, key: str, value: float) -> float:
        """Validate temperature value."""
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        return float(value)

    @validates('max_tokens')
    def validate_max_tokens(self, key: str, value: int) -> int:
        """Validate max tokens."""
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Max tokens must be a positive integer")

        # Reasonable upper limit
        if value > 32000:
            raise ValueError("Max tokens cannot exceed 32000")

        return value

    @validates('context_window')
    def validate_context_window(self, key: str, value: int) -> int:
        """Validate context window size."""
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Context window must be a positive integer")

        # Common context window sizes
        valid_sizes = [2048, 4096, 8192, 16384, 32768, 65536, 131072]
        if value not in valid_sizes:
            # Find the closest valid size
            closest = min(valid_sizes, key=lambda x: abs(x - value))
            return closest

        return value

    @validates('conversation_history')
    def validate_conversation_history(self, key: str, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate conversation history structure and limit."""
        if not isinstance(value, list):
            raise ValueError("Conversation history must be a list")

        # Limit to 100 messages to manage memory
        if len(value) > 100:
            value = value[-100:]  # Keep last 100 messages

        # Validate message structure
        for i, message in enumerate(value):
            if not isinstance(message, dict):
                raise ValueError(f"Message {i} must be a dictionary")

            required_fields = ["messageId", "timestamp", "role", "content", "type"]
            for field in required_fields:
                if field not in message:
                    raise ValueError(f"Message {i} missing required field: {field}")

            valid_roles = ["user", "assistant", "system"]
            if message.get("role") not in valid_roles:
                raise ValueError(f"Invalid role in message {i}: {message.get('role')}")

            valid_types = ["text", "voice", "command", "explanation"]
            if message.get("type") not in valid_types:
                raise ValueError(f"Invalid type in message {i}: {message.get('type')}")

        return value

    @validates('terminal_context')
    def validate_terminal_context(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate terminal context structure."""
        if not isinstance(value, dict):
            raise ValueError("Terminal context must be a dictionary")

        required_fields = ["recentCommands", "currentDirectory", "environmentInfo", "activeProcesses", "fileSystemContext"]
        for field in required_fields:
            if field not in value:
                value[field] = [] if field != "currentDirectory" and field != "environmentInfo" else ({} if field == "environmentInfo" else "/")

        # Validate recent commands structure
        recent_commands = value.get("recentCommands", [])
        if not isinstance(recent_commands, list):
            value["recentCommands"] = []
        else:
            # Limit to 20 most recent commands
            if len(recent_commands) > 20:
                value["recentCommands"] = recent_commands[-20:]

        return value

    @validates('token_usage')
    def validate_token_usage(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate token usage statistics."""
        if not isinstance(value, dict):
            raise ValueError("Token usage must be a dictionary")

        default_usage = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "request_count": 0,
            "average_response_time": 0.0
        }

        # Ensure all required fields exist
        for field, default_value in default_usage.items():
            if field not in value:
                value[field] = default_value

        # Validate numeric values
        for field in ["total_input_tokens", "total_output_tokens", "request_count"]:
            if not isinstance(value[field], int) or value[field] < 0:
                value[field] = 0

        for field in ["total_cost", "average_response_time"]:
            if not isinstance(value[field], (int, float)) or value[field] < 0:
                value[field] = 0.0

        return value

    def add_message(self, role: str, content: str, message_type: str = "text",
                   tokens: int = 0, processing_time: float = 0.0,
                   confidence: float = 1.0, sources: List[str] = None) -> str:
        """Add a new message to the conversation history."""
        message_id = str(uuid.uuid4())
        message = {
            "messageId": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
            "type": message_type,
            "tokens": tokens,
            "processingTime": processing_time,
            "confidence": confidence,
            "sources": sources or []
        }

        current_history = list(self.conversation_history or [])
        current_history.append(message)

        # Limit to 100 messages
        if len(current_history) > 100:
            current_history = current_history[-100:]

        self.conversation_history = current_history
        self.last_interaction_at = datetime.now(timezone.utc)

        # Update token usage
        self.update_token_usage(tokens, processing_time, role)

        return message_id

    def update_token_usage(self, tokens: int, processing_time: float, role: str) -> None:
        """Update token usage statistics."""
        current_usage = dict(self.token_usage or {})

        if role == "user":
            current_usage["total_input_tokens"] = current_usage.get("total_input_tokens", 0) + tokens
        elif role == "assistant":
            current_usage["total_output_tokens"] = current_usage.get("total_output_tokens", 0) + tokens

        current_usage["request_count"] = current_usage.get("request_count", 0) + 1

        # Update average response time
        if processing_time > 0:
            total_time = current_usage.get("average_response_time", 0.0) * (current_usage["request_count"] - 1)
            current_usage["average_response_time"] = (total_time + processing_time) / current_usage["request_count"]

        self.token_usage = current_usage

    def update_terminal_context(self, command: str, output: str, exit_code: int = 0,
                              working_directory: str = None) -> None:
        """Update terminal context with a new command."""
        current_context = dict(self.terminal_context or {})

        # Add command to recent commands
        recent_commands = list(current_context.get("recentCommands", []))

        command_entry = {
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "output": output[:1000] if output else "",  # Truncate output
            "exitCode": exit_code,
            "workingDirectory": working_directory or current_context.get("currentDirectory", "/")
        }

        recent_commands.append(command_entry)

        # Keep only last 20 commands
        if len(recent_commands) > 20:
            recent_commands = recent_commands[-20:]

        current_context["recentCommands"] = recent_commands

        # Update current directory if provided
        if working_directory:
            current_context["currentDirectory"] = working_directory

        self.terminal_context = current_context

    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages from conversation history."""
        if not self.conversation_history:
            return []

        return list(self.conversation_history[-count:])

    def get_context_for_ai(self, include_terminal: bool = True) -> Dict[str, Any]:
        """Get formatted context for AI model."""
        context = {
            "conversation_history": self.get_recent_messages(10),
            "model_config": {
                "provider": self.model_provider,
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            },
            "user_preferences": self.user_preferences,
            "system_prompt": self.system_prompt
        }

        if include_terminal and self.terminal_context:
            context["terminal_context"] = self.terminal_context

        return context

    def calculate_total_tokens(self) -> int:
        """Calculate total tokens used in this context."""
        usage = self.token_usage or {}
        return usage.get("total_input_tokens", 0) + usage.get("total_output_tokens", 0)

    def estimate_context_size(self) -> int:
        """Estimate current context size in tokens (rough approximation)."""
        total_chars = 0

        # Count characters in conversation history
        if self.conversation_history:
            for message in self.conversation_history:
                total_chars += len(message.get("content", ""))

        # Count characters in system prompt
        total_chars += len(self.system_prompt or "")

        # Count characters in terminal context
        if self.terminal_context:
            total_chars += len(str(self.terminal_context))

        # Rough approximation: 4 characters per token
        return total_chars // 4

    def should_prune_context(self) -> bool:
        """Check if context should be pruned based on size."""
        return self.estimate_context_size() > (self.context_window * 0.8)

    def prune_conversation_history(self, target_messages: int = 50) -> None:
        """Prune conversation history to manage context size."""
        if self.conversation_history and len(self.conversation_history) > target_messages:
            # Keep system messages and recent messages
            system_messages = [msg for msg in self.conversation_history if msg.get("role") == "system"]
            other_messages = [msg for msg in self.conversation_history if msg.get("role") != "system"]

            # Keep most recent messages
            recent_messages = other_messages[-target_messages:]

            self.conversation_history = system_messages + recent_messages

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage statistics summary."""
        usage = self.token_usage or {}
        total_tokens = self.calculate_total_tokens()

        return {
            "total_tokens": total_tokens,
            "input_tokens": usage.get("total_input_tokens", 0),
            "output_tokens": usage.get("total_output_tokens", 0),
            "request_count": usage.get("request_count", 0),
            "average_response_time": usage.get("average_response_time", 0.0),
            "estimated_cost": usage.get("total_cost", 0.0),
            "context_size_estimate": self.estimate_context_size(),
            "last_interaction": self.last_interaction_at.isoformat() if self.last_interaction_at else None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert AI context to dictionary representation."""
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "context_window": self.context_window,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "last_interaction_at": self.last_interaction_at.isoformat() if self.last_interaction_at else None,
            "conversation_history": self.conversation_history,
            "terminal_context": self.terminal_context,
            "user_preferences": self.user_preferences,
            "settings": self.settings,
            "extra_metadata": self.extra_metadata,
            "usage_summary": self.get_usage_summary(),
            "message_count": len(self.conversation_history or []),
            "should_prune": self.should_prune_context()
        }

    def __repr__(self) -> str:
        """String representation of the AI context."""
        return (
            f"<AIContext(context_id='{self.context_id}', "
            f"session_id='{self.session_id}', provider='{self.model_provider}', "
            f"model='{self.model_name}', messages={len(self.conversation_history or [])})>"
        )