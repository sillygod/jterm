"""Image Editor SQLAlchemy models."""

import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class ImageSourceType(str, enum.Enum):
    """Image source types."""
    FILE = "file"
    CLIPBOARD = "clipboard"
    URL = "url"


class ImageFormat(str, enum.Enum):
    """Supported image formats."""
    PNG = "png"
    JPEG = "jpeg"
    GIF = "gif"
    WEBP = "webp"
    BMP = "bmp"


class OperationType(str, enum.Enum):
    """Edit operation types for undo/redo."""
    DRAW = "draw"
    TEXT = "text"
    SHAPE = "shape"
    FILTER = "filter"
    CROP = "crop"
    RESIZE = "resize"


class ImageSession(Base):
    """
    Image Session model representing an active image editing session.

    Tracks the loaded image and its editing state, including source information,
    dimensions, and modification status.
    """
    __tablename__ = "image_sessions"

    # Primary fields
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique session identifier"
    )
    terminal_session_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Terminal session ID from jterm"
    )
    image_source_type = Column(
        String(20),
        nullable=False,
        comment="Source type: file, clipboard, or url"
    )
    image_source_path = Column(
        String(1024),
        nullable=True,
        comment="File path or URL (null for clipboard)"
    )
    image_format = Column(
        String(10),
        nullable=False,
        comment="Image format: png, jpeg, gif, webp, bmp"
    )
    image_width = Column(
        Integer,
        nullable=False,
        comment="Original image width in pixels"
    )
    image_height = Column(
        Integer,
        nullable=False,
        comment="Original image height in pixels"
    )
    image_size_bytes = Column(
        Integer,
        nullable=False,
        comment="File size in bytes"
    )
    temp_file_path = Column(
        String(1024),
        nullable=False,
        comment="Path to temporary working copy"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Session creation timestamp"
    )
    last_modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Last edit timestamp"
    )

    # State
    is_modified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether image has unsaved edits"
    )

    # Relationships
    annotation_layer = relationship(
        "AnnotationLayer",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )
    edit_operations = relationship(
        "EditOperation",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "image_source_type IN ('file', 'clipboard', 'url')",
            name='valid_source_type'
        ),
        CheckConstraint(
            "image_format IN ('png', 'jpeg', 'gif', 'webp', 'bmp')",
            name='valid_format'
        ),
        CheckConstraint(
            'image_width > 0 AND image_width <= 32767',
            name='valid_width'
        ),
        CheckConstraint(
            'image_height > 0 AND image_height <= 32767',
            name='valid_height'
        ),
        CheckConstraint(
            'image_size_bytes <= 52428800',
            name='file_size_limit'
        ),
        Index('idx_terminal_session', 'terminal_session_id'),
        Index('idx_created_at', 'created_at'),
    )

    @validates('image_width', 'image_height')
    def validate_dimensions(self, key, value):
        """Validate image dimensions are within Canvas API limits."""
        if value <= 0:
            raise ValueError(f"{key} must be positive")
        if value > 32767:
            raise ValueError(f"{key} exceeds Canvas API limit of 32767 pixels")
        return value

    @validates('image_size_bytes')
    def validate_file_size(self, key, file_size):
        """Validate file size is within 50MB limit."""
        if file_size <= 0:
            raise ValueError("File size must be positive")
        if file_size > 52428800:  # 50MB
            raise ValueError("File size exceeds 50MB limit")
        return file_size

    @validates('temp_file_path')
    def validate_temp_file_path(self, key, temp_file_path):
        """Validate temporary file path."""
        if not temp_file_path:
            raise ValueError("Temporary file path cannot be empty")
        # Basic path security check
        if '..' in temp_file_path:
            raise ValueError("Path traversal detected in temp_file_path")
        return temp_file_path

    def __repr__(self):
        """String representation of ImageSession."""
        return (
            f"<ImageSession(id={self.id}, "
            f"source_type={self.image_source_type}, "
            f"format={self.image_format}, "
            f"dimensions={self.image_width}x{self.image_height}, "
            f"is_modified={self.is_modified})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "terminal_session_id": self.terminal_session_id,
            "image_source_type": self.image_source_type,
            "image_source_path": self.image_source_path,
            "image_format": self.image_format,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "image_size_bytes": self.image_size_bytes,
            "temp_file_path": self.temp_file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_modified_at": self.last_modified_at.isoformat() if self.last_modified_at else None,
            "is_modified": self.is_modified
        }


