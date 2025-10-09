"""Media processing service for images, videos, and other multimedia content.

This service handles media upload, processing, thumbnails, validation, and security
scanning with performance optimization for <1s load times and secure file handling.
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum

try:
    from PIL import Image, ImageOps
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from src.models.media_asset import MediaAsset, MediaType, SecurityStatus
from src.models.terminal_session import TerminalSession
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class MediaProcessingError(Exception):
    """Base exception for media processing operations."""
    pass


class MediaValidationError(MediaProcessingError):
    """Raised when media validation fails."""
    pass


class MediaSecurityError(MediaProcessingError):
    """Raised when media fails security checks."""
    pass


class MediaSizeError(MediaProcessingError):
    """Raised when media exceeds size limits."""
    pass


@dataclass
class MediaConfig:
    """Media processing configuration."""
    upload_dir: str = "./uploads"
    thumbnail_dir: str = "./thumbnails"
    temp_dir: str = "./temp"
    max_image_size: int = 10 * 1024 * 1024  # 10MB
    max_video_size: int = 50 * 1024 * 1024  # 50MB
    max_html_size: int = 5 * 1024 * 1024    # 5MB
    max_document_size: int = 10 * 1024 * 1024  # 10MB
    thumbnail_size: Tuple[int, int] = (200, 200)
    image_quality: int = 85
    enable_security_scan: bool = True
    cleanup_temp_after: int = 3600  # 1 hour
    enable_ffmpeg: bool = True


@dataclass
class ProcessingResult:
    """Result of media processing operation."""
    asset_id: str
    file_path: str
    thumbnail_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    processing_time: float = 0.0
    security_status: SecurityStatus = SecurityStatus.SAFE
    errors: List[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []


class MediaValidator:
    """Handles media file validation and security checks."""

    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
    ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv'}
    ALLOWED_HTML_EXTENSIONS = {'.html', '.htm'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.txt', '.md'}

    DANGEROUS_PATTERNS = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'data:text/html',
        b'<iframe',
        b'<object',
        b'<embed',
        b'<link',
        b'<meta'
    ]

    @classmethod
    async def validate_file(cls, file_path: Path, mime_type: str, media_type: MediaType) -> SecurityStatus:
        """Validate file security and format."""
        try:
            # Check file extension
            extension = file_path.suffix.lower()
            if not cls._is_extension_allowed(extension, media_type):
                logger.warning(f"Disallowed file extension: {extension}")
                return SecurityStatus.SUSPICIOUS

            # Check MIME type consistency
            if not cls._is_mime_type_consistent(mime_type, extension):
                logger.warning(f"MIME type mismatch: {mime_type} vs {extension}")
                return SecurityStatus.SUSPICIOUS

            # Scan file content for dangerous patterns
            security_status = await cls._scan_file_content(file_path, media_type)

            return security_status

        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            return SecurityStatus.ERROR

    @classmethod
    def _is_extension_allowed(cls, extension: str, media_type: MediaType) -> bool:
        """Check if file extension is allowed for media type."""
        if media_type == MediaType.IMAGE:
            return extension in cls.ALLOWED_IMAGE_EXTENSIONS
        elif media_type == MediaType.VIDEO:
            return extension in cls.ALLOWED_VIDEO_EXTENSIONS
        elif media_type == MediaType.HTML:
            return extension in cls.ALLOWED_HTML_EXTENSIONS
        elif media_type == MediaType.DOCUMENT:
            return extension in cls.ALLOWED_DOCUMENT_EXTENSIONS
        return False

    @classmethod
    def _is_mime_type_consistent(cls, mime_type: str, extension: str) -> bool:
        """Check if MIME type is consistent with file extension."""
        expected_mime = mimetypes.guess_type(f"file{extension}")[0]
        return expected_mime == mime_type or mime_type.startswith(expected_mime.split('/')[0] if expected_mime else '')

    @classmethod
    async def _scan_file_content(cls, file_path: Path, media_type: MediaType) -> SecurityStatus:
        """Scan file content for dangerous patterns."""
        try:
            # Read first 8KB for pattern matching
            with open(file_path, 'rb') as f:
                content = f.read(8192)

            # Check for dangerous patterns
            content_lower = content.lower()
            for pattern in cls.DANGEROUS_PATTERNS:
                if pattern in content_lower:
                    logger.warning(f"Dangerous pattern found in {file_path}: {pattern}")
                    return SecurityStatus.MALICIOUS

            # Media-specific validation
            if media_type == MediaType.IMAGE:
                return await cls._validate_image_content(file_path)
            elif media_type == MediaType.VIDEO:
                return await cls._validate_video_content(file_path)
            elif media_type == MediaType.HTML:
                return await cls._validate_html_content(file_path)

            return SecurityStatus.SAFE

        except Exception as e:
            logger.error(f"Error scanning file content: {e}")
            return SecurityStatus.ERROR

    @classmethod
    async def _validate_image_content(cls, file_path: Path) -> SecurityStatus:
        """Validate image file content."""
        if not PILLOW_AVAILABLE:
            return SecurityStatus.SAFE

        try:
            with Image.open(file_path) as img:
                # Verify it's a valid image
                img.verify()
                return SecurityStatus.SAFE
        except Exception as e:
            logger.warning(f"Invalid image file {file_path}: {e}")
            return SecurityStatus.SUSPICIOUS

    @classmethod
    async def _validate_video_content(cls, file_path: Path) -> SecurityStatus:
        """Validate video file content using ffprobe."""
        try:
            # Use ffprobe to validate video
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(file_path)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return SecurityStatus.SAFE
            else:
                logger.warning(f"Invalid video file {file_path}: {stderr.decode()}")
                return SecurityStatus.SUSPICIOUS

        except FileNotFoundError:
            # ffprobe not available, skip validation
            return SecurityStatus.SAFE
        except Exception as e:
            logger.error(f"Error validating video {file_path}: {e}")
            return SecurityStatus.ERROR

    @classmethod
    async def _validate_html_content(cls, file_path: Path) -> SecurityStatus:
        """Validate HTML content for security."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000)  # Read first 50KB

            content_lower = content.lower()

            # Enhanced dangerous pattern check for HTML
            html_dangerous_patterns = [
                '<script',
                'javascript:',
                'vbscript:',
                'onload=',
                'onerror=',
                'onclick=',
                'onmouseover=',
                '<iframe',
                '<object',
                '<embed',
                '<form',
                'document.cookie',
                'document.write',
                'eval(',
                'setinterval(',
                'settimeout('
            ]

            for pattern in html_dangerous_patterns:
                if pattern in content_lower:
                    logger.warning(f"Dangerous HTML pattern found: {pattern}")
                    return SecurityStatus.MALICIOUS

            return SecurityStatus.SAFE

        except Exception as e:
            logger.error(f"Error validating HTML content: {e}")
            return SecurityStatus.ERROR


