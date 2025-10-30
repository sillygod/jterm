"""Ebook processing REST API endpoints.

This module provides HTTP endpoints for managing ebooks (PDF/EPUB) including:
- Processing and validating ebook files
- Retrieving ebook content
- Decrypting password-protected PDFs
- Getting metadata by file hash
"""

import os
from typing import Optional
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    status
)
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.models.ebook_metadata import EbookMetadata
from src.services.ebook_service import get_ebook_service, EbookValidationError, EbookDecryptionError, EbookProcessingError
from src.database.base import get_db

# Initialize router
router = APIRouter(prefix="/api/ebooks", tags=["Ebooks"])

# Get ebook service instance
ebook_service = get_ebook_service()


# Pydantic models for request/response validation
class ProcessEbookRequest(BaseModel):
    """Request model for ebook processing."""
    filePath: str = Field(..., description="Absolute filesystem path to ebook file")


class EbookMetadataResponse(BaseModel):
    """Response model for ebook metadata."""
    id: str
    file_path: str
    file_hash: str
    file_type: str
    file_size: int
    title: Optional[str] = None
    author: Optional[str] = None
    total_pages: Optional[int] = None
    is_encrypted: bool
    created_at: str
    last_accessed: str
    user_id: str

    class Config:
        from_attributes = True


class DecryptRequest(BaseModel):
    """Request model for PDF decryption."""
    password: str = Field(..., description="PDF password")


class DecryptResponse(BaseModel):
    """Response model for decryption result."""
    decrypted: bool
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[dict] = None


@router.post(
    "/process",
    response_model=EbookMetadataResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Ebook processed successfully"},
        400: {"description": "Invalid file (wrong type, too large, corrupted)", "model": ErrorResponse},
        404: {"description": "File not found", "model": ErrorResponse}
    },
    summary="Process and validate an ebook file"
)
async def process_ebook(
    request: ProcessEbookRequest,
    db: AsyncSession = Depends(get_db)
) -> EbookMetadataResponse:
    """
    Process and validate an ebook file.

    Validates file, extracts metadata, creates database record, returns ebook ID.

    Args:
        request: ProcessEbookRequest with filePath
        db: Database session

    Returns:
        EbookMetadataResponse with metadata

    Raises:
        HTTPException 404: If file not found
        HTTPException 400: If file invalid (wrong type, too large, etc.)
    """
    try:
        # For now, use default user ID (would come from auth in production)
        user_id = "00000000-0000-0000-0000-000000000001"

        # Process ebook
        ebook_metadata = await ebook_service.process_ebook(
            file_path=request.filePath,
            user_id=user_id,
            db=db
        )

        # Convert to response model
        return EbookMetadataResponse(
            id=ebook_metadata.id,
            file_path=ebook_metadata.file_path,
            file_hash=ebook_metadata.file_hash,
            file_type=ebook_metadata.file_type.value,
            file_size=ebook_metadata.file_size,
            title=ebook_metadata.title,
            author=ebook_metadata.author,
            total_pages=ebook_metadata.total_pages,
            is_encrypted=ebook_metadata.is_encrypted,
            created_at=ebook_metadata.created_at.isoformat(),
            last_accessed=ebook_metadata.last_accessed.isoformat(),
            user_id=ebook_metadata.user_id
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "FILE_NOT_FOUND",
                "message": str(e)
            }
        )
    except EbookValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "VALIDATION_ERROR",
                "message": str(e)
            }
        )
    except EbookProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "PROCESSING_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Unexpected error: {str(e)}"
            }
        )


@router.get(
    "/{ebook_id}/content",
    response_class=Response,
    responses={
        200: {"description": "Ebook content", "content": {"application/octet-stream": {}}},
        404: {"description": "Ebook not found", "model": ErrorResponse}
    },
    summary="Retrieve ebook content"
)
async def get_ebook_content(
    ebook_id: str = Path(..., description="Ebook ID"),
    page: Optional[int] = Query(None, ge=1, description="Page number (for PDF pagination)"),
    db: AsyncSession = Depends(get_db)
) -> Response:
    """
    Retrieve ebook file content for rendering.

    Returns ebook file content (paginated for large files).

    Args:
        ebook_id: Ebook metadata ID
        page: Optional page number for PDF pagination
        db: Database session

    Returns:
        File content as binary stream

    Raises:
        HTTPException 404: If ebook not found
    """
    try:
        # Get ebook metadata
        ebook_metadata = await ebook_service.get_ebook_by_id(ebook_id, db)

        if not ebook_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "EBOOK_NOT_FOUND",
                    "message": f"Ebook not found: {ebook_id}"
                }
            )

        # Check if PDF is encrypted and not yet decrypted
        if ebook_metadata.is_encrypted:
            # Check if decrypted content is cached
            decrypted_content = ebook_service.get_decrypted_content(ebook_id)

            if decrypted_content:
                # Return decrypted content from cache
                # Don't include filename in Content-Disposition to avoid encoding issues with non-ASCII characters
                return Response(
                    content=decrypted_content,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": "inline"
                    }
                )
            else:
                # PDF is encrypted but not decrypted yet
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={
                        "error": "ENCRYPTED_PDF",
                        "message": "PDF is password-protected. Please decrypt it first.",
                        "ebook_id": ebook_id
                    }
                )

        # Check if file still exists
        if not os.path.exists(ebook_metadata.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "FILE_NOT_FOUND",
                    "message": f"File no longer exists: {ebook_metadata.file_path}"
                }
            )

        # Return file content for non-encrypted files
        # Note: For production, consider streaming large files in chunks
        with open(ebook_metadata.file_path, 'rb') as f:
            content = f.read()

        # Determine media type based on file type
        media_type = "application/pdf" if ebook_metadata.file_type.value == "pdf" else "application/epub+zip"

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": "inline",
                "Content-Length": str(len(content))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Unexpected error: {str(e)}"
            }
        )


