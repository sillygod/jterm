"""File upload security validation and virus scanning middleware.

This middleware provides comprehensive security validation for file uploads including:
- File type validation (MIME type and extension)
- File size limits
- Malicious content detection
- Virus scanning (optional with ClamAV)
- Path traversal protection
- Archive bomb detection
"""

import hashlib
import logging
import magic
import mimetypes
import os
import re
import zipfile
from pathlib import Path
from typing import Optional, List, Set, Dict, Any
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Security validation configuration."""
    max_file_size: int = 50 * 1024 * 1024  # 50MB default
    allowed_mime_types: Optional[Set[str]] = None
    allowed_extensions: Optional[Set[str]] = None
    blocked_extensions: Set[str] = None
    enable_virus_scan: bool = False
    enable_magic_bytes_check: bool = True
    enable_archive_check: bool = True
    max_archive_ratio: float = 10.0  # Max compression ratio to detect bombs
    scan_timeout: int = 30  # seconds

    def __post_init__(self):
        """Initialize default values."""
        if self.blocked_extensions is None:
            self.blocked_extensions = {
                '.exe', '.dll', '.com', '.bat', '.cmd', '.sh', '.bash',
                '.ps1', '.vbs', '.js', '.jar', '.app', '.deb', '.rpm',
                '.msi', '.scr', '.pif', '.cpl', '.gadget'
            }

        # Safe default allowed types for web terminal
        if self.allowed_mime_types is None:
            self.allowed_mime_types = {
                # Images
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'image/bmp', 'image/tiff', 'image/svg+xml',
                # Videos
                'video/mp4', 'video/webm', 'video/ogg', 'video/avi',
                'video/mov', 'video/mkv',
                # Documents
                'text/plain', 'text/html', 'text/css', 'text/javascript',
                'text/markdown', 'text/csv',
                'application/json', 'application/xml',
                'application/pdf',
                # Archives (need careful handling)
                'application/zip', 'application/x-tar',
                'application/gzip', 'application/x-bzip2'
            }

        if self.allowed_extensions is None:
            self.allowed_extensions = {
                # Images
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',
                '.tiff', '.svg',
                # Videos
                '.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv',
                # Documents
                '.txt', '.html', '.css', '.js', '.md', '.csv',
                '.json', '.xml', '.pdf',
                # Archives
                '.zip', '.tar', '.gz', '.bz2'
            }


class FileSecurityError(Exception):
    """Base exception for file security violations."""
    pass


class FileSizeError(FileSecurityError):
    """Raised when file exceeds size limit."""
    pass


class FileTypeError(FileSecurityError):
    """Raised when file type is not allowed."""
    pass


class MaliciousFileError(FileSecurityError):
    """Raised when malicious content is detected."""
    pass


class ArchiveBombError(FileSecurityError):
    """Raised when archive bomb is detected."""
    pass


class FileValidator:
    """Comprehensive file security validator."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize file validator.

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()
        self._magic = magic.Magic(mime=True) if self.config.enable_magic_bytes_check else None

    async def validate_file(
        self,
        file: UploadFile,
        content: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Validate uploaded file for security issues.

        Args:
            file: Uploaded file object
            content: Optional file content (if already read)

        Returns:
            Validation result dictionary

        Raises:
            FileSecurityError: If validation fails
        """
        result = {
            "filename": file.filename,
            "declared_content_type": file.content_type,
            "size": 0,
            "actual_mime_type": None,
            "extension": None,
            "is_safe": True,
            "warnings": [],
            "hash": None
        }

        # Read file content if not provided
        if content is None:
            content = await file.read()
            await file.seek(0)  # Reset file pointer

        result["size"] = len(content)

        # Validate file size
        self._validate_size(len(content))

        # Get file extension
        extension = self._get_extension(file.filename)
        result["extension"] = extension

        # Validate extension
        self._validate_extension(extension)

        # Detect actual MIME type using magic bytes
        if self._magic:
            actual_mime = self._detect_mime_type(content)
            result["actual_mime_type"] = actual_mime

            # Check for MIME type mismatch
            if file.content_type and actual_mime != file.content_type:
                result["warnings"].append(
                    f"MIME type mismatch: declared {file.content_type}, "
                    f"detected {actual_mime}"
                )

            # Validate actual MIME type
            self._validate_mime_type(actual_mime)
        else:
            # Fall back to declared content type
            if file.content_type:
                self._validate_mime_type(file.content_type)

        # Calculate file hash
        result["hash"] = self._calculate_hash(content)

        # Check for path traversal
        self._check_path_traversal(file.filename)

        # Check for malicious patterns
        self._check_malicious_patterns(file.filename, content)

        # Check for archive bombs
        if self.config.enable_archive_check and self._is_archive(extension):
            self._check_archive_bomb(content)

        # Virus scan if enabled
        if self.config.enable_virus_scan:
            scan_result = await self._virus_scan(content)
            if not scan_result["is_clean"]:
                raise MaliciousFileError(
                    f"Virus detected: {scan_result.get('threat_name', 'Unknown')}"
                )
            result["virus_scan"] = scan_result

        return result

    def _validate_size(self, size: int) -> None:
        """Validate file size.

        Args:
            size: File size in bytes

        Raises:
            FileSizeError: If file exceeds size limit
        """
        if size > self.config.max_file_size:
            raise FileSizeError(
                f"File size {size} bytes exceeds maximum allowed "
                f"{self.config.max_file_size} bytes"
            )

        if size == 0:
            raise FileSizeError("File is empty")

    def _validate_extension(self, extension: str) -> None:
        """Validate file extension.

        Args:
            extension: File extension (including dot)

        Raises:
            FileTypeError: If extension is not allowed
        """
        extension_lower = extension.lower()

        # Check blocked extensions
        if extension_lower in self.config.blocked_extensions:
            raise FileTypeError(
                f"File extension {extension} is blocked for security reasons"
            )

        # Check allowed extensions
        if self.config.allowed_extensions:
            if extension_lower not in self.config.allowed_extensions:
                raise FileTypeError(
                    f"File extension {extension} is not allowed. "
                    f"Allowed: {', '.join(self.config.allowed_extensions)}"
                )

    def _validate_mime_type(self, mime_type: str) -> None:
        """Validate MIME type.

        Args:
            mime_type: MIME type string

        Raises:
            FileTypeError: If MIME type is not allowed
        """
        if self.config.allowed_mime_types:
            # Check exact match first
            if mime_type in self.config.allowed_mime_types:
                return

            # Check wildcard patterns (e.g., image/*)
            mime_category = mime_type.split('/')[0] if '/' in mime_type else None
            if mime_category:
                wildcard = f"{mime_category}/*"
                if wildcard in self.config.allowed_mime_types:
                    return

            raise FileTypeError(
                f"MIME type {mime_type} is not allowed. "
                f"Allowed: {', '.join(sorted(self.config.allowed_mime_types))}"
            )

    def _get_extension(self, filename: str) -> str:
        """Get file extension from filename.

        Args:
            filename: File name

        Returns:
            File extension (including dot)
        """
        return Path(filename).suffix

    def _detect_mime_type(self, content: bytes) -> str:
        """Detect MIME type from file content using magic bytes.

        Args:
            content: File content

        Returns:
            Detected MIME type
        """
        if self._magic:
            try:
                return self._magic.from_buffer(content)
            except Exception as e:
                logger.warning(f"Failed to detect MIME type: {e}")
                return "application/octet-stream"
        return "application/octet-stream"

    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content.

        Args:
            content: File content

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content).hexdigest()

    def _check_path_traversal(self, filename: str) -> None:
        """Check for path traversal attempts in filename.

        Args:
            filename: File name

        Raises:
            MaliciousFileError: If path traversal detected
        """
        # Check for directory traversal patterns
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            raise MaliciousFileError(
                f"Path traversal detected in filename: {filename}"
            )

        # Check for absolute paths
        if os.path.isabs(filename):
            raise MaliciousFileError(
                f"Absolute path detected in filename: {filename}"
            )

        # Normalize and check again
        normalized = os.path.normpath(filename)
        if normalized.startswith('..') or normalized.startswith('/'):
            raise MaliciousFileError(
                f"Path traversal detected after normalization: {filename}"
            )

    def _check_malicious_patterns(self, filename: str, content: bytes) -> None:
        """Check for malicious patterns in filename and content.

        Args:
            filename: File name
            content: File content

        Raises:
            MaliciousFileError: If malicious patterns detected
        """
        # Check for suspicious characters in filename
        suspicious_chars = ['<', '>', '|', '&', ';', '$', '`', '\n', '\r', '\0']
        for char in suspicious_chars:
            if char in filename:
                raise MaliciousFileError(
                    f"Suspicious character '{char}' in filename: {filename}"
                )

        # Check for null bytes in content (polyglot files)
        if b'\x00' in content[:1024]:  # Check first 1KB
            logger.warning(f"Null bytes detected in file: {filename}")

        # Check for script tags in files that shouldn't have them
        extension = self._get_extension(filename).lower()
        if extension in {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}:
            # Decode first part of content to check for scripts
            try:
                content_str = content[:4096].decode('utf-8', errors='ignore')
                if '<script' in content_str.lower() or 'javascript:' in content_str.lower():
                    raise MaliciousFileError(
                        f"Script content detected in {extension} file"
                    )
            except Exception:
                pass  # Binary content, can't decode

    def _is_archive(self, extension: str) -> bool:
        """Check if file is an archive.

        Args:
            extension: File extension

        Returns:
            True if archive, False otherwise
        """
        archive_extensions = {'.zip', '.tar', '.gz', '.bz2', '.7z', '.rar'}
        return extension.lower() in archive_extensions

    def _check_archive_bomb(self, content: bytes) -> None:
        """Check for archive bomb (zip bomb).

        Args:
            content: Archive file content

        Raises:
            ArchiveBombError: If archive bomb detected
        """
        try:
            # Only check ZIP files for now
            if not content.startswith(b'PK'):
                return

            import io
            zip_buffer = io.BytesIO(content)

            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                compressed_size = len(content)
                uncompressed_size = sum(info.file_size for info in zf.infolist())

                # Check compression ratio
                if uncompressed_size > 0:
                    ratio = uncompressed_size / compressed_size
                    if ratio > self.config.max_archive_ratio:
                        raise ArchiveBombError(
                            f"Suspicious compression ratio: {ratio:.1f}x "
                            f"(max allowed: {self.config.max_archive_ratio}x)"
                        )

                # Check for excessive number of files
                if len(zf.infolist()) > 1000:
                    raise ArchiveBombError(
                        f"Archive contains too many files: {len(zf.infolist())}"
                    )

                # Check for deeply nested archives
                for info in zf.infolist():
                    if info.filename.count('/') > 10:
                        raise ArchiveBombError(
                            f"Excessive directory nesting in archive: {info.filename}"
                        )

        except zipfile.BadZipFile:
            logger.warning("Invalid ZIP file")
        except ArchiveBombError:
            raise
        except Exception as e:
            logger.warning(f"Error checking archive: {e}")

    async def _virus_scan(self, content: bytes) -> Dict[str, Any]:
        """Scan file content for viruses using ClamAV.

        Args:
            content: File content

        Returns:
            Scan result dictionary
        """
        # This is a placeholder for ClamAV integration
        # In production, you would use python-clamd or similar

        result = {
            "is_clean": True,
            "threat_name": None,
            "scan_time": 0.0
        }

        try:
            # Try to import clamd
            import clamd
            import time

            start_time = time.time()

            # Connect to ClamAV daemon
            cd = clamd.ClamdUnixSocket()

            # Scan content
            scan_result = cd.instream(content)

            result["scan_time"] = time.time() - start_time

            # Check result
            if scan_result and 'stream' in scan_result:
                status, threat = scan_result['stream']
                if status == 'FOUND':
                    result["is_clean"] = False
                    result["threat_name"] = threat

        except ImportError:
            logger.warning("ClamAV not available, skipping virus scan")
            result["is_clean"] = True
            result["threat_name"] = "SCAN_NOT_AVAILABLE"
        except Exception as e:
            logger.error(f"Virus scan error: {e}")
            # Fail open (allow file) but log the error
            result["is_clean"] = True
            result["threat_name"] = f"SCAN_ERROR: {str(e)}"

        return result


class SecurityValidationMiddleware:
    """Middleware for validating file uploads in requests.

    This can be used as a dependency in FastAPI endpoints.
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize security validation middleware.

        Args:
            config: Security configuration
        """
        self.validator = FileValidator(config)

    async def __call__(self, file: UploadFile) -> UploadFile:
        """Validate uploaded file.

        Args:
            file: Uploaded file

        Returns:
            Validated file

        Raises:
            HTTPException: If validation fails
        """
        try:
            # Validate file
            validation_result = await self.validator.validate_file(file)

            # Attach validation result to file for later use
            file.validation_result = validation_result

            # Log warnings
            if validation_result.get("warnings"):
                logger.warning(
                    f"File validation warnings for {file.filename}: "
                    f"{', '.join(validation_result['warnings'])}"
                )

            return file

        except FileSizeError as e:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(e)
            )
        except FileTypeError as e:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=str(e)
            )
        except (MaliciousFileError, ArchiveBombError) as e:
            logger.error(f"Security threat detected: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File rejected due to security concerns"
            )
        except FileSecurityError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"File validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File validation failed"
            )


# Convenience instances for different use cases
default_validator = SecurityValidationMiddleware()

# Strict validator for sensitive operations
strict_config = SecurityConfig(
    max_file_size=10 * 1024 * 1024,  # 10MB
    enable_virus_scan=True,
    allowed_extensions={'.txt', '.json', '.csv'},
    allowed_mime_types={'text/plain', 'application/json', 'text/csv'}
)
strict_validator = SecurityValidationMiddleware(strict_config)

# Permissive validator for internal use
permissive_config = SecurityConfig(
    max_file_size=100 * 1024 * 1024,  # 100MB
    enable_virus_scan=False,
    allowed_extensions=None,  # Allow all except blocked
)
permissive_validator = SecurityValidationMiddleware(permissive_config)


async def validate_file_upload(
    file: UploadFile,
    config: Optional[SecurityConfig] = None
) -> Dict[str, Any]:
    """Standalone function to validate file upload.

    Args:
        file: Uploaded file
        config: Optional security configuration

    Returns:
        Validation result dictionary

    Raises:
        HTTPException: If validation fails
    """
    validator = SecurityValidationMiddleware(config)
    await validator(file)
    return getattr(file, 'validation_result', {})
