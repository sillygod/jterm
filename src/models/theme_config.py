"""Theme Configuration SQLAlchemy model."""

import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class ThemeConfiguration(Base):
    """
    Theme Configuration model for visual styling and customization.

    Defines color palettes, fonts, animations, and custom CSS for terminal appearance.
    Supports both built-in and user-created themes with sharing capabilities.
    """
    __tablename__ = "theme_configurations"

    # Primary fields
    theme_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the theme"
    )
    name = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Human-readable theme name"
    )
    description = Column(
        String(500),
        nullable=False,
        default="",
        comment="Theme description"
    )
    version = Column(
        String(20),
        nullable=False,
        default="1.0.0",
        comment="Theme version (semver format)"
    )
    author = Column(
        String(100),
        nullable=False,
        comment="Theme author name"
    )

    # Theme properties
    is_built_in = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether theme is built into the system"
    )
    is_public = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether theme can be shared publicly"
    )

    # Configuration objects
    colors = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "background": "#000000",
            "foreground": "#ffffff",
            "cursor": "#ffffff",
            "selection": "#ffffff40",
            "black": "#000000",
            "red": "#ff0000",
            "green": "#00ff00",
            "yellow": "#ffff00",
            "blue": "#0000ff",
            "magenta": "#ff00ff",
            "cyan": "#00ffff",
            "white": "#ffffff",
            "brightBlack": "#808080",
            "brightRed": "#ff8080",
            "brightGreen": "#80ff80",
            "brightYellow": "#ffff80",
            "brightBlue": "#8080ff",
            "brightMagenta": "#ff80ff",
            "brightCyan": "#80ffff",
            "brightWhite": "#ffffff"
        },
        comment="Color palette configuration"
    )
    fonts = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "family": "monospace",
            "size": 14,
            "weight": "normal",
            "lineHeight": 1.2,
            "letterSpacing": 0
        },
        comment="Font configuration"
    )
    animations = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "enabled": True,
            "fadeInText": {
                "enabled": True,
                "duration": 200,
                "easing": "ease-out"
            },
            "cursorBlink": {
                "enabled": True,
                "interval": 1000
            },
            "typewriterEffect": {
                "enabled": False,
                "speed": 50
            },
            "particleEffects": {
                "enabled": False,
                "type": "stars"
            }
        },
        comment="Animation settings"
    )
    cursor = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "style": "block",
            "blink": True,
            "color": "#ffffff"
        },
        comment="Cursor style configuration"
    )
    background = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "color": "#000000",
            "image": None,
            "opacity": 1.0,
            "blur": 0
        },
        comment="Background configuration"
    )

    # Custom styling
    custom_css = Column(
        Text,
        nullable=True,
        comment="Custom CSS overrides"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Theme creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Last update timestamp"
    )

    # Usage statistics
    download_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times downloaded (public themes)"
    )
    rating = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Average user rating (0-500, represents 0.0-5.0 with precision)"
    )

    # Additional metadata
    extra_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Additional theme metadata"
    )

    # Relationships
    terminal_sessions = relationship(
        "TerminalSession",
        foreign_keys="[TerminalSession.theme_id]",
        primaryjoin="ThemeConfiguration.theme_id == TerminalSession.theme_id",
        back_populates="theme_configuration"
    )
    user_profiles = relationship(
        "UserProfile",
        secondary="user_theme_associations",
        back_populates="installed_theme_objects"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_theme_configs_name_author", "name", "author"),
        Index("idx_theme_configs_public_rating", "is_public", "rating"),
        Index("idx_theme_configs_created_at", "created_at"),
    )

    @validates('version')
    def validate_version(self, key: str, value: str) -> str:
        """Validate semantic version format."""
        semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
        if not re.match(semver_pattern, value):
            raise ValueError(f"Version must follow semantic versioning format: {value}")
        return value

    @validates('colors')
    def validate_colors(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate color palette configuration."""
        if not isinstance(value, dict):
            raise ValueError("Colors must be a dictionary")

        required_colors = [
            "background", "foreground", "cursor", "selection",
            "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
            "brightBlack", "brightRed", "brightGreen", "brightYellow",
            "brightBlue", "brightMagenta", "brightCyan", "brightWhite"
        ]

        for color_name in required_colors:
            if color_name not in value:
                raise ValueError(f"Missing required color: {color_name}")

            color_value = value[color_name]
            if not self._is_valid_color(color_value):
                raise ValueError(f"Invalid color format for {color_name}: {color_value}")

        return value

    @validates('fonts')
    def validate_fonts(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate font configuration."""
        if not isinstance(value, dict):
            raise ValueError("Fonts must be a dictionary")

        required_fields = ["family", "size", "weight", "lineHeight"]
        for field in required_fields:
            if field not in value:
                raise ValueError(f"Missing required font field: {field}")

        font_size = value.get("size", 14)
        if not isinstance(font_size, (int, float)) or font_size < 8 or font_size > 32:
            raise ValueError("Font size must be between 8 and 32")

        line_height = value.get("lineHeight", 1.2)
        if not isinstance(line_height, (int, float)) or line_height < 0.5 or line_height > 3.0:
            raise ValueError("Line height must be between 0.5 and 3.0")

        return value

    @validates('animations')
    def validate_animations(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        """Validate animation configuration."""
        if not isinstance(value, dict):
            raise ValueError("Animations must be a dictionary")

        # Validate animation durations
        if "fadeInText" in value and isinstance(value["fadeInText"], dict):
            duration = value["fadeInText"].get("duration", 200)
            if not isinstance(duration, int) or duration < 0 or duration > 5000:
                raise ValueError("Animation duration must be between 0 and 5000ms")

        if "cursorBlink" in value and isinstance(value["cursorBlink"], dict):
            interval = value["cursorBlink"].get("interval", 1000)
            if not isinstance(interval, int) or interval < 100 or interval > 5000:
                raise ValueError("Cursor blink interval must be between 100 and 5000ms")

        if "typewriterEffect" in value and isinstance(value["typewriterEffect"], dict):
            speed = value["typewriterEffect"].get("speed", 50)
            if not isinstance(speed, int) or speed < 1 or speed > 500:
                raise ValueError("Typewriter speed must be between 1 and 500")

        if "particleEffects" in value and isinstance(value["particleEffects"], dict):
            effect_type = value["particleEffects"].get("type", "stars")
            valid_types = ["stars", "rain", "matrix", "snow", "bubbles"]
            if effect_type not in valid_types:
                raise ValueError(f"Invalid particle effect type. Must be one of: {valid_types}")

        return value

    @validates('custom_css')
    def validate_custom_css(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate custom CSS for security."""
        if value is None:
            return value

        # Basic security validation - prevent dangerous CSS
        dangerous_patterns = [
            r'@import\s+url\s*\(',  # Prevent external imports
            r'expression\s*\(',     # Prevent IE expressions
            r'javascript:',         # Prevent JavaScript URLs
            r'vbscript:',          # Prevent VBScript URLs
            r'data:.*script',       # Prevent script data URLs
        ]

        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, value_lower):
                raise ValueError(f"Custom CSS contains potentially dangerous content: {pattern}")

        # Limit CSS size to prevent abuse
        if len(value) > 50000:  # 50KB limit
            raise ValueError("Custom CSS cannot exceed 50KB")

        return value

    @validates('rating')
    def validate_rating(self, key: str, value: int) -> int:
        """Validate rating value (0-500, representing 0.0-5.0)."""
        if not isinstance(value, int) or value < 0 or value > 500:
            raise ValueError("Rating must be between 0 and 500 (representing 0.0-5.0)")
        return value

    def _is_valid_color(self, color: str) -> bool:
        """Validate color format (hex or rgba)."""
        if not isinstance(color, str):
            return False

        # Hex color validation
        hex_pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3}|[A-Fa-f0-9]{8})$'
        if re.match(hex_pattern, color):
            return True

        # RGBA color validation
        rgba_pattern = r'^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(0?\.\d+|1|0))?\s*\)$'
        rgba_match = re.match(rgba_pattern, color)
        if rgba_match:
            r, g, b = int(rgba_match.group(1)), int(rgba_match.group(2)), int(rgba_match.group(3))
            return 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255

        return False

    def get_rating_float(self) -> float:
        """Get rating as a float value (0.0-5.0)."""
        return self.rating / 100.0

    def set_rating_float(self, rating: float) -> None:
        """Set rating from a float value (0.0-5.0)."""
        if not 0.0 <= rating <= 5.0:
            raise ValueError("Rating must be between 0.0 and 5.0")
        self.rating = int(rating * 100)

    def increment_download_count(self) -> None:
        """Increment the download counter."""
        self.download_count += 1

    def is_compatible_with_version(self, min_version: str) -> bool:
        """Check if theme version meets minimum requirement."""
        try:
            theme_version = [int(x) for x in self.version.split('.')]
            min_version_parts = [int(x) for x in min_version.split('.')]

            # Pad shorter version with zeros
            max_len = max(len(theme_version), len(min_version_parts))
            theme_version += [0] * (max_len - len(theme_version))
            min_version_parts += [0] * (max_len - len(min_version_parts))

            return theme_version >= min_version_parts
        except (ValueError, AttributeError):
            return False

    def get_color_scheme_type(self) -> str:
        """Determine if theme is light or dark based on background color."""
        bg_color = self.colors.get("background", "#000000")

        if bg_color.startswith("#"):
            # Convert hex to RGB
            hex_color = bg_color.lstrip("#")
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])

            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)

                # Calculate luminance
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return "light" if luminance > 0.5 else "dark"
            except ValueError:
                pass

        return "dark"  # Default to dark

    def export_config(self) -> Dict[str, Any]:
        """Export theme configuration for sharing."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "colors": self.colors,
            "fonts": self.fonts,
            "animations": self.animations,
            "cursor": self.cursor,
            "background": self.background,
            "custom_css": self.custom_css,
            "extra_metadata": self.extra_metadata,
            "scheme_type": self.get_color_scheme_type()
        }

    def import_config(self, config: Dict[str, Any]) -> None:
        """Import theme configuration from external source."""
        # Update basic fields
        for field in ["name", "description", "version", "author"]:
            if field in config:
                setattr(self, field, config[field])

        # Update configuration objects
        for field in ["colors", "fonts", "animations", "cursor", "background"]:
            if field in config:
                setattr(self, field, config[field])

        if "custom_css" in config:
            self.custom_css = config["custom_css"]

        if "extra_metadata" in config:
            self.extra_metadata = config["extra_metadata"]

        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert theme configuration to dictionary representation."""
        return {
            "theme_id": self.theme_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "is_built_in": self.is_built_in,
            "is_public": self.is_public,
            "colors": self.colors,
            "fonts": self.fonts,
            "animations": self.animations,
            "cursor": self.cursor,
            "background": self.background,
            "custom_css": self.custom_css,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "download_count": self.download_count,
            "rating": self.get_rating_float(),
            "extra_metadata": self.extra_metadata,
            "scheme_type": self.get_color_scheme_type()
        }

    def __repr__(self) -> str:
        """String representation of the theme configuration."""
        return (
            f"<ThemeConfiguration(theme_id='{self.theme_id}', "
            f"name='{self.name}', version='{self.version}', "
            f"author='{self.author}', rating={self.get_rating_float()})>"
        )