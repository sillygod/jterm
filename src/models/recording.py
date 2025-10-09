"""Recording SQLAlchemy model."""

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Index, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class RecordingStatus(str, Enum):
    """Recording status enumeration."""
    RECORDING = "recording"
    STOPPED = "stopped"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Recording(Base):
    """
    Recording model containing timestamped input/output data and metadata.

    This model supports session playback with event storage, checkpoints for seeking,
    and export capabilities in multiple formats.
    """
    __tablename__ = "recordings"

    # Primary fields
    recording_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the recording"
    )
    session_id = Column(
        String(36),
        ForeignKey("terminal_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True,
        comment="Reference to the terminal session"
    )
    user_id = Column(
        String(36),
        ForeignKey("user_profiles.user_id"),
        nullable=False,
        index=True,
        comment="Reference to the user who owns the recording"
    )

    # Timing
    start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Recording start timestamp"
    )
    end_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Recording end timestamp (null if active)"
    )
    duration = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Recording duration in milliseconds"
    )

    # Status and metadata
    status = Column(
        String(20),
        nullable=False,
        default=RecordingStatus.RECORDING,
        index=True,
        comment="Current recording status"
    )
    file_size = Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total recording file size in bytes"
    )
    event_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of recorded events"
    )

    # Terminal configuration
    terminal_size = Column(
        JSON,
        nullable=False,
        default=lambda: {"cols": 80, "rows": 24},
        comment="Terminal dimensions during recording"
    )

    # Export and processing
    export_formats = Column(
        JSON,
        nullable=False,
        default=lambda: ["json"],
        comment="Available export formats"
    )
    compression_ratio = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Compression ratio achieved (percentage)"
    )

    # Data storage
    events = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Array of recorded events"
    )
    checkpoints = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Playback checkpoints for seeking"
    )
    extra_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional recording metadata"
    )

    # Relationships
    terminal_session = relationship(
        "TerminalSession",
        back_populates="recording"
    )
    user_profile = relationship(
        "UserProfile",
        back_populates="recordings"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_recordings_user_status", "user_id", "status"),
        Index("idx_recordings_start_time", "start_time"),
        Index("idx_recordings_file_size", "file_size"),
    )

    @validates('status')
    def validate_status(self, key: str, value: str) -> str:
        """Validate status transitions."""
        if value not in [status.value for status in RecordingStatus]:
            raise ValueError(f"Invalid status: {value}")
        return value

    @validates('file_size')
    def validate_file_size(self, key: str, value: int) -> int:
        """Validate file size does not exceed 100MB limit."""
        max_size = 100 * 1024 * 1024  # 100MB
        if value > max_size:
            raise ValueError(f"Recording file size cannot exceed {max_size} bytes")
        return value

    @validates('events')
    def validate_events(self, key: str, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate events are chronologically ordered."""
        if not isinstance(value, list):
            return value

        # Check chronological ordering
        last_timestamp = None
        for event in value:
            if isinstance(event, dict) and 'timestamp' in event:
                try:
                    timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    if last_timestamp and timestamp < last_timestamp:
                        raise ValueError("Events must be chronologically ordered")
                    last_timestamp = timestamp
                except (ValueError, TypeError):
                    continue  # Skip invalid timestamp formats

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

    def can_transition_to(self, new_status: RecordingStatus) -> bool:
        """
        Check if recording can transition to the new status.

        Valid transitions:
        - recording → stopped, failed
        - stopped → processing, failed
        - processing → ready, failed
        - ready → (no transitions)
        - failed → processing (for retry)
        """
        current = RecordingStatus(self.status)

        valid_transitions = {
            RecordingStatus.RECORDING: [RecordingStatus.STOPPED, RecordingStatus.FAILED],
            RecordingStatus.STOPPED: [RecordingStatus.PROCESSING, RecordingStatus.FAILED],
            RecordingStatus.PROCESSING: [RecordingStatus.READY, RecordingStatus.FAILED],
            RecordingStatus.READY: [],
            RecordingStatus.FAILED: [RecordingStatus.PROCESSING]  # Allow retry
        }

        return new_status in valid_transitions.get(current, [])

    def add_event(self, event_type: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a new event to the recording."""
        if self.status != RecordingStatus.RECORDING:
            raise ValueError("Cannot add events to non-recording session")

        now = datetime.now(timezone.utc)
        event = {
            "timestamp": now.isoformat(),
            "deltaTime": 0,  # Will be calculated
            "type": event_type,
            "data": data,
            "size": len(str(data).encode('utf-8')),
            "extra_metadata": metadata or {}
        }

        # Calculate delta time from previous event
        if self.events:
            last_event = self.events[-1]
            try:
                last_timestamp = datetime.fromisoformat(last_event['timestamp'].replace('Z', '+00:00'))
                delta = int((now - last_timestamp).total_seconds() * 1000)
                event["deltaTime"] = delta
            except (ValueError, KeyError):
                pass

        # Add event and update counters
        current_events = list(self.events or [])
        current_events.append(event)
        self.events = current_events
        self.event_count = len(current_events)
        self.file_size += event["size"]

    def add_checkpoint(self, description: str, terminal_state: str) -> None:
        """Add a playback checkpoint."""
        checkpoint = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "eventIndex": len(self.events or []),
            "terminalState": terminal_state,
            "description": description
        }

        current_checkpoints = list(self.checkpoints or [])
        current_checkpoints.append(checkpoint)
        self.checkpoints = current_checkpoints

    def stop_recording(self) -> None:
        """Stop the recording and calculate final duration."""
        if self.can_transition_to(RecordingStatus.STOPPED):
            self.status = RecordingStatus.STOPPED
            self.end_time = datetime.now(timezone.utc)
            if self.start_time:
                # Ensure start_time is timezone-aware for proper calculation
                start_time = self.start_time
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                self.duration = int((self.end_time - start_time).total_seconds() * 1000)
        else:
            raise ValueError(f"Cannot stop recording from status: {self.status}")

    def start_processing(self) -> None:
        """Start processing the recording."""
        if self.can_transition_to(RecordingStatus.PROCESSING):
            self.status = RecordingStatus.PROCESSING
        else:
            raise ValueError(f"Cannot start processing from status: {self.status}")

    def mark_ready(self, compression_ratio: int = 0) -> None:
        """Mark recording as ready and set compression ratio."""
        if self.can_transition_to(RecordingStatus.READY):
            self.status = RecordingStatus.READY
            self.compression_ratio = compression_ratio
        else:
            raise ValueError(f"Cannot mark ready from status: {self.status}")

    def mark_failed(self) -> None:
        """Mark recording as failed."""
        if self.can_transition_to(RecordingStatus.FAILED):
            self.status = RecordingStatus.FAILED
        else:
            raise ValueError(f"Cannot mark failed from status: {self.status}")

    def is_expired(self, retention_days: int = 30) -> bool:
        """Check if recording is expired based on retention policy."""
        if not self.end_time:
            return False

        expiry_date = self.end_time + timedelta(days=retention_days)
        return datetime.now(timezone.utc) > expiry_date

    def get_events_in_range(self, start_index: int, end_index: int) -> List[Dict[str, Any]]:
        """Get events within a specific index range."""
        if not self.events:
            return []

        start_index = max(0, start_index)
        end_index = min(len(self.events), end_index)

        return self.events[start_index:end_index]

    def get_checkpoint_at_time(self, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Find the nearest checkpoint before or at the given timestamp."""
        if not self.checkpoints:
            return None

        target_timestamp = timestamp.isoformat()
        nearest_checkpoint = None

        for checkpoint in self.checkpoints:
            if checkpoint.get('timestamp', '') <= target_timestamp:
                nearest_checkpoint = checkpoint
            else:
                break

        return nearest_checkpoint

    def calculate_compression_savings(self) -> Dict[str, Any]:
        """Calculate compression statistics."""
        if not self.events:
            return {"original_size": 0, "compressed_size": 0, "savings": 0}

        # Estimate original size (uncompressed JSON)
        original_size = len(str(self.events).encode('utf-8'))
        compressed_size = self.file_size
        savings = max(0, original_size - compressed_size)

        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "savings": savings,
            "ratio": self.compression_ratio
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert recording to dictionary representation."""
        return {
            "recording_id": self.recording_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status,
            "file_size": self.file_size,
            "event_count": self.event_count,
            "terminal_size": self.terminal_size,
            "export_formats": self.export_formats,
            "compression_ratio": self.compression_ratio,
            "extra_metadata": self.extra_metadata,
            "checkpoint_count": len(self.checkpoints or [])
        }

    def __repr__(self) -> str:
        """String representation of the recording."""
        return (
            f"<Recording(recording_id='{self.recording_id}', "
            f"session_id='{self.session_id}', status='{self.status}', "
            f"duration={self.duration}ms, events={self.event_count})>"
        )