"""Image Loader Service for loading images from various sources.

This service handles loading images from:
- File paths (local filesystem)
- URLs (HTTP/HTTPS)
- Stdin (clipboard pipe)
"""

import asyncio
import hashlib
import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timezone

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.image_editor import ImageSession, ImageSourceType, ImageFormat


logger = logging.getLogger(__name__)


class ImageLoaderError(Exception):
    """Base exception for image loader operations."""
    pass


class ImageValidationError(ImageLoaderError):
    """Raised when image validation fails."""
    pass


class ImageLoaderService:
    """
    Service for loading images from various sources.

    Handles file validation, format detection, and creates ImageSession records.
    """

    # Maximum image size: 50MB
    MAX_IMAGE_SIZE = 52428800

    # Maximum dimensions (Canvas API limit)
    MAX_WIDTH = 32767
    MAX_HEIGHT = 32767

    # Supported formats
    SUPPORTED_FORMATS = {'png', 'jpeg', 'jpg', 'gif', 'webp', 'bmp'}

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the image loader service.

        Args:
            temp_dir: Directory for temporary files. Defaults to system temp.
        """
        if not PILLOW_AVAILABLE:
            raise RuntimeError("Pillow is required for ImageLoaderService")

        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_path_security(file_path: str, allow_symlinks: bool = False) -> Path:
        """
        Validate file path for security vulnerabilities (T139).

        Args:
            file_path: Path to validate
            allow_symlinks: Whether to allow symbolic links

        Returns:
            Path: Validated and resolved Path object

        Raises:
            ImageValidationError: If path is invalid or unsafe

        Security checks:
        - Block path traversal (../ sequences)
        - Block home directory expansion (~)
        - Block null bytes
        - Validate file extension
        - Optionally block symbolic links
        """
        if not file_path or not isinstance(file_path, str):
            raise ImageValidationError("Invalid file path: path must be a non-empty string")

        # Block null bytes (path injection)
        if '\x00' in file_path:
            raise ImageValidationError("Invalid file path: null byte detected")

        # Create Path object
        try:
            path = Path(file_path)
        except (ValueError, OSError) as e:
            raise ImageValidationError(f"Invalid file path format: {str(e)}")

        # Block path traversal patterns
        path_str = str(path)
        if '..' in path_str:
            raise ImageValidationError("Path traversal detected: '..' not allowed in path")

        # Block home directory expansion
        if '~' in path_str:
            raise ImageValidationError("Home directory expansion not allowed: '~' detected")

        # Check if path exists
        if not path.exists():
            raise ImageValidationError(f"File not found: {file_path}")

        # Resolve to absolute path (detects symlinks)
        try:
            resolved_path = path.resolve(strict=True)
        except (RuntimeError, OSError) as e:
            raise ImageValidationError(f"Cannot resolve path: {str(e)}")

        # Block symbolic links if not allowed
        if not allow_symlinks and path.is_symlink():
            raise ImageValidationError("Symbolic links not allowed")

        # Validate it's a file (not directory)
        if not resolved_path.is_file():
            raise ImageValidationError(f"Path is not a file: {file_path}")

        # Validate file extension
        extension = resolved_path.suffix.lower().lstrip('.')
        if extension not in {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}:
            raise ImageValidationError(
                f"Unsupported file extension: .{extension}. "
                f"Allowed extensions: .png, .jpg, .jpeg, .gif, .webp, .bmp"
            )

        return resolved_path

    @staticmethod
    def get_clipboard_utility() -> Tuple[str, str]:
        """
        Detect platform and return appropriate clipboard utility command.

        Returns:
            Tuple[str, str]: (utility_name, install_instructions)

        Examples:
            - macOS: ('pngpaste' or 'osascript', 'brew install pngpaste (or use built-in AppleScript)')
            - Linux (X11): ('xclip', 'Install with: sudo apt-get install xclip')
            - Linux (Wayland): ('wl-paste', 'Install with: sudo apt-get install wl-clipboard')
            - Windows: ('powershell Get-Clipboard', 'Built-in on Windows (PowerShell required)')

        Note: pbpaste on macOS only works with TEXT, not images!
        """
        platform = sys.platform

        if platform == 'darwin':
            # macOS - pbpaste is TEXT-ONLY, use pngpaste or osascript for images
            return ('pngpaste', 'For images: brew install pngpaste (or use built-in AppleScript)')
        elif platform.startswith('linux'):
            # Linux - prefer Wayland if available, fallback to X11
            return ('wl-paste -t image/png', 'Install with: sudo apt-get install wl-clipboard (or xclip for X11)')
        elif platform == 'win32':
            # Windows
            return ('powershell Get-Clipboard -Format Image', 'Built-in on Windows (PowerShell required)')
        else:
            return ('unknown', f'Unsupported platform: {platform}')

    @staticmethod
    def suggest_clipboard_command(file_path: Optional[str] = None) -> str:
        """
        Suggest platform-specific clipboard command for loading images.

        Args:
            file_path: Optional file path to suggest in example

        Returns:
            str: Suggested command string

        Examples:
            - macOS: 'pngpaste - | imgcat' or 'imgcat --clipboard' (uses AppleScript)
            - Linux: 'wl-paste -t image/png | imgcat' or 'xclip -selection clipboard -t image/png -o | imgcat'
            - Windows: 'imgcat --clipboard' (uses PowerShell Get-Clipboard)

        Note: pbpaste does NOT work for images on macOS (text only)!
        """
        platform = sys.platform
        example_file = file_path or "screenshot.png"

        if platform == 'darwin':
            return (
                f'imgcat --clipboard   # Uses AppleScript (built-in)\n'
                f'  or: pngpaste - | imgcat   # Requires: brew install pngpaste\n'
                f'\n'
                f'Note: pbpaste does NOT work for images (text only)!'
            )
        elif platform.startswith('linux'):
            return (
                f'wl-paste -t image/png | imgcat   # Wayland\n'
                f'  or: xclip -selection clipboard -t image/png -o | imgcat   # X11\n'
                f'  or: imgcat --clipboard'
            )
        elif platform == 'win32':
            return (
                f'imgcat --clipboard   # Uses PowerShell Get-Clipboard\n'
                f'  or: powershell -Command "Get-Clipboard -Format Image | Set-Content -Path temp.png -Encoding Byte; imgcat temp.png"'
            )
        else:
            return f'imgcat --clipboard (platform-specific clipboard handling)'

    async def load_from_file(
        self,
        file_path: str,
        terminal_session_id: str,
        db: AsyncSession
    ) -> ImageSession:
        """
        Load image from local file path.

        Args:
            file_path: Absolute path to image file
            terminal_session_id: Terminal session ID from jterm
            db: Database session

        Returns:
            ImageSession: Created image session record

        Raises:
            ImageValidationError: If file validation fails
            ImageLoaderError: If loading fails
        """
        logger.info(f"Loading image from file: {file_path}")

        try:
            # T139: Validate file path for security (path traversal, symlinks, extensions)
            path = self.validate_path_security(file_path, allow_symlinks=False)

            # Validate file size
            file_size = self._validate_file_size(path)

            # Load and validate image with Pillow
            try:
                # First, verify image integrity
                with Image.open(path) as img:
                    img.verify()  # Verify image data integrity

                # Reopen for actual use (verify closes the file)
                image = Image.open(path)
                image.load()  # Force load to validate format
            except (IOError, OSError) as e:
                raise ImageValidationError(f"Corrupt or invalid image file: {str(e)}")
            except Exception as e:
                raise ImageValidationError(f"Failed to load image: {str(e)}")

            try:
                # Validate format
                image_format = self._validate_image_format(image, path)

                # Validate dimensions
                width, height = self._validate_dimensions(image)
            finally:
                # Close the image to free resources
                if image is not None:
                    image.close()

            # Create temporary working copy
            temp_file = await self._create_temp_copy(path)

            # Create ImageSession record
            session = await self._create_session_record(
                terminal_session_id=terminal_session_id,
                source_type=ImageSourceType.FILE,
                source_path=file_path,
                image_format=image_format,
                width=width,
                height=height,
                file_size=file_size,
                temp_file_path=str(temp_file),
                db=db
            )

            logger.info(f"Successfully loaded image from file: {file_path} (session: {session.id})")
            return session

        except ImageValidationError:
            raise
        except Exception as e:
            logger.error(f"Error loading image from file {file_path}: {str(e)}")
            raise ImageLoaderError(f"Failed to load image: {str(e)}")

    def validate_url(self, url: str) -> bool:
        """
        Validate URL for security (T106, T115 - SSRF prevention).

        Args:
            url: URL to validate

        Returns:
            bool: True if URL is valid and safe, False otherwise

        Security checks:
        - Only HTTP/HTTPS schemes allowed
        - Block private IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
        - Block AWS metadata service (169.254.169.254)
        - Block localhost
        """
        from urllib.parse import urlparse
        import ipaddress
        import socket

        try:
            parsed = urlparse(url)

            # Only allow HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                logger.warning(f"Invalid URL scheme: {parsed.scheme}")
                return False

            # Extract hostname
            hostname = parsed.hostname
            if not hostname:
                return False

            # Block localhost variations
            if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
                logger.warning(f"Blocked localhost URL: {url}")
                return False

            # Resolve hostname to IP
            try:
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)

                # Block private IP ranges
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    logger.warning(f"Blocked private IP URL: {url} ({ip})")
                    return False

                # Block AWS metadata service specifically
                if ip_str == '169.254.169.254':
                    logger.warning(f"Blocked AWS metadata service URL: {url}")
                    return False

            except socket.gaierror:
                # DNS resolution failed - let it fail later in download
                pass
            except ValueError:
                # Invalid IP address format
                return False

            return True

        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False

    async def load_from_url(
        self,
        url: str,
        terminal_session_id: str,
        db: AsyncSession,
        timeout: int = 10
    ) -> ImageSession:
        """
        Load image from URL (T108-T109, T112, T115).

        Args:
            url: HTTP/HTTPS URL to image
            terminal_session_id: Terminal session ID from jterm
            db: Database session
            timeout: Request timeout in seconds (default 10s)

        Returns:
            ImageSession: Created image session record

        Raises:
            ImageValidationError: If URL or image validation fails
            ImageLoaderError: If download fails
        """
        logger.info(f"Loading image from URL: {url}")

        # T106, T115: Validate URL (SSRF prevention)
        if not self.validate_url(url):
            raise ImageValidationError(f"Invalid or unsafe URL: {url}")

        try:
            # T108: Download image with aiohttp
            timeout_obj = aiohttp.ClientTimeout(total=timeout)

            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(url) as response:
                    # Check response status
                    if response.status != 200:
                        raise ImageLoaderError(f"HTTP {response.status}: Failed to download image from {url}")

                    # T109: Validate Content-Type header
                    content_type = response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        raise ImageValidationError(f"URL does not point to an image. Content-Type: {content_type}")

                    # T108: Check size limit (50MB)
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.MAX_IMAGE_SIZE:
                        size_mb = int(content_length) / (1024 * 1024)
                        raise ImageValidationError(
                            f"Image too large: {size_mb:.1f}MB (max 50MB)"
                        )

                    # T108: Read image data
                    image_data = await response.read()

                    # Verify size after download
                    if len(image_data) > self.MAX_IMAGE_SIZE:
                        size_mb = len(image_data) / (1024 * 1024)
                        raise ImageValidationError(
                            f"Image too large: {size_mb:.1f}MB (max 50MB)"
                        )

        except aiohttp.ClientTimeout:
            # T112: Handle timeout
            raise ImageLoaderError(f"Timeout downloading image from {url} (>{timeout}s)")
        except aiohttp.ClientConnectorError as e:
            # T112: Handle connection errors
            raise ImageLoaderError(f"Connection failed: {str(e)}")
        except aiohttp.ClientError as e:
            # T112: Handle other HTTP errors
            raise ImageLoaderError(f"Download failed: {str(e)}")

        # T108: Save to temporary file
        temp_path = self.temp_dir / f"url_{hashlib.md5(url.encode()).hexdigest()}.tmp"
        try:
            await asyncio.to_thread(temp_path.write_bytes, image_data)

            # Validate image format and dimensions
            try:
                img = await asyncio.to_thread(Image.open, temp_path)
                width, height = img.size
                image_format = img.format.lower() if img.format else 'unknown'

                # Validate format
                if image_format not in self.SUPPORTED_FORMATS:
                    raise ImageValidationError(f"Unsupported image format: {image_format}")

                # Validate dimensions
                if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                    raise ImageValidationError(
                        f"Image dimensions {width}x{height} exceed maximum {self.MAX_WIDTH}x{self.MAX_HEIGHT}"
                    )

                # Convert format name for enum
                if image_format == 'jpeg' or image_format == 'jpg':
                    enum_format = 'jpeg'
                else:
                    enum_format = image_format

            except Exception as e:
                # T112: Invalid image data
                raise ImageValidationError(f"Invalid image data: {str(e)}")

            # Create working copy
            working_copy = await self._create_temp_copy(Path(temp_path))

            # Create session record
            session = await self._create_session_record(
                terminal_session_id=terminal_session_id,
                source_type=ImageSourceType.URL,
                source_path=url,
                image_format=enum_format,
                width=width,
                height=height,
                file_size=len(image_data),
                temp_file_path=str(working_copy),
                db=db
            )

            logger.info(f"Successfully loaded image from URL: {url} ({width}x{height}, {image_format})")
            return session

        except ImageValidationError:
            raise
        except ImageLoaderError:
            raise
        except Exception as e:
            logger.error(f"Error loading image from URL {url}: {str(e)}")
            raise ImageLoaderError(f"Failed to load image: {str(e)}")
        finally:
            # Clean up temp file
            if temp_path.exists():
                await asyncio.to_thread(temp_path.unlink)

    async def load_from_stdin(
        self,
        stdin_data: bytes,
        terminal_session_id: str,
        db: AsyncSession
    ) -> ImageSession:
        """
        Load image from stdin (clipboard pipe).

        Args:
            stdin_data: Raw image data from stdin
            terminal_session_id: Terminal session ID from jterm
            db: Database session

        Returns:
            ImageSession: Created image session record

        Raises:
            ImageValidationError: If data validation fails
            ImageLoaderError: If loading fails
        """
        logger.info("Loading image from stdin (clipboard)")

        try:
            from io import BytesIO
            import imghdr
            import uuid

            # Validate data is not empty (FR-025)
            if not stdin_data or len(stdin_data) == 0:
                raise ImageValidationError("Clipboard data is empty. No image data provided via stdin.")

            # Validate data size before processing
            data_size = len(stdin_data)
            if data_size > self.MAX_IMAGE_SIZE:
                size_mb = data_size / (1024 * 1024)
                max_mb = self.MAX_IMAGE_SIZE / (1024 * 1024)
                raise ImageValidationError(
                    f"Clipboard data size {size_mb:.1f}MB exceeds maximum {max_mb:.0f}MB"
                )

            # Detect image format from magic bytes
            image_format_detected = imghdr.what(None, h=stdin_data[:32])
            if not image_format_detected:
                raise ImageValidationError(
                    "Unable to detect image format from clipboard data. "
                    "Data may not be a valid image."
                )

            # Normalize format
            format_lower = image_format_detected.lower()
            if format_lower == 'jpg':
                format_lower = 'jpeg'

            # Validate supported format
            if format_lower not in self.SUPPORTED_FORMATS:
                raise ImageValidationError(
                    f"Unsupported image format from clipboard: {image_format_detected}. "
                    f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
                )

            # Load image with Pillow from BytesIO
            try:
                image = Image.open(BytesIO(stdin_data))
                image.load()  # Force load to validate format
            except Exception as e:
                raise ImageValidationError(f"Failed to parse clipboard image data: {str(e)}")

            # Validate dimensions
            width, height = self._validate_dimensions(image)

            # Save to temporary file
            temp_filename = f"imgcat_clipboard_{uuid.uuid4().hex}.{format_lower}"
            temp_path = self.temp_dir / temp_filename

            # Write data to temp file
            await asyncio.to_thread(temp_path.write_bytes, stdin_data)

            logger.info(f"Saved clipboard image to temp file: {temp_path} ({data_size} bytes)")

            # Create ImageSession record with source_type='clipboard'
            session = await self._create_session_record(
                terminal_session_id=terminal_session_id,
                source_type=ImageSourceType.CLIPBOARD,
                source_path=None,  # No source path for clipboard
                image_format=format_lower,
                width=width,
                height=height,
                file_size=data_size,
                temp_file_path=str(temp_path),
                db=db
            )

            logger.info(f"Successfully loaded image from clipboard (session: {session.id})")
            return session

        except ImageValidationError:
            raise
        except Exception as e:
            logger.error(f"Error loading image from clipboard: {str(e)}")
            raise ImageLoaderError(f"Failed to load clipboard image: {str(e)}")

    async def load_from_clipboard(
        self,
        terminal_session_id: str,
        db: AsyncSession
    ) -> ImageSession:
        """
        Load image directly from system clipboard using PIL.ImageGrab.

        This method uses Pillow's built-in ImageGrab.grabclipboard() which works
        on macOS and Windows without requiring external tools.

        Args:
            terminal_session_id: Terminal session ID from jterm
            db: Database session

        Returns:
            ImageSession: Created image session record

        Raises:
            ImageValidationError: If clipboard is empty or contains invalid image
            ImageLoaderError: If loading fails

        Note:
            - macOS: Uses Cocoa/AppKit (built into Pillow)
            - Windows: Uses Win32 API (built into Pillow)
            - Linux: Falls back to stdin method (use wl-paste or xclip to pipe)
        """
        logger.info("Loading image from clipboard using PIL.ImageGrab")

        try:
            from io import BytesIO
            import uuid

            # Check if ImageGrab is available (not available on all platforms)
            try:
                from PIL import ImageGrab
            except ImportError:
                raise ImageLoaderError(
                    "PIL.ImageGrab not available on this platform. "
                    "Use clipboard pipe instead: wl-paste -t image/png | imgcat"
                )

            # Try to grab image from clipboard
            clipboard_image = await asyncio.to_thread(ImageGrab.grabclipboard)

            # Check if clipboard contains an image
            if clipboard_image is None:
                raise ImageValidationError(
                    "Clipboard is empty or does not contain image data.\n\n"
                    "Make sure you:\n"
                    "  1. Copy an IMAGE (not a file path) - use ⌘C on an image\n"
                    "  2. For screenshots, use ⌘⇧⌃4 to copy to clipboard\n"
                    "  3. Right-click on image → 'Copy Image' (not 'Copy Image Address')"
                )

            # Check if it's a list of file paths (some apps copy files as paths)
            if isinstance(clipboard_image, list):
                raise ImageValidationError(
                    "Clipboard contains file paths, not image data.\n\n"
                    "Try:\n"
                    "  1. Right-click on image → 'Copy Image' (not just Copy)\n"
                    "  2. Or open the image and copy the content (⌘C)"
                )

            # Validate it's a PIL Image
            if not isinstance(clipboard_image, Image.Image):
                raise ImageValidationError(
                    f"Clipboard contains unsupported data type: {type(clipboard_image).__name__}"
                )

            # Validate dimensions
            width, height = self._validate_dimensions(clipboard_image)

            # Determine format (default to PNG for clipboard)
            image_format = clipboard_image.format or 'png'
            format_lower = image_format.lower()
            if format_lower == 'jpg':
                format_lower = 'jpeg'

            # Convert to bytes to validate size
            buffer = BytesIO()
            save_format = 'PNG' if format_lower == 'png' else format_lower.upper()
            clipboard_image.save(buffer, format=save_format)
            image_bytes = buffer.getvalue()
            data_size = len(image_bytes)

            # Validate size
            if data_size > self.MAX_IMAGE_SIZE:
                size_mb = data_size / (1024 * 1024)
                max_mb = self.MAX_IMAGE_SIZE / (1024 * 1024)
                raise ImageValidationError(
                    f"Clipboard image size {size_mb:.1f}MB exceeds maximum {max_mb:.0f}MB"
                )

            # Save to temporary file
            temp_filename = f"imgcat_clipboard_{uuid.uuid4().hex}.{format_lower}"
            temp_path = self.temp_dir / temp_filename

            # Save image to temp file
            await asyncio.to_thread(clipboard_image.save, temp_path, format=save_format)

            logger.info(f"Saved clipboard image to temp file: {temp_path} ({data_size} bytes)")

            # Create ImageSession record
            session = await self._create_session_record(
                terminal_session_id=terminal_session_id,
                source_type=ImageSourceType.CLIPBOARD,
                source_path=None,  # No source path for clipboard
                image_format=format_lower,
                width=width,
                height=height,
                file_size=data_size,
                temp_file_path=str(temp_path),
                db=db
            )

            logger.info(f"Successfully loaded image from clipboard using PIL.ImageGrab (session: {session.id})")
            return session

        except ImageValidationError:
            raise
        except ImportError as e:
            raise ImageLoaderError(f"ImageGrab not available: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading image from clipboard: {str(e)}")
            raise ImageLoaderError(f"Failed to load clipboard image: {str(e)}")

    def _validate_image_format(self, image: Image.Image, file_path: Path) -> str:
        """
        Validate image format is supported.

        Args:
            image: PIL Image object
            file_path: Path to image file for format detection

        Returns:
            str: Normalized format (png, jpeg, gif, webp, bmp)

        Raises:
            ImageValidationError: If format is not supported
        """
        # Get format from Pillow
        image_format = image.format
        if not image_format:
            # Try to detect from file extension
            ext = file_path.suffix.lower().lstrip('.')
            if ext in self.SUPPORTED_FORMATS:
                image_format = ext
            else:
                raise ImageValidationError(f"Unable to detect image format")

        # Normalize format
        format_lower = image_format.lower()
        if format_lower == 'jpg':
            format_lower = 'jpeg'

        # Validate supported
        if format_lower not in self.SUPPORTED_FORMATS:
            raise ImageValidationError(
                f"Unsupported image format: {image_format}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        return format_lower

    def _validate_dimensions(self, image: Image.Image) -> Tuple[int, int]:
        """
        Validate image dimensions are within limits.

        Args:
            image: PIL Image object

        Returns:
            Tuple[int, int]: (width, height)

        Raises:
            ImageValidationError: If dimensions exceed limits
        """
        width, height = image.size

        if width <= 0 or height <= 0:
            raise ImageValidationError(f"Invalid dimensions: {width}x{height}")

        if width > self.MAX_WIDTH:
            raise ImageValidationError(
                f"Image width {width}px exceeds maximum {self.MAX_WIDTH}px (Canvas API limit)"
            )

        if height > self.MAX_HEIGHT:
            raise ImageValidationError(
                f"Image height {height}px exceeds maximum {self.MAX_HEIGHT}px (Canvas API limit)"
            )

        return width, height

    def _validate_file_size(self, file_path: Path) -> int:
        """
        Validate file size is within limit.

        Args:
            file_path: Path to file

        Returns:
            int: File size in bytes

        Raises:
            ImageValidationError: If size exceeds limit
        """
        file_size = file_path.stat().st_size

        if file_size <= 0:
            raise ImageValidationError("File is empty")

        if file_size > self.MAX_IMAGE_SIZE:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.MAX_IMAGE_SIZE / (1024 * 1024)
            raise ImageValidationError(
                f"File size {size_mb:.1f}MB exceeds maximum {max_mb:.0f}MB"
            )

        return file_size

    async def _create_temp_copy(self, source_path: Path) -> Path:
        """
        Create temporary working copy of image.

        Args:
            source_path: Source image path

        Returns:
            Path: Path to temporary copy
        """
        import shutil
        import uuid

        # Create unique temp filename
        temp_filename = f"imgcat_{uuid.uuid4().hex}{source_path.suffix}"
        temp_path = self.temp_dir / temp_filename

        # Copy file
        await asyncio.to_thread(shutil.copy2, source_path, temp_path)

        return temp_path

    async def _create_session_record(
        self,
        terminal_session_id: str,
        source_type: ImageSourceType,
        source_path: Optional[str],
        image_format: str,
        width: int,
        height: int,
        file_size: int,
        temp_file_path: str,
        db: AsyncSession
    ) -> ImageSession:
        """
        Create ImageSession database record.

        Args:
            terminal_session_id: Terminal session ID
            source_type: Source type (file, clipboard, url)
            source_path: Original source path (None for clipboard)
            image_format: Image format
            width: Image width
            height: Image height
            file_size: File size in bytes
            temp_file_path: Path to temporary working copy
            db: Database session

        Returns:
            ImageSession: Created session record
        """
        import uuid

        session = ImageSession(
            id=str(uuid.uuid4()),
            terminal_session_id=terminal_session_id,
            image_source_type=source_type.value,
            image_source_path=source_path,
            image_format=image_format,
            image_width=width,
            image_height=height,
            image_size_bytes=file_size,
            temp_file_path=temp_file_path,
            is_modified=False
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session
