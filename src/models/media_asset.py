"""Media Asset SQLAlchemy model."""

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Index, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class MediaType(str, Enum):
    """Media type enumeration."""
    IMAGE = "image"
    VIDEO = "video"
    HTML = "html"
    DOCUMENT = "document"


class SecurityStatus(str, Enum):
    """Security scan status enumeration."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    ERROR = "error"


class MediaAsset(Base):
    """
    Media Asset model for images, videos, HTML files and documents.

    Supports inline display within terminal sessions with security scanning,
    temporary assets with expiration, and comprehensive metadata tracking.
    """
    __tablename__ = "media_assets"

    # Primary fields
    asset_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the media asset"
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
        comment="Reference to the user who owns the asset"
    )

    # File information
    file_name = Column(
        String(255),
        nullable=False,
        comment="Original filename"
    )
    file_path = Column(
        String(1024),
        nullable=False,
        comment="Storage path or URL"
    )
    file_size = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes"
    )
    mime_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="MIME type"
    )
    media_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Media type category"
    )

    # Media-specific properties
    dimensions = Column(
        JSON,
        nullable=True,
        comment="Width and height for images/videos"
    )
    duration = Column(
        Integer,
        nullable=True,
        comment="Duration in seconds for videos"
    )
    thumbnail_path = Column(
        String(1024),
        nullable=True,
        comment="Path to generated thumbnail"
    )

    # Timestamps and access tracking
    uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Upload timestamp"
    )
    last_accessed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Last access timestamp"
    )
    access_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times accessed"
    )

    # Lifecycle management
    is_temporary = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether asset should be auto-deleted"
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Expiration timestamp for temporary assets"
    )

    # Security scanning
    security_scan = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "scannedAt": datetime.now(timezone.utc).isoformat(),
            "status": SecurityStatus.SAFE,
            "threats": [],
            "scannerVersion": "1.0"
        },
        comment="Security scan results"
    )

    # Additional metadata
    extra_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional metadata (EXIF, codec info, etc.)"
    )

    # Relationships
    terminal_session = relationship(
        "TerminalSession",
        back_populates="media_assets"
    )
    user_profile = relationship(
        "UserProfile",
        back_populates="media_assets"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_media_assets_user_type", "user_id", "media_type"),
        Index("idx_media_assets_session_uploaded", "session_id", "uploaded_at"),
        Index("idx_media_assets_expires_at", "expires_at"),
        Index("idx_media_assets_file_size", "file_size"),
    )

    @validates('media_type')
    def validate_media_type(self, key: str, value: str) -> str:
        """Validate media type."""
        if value not in [media_type.value for media_type in MediaType]:
            raise ValueError(f"Invalid media type: {value}")
        return value

    @validates('file_size')
    def validate_file_size(self, key: str, value: int) -> int:
        """Validate file size based on media type."""
        if not hasattr(self, 'media_type') or not self.media_type:
            return value

        size_limits = {
            MediaType.VIDEO: 50 * 1024 * 1024,    # 50MB for videos
            MediaType.IMAGE: 10 * 1024 * 1024,    # 10MB for images
            MediaType.HTML: 5 * 1024 * 1024,      # 5MB for HTML
            MediaType.DOCUMENT: 10 * 1024 * 1024  # 10MB for documents
        }

        limit = size_limits.get(MediaType(self.media_type), 10 * 1024 * 1024)
        if value > limit:
            raise ValueError(f"File size {value} exceeds limit {limit} for {self.media_type}")

        return value

    @validates('mime_type')
    def validate_mime_type(self, key: str, value: str) -> str:
        """Validate MIME type against allowed list."""
        allowed_mime_types = {
            # Images
            "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp",
            "image/svg+xml", "image/bmp", "image/tiff",
            # Videos
            "video/mp4", "video/webm", "video/ogg", "video/avi", "video/mov",
            "video/mkv", "video/flv", "video/wmv",
            # HTML
            "text/html", "application/xhtml+xml",
            # Documents
            "application/pdf", "text/plain", "text/markdown",
            "application/json", "application/xml"
        }

        if value not in allowed_mime_types:
            raise ValueError(f"MIME type '{value}' not allowed for security reasons")

        return value

    @validates('dimensions')
    def validate_dimensions(self, key: str, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate dimensions for image and video types."""
        if value is None:
            return value

        if not isinstance(value, dict):
            raise ValueError("Dimensions must be a dictionary")

        width = value.get('width')
        height = value.get('height')

        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("Width and height must be integers")

        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive integers")

        if width > 10000 or height > 10000:
            raise ValueError("Dimensions cannot exceed 10000 pixels")

        return {"width": width, "height": height}

    @validates('duration')
    def validate_duration(self, key: str, value: Optional[int]) -> Optional[int]:
        """Validate duration for video types."""
        if value is None:
            return value

        if not isinstance(value, int) or value < 0:
            raise ValueError("Duration must be a non-negative integer")

        # Maximum 4 hours
        if value > 14400:
            raise ValueError("Video duration cannot exceed 4 hours (14400 seconds)")

        return value

    @validates('security_scan')
    def validate_security_scan(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate security scan structure."""
        if not isinstance(value, dict):
            raise ValueError("Security scan must be a dictionary")

        required_fields = ["scannedAt", "status", "threats", "scannerVersion"]
        for field in required_fields:
            if field not in value:
                raise ValueError(f"Security scan missing required field: {field}")

        status = value.get("status")
        if status not in [s.value for s in SecurityStatus]:
            raise ValueError(f"Invalid security status: {status}")

        if not isinstance(value.get("threats"), list):
            raise ValueError("Threats must be a list")

        return value

    def requires_dimensions(self) -> bool:
        """Check if this media type requires dimensions."""
        return self.media_type in [MediaType.IMAGE, MediaType.VIDEO]

    def requires_duration(self) -> bool:
        """Check if this media type requires duration."""
        return self.media_type == MediaType.VIDEO

    def validate_required_fields(self) -> None:
        """Validate all required fields based on media type."""
        if self.requires_dimensions() and not self.dimensions:
            raise ValueError(f"Dimensions required for {self.media_type} media type")

        if self.requires_duration() and self.duration is None:
            raise ValueError(f"Duration required for {self.media_type} media type")

        if self.is_temporary and not self.expires_at:
            raise ValueError("Temporary assets must have expiration timestamp")

    def record_access(self) -> None:
        """Record an access to this media asset."""
        self.access_count += 1
        self.last_accessed_at = datetime.now(timezone.utc)

    def is_expired(self) -> bool:
        """Check if the asset is expired."""
        if not self.is_temporary or not self.expires_at:
            return False

        return datetime.now(timezone.utc) > self.expires_at

    def is_safe(self) -> bool:
        """Check if the asset passed security scanning."""
        if not self.security_scan:
            return False

        return self.security_scan.get("status") == SecurityStatus.SAFE

    def update_security_scan(self, status: SecurityStatus, threats: List[str] = None,
                           scanner_version: str = "1.0") -> None:
        """Update security scan results."""
        self.security_scan = {
            "scannedAt": datetime.now(timezone.utc).isoformat(),
            "status": status.value,
            "threats": threats or [],
            "scannerVersion": scanner_version
        }

    def get_display_info(self) -> Dict[str, Any]:
        """Get information needed for display rendering."""
        info = {
            "asset_id": self.asset_id,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "media_type": self.media_type,
            "file_size": self.file_size,
            "is_safe": self.is_safe(),
            "thumbnail_path": self.thumbnail_path
        }

        if self.dimensions:
            info["dimensions"] = self.dimensions

        if self.duration is not None:
            info["duration"] = self.duration

        return info

    def get_file_extension(self) -> str:
        """Extract file extension from filename."""
        if '.' in self.file_name:
            return self.file_name.split('.')[-1].lower()
        return ""

    def calculate_age_days(self) -> int:
        """Calculate asset age in days."""
        return (datetime.now(timezone.utc) - self.uploaded_at).days

    def to_dict(self) -> Dict[str, Any]:
        """Convert media asset to dictionary representation."""
        return {
            "asset_id": self.asset_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "media_type": self.media_type,
            "dimensions": self.dimensions,
            "duration": self.duration,
            "thumbnail_path": self.thumbnail_path,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "access_count": self.access_count,
            "is_temporary": self.is_temporary,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "security_scan": self.security_scan,
            "extra_metadata": self.extra_metadata,
            "age_days": self.calculate_age_days(),
            "is_expired": self.is_expired(),
            "is_safe": self.is_safe()
        }

    def __repr__(self) -> str:
        """String representation of the media asset."""
        return (
            f"<MediaAsset(asset_id='{self.asset_id}', "
            f"file_name='{self.file_name}', media_type='{self.media_type}', "
            f"file_size={self.file_size}, is_safe={self.is_safe()})>"
        )