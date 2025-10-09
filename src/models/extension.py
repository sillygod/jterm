"""Extension SQLAlchemy model."""

import uuid
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from src.database.base import Base


class SecurityStatus(str, Enum):
    """Security scan status enumeration."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    ERROR = "error"


class Extension(Base):
    """
    Extension model for installable plugins.

    Provides custom commands, UI elements, and functionality through sandboxed JavaScript.
    Supports permission management, security scanning, and marketplace distribution.
    """
    __tablename__ = "extensions"

    # Primary fields
    extension_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the extension"
    )
    name = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Extension name (must be unique)"
    )
    display_name = Column(
        String(150),
        nullable=False,
        comment="Human-readable display name"
    )
    description = Column(
        String(1000),
        nullable=False,
        comment="Extension description"
    )
    version = Column(
        String(20),
        nullable=False,
        comment="Extension version (semver format)"
    )

    # Author information
    author = Column(
        String(100),
        nullable=False,
        comment="Extension author"
    )
    author_email = Column(
        String(255),
        nullable=True,
        comment="Author email"
    )
    homepage = Column(
        String(500),
        nullable=True,
        comment="Extension homepage URL"
    )
    repository = Column(
        String(500),
        nullable=True,
        comment="Source code repository URL"
    )
    license = Column(
        String(50),
        nullable=False,
        default="MIT",
        comment="License identifier"
    )

    # Extension properties
    is_built_in = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether extension is built into the system"
    )
    is_public = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether extension can be shared publicly"
    )

    # Extension configuration
    commands = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Commands provided by the extension"
    )
    permissions = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Required permissions"
    )
    dependencies = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Required dependencies"
    )
    manifest = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Extension manifest data"
    )

    # Extension code
    code = Column(
        Text,
        nullable=False,
        comment="Extension JavaScript code (sandboxed)"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Extension creation timestamp"
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
        comment="Number of times downloaded"
    )
    rating = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Average user rating (0-500, represents 0.0-5.0 with precision)"
    )

    # Security scanning
    security_scan = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "scannedAt": datetime.now(timezone.utc).isoformat(),
            "status": "safe",
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
        comment="Additional extension metadata"
    )

    # Relationships
    user_profiles = relationship(
        "UserProfile",
        secondary="user_extension_associations",
        back_populates="installed_extension_objects"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_extensions_name_version", "name", "version"),
        Index("idx_extensions_public_rating", "is_public", "rating"),
        Index("idx_extensions_author", "author"),
        Index("idx_extensions_created_at", "created_at"),
    )

    @validates('name')
    def validate_name(self, key: str, value: str) -> str:
        """Validate extension name format."""
        # Extension names must be alphanumeric with hyphens/underscores
        name_pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(name_pattern, value):
            raise ValueError("Extension name must contain only alphanumeric characters, hyphens, and underscores")

        if len(value) < 3 or len(value) > 50:
            raise ValueError("Extension name must be between 3 and 50 characters")

        return value.lower()  # Normalize to lowercase

    @validates('version')
    def validate_version(self, key: str, value: str) -> str:
        """Validate semantic version format."""
        semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
        if not re.match(semver_pattern, value):
            raise ValueError(f"Version must follow semantic versioning format: {value}")
        return value

    @validates('author_email')
    def validate_author_email(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate author email format."""
        if value is None:
            return value

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")

        return value

    @validates('homepage')
    def validate_homepage(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate homepage URL format."""
        if value is None:
            return value

        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, value):
            raise ValueError(f"Invalid URL format: {value}")

        return value

    @validates('repository')
    def validate_repository(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate repository URL format."""
        if value is None:
            return value

        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, value):
            raise ValueError(f"Invalid repository URL format: {value}")

        return value

    @validates('commands')
    def validate_commands(self, key: str, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extension commands structure."""
        if not isinstance(value, list):
            raise ValueError("Commands must be a list")

        for i, command in enumerate(value):
            if not isinstance(command, dict):
                raise ValueError(f"Command {i} must be a dictionary")

            required_fields = ["name", "description", "usage"]
            for field in required_fields:
                if field not in command:
                    raise ValueError(f"Command {i} missing required field: {field}")

            # Validate command name
            cmd_name = command.get("name", "")
            if not re.match(r'^[a-zA-Z0-9_-]+$', cmd_name):
                raise ValueError(f"Invalid command name: {cmd_name}")

            # Validate parameters if present
            if "parameters" in command:
                params = command["parameters"]
                if not isinstance(params, list):
                    raise ValueError(f"Command {cmd_name} parameters must be a list")

                for param in params:
                    if not isinstance(param, dict):
                        raise ValueError(f"Command {cmd_name} parameter must be a dictionary")

                    param_required_fields = ["name", "type", "required", "description"]
                    for field in param_required_fields:
                        if field not in param:
                            raise ValueError(f"Command {cmd_name} parameter missing field: {field}")

                    valid_types = ["string", "number", "boolean", "file"]
                    if param.get("type") not in valid_types:
                        raise ValueError(f"Invalid parameter type: {param.get('type')}")

        return value

    @validates('permissions')
    def validate_permissions(self, key: str, value: List[str]) -> List[str]:
        """Validate extension permissions."""
        if not isinstance(value, list):
            raise ValueError("Permissions must be a list")

        valid_permissions = [
            "filesystem.read",
            "filesystem.write",
            "network.http",
            "terminal.input",
            "terminal.output",
            "ai.query"
        ]

        for permission in value:
            if permission not in valid_permissions:
                raise ValueError(f"Invalid permission: {permission}")

        return list(set(value))  # Remove duplicates

    @validates('code')
    def validate_code(self, key: str, value: str) -> str:
        """Validate extension code for basic security."""
        if not isinstance(value, str):
            raise ValueError("Extension code must be a string")

        # Limit code size to prevent abuse
        if len(value) > 500000:  # 500KB limit
            raise ValueError("Extension code cannot exceed 500KB")

        # Basic security checks for dangerous patterns
        dangerous_patterns = [
            r'eval\s*\(',          # Prevent eval
            r'Function\s*\(',      # Prevent Function constructor
            r'import\s+.*\s+from', # Prevent ES6 imports (use controlled imports)
            r'require\s*\(',       # Prevent CommonJS requires
            r'process\.',          # Prevent process access
            r'global\.',           # Prevent global access
            r'window\.',           # Prevent window access (if in browser context)
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Extension code contains potentially dangerous pattern: {pattern}")

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

        valid_statuses = ["safe", "suspicious", "malicious", "error"]
        if value.get("status") not in valid_statuses:
            raise ValueError(f"Invalid security status: {value.get('status')}")

        if not isinstance(value.get("threats"), list):
            raise ValueError("Threats must be a list")

        return value

    @validates('rating')
    def validate_rating(self, key: str, value: int) -> int:
        """Validate rating value (0-500, representing 0.0-5.0)."""
        if not isinstance(value, int) or value < 0 or value > 500:
            raise ValueError("Rating must be between 0 and 500 (representing 0.0-5.0)")
        return value

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

    def is_safe(self) -> bool:
        """Check if the extension passed security scanning."""
        if not self.security_scan:
            return False
        return self.security_scan.get("status") == "safe"

    def has_permission(self, permission: str) -> bool:
        """Check if extension has a specific permission."""
        return permission in (self.permissions or [])

    def get_command(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific command by name."""
        if not self.commands:
            return None

        for command in self.commands:
            if command.get("name") == command_name:
                return command

        return None

    def add_command(self, command: Dict[str, Any]) -> None:
        """Add a new command to the extension."""
        # Validate command structure first
        self.validate_commands("commands", [command])

        current_commands = list(self.commands or [])

        # Check for duplicate command names
        for existing_cmd in current_commands:
            if existing_cmd.get("name") == command.get("name"):
                raise ValueError(f"Command '{command.get('name')}' already exists")

        current_commands.append(command)
        self.commands = current_commands

    def remove_command(self, command_name: str) -> bool:
        """Remove a command by name."""
        if not self.commands:
            return False

        current_commands = [cmd for cmd in self.commands if cmd.get("name") != command_name]

        if len(current_commands) == len(self.commands):
            return False  # Command not found

        self.commands = current_commands
        return True

    def update_security_scan(self, status: str, threats: List[str] = None,
                           scanner_version: str = "1.0") -> None:
        """Update security scan results."""
        self.security_scan = {
            "scannedAt": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "threats": threats or [],
            "scannerVersion": scanner_version
        }

    def is_compatible_with_version(self, min_version: str) -> bool:
        """Check if extension version meets minimum requirement."""
        try:
            ext_version = [int(x) for x in self.version.split('.')]
            min_version_parts = [int(x) for x in min_version.split('.')]

            # Pad shorter version with zeros
            max_len = max(len(ext_version), len(min_version_parts))
            ext_version += [0] * (max_len - len(ext_version))
            min_version_parts += [0] * (max_len - len(min_version_parts))

            return ext_version >= min_version_parts
        except (ValueError, AttributeError):
            return False

    def export_config(self) -> Dict[str, Any]:
        """Export extension configuration for sharing."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "author_email": self.author_email,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "commands": self.commands,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "manifest": self.manifest,
            "code": self.code,
            "extra_metadata": self.extra_metadata
        }

    def to_dict(self, include_code: bool = False) -> Dict[str, Any]:
        """Convert extension to dictionary representation."""
        result = {
            "extension_id": self.extension_id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "author_email": self.author_email,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "is_built_in": self.is_built_in,
            "is_public": self.is_public,
            "commands": self.commands,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "manifest": self.manifest,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "download_count": self.download_count,
            "rating": self.get_rating_float(),
            "security_scan": self.security_scan,
            "extra_metadata": self.extra_metadata,
            "is_safe": self.is_safe(),
            "command_count": len(self.commands or [])
        }

        if include_code:
            result["code"] = self.code

        return result

    def __repr__(self) -> str:
        """String representation of the extension."""
        return (
            f"<Extension(extension_id='{self.extension_id}', "
            f"name='{self.name}', version='{self.version}', "
            f"author='{self.author}', is_safe={self.is_safe()})>"
        )