class AnnotationLayer(Base):
    """
    Annotation Layer model storing canvas annotation state.

    Uses Fabric.js JSON serialization to persist canvas objects (drawings, text, shapes)
    for save/restore operations with optimistic locking via version field.
    """
    __tablename__ = "annotation_layers"

    # Primary fields
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique layer identifier"
    )
    session_id = Column(
        String(36),
        ForeignKey('image_sessions.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        comment="Reference to ImageSession (one-to-one)"
    )
    canvas_json = Column(
        Text,
        nullable=False,
        comment="Fabric.js canvas serialization"
    )
    version = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Increments on each save (optimistic locking)"
    )
    last_updated = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Timestamp of last update"
    )

    # Relationships
    session = relationship("ImageSession", back_populates="annotation_layer")

    @validates('canvas_json')
    def validate_canvas_json(self, key, canvas_json):
        """Validate canvas JSON is not empty."""
        if not canvas_json:
            raise ValueError("Canvas JSON cannot be empty")
        # Basic JSON size check (warn if >50MB)
        if len(canvas_json) > 52428800:
            raise ValueError("Canvas JSON exceeds 50MB size limit")
        return canvas_json

    @validates('version')
    def validate_version(self, key, version):
        """Validate version is positive."""
        if version < 1:
            raise ValueError("Version must be at least 1")
        return version

    def __repr__(self):
        """String representation of AnnotationLayer."""
        json_size = len(self.canvas_json) if self.canvas_json else 0
        return (
            f"<AnnotationLayer(id={self.id}, "
            f"session_id={self.session_id}, "
            f"version={self.version}, "
            f"json_size={json_size} bytes)>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "canvas_json": self.canvas_json,
            "version": self.version,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class EditOperation(Base):
    """
    Edit Operation model representing a single edit in the undo/redo history stack.

    Stores canvas state snapshots to enable undo/redo functionality with a circular
    buffer of up to 50 operations per session.
    """
    __tablename__ = "edit_operations"

    # Primary fields
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique operation identifier"
    )
    session_id = Column(
        String(36),
        ForeignKey('image_sessions.id', ondelete='CASCADE'),
        nullable=False,
        comment="Reference to ImageSession"
    )
    operation_type = Column(
        String(20),
        nullable=False,
        comment="Type: draw, text, shape, filter, crop, resize"
    )
    canvas_snapshot = Column(
        Text,
        nullable=False,
        comment="Fabric.js canvas state at this point"
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When operation was performed"
    )
    position = Column(
        Integer,
        nullable=False,
        comment="Position in undo/redo stack (0-49)"
    )

    # Relationships
    session = relationship("ImageSession", back_populates="edit_operations")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('draw', 'text', 'shape', 'filter', 'crop', 'resize')",
            name='valid_operation_type'
        ),
        CheckConstraint(
            'position >= 0 AND position < 50',
            name='valid_position'
        ),
        Index('idx_session_position', 'session_id', 'position'),
    )

    @validates('position')
    def validate_position(self, key, position):
        """Validate position is within circular buffer range."""
        if position < 0 or position >= 50:
            raise ValueError("Position must be between 0 and 49")
        return position

    @validates('canvas_snapshot')
    def validate_canvas_snapshot(self, key, canvas_snapshot):
        """Validate canvas snapshot is not empty."""
        if not canvas_snapshot:
            raise ValueError("Canvas snapshot cannot be empty")
        return canvas_snapshot

    def __repr__(self):
        """String representation of EditOperation."""
        return (
            f"<EditOperation(id={self.id}, "
            f"session_id={self.session_id}, "
            f"operation_type={self.operation_type}, "
            f"position={self.position})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "operation_type": self.operation_type,
            "canvas_snapshot": self.canvas_snapshot,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "position": self.position
        }


class SessionHistory(Base):
    """
    Session History model tracking recently viewed/edited images.

    Enables quick re-access via `imgcat --history` and `imgcat -e N` commands
    with LRU cache eviction (20 entries per terminal session).
    """
    __tablename__ = "session_history"

    # Primary fields
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique history entry identifier"
    )
    terminal_session_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Terminal session ID from jterm"
    )
    image_path = Column(
        String(1024),
        nullable=False,
        comment="File path or URL of image"
    )
    image_source_type = Column(
        String(20),
        nullable=False,
        comment="Source: file, clipboard, or url"
    )
    thumbnail_path = Column(
        String(1024),
        nullable=True,
        comment="Path to cached thumbnail (optional)"
    )
    last_viewed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Most recent view timestamp"
    )
    view_count = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of times viewed in this session"
    )
    is_edited = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether image was edited (vs just viewed)"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "image_source_type IN ('file', 'clipboard', 'url')",
            name='valid_history_source_type'
        ),
        UniqueConstraint('terminal_session_id', 'image_path', name='unique_terminal_image'),
        Index('idx_terminal_last_viewed', 'terminal_session_id', 'last_viewed_at'),
    )

    @validates('image_path')
    def validate_image_path(self, key, image_path):
        """Validate image path is not empty."""
        if not image_path:
            raise ValueError("Image path cannot be empty")
        # Basic security check
        if '..' in image_path:
            raise ValueError("Path traversal detected in image_path")
        return image_path

    @validates('view_count')
    def validate_view_count(self, key, view_count):
        """Validate view count is positive."""
        if view_count < 1:
            raise ValueError("View count must be at least 1")
        return view_count

    def __repr__(self):
        """String representation of SessionHistory."""
        return (
            f"<SessionHistory(id={self.id}, "
            f"terminal_session_id={self.terminal_session_id}, "
            f"image_path={self.image_path}, "
            f"view_count={self.view_count}, "
            f"is_edited={self.is_edited})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "terminal_session_id": self.terminal_session_id,
            "image_path": self.image_path,
            "image_source_type": self.image_source_type,
            "thumbnail_path": self.thumbnail_path,
            "last_viewed_at": self.last_viewed_at.isoformat() if self.last_viewed_at else None,
            "view_count": self.view_count,
            "is_edited": self.is_edited
        }
