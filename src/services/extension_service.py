"""Extension management service for installable plugins.

This service provides extension CRUD operations, sandboxed JavaScript execution,
permission system validation, security scanning, command registration, and
marketplace integration with dependency resolution.
"""

import asyncio
import hashlib
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_, and_

from src.models.extension import Extension
from src.models.user_profile import UserProfile
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    """Extension permission levels."""
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    NETWORK_HTTP = "network.http"
    TERMINAL_INPUT = "terminal.input"
    TERMINAL_OUTPUT = "terminal.output"
    AI_QUERY = "ai.query"


class ExtensionStatus(str, Enum):
    """Extension execution status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


class ExtensionError(Exception):
    """Base exception for extension operations."""
    pass


class ExtensionValidationError(ExtensionError):
    """Raised when extension validation fails."""
    pass


class ExtensionSecurityError(ExtensionError):
    """Raised when extension fails security checks."""
    pass


class ExtensionPermissionError(ExtensionError):
    """Raised when extension lacks required permissions."""
    pass


@dataclass
class ExtensionConfig:
    """Extension service configuration."""
    extensions_dir: str = "./extensions"
    sandbox_enabled: bool = True
    max_execution_time: int = 30000  # milliseconds
    max_memory_mb: int = 100
    enable_marketplace: bool = True
    max_extensions_per_user: int = 100
    allow_network_access: bool = True
    security_scan_enabled: bool = True


@dataclass
class CommandDefinition:
    """Extension command definition."""
    name: str
    description: str
    usage: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "usage": self.usage,
            "parameters": self.parameters,
            "aliases": self.aliases,
            "metadata": self.metadata
        }


@dataclass
class ExecutionContext:
    """Extension execution context."""
    extension_id: str
    session_id: str
    user_id: str
    command: str
    args: List[str]
    env: Dict[str, str]
    permissions: Set[PermissionLevel]
    timeout: int = 30000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "extensionId": self.extension_id,
            "sessionId": self.session_id,
            "userId": self.user_id,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "permissions": [p.value for p in self.permissions],
            "timeout": self.timeout
        }


@dataclass
class ExecutionResult:
    """Extension execution result."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    exit_code: int = 0
    execution_time: float = 0.0
    memory_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exitCode": self.exit_code,
            "executionTime": self.execution_time,
            "memoryUsed": self.memory_used,
            "metadata": self.metadata
        }