@router.post(
    "/{ebook_id}/decrypt",
    response_model=DecryptResponse,
    responses={
        200: {"description": "Decryption successful"},
        401: {"description": "Incorrect password", "model": ErrorResponse},
        429: {"description": "Too many password attempts", "model": ErrorResponse}
    },
    summary="Decrypt password-protected PDF"
)
async def decrypt_pdf(
    ebook_id: str = Path(..., description="Ebook ID"),
    request: DecryptRequest = ...,
    db: AsyncSession = Depends(get_db)
) -> DecryptResponse:
    """
    Decrypt password-protected PDF with provided password.

    Attempts to decrypt PDF. Limited to 3 attempts per ebook.

    Args:
        ebook_id: Ebook metadata ID
        request: DecryptRequest with password
        db: Database session

    Returns:
        DecryptResponse with success status

    Raises:
        HTTPException 401: If incorrect password
        HTTPException 429: If too many attempts
    """
    try:
        # Get ebook metadata
        ebook_metadata = await ebook_service.get_ebook_by_id(ebook_id, db)

        if not ebook_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "EBOOK_NOT_FOUND",
                    "message": f"Ebook not found: {ebook_id}"
                }
            )

        # Check if file is encrypted
        if not ebook_metadata.is_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "NOT_ENCRYPTED",
                    "message": "PDF is not encrypted"
                }
            )

        # Attempt decryption
        success = await ebook_service.decrypt_pdf(
            ebook_id=ebook_id,
            file_path=ebook_metadata.file_path,
            password=request.password
        )

        return DecryptResponse(
            decrypted=True,
            message="PDF decrypted successfully"
        )

    except EbookDecryptionError as e:
        if "Maximum decryption attempts" in str(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "TOO_MANY_ATTEMPTS",
                    "message": str(e)
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INCORRECT_PASSWORD",
                    "message": str(e)
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Unexpected error: {str(e)}"
            }
        )


@router.get(
    "/metadata/{file_hash}",
    response_model=EbookMetadataResponse,
    responses={
        200: {"description": "Metadata found"},
        404: {"description": "No cached metadata for this hash", "model": ErrorResponse}
    },
    summary="Get ebook metadata by file hash"
)
async def get_metadata_by_hash(
    file_hash: str = Path(..., pattern="^[a-f0-9]{64}$", description="SHA-256 hash of file content"),
    db: AsyncSession = Depends(get_db)
) -> EbookMetadataResponse:
    """
    Retrieve cached metadata using SHA-256 file hash.

    Args:
        file_hash: SHA-256 hash (64 hex characters)
        db: Database session

    Returns:
        EbookMetadataResponse if found

    Raises:
        HTTPException 404: If no cached metadata found
    """
    try:
        # Get ebook metadata by hash
        ebook_metadata = await ebook_service.get_ebook_by_hash(file_hash, db)

        if not ebook_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "METADATA_NOT_FOUND",
                    "message": f"No cached metadata for hash: {file_hash}"
                }
            )

        # Convert to response model
        return EbookMetadataResponse(
            id=ebook_metadata.id,
            file_path=ebook_metadata.file_path,
            file_hash=ebook_metadata.file_hash,
            file_type=ebook_metadata.file_type.value,
            file_size=ebook_metadata.file_size,
            title=ebook_metadata.title,
            author=ebook_metadata.author,
            total_pages=ebook_metadata.total_pages,
            is_encrypted=ebook_metadata.is_encrypted,
            created_at=ebook_metadata.created_at.isoformat(),
            last_accessed=ebook_metadata.last_accessed.isoformat(),
            user_id=ebook_metadata.user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Unexpected error: {str(e)}"
            }
        )
