"""Image Loader Service for loading images from various sources.

This service handles loading images from:
- File paths (local filesystem)
- URLs (HTTP/HTTPS)
- Stdin (clipboard pipe)
"""

import asyncio
import hashlib
import logging
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
            # Validate file path
            path = Path(file_path)

            # Security: Check for path traversal
            if '..' in str(path) or '~' in str(path):
                raise ImageValidationError("Path traversal detected in file path")

            # Check file exists
            if not path.exists():
                raise ImageValidationError(f"File not found: {file_path}")

            if not path.is_file():
                raise ImageValidationError(f"Path is not a file: {file_path}")

            # Validate file size
            file_size = self._validate_file_size(path)

            # Load and validate image with Pillow
            try:
                image = Image.open(path)
                image.load()  # Force load to validate format
            except Exception as e:
                raise ImageValidationError(f"Failed to load image: {str(e)}")

            # Validate format
            image_format = self._validate_image_format(image, path)

            # Validate dimensions
            width, height = self._validate_dimensions(image)

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

    async def load_from_url(
        self,
        url: str,
        terminal_session_id: str,
        db: AsyncSession,
        timeout: int = 10
    ) -> ImageSession:
        """
        Load image from URL.

        Args:
            url: HTTP/HTTPS URL to image
            terminal_session_id: Terminal session ID from jterm
            db: Database session
            timeout: Request timeout in seconds

        Returns:
            ImageSession: Created image session record

        Raises:
            ImageValidationError: If URL or image validation fails
            ImageLoaderError: If download fails
        """
        logger.info(f"Loading image from URL: {url}")

        # TODO: Implement URL loading logic
        # - Validate URL scheme (HTTP/HTTPS only)
        # - Download image with aiohttp (with size limit)
        # - Validate Content-Type header
        # - Save to temporary file
        # - Validate format, size, dimensions
        # - Create ImageSession record

        raise NotImplementedError("load_from_url not yet implemented")

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

        # TODO: Implement stdin loading logic
        # - Validate data is not empty
        # - Detect image format from magic bytes
        # - Load image with Pillow from BytesIO
        # - Validate size and dimensions
        # - Save to temporary file
        # - Create ImageSession record with source_type='clipboard'

        raise NotImplementedError("load_from_stdin not yet implemented")

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