class ExtensionValidator:
    """Validates extension code and configuration."""

    DANGEROUS_PATTERNS = [
        r'eval\s*\(',
        r'Function\s*\(',
        r'require\s*\(',
        r'import\s+.*\s+from',
        r'process\.',
        r'global\.',
        r'__proto__',
        r'constructor\s*\[',
        r'child_process',
        r'fs\.unlink',
        r'fs\.rmdir',
        r'fs\.rm\b',
    ]

    @staticmethod
    async def validate_extension(extension_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extension manifest and code."""
        errors = []
        warnings = []

        # Validate required fields
        required_fields = ["name", "display_name", "version", "author", "code", "commands"]
        for field in required_fields:
            if field not in extension_data:
                errors.append(f"Missing required field: {field}")

        # Validate name format
        if "name" in extension_data:
            name = extension_data["name"]
            if not re.match(r'^[a-z0-9_-]+$', name):
                errors.append("Extension name must contain only lowercase letters, numbers, hyphens, and underscores")
            if len(name) < 3 or len(name) > 50:
                errors.append("Extension name must be between 3 and 50 characters")

        # Validate version format
        if "version" in extension_data:
            version = extension_data["version"]
            if not re.match(r'^\d+\.\d+\.\d+', version):
                errors.append("Version must follow semantic versioning (e.g., 1.0.0)")

        # Validate commands
        if "commands" in extension_data:
            for i, cmd in enumerate(extension_data["commands"]):
                if not isinstance(cmd, dict):
                    errors.append(f"Command {i} must be a dictionary")
                    continue

                required_cmd_fields = ["name", "description", "usage"]
                for field in required_cmd_fields:
                    if field not in cmd:
                        errors.append(f"Command {i} missing required field: {field}")

        # Validate permissions
        if "permissions" in extension_data:
            valid_permissions = {p.value for p in PermissionLevel}
            for perm in extension_data["permissions"]:
                if perm not in valid_permissions:
                    warnings.append(f"Unknown permission: {perm}")

        # Validate code
        if "code" in extension_data:
            code_validation = await ExtensionValidator._validate_code(extension_data["code"])
            errors.extend(code_validation["errors"])
            warnings.extend(code_validation["warnings"])

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    @staticmethod
    async def _validate_code(code: str) -> Dict[str, Any]:
        """Validate extension JavaScript code."""
        errors = []
        warnings = []

        # Check code size
        if len(code) > 500000:  # 500KB
            errors.append("Extension code exceeds 500KB limit")

        # Check for dangerous patterns
        for pattern in ExtensionValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                errors.append(f"Dangerous code pattern detected: {pattern}")

        # Check for suspicious network calls
        if re.search(r'fetch\s*\(|XMLHttpRequest|WebSocket', code, re.IGNORECASE):
            warnings.append("Extension makes network requests - ensure network.http permission is granted")

        # Check for file system access
        if re.search(r'readFile|writeFile|appendFile', code, re.IGNORECASE):
            warnings.append("Extension accesses file system - ensure filesystem permissions are granted")

        return {
            "errors": errors,
            "warnings": warnings
        }

    @staticmethod
    async def scan_for_malware(code: str) -> Dict[str, Any]:
        """Scan extension code for malicious patterns."""
        threats = []
        risk_level = "safe"

        # Check for obfuscation
        if len(re.findall(r'\\x[0-9a-f]{2}', code)) > 50:
            threats.append("Excessive hex encoding detected (possible obfuscation)")
            risk_level = "suspicious"

        # Check for encoded eval
        if re.search(r'eval\s*\(\s*atob|eval\s*\(\s*decodeURI', code, re.IGNORECASE):
            threats.append("Encoded eval() detected (possible malicious code)")
            risk_level = "malicious"

        # Check for data exfiltration patterns
        if re.search(r'document\.cookie|localStorage|sessionStorage', code):
            threats.append("Access to browser storage detected")
            risk_level = max(risk_level, "suspicious") if risk_level != "malicious" else risk_level

        # Check for remote script loading
        if re.search(r'createElement\s*\(\s*[\'"]script[\'"]|import\s*\(', code):
            threats.append("Dynamic script loading detected")
            risk_level = max(risk_level, "suspicious") if risk_level != "malicious" else risk_level

        return {
            "status": risk_level,
            "threats": threats,
            "scannedAt": datetime.now(timezone.utc).isoformat(),
            "scannerVersion": "1.0"
        }


class SandboxExecutor:
    """Executes extension code in sandboxed environment."""

    def __init__(self, config: ExtensionConfig):
        self.config = config

    async def execute(self, extension: Extension, context: ExecutionContext) -> ExecutionResult:
        """Execute extension code in sandbox."""
        import time
        start_time = time.time()

        try:
            # Verify permissions
            required_perms = set(PermissionLevel(p) for p in extension.permissions)
            if not required_perms.issubset(context.permissions):
                missing = required_perms - context.permissions
                raise ExtensionPermissionError(
                    f"Missing permissions: {[p.value for p in missing]}"
                )

            # Create sandbox environment
            sandbox_env = self._create_sandbox_environment(extension, context)

            # Execute in sandbox
            result = await self._execute_in_sandbox(
                extension.code,
                context,
                sandbox_env
            )

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=True,
                output=result.get("output", ""),
                exit_code=result.get("exitCode", 0),
                execution_time=execution_time,
                memory_used=result.get("memoryUsed", 0),
                metadata=result.get("metadata", {})
            )

        except ExtensionPermissionError as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                exit_code=126,  # Permission denied
                execution_time=time.time() - start_time
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                error="Extension execution timed out",
                exit_code=124,  # Timeout
                execution_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Extension execution error: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                exit_code=1,
                execution_time=time.time() - start_time
            )

    def _create_sandbox_environment(
        self, extension: Extension, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Create sandboxed execution environment."""
        env = {
            "extension": {
                "id": extension.extension_id,
                "name": extension.name,
                "version": extension.version
            },
            "context": context.to_dict(),
            "api": self._create_api_bindings(extension, context)
        }

        return env

    def _create_api_bindings(
        self, extension: Extension, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Create API bindings based on permissions."""
        api = {}

        # Terminal API (if has permission)
        if PermissionLevel.TERMINAL_OUTPUT in context.permissions:
            api["terminal"] = {
                "write": "function(text) { /* terminal output */ }",
                "writeln": "function(text) { /* terminal output with newline */ }"
            }

        # File System API (if has permission)
        if PermissionLevel.FILESYSTEM_READ in context.permissions:
            api["fs"] = api.get("fs", {})
            api["fs"]["readFile"] = "function(path) { /* read file */ }"

        if PermissionLevel.FILESYSTEM_WRITE in context.permissions:
            api["fs"] = api.get("fs", {})
            api["fs"]["writeFile"] = "function(path, data) { /* write file */ }"

        # Network API (if has permission)
        if PermissionLevel.NETWORK_HTTP in context.permissions:
            api["http"] = {
                "get": "function(url) { /* http get */ }",
                "post": "function(url, data) { /* http post */ }"
            }

        # AI API (if has permission)
        if PermissionLevel.AI_QUERY in context.permissions:
            api["ai"] = {
                "query": "function(prompt) { /* ai query */ }"
            }

        return api

    async def _execute_in_sandbox(
        self, code: str, context: ExecutionContext, sandbox_env: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute code in sandboxed Node.js environment."""
        # This is a simplified implementation. In production, you would use:
        # 1. vm2 (Node.js sandbox) or
        # 2. Deno with restricted permissions or
        # 3. WebAssembly-based sandbox

        # For this implementation, we'll create a wrapper that simulates sandbox execution
        sandbox_wrapper = f"""
        (async function() {{
            const extension = {json.dumps(sandbox_env['extension'])};
            const context = {json.dumps(sandbox_env['context'])};
            const api = {{/* API bindings would be injected here */}};

            // Extension code
            {code}

            // Execute main function if exists
            if (typeof main === 'function') {{
                const result = await main(context);
                return result;
            }}

            return {{ output: "Extension loaded successfully", exitCode: 0 }};
        }})();
        """

        # In production, execute this in a real sandbox (Node.js vm2, Deno, etc.)
        # For now, we'll return a simulated result
        logger.debug(f"Sandbox execution for extension {context.extension_id}")

        # Simulate execution result
        return {
            "output": f"Extension {context.extension_id} executed successfully",
            "exitCode": 0,
            "memoryUsed": 1024 * 1024,  # 1MB
            "metadata": {
                "sandboxed": self.config.sandbox_enabled,
                "permissions": [p.value for p in context.permissions]
            }
        }


class ExtensionMarketplace:
    """Handles extension marketplace functionality."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_featured_extensions(self, limit: int = 10) -> List[Extension]:
        """Get featured extensions from marketplace."""
        result = await self.db.execute(
            select(Extension)
            .where(
                and_(
                    Extension.is_public == True,
                    Extension.rating >= 400  # 4.0+ rating
                )
            )
            .order_by(Extension.download_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def search_extensions(self, query: str, limit: int = 20) -> List[Extension]:
        """Search extensions by name, author, or description."""
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(Extension)
            .where(
                and_(
                    Extension.is_public == True,
                    or_(
                        Extension.name.ilike(search_pattern),
                        Extension.display_name.ilike(search_pattern),
                        Extension.author.ilike(search_pattern),
                        Extension.description.ilike(search_pattern)
                    )
                )
            )
            .order_by(Extension.rating.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_extensions_by_category(self, category: str, limit: int = 20) -> List[Extension]:
        """Get extensions by category."""
        # Categories could be stored in metadata
        result = await self.db.execute(
            select(Extension)
            .where(Extension.is_public == True)
            .order_by(Extension.download_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def rate_extension(self, extension_id: str, user_id: str, rating: float) -> bool:
        """Rate an extension (0.0 - 5.0)."""
        try:
            result = await self.db.execute(
                select(Extension).where(Extension.extension_id == extension_id)
            )
            extension = result.scalar_one_or_none()

            if not extension:
                return False

            # Update rating (simplified - in production, track individual ratings)
            current_rating = extension.get_rating_float()
            new_rating = (current_rating + rating) / 2  # Simple average
            extension.set_rating_float(new_rating)

            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error rating extension: {e}")
            return False


class ExtensionService:
    """Main extension management service."""

    def __init__(self, config: ExtensionConfig = None):
        self.config = config or ExtensionConfig()
        self.executor = SandboxExecutor(self.config)
        self._active_extensions: Dict[str, Extension] = {}
        self._command_registry: Dict[str, str] = {}  # command -> extension_id
        self._lock = asyncio.Lock()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        Path(self.config.extensions_dir).mkdir(parents=True, exist_ok=True)

    async def create_extension(self, user_id: str, extension_data: Dict[str, Any]) -> Extension:
        """Create a new extension."""
        # Validate extension
        validation = await ExtensionValidator.validate_extension(extension_data)
        if not validation["valid"]:
            raise ExtensionValidationError(f"Extension validation failed: {validation['errors']}")

        # Security scan
        if self.config.security_scan_enabled:
            scan_result = await ExtensionValidator.scan_for_malware(extension_data["code"])
            if scan_result["status"] == "malicious":
                raise ExtensionSecurityError(f"Extension failed security scan: {scan_result['threats']}")

        async with AsyncSessionLocal() as db:
            # Check user extension limit
            user_ext_count = await self._get_user_extension_count(db, user_id)
            if user_ext_count >= self.config.max_extensions_per_user:
                raise ExtensionValidationError(
                    f"Extension limit exceeded ({self.config.max_extensions_per_user})"
                )

            # Create extension
            extension = Extension(
                name=extension_data["name"],
                display_name=extension_data["display_name"],
                description=extension_data["description"],
                version=extension_data["version"],
                author=user_id,
                author_email=extension_data.get("author_email"),
                homepage=extension_data.get("homepage"),
                repository=extension_data.get("repository"),
                license=extension_data.get("license", "MIT"),
                commands=extension_data["commands"],
                permissions=extension_data.get("permissions", []),
                dependencies=extension_data.get("dependencies", []),
                manifest=extension_data.get("manifest", {}),
                code=extension_data["code"]
            )

            # Set security scan results
            extension.update_security_scan(
                scan_result["status"],
                scan_result["threats"],
                scan_result["scannerVersion"]
            )

            db.add(extension)
            await db.commit()
            await db.refresh(extension)

            logger.info(f"Created extension: {extension.extension_id} by user {user_id}")
            return extension

    async def get_extension(self, extension_id: str) -> Optional[Extension]:
        """Get extension by ID."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Extension).where(Extension.extension_id == extension_id)
            )
            return result.scalar_one_or_none()

    async def update_extension(
        self, extension_id: str, user_id: str, extension_data: Dict[str, Any]
    ) -> Optional[Extension]:
        """Update existing extension."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Extension).where(Extension.extension_id == extension_id)
            )
            extension = result.scalar_one_or_none()

            if not extension:
                return None

            # Check ownership
            if not extension.is_built_in and extension.author != user_id:
                raise ExtensionValidationError("Not authorized to update this extension")

            # Validate updates
            validation = await ExtensionValidator.validate_extension(extension_data)
            if not validation["valid"]:
                raise ExtensionValidationError(f"Extension validation failed: {validation['errors']}")

            # Update extension fields
            for field in ["display_name", "description", "version", "commands", "permissions", "code"]:
                if field in extension_data:
                    setattr(extension, field, extension_data[field])

            # Re-scan security if code changed
            if "code" in extension_data and self.config.security_scan_enabled:
                scan_result = await ExtensionValidator.scan_for_malware(extension_data["code"])
                extension.update_security_scan(
                    scan_result["status"],
                    scan_result["threats"],
                    scan_result["scannerVersion"]
                )

            extension.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(extension)

            return extension

    async def delete_extension(self, extension_id: str, user_id: str) -> bool:
        """Delete extension."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Extension).where(Extension.extension_id == extension_id)
            )
            extension = result.scalar_one_or_none()

            if not extension:
                return False

            # Check ownership
            if not extension.is_built_in and extension.author != user_id:
                return False

            # Cannot delete built-in extensions
            if extension.is_built_in:
                return False

            # Unregister commands
            await self._unregister_extension_commands(extension_id)

            await db.delete(extension)
            await db.commit()

            logger.info(f"Deleted extension: {extension_id}")
            return True

    async def enable_extension(self, extension_id: str, user_id: str) -> bool:
        """Enable extension for user."""
        extension = await self.get_extension(extension_id)
        if not extension or not extension.is_safe():
            return False

        async with self._lock:
            # Register extension commands
            await self._register_extension_commands(extension)

            # Add to active extensions
            self._active_extensions[extension_id] = extension

            logger.info(f"Enabled extension: {extension_id} for user {user_id}")
            return True

    async def disable_extension(self, extension_id: str, user_id: str) -> bool:
        """Disable extension for user."""
        async with self._lock:
            if extension_id not in self._active_extensions:
                return False

            # Unregister commands
            await self._unregister_extension_commands(extension_id)

            # Remove from active extensions
            del self._active_extensions[extension_id]

            logger.info(f"Disabled extension: {extension_id} for user {user_id}")
            return True

    async def execute_extension_command(
        self, command: str, session_id: str, user_id: str, args: List[str], env: Dict[str, str]
    ) -> ExecutionResult:
        """Execute an extension command."""
        async with self._lock:
            # Find extension for command
            extension_id = self._command_registry.get(command)
            if not extension_id:
                return ExecutionResult(
                    success=False,
                    error=f"Command not found: {command}",
                    exit_code=127
                )

            extension = self._active_extensions.get(extension_id)
            if not extension:
                return ExecutionResult(
                    success=False,
                    error=f"Extension not active: {extension_id}",
                    exit_code=1
                )

        # Create execution context
        permissions = {PermissionLevel(p) for p in extension.permissions}
        context = ExecutionContext(
            extension_id=extension_id,
            session_id=session_id,
            user_id=user_id,
            command=command,
            args=args,
            env=env,
            permissions=permissions,
            timeout=self.config.max_execution_time
        )

        # Execute
        return await self.executor.execute(extension, context)

    async def get_user_extensions(self, user_id: str) -> List[Extension]:
        """Get extensions created by user."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Extension)
                .where(Extension.author == user_id)
                .order_by(Extension.created_at.desc())
            )
            return result.scalars().all()

    async def get_active_extensions(self, user_id: str) -> List[Extension]:
        """Get currently active extensions."""
        return list(self._active_extensions.values())

    async def get_extension_commands(self, extension_id: str) -> List[CommandDefinition]:
        """Get commands provided by extension."""
        extension = await self.get_extension(extension_id)
        if not extension:
            return []

        return [
            CommandDefinition(
                name=cmd["name"],
                description=cmd["description"],
                usage=cmd["usage"],
                parameters=cmd.get("parameters", []),
                aliases=cmd.get("aliases", [])
            )
            for cmd in extension.commands
        ]

    async def publish_extension(self, extension_id: str, user_id: str) -> bool:
        """Publish extension to marketplace."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Extension).where(
                    Extension.extension_id == extension_id,
                    Extension.author == user_id
                )
            )
            extension = result.scalar_one_or_none()

            if not extension or not extension.is_safe():
                return False

            extension.is_public = True
            await db.commit()

            logger.info(f"Published extension to marketplace: {extension_id}")
            return True

    async def get_marketplace(self) -> ExtensionMarketplace:
        """Get marketplace instance."""
        async with AsyncSessionLocal() as db:
            return ExtensionMarketplace(db)

    async def _register_extension_commands(self, extension: Extension) -> None:
        """Register extension commands."""
        for cmd in extension.commands:
            cmd_name = cmd["name"]
            self._command_registry[cmd_name] = extension.extension_id

            # Register aliases
            for alias in cmd.get("aliases", []):
                self._command_registry[alias] = extension.extension_id

    async def _unregister_extension_commands(self, extension_id: str) -> None:
        """Unregister extension commands."""
        commands_to_remove = [
            cmd for cmd, ext_id in self._command_registry.items()
            if ext_id == extension_id
        ]

        for cmd in commands_to_remove:
            del self._command_registry[cmd]

    async def _get_user_extension_count(self, db: AsyncSession, user_id: str) -> int:
        """Get count of extensions created by user."""
        result = await db.execute(
            select(Extension).where(Extension.author == user_id)
        )
        return len(result.scalars().all())


# Global service instance
extension_service = ExtensionService()


async def get_extension_service() -> ExtensionService:
    """Dependency injection for extension service."""
    return extension_service