"""Terminal Session SQLAlchemy model."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class SessionStatus(str, Enum):
    """Terminal session status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    RECORDING = "recording"


class TerminalSession(Base):
    """
    Terminal Session model representing an active or historical terminal instance.

    This model tracks terminal sessions with their state, metadata, and configuration.
    Supports status transitions, recording capabilities, AI assistance, and theme customization.
    """
    __tablename__ = "terminal_sessions"

    # Primary fields
    session_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the session"
    )
    user_id = Column(
        String(36),
        ForeignKey('user_profiles.user_id'),
        nullable=False,
        index=True,
        comment="Reference to the user who owns the session"
    )

    # Status and timing
    status = Column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
        comment="Current session status"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Session creation timestamp"
    )
    last_active_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Last activity timestamp"
    )
    terminated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Session termination timestamp"
    )

    # Terminal configuration
    terminal_size = Column(
        JSON,
        nullable=False,
        default=lambda: {"cols": 80, "rows": 24},
        comment="Terminal dimensions in columns and rows"
    )
    working_directory = Column(
        String(1024),
        nullable=False,
        default="/",
        comment="Current working directory path"
    )
    environment_variables = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Session environment variables"
    )
    shell_type = Column(
        String(50),
        nullable=False,
        default="bash",
        comment="Shell type (bash, zsh, fish, etc.)"
    )
    shell_pid = Column(
        Integer,
        nullable=True,
        comment="Process ID of the shell"
    )

    # Feature flags
    recording_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether session recording is active"
    )
    ai_assistant_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether AI assistance is enabled"
    )

    # References
    theme_id = Column(
        String(36),
        nullable=True,
        comment="Reference to active theme"
    )

    # Metadata
    extra_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional session metadata"
    )

    # Relationships
    recording = relationship(
        "Recording",
        back_populates="terminal_session",
        uselist=False,
        cascade="all, delete-orphan"
    )
    media_assets = relationship(
        "MediaAsset",
        back_populates="terminal_session",
        cascade="all, delete-orphan"
    )
    ai_contexts = relationship(
        "AIContext",
        back_populates="terminal_session",
        cascade="all, delete-orphan"
    )
    performance_snapshots = relationship(
        "PerformanceSnapshot",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    user_profile = relationship(
        "UserProfile",
        back_populates="terminal_sessions"
    )
    theme_configuration = relationship(
        "ThemeConfiguration",
        foreign_keys=[theme_id],
        primaryjoin="TerminalSession.theme_id == ThemeConfiguration.theme_id",
        back_populates="terminal_sessions",
        uselist=False
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_terminal_sessions_user_status", "user_id", "status"),
        Index("idx_terminal_sessions_created_at", "created_at"),
        Index("idx_terminal_sessions_last_active", "last_active_at"),
    )

    @validates('status')
    def validate_status(self, key: str, value: str) -> str:
        """Validate status transitions."""
        if value not in [status.value for status in SessionStatus]:
            raise ValueError(f"Invalid status: {value}")
        return value

    @validates('terminal_size')
    def validate_terminal_size(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate terminal size dimensions."""
        if not isinstance(value, dict):
            raise ValueError("Terminal size must be a dictionary")

        cols = value.get('cols', 80)
        rows = value.get('rows', 24)

        if not isinstance(cols, int) or not isinstance(rows, int):
            raise ValueError("Terminal columns and rows must be integers")

        if not (20 <= cols <= 500):
            raise ValueError("Terminal columns must be between 20 and 500")

        if not (5 <= rows <= 200):
            raise ValueError("Terminal rows must be between 5 and 200")

        return {"cols": cols, "rows": rows}

    @validates('last_active_at')
    def validate_last_active_at(self, key: str, value: datetime) -> datetime:
        """Validate that last_active_at is not before created_at."""
        if hasattr(self, 'created_at') and self.created_at and value < self.created_at:
            raise ValueError("last_active_at must be >= created_at")
        return value

    def can_transition_to(self, new_status: SessionStatus) -> bool:
        """
        Check if session can transition to the new status.

        Valid transitions:
        - active → inactive, terminated, recording
        - inactive → active, terminated
        - recording → active, inactive
        - terminated → (no transitions allowed)
        """
        current = SessionStatus(self.status)

        valid_transitions = {
            SessionStatus.ACTIVE: [SessionStatus.INACTIVE, SessionStatus.TERMINATED, SessionStatus.RECORDING],
            SessionStatus.INACTIVE: [SessionStatus.ACTIVE, SessionStatus.TERMINATED],
            SessionStatus.RECORDING: [SessionStatus.ACTIVE, SessionStatus.INACTIVE],
            SessionStatus.TERMINATED: []  # No transitions from terminated
        }

        return new_status in valid_transitions.get(current, [])

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_active_at = datetime.now(timezone.utc)

    def terminate(self) -> None:
        """Terminate the session and set the terminated timestamp."""
        if self.can_transition_to(SessionStatus.TERMINATED):
            self.status = SessionStatus.TERMINATED
            self.terminated_at = datetime.now(timezone.utc)
        else:
            raise ValueError(f"Cannot terminate session from status: {self.status}")

    def start_recording(self) -> None:
        """Start recording the session."""
        if self.can_transition_to(SessionStatus.RECORDING):
            self.status = SessionStatus.RECORDING
            self.recording_enabled = True
        else:
            raise ValueError(f"Cannot start recording from status: {self.status}")

    def stop_recording(self) -> None:
        """Stop recording the session."""
        if self.status == SessionStatus.RECORDING:
            self.status = SessionStatus.ACTIVE
            self.recording_enabled = False
        else:
            raise ValueError("Session is not currently recording")

    def get_uptime_seconds(self) -> int:
        """Calculate session uptime in seconds."""
        end_time = self.terminated_at or datetime.now(timezone.utc)
        return int((end_time - self.created_at).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "terminal_size": self.terminal_size,
            "working_directory": self.working_directory,
            "environment_variables": self.environment_variables,
            "shell_type": self.shell_type,
            "shell_pid": self.shell_pid,
            "recording_enabled": self.recording_enabled,
            "ai_assistant_enabled": self.ai_assistant_enabled,
            "theme_id": self.theme_id,
            "extra_metadata": self.extra_metadata,
            "uptime_seconds": self.get_uptime_seconds()
        }

    def __repr__(self) -> str:
        """String representation of the terminal session."""
        return (
            f"<TerminalSession(session_id='{self.session_id}', "
            f"user_id='{self.user_id}', status='{self.status}', "
            f"shell_type='{self.shell_type}')>"
        )