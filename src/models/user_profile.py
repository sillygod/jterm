"""User Profile SQLAlchemy model."""

import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Index, BigInteger, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


# Association tables for many-to-many relationships
user_theme_associations = Table(
    'user_theme_associations',
    Base.metadata,
    Column('user_id', String(36), ForeignKey('user_profiles.user_id'), primary_key=True),
    Column('theme_id', String(36), ForeignKey('theme_configurations.theme_id'), primary_key=True)
)

user_extension_associations = Table(
    'user_extension_associations',
    Base.metadata,
    Column('user_id', String(36), ForeignKey('user_profiles.user_id'), primary_key=True),
    Column('extension_id', String(36), ForeignKey('extensions.extension_id'), primary_key=True)
)


class UserProfile(Base):
    """
    User Profile model for preferences, settings, and personalization data.

    Manages user account information, preferences, installed themes and extensions,
    storage quotas, and privacy settings across terminal sessions.
    """
    __tablename__ = "user_profiles"

    # Primary fields
    user_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the user"
    )
    username = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique username"
    )
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User email address"
    )
    display_name = Column(
        String(100),
        nullable=False,
        comment="User's display name"
    )
    avatar_url = Column(
        String(500),
        nullable=True,
        comment="User avatar image URL"
    )

    # User preferences
    preferences = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "terminal": {
                "fontSize": 14,
                "fontFamily": "monospace",
                "cursorStyle": "block",
                "scrollback": 1000,
                "bellStyle": "sound"
            },
            "animations": {
                "enabled": True,
                "reducedMotion": False
            },
            "media": {
                "autoLoadImages": True,
                "maxVideoSize": "50MB",
                "imageScaling": "fit"
            },
            "recordings": {
                "autoRecord": False,
                "maxDuration": 3600,
                "compressionLevel": 5
            }
        },
        comment="User preferences and settings"
    )

    # Theme and extension management - these are handled via relationships
    # installed_themes and installed_extensions are managed through many-to-many relationships
    active_theme_id = Column(
        String(36),
        nullable=True,
        comment="Currently active theme"
    )

    # Shell and keyboard preferences
    default_shell = Column(
        String(50),
        nullable=False,
        default="bash",
        comment="Default shell preference"
    )
    keyboard_shortcuts = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "copy": "Ctrl+C",
            "paste": "Ctrl+V",
            "clear": "Ctrl+L",
            "newTab": "Ctrl+T",
            "closeTab": "Ctrl+W",
            "search": "Ctrl+F"
        },
        comment="Custom keyboard shortcuts"
    )

    # AI and recording settings
    ai_settings = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "enabled": True,
            "provider": "openai",
            "model": "gpt-4",
            "voiceEnabled": True,
            "voiceLanguage": "en-US",
            "autoSuggestions": True,
            "contextSharing": "full",
            "responseFormat": "text"
        },
        comment="AI assistant preferences"
    )
    recording_settings = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "defaultEnabled": False,
            "maxDuration": 3600,
            "compressionLevel": 5,
            "retentionDays": 30,
            "autoDelete": True
        },
        comment="Default recording preferences"
    )
    privacy_settings = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "shareUsageData": False,
            "allowAnalytics": False,
            "sessionTracking": "minimal",
            "dataRetention": 30,
            "exportData": True
        },
        comment="Privacy and data retention preferences"
    )

    # Storage management
    storage_quota = Column(
        BigInteger,
        nullable=False,
        default=1024 * 1024 * 1024,  # 1GB default
        comment="Storage quota in bytes"
    )
    storage_used = Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Current storage usage in bytes"
    )

    # Account status and timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Account creation timestamp"
    )
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Last login timestamp"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether account is active"
    )

    # Additional metadata
    extra_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional user metadata"
    )

    # Relationships
    terminal_sessions = relationship(
        "TerminalSession",
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )
    recordings = relationship(
        "Recording",
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )
    media_assets = relationship(
        "MediaAsset",
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )
    ai_contexts = relationship(
        "AIContext",
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )

    # Many-to-many relationships
    installed_theme_objects = relationship(
        "ThemeConfiguration",
        secondary=user_theme_associations,
        back_populates="user_profiles"
    )
    installed_extension_objects = relationship(
        "Extension",
        secondary=user_extension_associations,
        back_populates="user_profiles"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_user_profiles_username", "username"),
        Index("idx_user_profiles_email", "email"),
        Index("idx_user_profiles_last_login", "last_login_at"),
        Index("idx_user_profiles_storage", "storage_used"),
    )

    @validates('username')
    def validate_username(self, key: str, value: str) -> str:
        """Validate username format."""
        if not value or len(value) < 3 or len(value) > 50:
            raise ValueError("Username must be between 3 and 50 characters")

        # Allow alphanumeric, hyphens, underscores
        username_pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(username_pattern, value):
            raise ValueError("Username can only contain alphanumeric characters, hyphens, and underscores")

        return value.lower()  # Normalize to lowercase

    @validates('email')
    def validate_email(self, key: str, value: str) -> str:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")
        return value.lower()  # Normalize to lowercase

    @validates('display_name')
    def validate_display_name(self, key: str, value: str) -> str:
        """Validate display name."""
        if not value or len(value.strip()) < 1 or len(value) > 100:
            raise ValueError("Display name must be between 1 and 100 characters")
        return value.strip()

    @validates('avatar_url')
    def validate_avatar_url(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate avatar URL format."""
        if value is None:
            return value

        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, value):
            raise ValueError(f"Invalid avatar URL format: {value}")

        return value

    @validates('preferences')
    def validate_preferences(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user preferences structure."""
        if not isinstance(value, dict):
            raise ValueError("Preferences must be a dictionary")

        # Validate terminal preferences
        if "terminal" in value and isinstance(value["terminal"], dict):
            terminal = value["terminal"]

            font_size = terminal.get("fontSize", 14)
            if not isinstance(font_size, int) or not 8 <= font_size <= 32:
                raise ValueError("Font size must be between 8 and 32")

            scrollback = terminal.get("scrollback", 1000)
            if not isinstance(scrollback, int) or not 100 <= scrollback <= 10000:
                raise ValueError("Scrollback must be between 100 and 10000")

            cursor_style = terminal.get("cursorStyle", "block")
            valid_cursor_styles = ["block", "underline", "bar"]
            if cursor_style not in valid_cursor_styles:
                raise ValueError(f"Invalid cursor style. Must be one of: {valid_cursor_styles}")

            bell_style = terminal.get("bellStyle", "sound")
            valid_bell_styles = ["sound", "visual", "none"]
            if bell_style not in valid_bell_styles:
                raise ValueError(f"Invalid bell style. Must be one of: {valid_bell_styles}")

        return value

    @validates('ai_settings')
    def validate_ai_settings(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate AI settings structure."""
        if not isinstance(value, dict):
            raise ValueError("AI settings must be a dictionary")

        valid_providers = ["openai", "anthropic", "local", "huggingface", "cohere"]
        provider = value.get("provider", "openai")
        if provider not in valid_providers:
            raise ValueError(f"Invalid AI provider. Must be one of: {valid_providers}")

        valid_context_sharing = ["full", "limited", "none"]
        context_sharing = value.get("contextSharing", "full")
        if context_sharing not in valid_context_sharing:
            raise ValueError(f"Invalid context sharing setting. Must be one of: {valid_context_sharing}")

        valid_response_formats = ["text", "voice", "both"]
        response_format = value.get("responseFormat", "text")
        if response_format not in valid_response_formats:
            raise ValueError(f"Invalid response format. Must be one of: {valid_response_formats}")

        return value

    @validates('storage_used')
    def validate_storage_used(self, key: str, value: int) -> int:
        """Validate storage usage against quota."""
        if not isinstance(value, int) or value < 0:
            raise ValueError("Storage used must be a non-negative integer")

        if hasattr(self, 'storage_quota') and self.storage_quota and value > self.storage_quota:
            raise ValueError("Storage used cannot exceed storage quota")

        return value

    @validates('default_shell')
    def validate_default_shell(self, key: str, value: str) -> str:
        """Validate shell type."""
        valid_shells = ["bash", "zsh", "fish", "sh", "csh", "tcsh", "ksh"]
        if value not in valid_shells:
            raise ValueError(f"Invalid shell type. Must be one of: {valid_shells}")
        return value

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login_at = datetime.now(timezone.utc)

    def calculate_storage_usage_percent(self) -> float:
        """Calculate storage usage as a percentage."""
        if not self.storage_quota or self.storage_quota == 0:
            return 0.0
        return (self.storage_used / self.storage_quota) * 100.0

    def get_remaining_storage(self) -> int:
        """Get remaining storage in bytes."""
        return max(0, self.storage_quota - self.storage_used)

    def can_store_additional(self, bytes_needed: int) -> bool:
        """Check if user can store additional bytes."""
        return self.storage_used + bytes_needed <= self.storage_quota

    def increment_storage_used(self, bytes_added: int) -> None:
        """Increment storage used, with validation."""
        new_usage = self.storage_used + bytes_added
        if new_usage > self.storage_quota:
            raise ValueError("Storage operation would exceed quota")
        self.storage_used = new_usage

    def decrement_storage_used(self, bytes_removed: int) -> None:
        """Decrement storage used."""
        self.storage_used = max(0, self.storage_used - bytes_removed)

    @property
    def installed_themes(self) -> List[str]:
        """Get list of installed theme IDs."""
        return [theme.theme_id for theme in self.installed_theme_objects or []]

    @property
    def installed_extensions(self) -> List[str]:
        """Get list of installed extension IDs."""
        return [ext.extension_id for ext in self.installed_extension_objects or []]

    def install_theme(self, theme_object) -> bool:
        """Install a theme."""
        if theme_object not in (self.installed_theme_objects or []):
            if not self.installed_theme_objects:
                self.installed_theme_objects = []
            self.installed_theme_objects.append(theme_object)
            return True
        return False

    def uninstall_theme(self, theme_id: str) -> bool:
        """Uninstall a theme."""
        if self.installed_theme_objects:
            for theme in self.installed_theme_objects:
                if theme.theme_id == theme_id:
                    self.installed_theme_objects.remove(theme)

                    # Clear active theme if it's being uninstalled
                    if self.active_theme_id == theme_id:
                        self.active_theme_id = None

                    return True
        return False

    def install_extension(self, extension_object) -> bool:
        """Install an extension."""
        if extension_object not in (self.installed_extension_objects or []):
            if not self.installed_extension_objects:
                self.installed_extension_objects = []
            self.installed_extension_objects.append(extension_object)
            return True
        return False

    def uninstall_extension(self, extension_id: str) -> bool:
        """Uninstall an extension."""
        if self.installed_extension_objects:
            for ext in self.installed_extension_objects:
                if ext.extension_id == extension_id:
                    self.installed_extension_objects.remove(ext)
                    return True
        return False

    def set_active_theme(self, theme_id: str) -> None:
        """Set the active theme."""
        if theme_id and theme_id not in self.installed_themes:
            raise ValueError("Cannot activate theme that is not installed")
        self.active_theme_id = theme_id

    def update_preference(self, category: str, key: str, value: Any) -> None:
        """Update a specific preference."""
        current_prefs = dict(self.preferences or {})
        if category not in current_prefs:
            current_prefs[category] = {}

        current_prefs[category][key] = value
        self.preferences = current_prefs

    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a specific preference value."""
        prefs = self.preferences or {}
        return prefs.get(category, {}).get(key, default)

    def export_profile(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export user profile data."""
        data = {
            "username": self.username,
            "display_name": self.display_name,
            "preferences": self.preferences,
            "ai_settings": self.ai_settings,
            "recording_settings": self.recording_settings,
            "keyboard_shortcuts": self.keyboard_shortcuts,
            "default_shell": self.default_shell,
            "installed_themes": self.installed_themes,
            "installed_extensions": self.installed_extensions,
            "active_theme_id": self.active_theme_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        if include_sensitive:
            data.update({
                "email": self.email,
                "privacy_settings": self.privacy_settings,
                "extra_metadata": self.extra_metadata
            })

        return data

    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary information."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "storage_usage": {
                "used": self.storage_used,
                "quota": self.storage_quota,
                "percent": round(self.calculate_storage_usage_percent(), 2),
                "remaining": self.get_remaining_storage()
            },
            "installed_count": {
                "themes": len(self.installed_themes),
                "extensions": len(self.installed_extensions)
            },
            "active_theme_id": self.active_theme_id,
            "default_shell": self.default_shell
        }

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user profile to dictionary representation."""
        result = {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "preferences": self.preferences,
            "installed_themes": self.installed_themes,
            "installed_extensions": self.installed_extensions,
            "active_theme_id": self.active_theme_id,
            "default_shell": self.default_shell,
            "keyboard_shortcuts": self.keyboard_shortcuts,
            "ai_settings": self.ai_settings,
            "recording_settings": self.recording_settings,
            "storage_quota": self.storage_quota,
            "storage_used": self.storage_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_active": self.is_active,
            "storage_usage_percent": round(self.calculate_storage_usage_percent(), 2),
            "remaining_storage": self.get_remaining_storage()
        }

        if include_sensitive:
            result.update({
                "email": self.email,
                "privacy_settings": self.privacy_settings,
                "extra_metadata": self.extra_metadata
            })

        return result

    def __repr__(self) -> str:
        """String representation of the user profile."""
        return (
            f"<UserProfile(user_id='{self.user_id}', "
            f"username='{self.username}', email='{self.email}', "
            f"is_active={self.is_active}, storage_used={self.storage_used})>"
        )