class ThumbnailGenerator:
    """Handles thumbnail generation for various media types."""

    @staticmethod
    async def generate_image_thumbnail(source_path: Path, output_path: Path,
                                     size: Tuple[int, int] = (200, 200),
                                     quality: int = 85) -> bool:
        """Generate thumbnail for image files."""
        if not PILLOW_AVAILABLE:
            return False

        try:
            with Image.open(source_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background

                # Generate thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(output_path, 'JPEG', quality=quality, optimize=True)

            return True

        except Exception as e:
            logger.error(f"Error generating image thumbnail: {e}")
            return False

    @staticmethod
    async def generate_video_thumbnail(source_path: Path, output_path: Path,
                                     size: Tuple[int, int] = (200, 200),
                                     timestamp: str = "00:00:01") -> bool:
        """Generate thumbnail for video files using ffmpeg."""
        try:
            cmd = [
                'ffmpeg', '-i', str(source_path),
                '-ss', timestamp,
                '-vframes', '1',
                '-vf', f'scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease,pad={size[0]}:{size[1]}:(ow-iw)/2:(oh-ih)/2',
                '-y', str(output_path)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return True
            else:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return False

        except FileNotFoundError:
            # ffmpeg not available
            logger.warning("FFmpeg not available for video thumbnail generation")
            return False
        except Exception as e:
            logger.error(f"Error generating video thumbnail: {e}")
            return False


class MediaMetadataExtractor:
    """Extracts metadata from various media types."""

    @staticmethod
    async def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
        """Extract metadata from image files."""
        metadata = {}

        if not PILLOW_AVAILABLE:
            return metadata

        try:
            with Image.open(file_path) as img:
                metadata.update({
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                })

                # Extract EXIF data if available
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        # Basic EXIF data (be careful about privacy)
                        safe_exif = {}
                        for tag_id in [0x0112, 0x0132, 0x010f, 0x0110]:  # Orientation, DateTime, Make, Model
                            if tag_id in exif:
                                safe_exif[str(tag_id)] = str(exif[tag_id])
                        if safe_exif:
                            metadata['exif'] = safe_exif

        except Exception as e:
            logger.error(f"Error extracting image metadata: {e}")

        return metadata

    @staticmethod
    async def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
        """Extract metadata from video files using ffprobe."""
        metadata = {}

        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(file_path)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                import json
                probe_data = json.loads(stdout.decode())

                # Extract basic format info
                if 'format' in probe_data:
                    format_info = probe_data['format']
                    metadata.update({
                        'duration': float(format_info.get('duration', 0)),
                        'bit_rate': int(format_info.get('bit_rate', 0)),
                        'size': int(format_info.get('size', 0))
                    })

                # Extract video stream info
                for stream in probe_data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        metadata.update({
                            'width': stream.get('width'),
                            'height': stream.get('height'),
                            'codec': stream.get('codec_name'),
                            'fps': eval(stream.get('r_frame_rate', '0/1')) if stream.get('r_frame_rate') else 0
                        })
                        break

        except FileNotFoundError:
            logger.warning("FFprobe not available for video metadata extraction")
        except Exception as e:
            logger.error(f"Error extracting video metadata: {e}")

        return metadata


class MediaService:
    """Main service for media processing operations."""

    def __init__(self, config: MediaConfig = None):
        self.config = config or MediaConfig()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        for directory in [self.config.upload_dir, self.config.thumbnail_dir, self.config.temp_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)

    async def upload_media(self, file_data: bytes, filename: str, mime_type: str,
                          session_id: str, user_id: str,
                          is_temporary: bool = False,
                          expires_hours: int = 24) -> ProcessingResult:
        """Upload and process media file."""
        start_time = time.time()

        try:
            # Determine media type
            media_type = self._determine_media_type(mime_type, filename)

            # Validate file size
            self._validate_file_size(len(file_data), media_type)

            # Create temporary file
            temp_file = await self._create_temp_file(file_data, filename)

            try:
                # Security validation
                security_status = await MediaValidator.validate_file(temp_file, mime_type, media_type)

                if security_status == SecurityStatus.MALICIOUS:
                    raise MediaSecurityError("File failed security validation")

                # Generate unique filename
                file_hash = hashlib.sha256(file_data).hexdigest()[:16]
                extension = Path(filename).suffix
                unique_filename = f"{file_hash}_{int(time.time())}{extension}"

                # Move to upload directory
                final_path = Path(self.config.upload_dir) / unique_filename
                shutil.move(str(temp_file), str(final_path))

                # Extract metadata
                metadata = await self._extract_metadata(final_path, media_type)

                # Generate thumbnail
                thumbnail_path = await self._generate_thumbnail(final_path, unique_filename, media_type)

                # Create database record
                asset = await self._create_media_asset(
                    session_id=session_id,
                    user_id=user_id,
                    filename=filename,
                    file_path=str(final_path),
                    file_size=len(file_data),
                    mime_type=mime_type,
                    media_type=media_type,
                    thumbnail_path=thumbnail_path,
                    metadata=metadata,
                    security_status=security_status,
                    is_temporary=is_temporary,
                    expires_hours=expires_hours
                )

                processing_time = time.time() - start_time

                logger.info(f"Media uploaded successfully: {asset.asset_id} ({processing_time:.2f}s)")

                return ProcessingResult(
                    asset_id=asset.asset_id,
                    file_path=str(final_path),
                    thumbnail_path=thumbnail_path,
                    metadata=metadata,
                    processing_time=processing_time,
                    security_status=security_status
                )

            finally:
                # Clean up temp file if it still exists
                if temp_file.exists():
                    temp_file.unlink()

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error uploading media: {e} ({processing_time:.2f}s)")

            return ProcessingResult(
                asset_id="",
                file_path="",
                processing_time=processing_time,
                errors=[str(e)]
            )

    async def get_media_asset(self, asset_id: str) -> Optional[MediaAsset]:
        """Get media asset by ID."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(MediaAsset).where(MediaAsset.asset_id == asset_id)
            )
            asset = result.scalar_one_or_none()

            if asset:
                # Record access
                asset.record_access()
                await db.commit()

            return asset

    async def delete_media_asset(self, asset_id: str, user_id: str) -> bool:
        """Delete media asset."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(MediaAsset).where(
                    MediaAsset.asset_id == asset_id,
                    MediaAsset.user_id == user_id
                )
            )
            asset = result.scalar_one_or_none()

            if not asset:
                return False

            # Delete files
            try:
                if asset.file_path and Path(asset.file_path).exists():
                    Path(asset.file_path).unlink()

                if asset.thumbnail_path and Path(asset.thumbnail_path).exists():
                    Path(asset.thumbnail_path).unlink()
            except Exception as e:
                logger.error(f"Error deleting files for asset {asset_id}: {e}")

            # Delete database record
            await db.delete(asset)
            await db.commit()

            logger.info(f"Deleted media asset: {asset_id}")
            return True

    async def cleanup_expired_assets(self) -> int:
        """Clean up expired temporary assets."""
        async with AsyncSessionLocal() as db:
            # Find expired assets
            result = await db.execute(
                select(MediaAsset).where(
                    MediaAsset.is_temporary == True,
                    MediaAsset.expires_at <= datetime.now(timezone.utc)
                )
            )
            expired_assets = result.scalars().all()

            cleaned_count = 0
            for asset in expired_assets:
                try:
                    # Delete files
                    if asset.file_path and Path(asset.file_path).exists():
                        Path(asset.file_path).unlink()

                    if asset.thumbnail_path and Path(asset.thumbnail_path).exists():
                        Path(asset.thumbnail_path).unlink()

                    # Delete database record
                    await db.delete(asset)
                    cleaned_count += 1

                except Exception as e:
                    logger.error(f"Error cleaning up expired asset {asset.asset_id}: {e}")

            await db.commit()

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired media assets")

            return cleaned_count

    async def get_session_media(self, session_id: str, limit: int = 50) -> List[MediaAsset]:
        """Get media assets for a session."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(MediaAsset)
                .where(MediaAsset.session_id == session_id)
                .order_by(MediaAsset.uploaded_at.desc())
                .limit(limit)
            )
            return result.scalars().all()

    def _determine_media_type(self, mime_type: str, filename: str) -> MediaType:
        """Determine media type from MIME type and filename."""
        if mime_type.startswith('image/'):
            return MediaType.IMAGE
        elif mime_type.startswith('video/'):
            return MediaType.VIDEO
        elif mime_type in ['text/html', 'application/xhtml+xml']:
            return MediaType.HTML
        elif mime_type in ['application/pdf', 'text/plain', 'text/markdown']:
            return MediaType.DOCUMENT
        else:
            # Fallback to extension
            extension = Path(filename).suffix.lower()
            if extension in MediaValidator.ALLOWED_IMAGE_EXTENSIONS:
                return MediaType.IMAGE
            elif extension in MediaValidator.ALLOWED_VIDEO_EXTENSIONS:
                return MediaType.VIDEO
            elif extension in MediaValidator.ALLOWED_HTML_EXTENSIONS:
                return MediaType.HTML
            else:
                return MediaType.DOCUMENT

    def _validate_file_size(self, file_size: int, media_type: MediaType):
        """Validate file size against limits."""
        limits = {
            MediaType.IMAGE: self.config.max_image_size,
            MediaType.VIDEO: self.config.max_video_size,
            MediaType.HTML: self.config.max_html_size,
            MediaType.DOCUMENT: self.config.max_document_size
        }

        limit = limits.get(media_type, self.config.max_document_size)

        if file_size > limit:
            raise MediaSizeError(f"File size {file_size} exceeds limit {limit} for {media_type}")

    async def _create_temp_file(self, file_data: bytes, filename: str) -> Path:
        """Create temporary file from uploaded data."""
        suffix = Path(filename).suffix
        temp_file = Path(self.config.temp_dir) / f"upload_{int(time.time())}_{hash(filename) % 10000}{suffix}"

        with open(temp_file, 'wb') as f:
            f.write(file_data)

        return temp_file

    async def _extract_metadata(self, file_path: Path, media_type: MediaType) -> Dict[str, Any]:
        """Extract metadata from media file."""
        try:
            if media_type == MediaType.IMAGE:
                return await MediaMetadataExtractor.extract_image_metadata(file_path)
            elif media_type == MediaType.VIDEO:
                return await MediaMetadataExtractor.extract_video_metadata(file_path)
            else:
                return {}
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}

    async def _generate_thumbnail(self, file_path: Path, filename: str, media_type: MediaType) -> Optional[str]:
        """Generate thumbnail for media file."""
        try:
            if media_type not in [MediaType.IMAGE, MediaType.VIDEO]:
                return None

            thumbnail_name = f"thumb_{Path(filename).stem}.jpg"
            thumbnail_path = Path(self.config.thumbnail_dir) / thumbnail_name

            success = False
            if media_type == MediaType.IMAGE:
                success = await ThumbnailGenerator.generate_image_thumbnail(
                    file_path, thumbnail_path, self.config.thumbnail_size
                )
            elif media_type == MediaType.VIDEO:
                success = await ThumbnailGenerator.generate_video_thumbnail(
                    file_path, thumbnail_path, self.config.thumbnail_size
                )

            return str(thumbnail_path) if success else None

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None

    async def _create_media_asset(self, **kwargs) -> MediaAsset:
        """Create media asset database record."""
        async with AsyncSessionLocal() as db:
            # Set expiration if temporary
            expires_at = None
            if kwargs.get('is_temporary'):
                expires_at = datetime.now(timezone.utc) + timedelta(hours=kwargs.get('expires_hours', 24))

            # Get dimensions from metadata
            dimensions = None
            metadata = kwargs.get('metadata', {})
            if metadata.get('width') and metadata.get('height'):
                dimensions = {'width': metadata['width'], 'height': metadata['height']}

            asset = MediaAsset(
                session_id=kwargs['session_id'],
                user_id=kwargs['user_id'],
                file_name=kwargs['filename'],
                file_path=kwargs['file_path'],
                file_size=kwargs['file_size'],
                mime_type=kwargs['mime_type'],
                media_type=kwargs['media_type'],
                dimensions=dimensions,
                duration=metadata.get('duration'),
                thumbnail_path=kwargs.get('thumbnail_path'),
                is_temporary=kwargs.get('is_temporary', False),
                expires_at=expires_at,
                metadata=metadata
            )

            # Set security scan results
            asset.update_security_scan(kwargs.get('security_status', SecurityStatus.SAFE))

            db.add(asset)
            await db.commit()
            await db.refresh(asset)

            return asset


# Global service instance
media_service = MediaService()


async def get_media_service() -> MediaService:
    """Dependency injection for media service."""
    return media_service