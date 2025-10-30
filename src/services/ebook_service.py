"""Ebook processing service for PDF and EPUB files.

This service handles ebook file validation, metadata extraction, password decryption,
and caching with SHA-256 hash-based deduplication.
"""

import asyncio
import hashlib
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from pypdf import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    try:
        # Fallback to PyPDF2 for backwards compatibility
        from PyPDF2 import PdfReader, PdfWriter
        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False

try:
    import ebooklib
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.ebook_metadata import EbookMetadata, EbookFileType
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class EbookProcessingError(Exception):
    """Base exception for ebook processing operations."""
    pass


class EbookValidationError(EbookProcessingError):
    """Raised when ebook validation fails."""
    pass


class EbookDecryptionError(EbookProcessingError):
    """Raised when PDF decryption fails."""
    pass


class EbookSizeError(EbookProcessingError):
    """Raised when ebook exceeds size limits."""
    pass


@dataclass
class EbookConfig:
    """Ebook processing configuration."""
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    max_decrypt_attempts: int = 3
    decrypt_cache_ttl: int = 3600  # 1 hour in seconds


class EbookService:
    """
    Service for processing and managing ebook files (PDF/EPUB).

    Features:
    - File validation (path, size, magic bytes)
    - SHA-256 hash calculation for caching
    - PDF metadata extraction (PyPDF2)
    - EPUB metadata extraction (ebooklib)
    - Password-protected PDF decryption
    - Database storage and retrieval
    """

    def __init__(self, config: Optional[EbookConfig] = None):
        """Initialize ebook service with configuration."""
        self.config = config or EbookConfig()
        self._decrypt_attempts: Dict[str, int] = {}  # Track password attempts per ebook_id
        self._decrypted_cache: Dict[str, Tuple[bytes, float]] = {}  # (content, expiry_time)

        if not PYPDF2_AVAILABLE:
            logger.warning("PyPDF2 not available - PDF processing will be limited")

        if not EBOOKLIB_AVAILABLE:
            logger.warning("ebooklib not available - EPUB processing will be limited")

    def validate_ebook_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate ebook file (path, size, magic bytes).

        Args:
            file_path: Absolute path to the ebook file

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            EbookValidationError: If validation fails
        """
        # Check file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        # Check it's an absolute path
        if not os.path.isabs(file_path):
            return False, "File path must be absolute"

        # Check for path traversal attempts
        if '..' in file_path or '~' in file_path:
            return False, "File path contains invalid sequences (path traversal)"

        # Check it's a file (not directory)
        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.config.max_file_size:
            size_mb = file_size / (1024 * 1024)
            limit_mb = self.config.max_file_size / (1024 * 1024)
            return False, f"File size ({size_mb:.2f}MB) exceeds limit ({limit_mb:.2f}MB)"

        if file_size == 0:
            return False, "File is empty"

        # Check magic bytes to determine file type
        try:
            with open(file_path, 'rb') as f:
                magic_bytes = f.read(4)

            # PDF magic bytes: %PDF-
            if magic_bytes.startswith(b'%PDF'):
                return True, None

            # EPUB is a ZIP file with specific structure
            # ZIP magic bytes: PK\x03\x04 or PK\x05\x06
            if magic_bytes.startswith(b'PK\x03\x04') or magic_bytes.startswith(b'PK\x05\x06'):
                # Verify it's an EPUB by checking for mimetype file
                try:
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        if 'mimetype' in zf.namelist():
                            mimetype = zf.read('mimetype').decode('utf-8').strip()
                            if mimetype == 'application/epub+zip':
                                return True, None
                except zipfile.BadZipFile:
                    return False, "Invalid ZIP/EPUB file structure"

                return False, "ZIP file is not a valid EPUB (missing or invalid mimetype)"

            return False, "File is not a valid PDF or EPUB (invalid magic bytes)"

        except Exception as e:
            logger.error(f"Error reading file magic bytes: {e}")
            return False, f"Error reading file: {str(e)}"

    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash as hexadecimal string
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    def detect_file_type(self, file_path: str) -> EbookFileType:
        """
        Detect ebook file type from magic bytes.

        Args:
            file_path: Path to the file

        Returns:
            EbookFileType enum value

        Raises:
            EbookValidationError: If file type cannot be determined
        """
        with open(file_path, 'rb') as f:
            magic_bytes = f.read(4)

        if magic_bytes.startswith(b'%PDF'):
            return EbookFileType.PDF
        elif magic_bytes.startswith(b'PK'):
            return EbookFileType.EPUB
        else:
            raise EbookValidationError(f"Unknown file type for: {file_path}")

    async def extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from PDF file using PyPDF2.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary with metadata (title, author, page_count, is_encrypted)

        Raises:
            EbookProcessingError: If PDF cannot be read
        """
        if not PYPDF2_AVAILABLE:
            raise EbookProcessingError("PyPDF2 not available")

        try:
            # Use strict=False to handle malformed PDFs more gracefully
            reader = PdfReader(file_path, strict=False)

            # Check if encrypted first (before trying to access pages)
            is_encrypted = False
            try:
                is_encrypted = reader.is_encrypted
            except Exception as e:
                logger.warning(f"Error checking encryption status: {e}")
                # Assume not encrypted if we can't check
                is_encrypted = False

            if is_encrypted:
                # For encrypted PDFs, return minimal metadata
                # Don't try to access pages or metadata until decrypted
                metadata = {
                    'title': None,
                    'author': None,
                    'total_pages': None,  # Unknown until decrypted
                    'is_encrypted': True
                }
                logger.info(f"PDF is encrypted: {file_path}")
                return metadata

            # For non-encrypted PDFs, extract full metadata
            metadata = {
                'title': None,
                'author': None,
                'total_pages': None,
                'is_encrypted': False
            }

            # Try to get page count
            try:
                metadata['total_pages'] = len(reader.pages)
            except Exception as e:
                logger.warning(f"Error getting page count: {e}")

            # Try to extract metadata if available (handle encoding errors)
            try:
                if reader.metadata:
                    # Get title with encoding fallback
                    try:
                        title = reader.metadata.get('/Title')
                        if title:
                            # Try to decode if it's bytes
                            if isinstance(title, bytes):
                                try:
                                    title = title.decode('utf-8')
                                except UnicodeDecodeError:
                                    try:
                                        title = title.decode('latin-1')
                                    except:
                                        title = None
                            metadata['title'] = title
                    except Exception as e:
                        logger.warning(f"Error extracting title: {e}")

                    # Get author with encoding fallback
                    try:
                        author = reader.metadata.get('/Author')
                        if author:
                            # Try to decode if it's bytes
                            if isinstance(author, bytes):
                                try:
                                    author = author.decode('utf-8')
                                except UnicodeDecodeError:
                                    try:
                                        author = author.decode('latin-1')
                                    except:
                                        author = None
                            metadata['author'] = author
                    except Exception as e:
                        logger.warning(f"Error extracting author: {e}")
            except Exception as e:
                logger.warning(f"Error extracting metadata: {e}")

            return metadata

        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            raise EbookProcessingError(f"Failed to read PDF: {str(e)}")

    async def extract_epub_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from EPUB file using ebooklib.

        Args:
            file_path: Path to the EPUB file

        Returns:
            Dictionary with metadata (title, author, total_pages)

        Raises:
            EbookProcessingError: If EPUB cannot be read
        """
        if not EBOOKLIB_AVAILABLE:
            raise EbookProcessingError("ebooklib not available")

        try:
            book = epub.read_epub(file_path)

            metadata = {
                'title': None,
                'author': None,
                'total_pages': None,  # EPUB doesn't have fixed pages
                'is_encrypted': False  # EPUB encryption not commonly used
            }

            # Extract metadata
            metadata['title'] = book.get_metadata('DC', 'title')
            if metadata['title']:
                metadata['title'] = metadata['title'][0][0] if metadata['title'] else None

            metadata['author'] = book.get_metadata('DC', 'creator')
            if metadata['author']:
                metadata['author'] = metadata['author'][0][0] if metadata['author'] else None

            return metadata

        except Exception as e:
            logger.error(f"Error extracting EPUB metadata: {e}")
            raise EbookProcessingError(f"Failed to read EPUB: {str(e)}")

    async def decrypt_pdf(self, ebook_id: str, file_path: str, password: str) -> bool:
        """
        Decrypt password-protected PDF with PyPDF2.

        Args:
            ebook_id: ID of the ebook record
            file_path: Path to the encrypted PDF
            password: Password to decrypt the PDF

        Returns:
            True if decryption successful

        Raises:
            EbookDecryptionError: If decryption fails or too many attempts
        """
        if not PYPDF2_AVAILABLE:
            raise EbookProcessingError("PyPDF2 not available")

        # Check attempt limit
        attempts = self._decrypt_attempts.get(ebook_id, 0)
        if attempts >= self.config.max_decrypt_attempts:
            raise EbookDecryptionError(
                f"Maximum decryption attempts ({self.config.max_decrypt_attempts}) exceeded"
            )

        try:
            # Use strict=False to handle PDFs with encoding issues
            reader = PdfReader(file_path, strict=False)

            if not reader.is_encrypted:
                raise EbookDecryptionError("PDF is not encrypted")

            # Attempt decryption
            result = reader.decrypt(password)

            if result == 0:
                # Decryption failed
                self._decrypt_attempts[ebook_id] = attempts + 1
                raise EbookDecryptionError("Incorrect password")

            # Decryption successful - cache the decrypted content
            # Create writer without strict mode to handle encoding issues
            writer = PdfWriter()

            # Copy all pages from decrypted reader to writer
            try:
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                logger.warning(f"Error copying pages, attempting alternative method: {e}")
                # Alternative: try cloning pages
                for i in range(len(reader.pages)):
                    try:
                        page = reader.pages[i]
                        writer.add_page(page)
                    except Exception as page_error:
                        logger.error(f"Failed to copy page {i}: {page_error}")
                        raise EbookDecryptionError(f"Failed to decrypt page {i}: {str(page_error)}")

            # Write to memory buffer
            from io import BytesIO
            buffer = BytesIO()
            try:
                writer.write(buffer)
            except Exception as e:
                logger.error(f"Error writing decrypted PDF: {e}")
                raise EbookDecryptionError(f"Failed to write decrypted content: {str(e)}")

            decrypted_content = buffer.getvalue()

            # Cache with expiry time
            expiry_time = datetime.now(timezone.utc).timestamp() + self.config.decrypt_cache_ttl
            self._decrypted_cache[ebook_id] = (decrypted_content, expiry_time)

            # Reset attempts on success
            self._decrypt_attempts[ebook_id] = 0

            logger.info(f"Successfully decrypted PDF: {ebook_id}")
            return True

        except EbookDecryptionError:
            raise
        except Exception as e:
            logger.error(f"Error decrypting PDF: {e}")
            self._decrypt_attempts[ebook_id] = attempts + 1
            raise EbookDecryptionError(f"Decryption failed: {str(e)}")

    def get_decrypted_content(self, ebook_id: str) -> Optional[bytes]:
        """
        Get cached decrypted PDF content.

        Args:
            ebook_id: ID of the ebook

        Returns:
            Decrypted content bytes if cached and not expired, None otherwise
        """
        if ebook_id not in self._decrypted_cache:
            return None

        content, expiry_time = self._decrypted_cache[ebook_id]

        # Check if expired
        if datetime.now(timezone.utc).timestamp() > expiry_time:
            del self._decrypted_cache[ebook_id]
            return None

        return content

    def clear_decrypt_cache(self, ebook_id: Optional[str] = None):
        """
        Clear decrypted content cache.

        Args:
            ebook_id: Specific ebook ID to clear, or None to clear all
        """
        if ebook_id:
            self._decrypted_cache.pop(ebook_id, None)
        else:
            self._decrypted_cache.clear()

    async def process_ebook(
        self,
        file_path: str,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> EbookMetadata:
        """
        Main orchestration function for ebook processing workflow.

        Steps:
        1. Validate file (path, size, magic bytes)
        2. Calculate SHA-256 hash
        3. Check cache by hash (return existing if found)
        4. Extract metadata (PDF or EPUB)
        5. Create database record
        6. Return EbookMetadata object

        Args:
            file_path: Absolute path to the ebook file
            user_id: ID of the user processing the ebook
            db: Optional database session (will create if not provided)

        Returns:
            EbookMetadata object

        Raises:
            EbookValidationError: If validation fails
            EbookProcessingError: If processing fails
        """
        # Step 1: Validate file
        is_valid, error_msg = self.validate_ebook_file(file_path)
        if not is_valid:
            raise EbookValidationError(error_msg)

        # Step 2: Calculate hash
        file_hash = self.calculate_file_hash(file_path)

        # Use provided session or create new one
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            # Step 3: Check cache by hash
            query = select(EbookMetadata).where(EbookMetadata.file_hash == file_hash)
            result = await db.execute(query)
            existing_ebook = result.scalar_one_or_none()

            if existing_ebook:
                # Update last_accessed timestamp
                existing_ebook.last_accessed = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(existing_ebook)
                logger.info(f"Returning cached ebook metadata: {existing_ebook.id}")
                return existing_ebook

            # Step 4: Extract metadata
            file_type = self.detect_file_type(file_path)
            file_size = os.path.getsize(file_path)

            if file_type == EbookFileType.PDF:
                metadata = await self.extract_pdf_metadata(file_path)
            else:  # EPUB
                metadata = await self.extract_epub_metadata(file_path)

            # Step 5: Create database record
            ebook = EbookMetadata(
                file_path=file_path,
                file_hash=file_hash,
                file_type=file_type,
                file_size=file_size,
                title=metadata.get('title'),
                author=metadata.get('author'),
                total_pages=metadata.get('total_pages'),
                is_encrypted=metadata.get('is_encrypted', False),
                user_id=user_id
            )

            db.add(ebook)
            await db.commit()
            await db.refresh(ebook)

            logger.info(f"Created new ebook metadata: {ebook.id}")

            # Step 6: Return EbookMetadata object
            return ebook

        finally:
            if close_session:
                await db.close()

    async def get_ebook_by_hash(self, file_hash: str, db: Optional[AsyncSession] = None) -> Optional[EbookMetadata]:
        """
        Retrieve ebook metadata by file hash.

        Args:
            file_hash: SHA-256 hash of the file
            db: Optional database session

        Returns:
            EbookMetadata if found, None otherwise
        """
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            query = select(EbookMetadata).where(EbookMetadata.file_hash == file_hash)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        finally:
            if close_session:
                await db.close()

    async def get_ebook_by_id(self, ebook_id: str, db: Optional[AsyncSession] = None) -> Optional[EbookMetadata]:
        """
        Retrieve ebook metadata by ID.

        Args:
            ebook_id: Ebook metadata ID
            db: Optional database session

        Returns:
            EbookMetadata if found, None otherwise
        """
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            query = select(EbookMetadata).where(EbookMetadata.id == ebook_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        finally:
            if close_session:
                await db.close()


# Global service instance
_ebook_service: Optional[EbookService] = None


def get_ebook_service() -> EbookService:
    """Get or create global ebook service instance."""
    global _ebook_service
    if _ebook_service is None:
        _ebook_service = EbookService()
    return _ebook_service
