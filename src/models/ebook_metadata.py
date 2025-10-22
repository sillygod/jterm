"""Ebook Metadata SQLAlchemy model."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, BigInteger, Enum, Index, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship, validates
from src.database.base import Base
import enum


class EbookFileType(str, enum.Enum):
    """Supported ebook file types."""
    PDF = "pdf"
    EPUB = "epub"


class EbookMetadata(Base):
    """
    Ebook Metadata model for storing PDF/EPUB file information.

    Stores metadata and caching information for viewed PDF/EPUB files,
    enabling quick retrieval by file hash and efficient re-opening of
    previously accessed ebooks.
    """
    __tablename__ = "ebook_metadata"

    # Primary fields
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the ebook metadata record"
    )
    file_path = Column(
        String(512),
        nullable=False,
        index=True,
        comment="Absolute filesystem path to the ebook file"
    )
    file_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of file content for deduplication"
    )
    file_type = Column(
        Enum(EbookFileType),
        nullable=False,
        comment="File format (pdf or epub)"
    )
    file_size = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes (max 50MB)"
    )

    # Metadata fields (extracted from file)
    title = Column(
        String(255),
        nullable=True,
        comment="Book title extracted from metadata"
    )
    author = Column(
        String(255),
        nullable=True,
        comment="Author name extracted from metadata"
    )
    total_pages = Column(
        Integer,
        nullable=True,
        comment="Total pages (PDF only, NULL for EPUB)"
    )
    is_encrypted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the PDF is password-protected"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="First access time"
    )
    last_accessed = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Most recent access time"
    )

    # Foreign key
    user_id = Column(
        String(36),
        ForeignKey('user_profiles.user_id'),
        nullable=False,
        index=True,
        comment="Owner of the ebook metadata"
    )

    # Relationships
    user = relationship("UserProfile", back_populates="ebook_metadata")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            'file_size <= 52428800',
            name='file_size_limit'
        ),
        Index('idx_ebook_user', 'user_id'),
        Index('idx_ebook_file_path', 'file_path'),
        Index('idx_ebook_file_hash', 'file_hash'),
    )

    @validates('file_path')
    def validate_file_path(self, key, file_path):
        """Validate file path is absolute and secure."""
        if not file_path:
            raise ValueError("File path cannot be empty")

        # Check for path traversal attempts
        if '..' in file_path or '~' in file_path:
            raise ValueError("File path contains invalid sequences (path traversal)")

        # Ensure it's an absolute path (starts with /)
        if not file_path.startswith('/'):
            raise ValueError("File path must be absolute")

        return file_path

    @validates('file_hash')
    def validate_file_hash(self, key, file_hash):
        """Validate file hash is a valid SHA-256 hash."""
        if not file_hash:
            raise ValueError("File hash cannot be empty")

        # SHA-256 hash should be exactly 64 hexadecimal characters
        if len(file_hash) != 64:
            raise ValueError("File hash must be 64 characters (SHA-256)")

        # Verify it's hexadecimal
        try:
            int(file_hash, 16)
        except ValueError:
            raise ValueError("File hash must contain only hexadecimal characters")

        return file_hash.lower()

    @validates('file_size')
    def validate_file_size(self, key, file_size):
        """Validate file size is within limits."""
        if file_size <= 0:
            raise ValueError("File size must be positive")

        # 50MB limit = 52428800 bytes
        if file_size > 52428800:
            raise ValueError("File size exceeds 50MB limit")

        return file_size

    @validates('file_type')
    def validate_file_type(self, key, file_type):
        """Validate file type is supported."""
        if isinstance(file_type, str):
            try:
                file_type = EbookFileType(file_type.lower())
            except ValueError:
                raise ValueError(f"Unsupported file type: {file_type}. Must be 'pdf' or 'epub'")

        return file_type

    def __repr__(self):
        """String representation of EbookMetadata."""
        return (
            f"<EbookMetadata(id={self.id}, "
            f"file_path={self.file_path}, "
            f"file_type={self.file_type.value}, "
            f"file_size={self.file_size}, "
            f"is_encrypted={self.is_encrypted})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "file_type": self.file_type.value,
            "file_size": self.file_size,
            "title": self.title,
            "author": self.author,
            "total_pages": self.total_pages,
            "is_encrypted": self.is_encrypted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "user_id": self.user_id
        }
