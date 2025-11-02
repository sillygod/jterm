"""Performance Snapshot SQLAlchemy model."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, DateTime, Float, Integer, Index, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class PerformanceSnapshot(Base):
    """
    Performance Snapshot model for time-series performance metrics.

    Stores system performance metrics (CPU, memory, WebSocket connections)
    at regular intervals, enabling performance monitoring and historical analysis.
    Snapshots are automatically cleaned up after 24 hours.
    """
    __tablename__ = "performance_snapshots"

    # Primary fields
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the performance snapshot"
    )
    session_id = Column(
        String(36),
        ForeignKey('terminal_sessions.session_id'),
        nullable=False,
        index=True,
        comment="Associated terminal session"
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
        comment="Snapshot time"
    )

    # Server-side metrics
    cpu_percent = Column(
        Float,
        nullable=False,
        comment="Server CPU percentage (0-100)"
    )
    memory_mb = Column(
        Float,
        nullable=False,
        comment="Server memory usage in MB"
    )
    active_websockets = Column(
        Integer,
        nullable=False,
        comment="Number of active WebSocket connections"
    )
    terminal_updates_per_sec = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="Terminal write operations per second"
    )

    # Client-side metrics (optional)
    client_fps = Column(
        Float,
        nullable=True,
        comment="Client-reported frames per second"
    )
    client_memory_mb = Column(
        Float,
        nullable=True,
        comment="Client JavaScript heap memory in MB"
    )

    # Relationships
    session = relationship("TerminalSession", back_populates="performance_snapshots")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            'cpu_percent >= 0 AND cpu_percent <= 100',
            name='cpu_range'
        ),
        CheckConstraint(
            'memory_mb > 0',
            name='memory_positive'
        ),
        CheckConstraint(
            'active_websockets >= 0',
            name='websockets_non_negative'
        ),
        CheckConstraint(
            'terminal_updates_per_sec >= 0',
            name='updates_non_negative'
        ),
        Index('idx_perf_session_time', 'session_id', 'timestamp'),
        Index('idx_perf_timestamp', 'timestamp'),
    )

    @validates('cpu_percent')
    def validate_cpu_percent(self, key, cpu_percent):
        """Validate CPU percentage is within valid range."""
        if cpu_percent is None:
            raise ValueError("CPU percent cannot be None")

        if cpu_percent < 0 or cpu_percent > 100:
            raise ValueError(f"CPU percent must be between 0 and 100, got {cpu_percent}")

        return cpu_percent

    @validates('memory_mb')
    def validate_memory_mb(self, key, memory_mb):
        """Validate memory is positive."""
        if memory_mb is None:
            raise ValueError("Memory MB cannot be None")

        if memory_mb <= 0:
            raise ValueError(f"Memory MB must be positive, got {memory_mb}")

        return memory_mb

    @validates('active_websockets')
    def validate_active_websockets(self, key, active_websockets):
        """Validate websocket count is non-negative."""
        if active_websockets is None:
            raise ValueError("Active websockets cannot be None")

        if active_websockets < 0:
            raise ValueError(f"Active websockets must be non-negative, got {active_websockets}")

        return active_websockets

    @validates('terminal_updates_per_sec')
    def validate_terminal_updates(self, key, terminal_updates_per_sec):
        """Validate terminal updates per second is non-negative."""
        if terminal_updates_per_sec is None:
            raise ValueError("Terminal updates per sec cannot be None")

        if terminal_updates_per_sec < 0:
            raise ValueError(f"Terminal updates per sec must be non-negative, got {terminal_updates_per_sec}")

        return terminal_updates_per_sec

    @validates('timestamp')
    def validate_timestamp(self, key, timestamp):
        """Validate timestamp is not too old (reject stale data)."""
        if timestamp is None:
            raise ValueError("Timestamp cannot be None")

        # Reject data older than 1 hour (likely stale/erroneous)
        now = datetime.now(timezone.utc)
        age = now - timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else now - timestamp

        if age.total_seconds() > 3600:  # 1 hour
            raise ValueError(f"Timestamp is too old ({age.total_seconds()}s), rejecting stale data")

        # Also reject future timestamps (clock skew tolerance: 5 minutes)
        if timestamp > now and (timestamp - now).total_seconds() > 300:
            raise ValueError("Timestamp is in the future beyond acceptable clock skew")

        return timestamp

    @validates('client_fps')
    def validate_client_fps(self, key, client_fps):
        """Validate client FPS if provided."""
        if client_fps is not None:
            if client_fps < 0:
                raise ValueError(f"Client FPS must be non-negative, got {client_fps}")
            # Reasonable upper bound: 240 FPS
            if client_fps > 240:
                raise ValueError(f"Client FPS seems unrealistic ({client_fps}), max expected 240")

        return client_fps

    @validates('client_memory_mb')
    def validate_client_memory(self, key, client_memory_mb):
        """Validate client memory if provided."""
        if client_memory_mb is not None:
            if client_memory_mb < 0:
                raise ValueError(f"Client memory MB must be non-negative, got {client_memory_mb}")
            # Reasonable upper bound: 4GB (browser would likely crash before this)
            if client_memory_mb > 4096:
                raise ValueError(f"Client memory seems unrealistic ({client_memory_mb}MB), max expected 4096MB")

        return client_memory_mb

    def __repr__(self):
        """String representation of PerformanceSnapshot."""
        return (
            f"<PerformanceSnapshot(id={self.id}, "
            f"session_id={self.session_id}, "
            f"timestamp={self.timestamp}, "
            f"cpu={self.cpu_percent}%, "
            f"memory={self.memory_mb}MB)>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "active_websockets": self.active_websockets,
            "terminal_updates_per_sec": self.terminal_updates_per_sec,
            "client_fps": self.client_fps,
            "client_memory_mb": self.client_memory_mb
        }
