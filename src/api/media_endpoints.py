"""Media asset upload and serving REST API endpoints.

This module provides HTTP endpoints for managing media assets including:
- Uploading media files (images, videos, HTML, documents)
- Listing and retrieving media assets
- Serving media content and thumbnails
- Deleting media assets
"""

import os
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    File,
    UploadFile,
    status
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field

from src.models.media_asset import MediaAsset, MediaType, SecurityStatus
from src.services.media_service import MediaService, MediaConfig
from src.database.base import get_db

# Initialize router
router = APIRouter(prefix="/api/v1/media", tags=["Media Assets"])

# Initialize media service (singleton)
media_service = MediaService(config=MediaConfig())


# Pydantic models for request/response validation
class MediaAssetResponse(BaseModel):
    """Response model for media asset."""
    assetId: UUID
    sessionId: UUID
    userId: UUID
    mediaType: str
    fileName: str
    filePath: str
    fileSize: int
    mimeType: str
    thumbnailPath: Optional[str]
    isTemporary: bool
    expiresAt: Optional[datetime]
    createdAt: datetime
    lastAccessedAt: Optional[datetime]
    accessCount: int
    securityStatus: str
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class MediaListResponse(BaseModel):
    """Response model for media asset list."""
    assets: List[MediaAssetResponse]
    total: int
    limit: int
    offset: int


class MediaUploadResponse(BaseModel):
    """Response model for media upload."""
    assetId: UUID
    sessionId: UUID
    mediaType: str
    fileName: str
    fileSize: int
    thumbnailPath: Optional[str]
    securityStatus: str
    processingTime: float


# Dependency to get current user ID (placeholder for auth)
async def get_current_user_id() -> UUID:
    """Get current authenticated user ID.

    TODO: Replace with actual authentication logic.
    """
    # Placeholder - in production this would verify JWT/session token
    return UUID("00000000-0000-0000-0000-000000000001")


# API Endpoints
@router.get("", response_model=MediaListResponse)
async def list_media_assets(
    sessionId: Optional[UUID] = Query(None, description="Filter by session ID"),
    mediaType: Optional[str] = Query(None, description="Filter by media type"),
    limit: int = Query(20, ge=1, le=100, description="Maximum assets to return"),
    offset: int = Query(0, ge=0, description="Number of assets to skip"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List media assets for the authenticated user.

    Args:
        sessionId: Optional session ID filter
        mediaType: Optional media type filter (image, video, html, document)
        limit: Maximum number of assets to return (1-100)
        offset: Number of assets to skip for pagination
        db: Database session
        user_id: Current user ID

    Returns:
        MediaListResponse with assets array, total count, limit, and offset
    """
    # Build query
    query = select(MediaAsset).where(MediaAsset.user_id == user_id)

    # Apply session filter if provided
    if sessionId:
        query = query.where(MediaAsset.session_id == sessionId)

    # Apply media type filter if provided
    if mediaType:
        try:
            media_type_enum = MediaType(mediaType.upper())
            query = query.where(MediaAsset.media_type == media_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid media type: {mediaType}. Valid values: image, video, html, document"
            )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and execute
    query = query.limit(limit).offset(offset).order_by(MediaAsset.created_at.desc())
    result = await db.execute(query)
    assets = result.scalars().all()

    # Convert to response models
    asset_responses = [
        MediaAssetResponse(
            assetId=a.asset_id,
            sessionId=a.session_id,
            userId=a.user_id,
            mediaType=a.media_type.value.lower(),
            fileName=a.file_name,
            filePath=a.file_path,
            fileSize=a.file_size,
            mimeType=a.mime_type,
            thumbnailPath=a.thumbnail_path,
            isTemporary=a.is_temporary,
            expiresAt=a.expires_at,
            createdAt=a.created_at,
            lastAccessedAt=a.last_accessed_at,
            accessCount=a.access_count,
            securityStatus=a.security_status.value.lower(),
            metadata=a.metadata
        )
        for a in assets
    ]

    return MediaListResponse(
        assets=asset_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_media_asset(
    file: UploadFile = File(..., description="Media file to upload"),
    sessionId: UUID = Query(..., description="Terminal session ID"),
    isTemporary: bool = Query(False, description="Whether asset should be auto-deleted"),
    expiresAt: Optional[datetime] = Query(None, description="Expiration timestamp"),
    metadata: Optional[str] = Query(None, description="JSON metadata string"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Upload a new media asset.

    Args:
        file: Media file to upload
        sessionId: Terminal session ID to associate with the asset
        isTemporary: Whether asset should be auto-deleted
        expiresAt: Optional expiration timestamp
        metadata: Optional JSON metadata string
        db: Database session
        user_id: Current user ID

    Returns:
        MediaUploadResponse with upload details

    Raises:
        HTTPException: 400 if validation fails, 413 if too large, 415 if unsupported
    """
    import json
    from datetime import timezone

    # Validate session exists
    from src.models.terminal_session import TerminalSession
    session_query = select(TerminalSession).where(
        TerminalSession.session_id == sessionId,
        TerminalSession.user_id == user_id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {sessionId} not found"
        )

    # Parse metadata if provided
    parsed_metadata = {}
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON metadata"
            )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    # Process media upload
    try:
        result = await media_service.upload_media(
            session_id=str(sessionId),
            user_id=str(user_id),
            file_name=file.filename,
            file_content=file_content,
            mime_type=file.content_type or "application/octet-stream",
            is_temporary=isTemporary,
            expires_at=expiresAt,
            metadata=parsed_metadata
        )
    except Exception as e:
        # Map specific errors to HTTP status codes
        if "size" in str(e).lower() or "too large" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(e)
            )
        elif "unsupported" in str(e).lower() or "invalid" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to upload media: {str(e)}"
            )

    # Create database record
    media_asset = MediaAsset(
        asset_id=UUID(result.asset_id),
        session_id=sessionId,
        user_id=user_id,
        media_type=MediaType.from_mime_type(file.content_type or "application/octet-stream"),
        file_name=file.filename,
        file_path=result.file_path,
        file_size=len(file_content),
        mime_type=file.content_type or "application/octet-stream",
        thumbnail_path=result.thumbnail_path,
        is_temporary=isTemporary,
        expires_at=expiresAt,
        security_status=result.security_status,
        metadata=parsed_metadata
    )

    db.add(media_asset)
    await db.commit()
    await db.refresh(media_asset)

    return MediaUploadResponse(
        assetId=media_asset.asset_id,
        sessionId=media_asset.session_id,
        mediaType=media_asset.media_type.value.lower(),
        fileName=media_asset.file_name,
        fileSize=media_asset.file_size,
        thumbnailPath=media_asset.thumbnail_path,
        securityStatus=media_asset.security_status.value.lower(),
        processingTime=result.processing_time
    )


@router.get("/{assetId}", response_model=MediaAssetResponse)
async def get_media_asset(
    assetId: UUID = Path(..., description="Media asset ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get media asset details.

    Args:
        assetId: Asset identifier
        db: Database session
        user_id: Current user ID

    Returns:
        Media asset details

    Raises:
        HTTPException: 404 if asset not found or unauthorized
    """
    from datetime import timezone

    query = select(MediaAsset).where(
        MediaAsset.asset_id == assetId,
        MediaAsset.user_id == user_id
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset {assetId} not found"
        )

    # Update access tracking
    asset.access_count += 1
    asset.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()

    return MediaAssetResponse(
        assetId=asset.asset_id,
        sessionId=asset.session_id,
        userId=asset.user_id,
        mediaType=asset.media_type.value.lower(),
        fileName=asset.file_name,
        filePath=asset.file_path,
        fileSize=asset.file_size,
        mimeType=asset.mime_type,
        thumbnailPath=asset.thumbnail_path,
        isTemporary=asset.is_temporary,
        expiresAt=asset.expires_at,
        createdAt=asset.created_at,
        lastAccessedAt=asset.last_accessed_at,
        accessCount=asset.access_count,
        securityStatus=asset.security_status.value.lower(),
        metadata=asset.metadata
    )


@router.delete("/{assetId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_asset(
    assetId: UUID = Path(..., description="Media asset ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete a media asset and its associated files.

    Args:
        assetId: Asset identifier
        db: Database session
        user_id: Current user ID

    Raises:
        HTTPException: 404 if asset not found
    """
    query = select(MediaAsset).where(
        MediaAsset.asset_id == assetId,
        MediaAsset.user_id == user_id
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset {assetId} not found"
        )

    # Delete files
    try:
        await media_service.delete_media(str(assetId))
    except Exception as e:
        # Log error but continue with database cleanup
        import logging
        logging.error(f"Error deleting media files for asset {assetId}: {e}")

    # Delete database record
    await db.delete(asset)
    await db.commit()


@router.get("/{assetId}/content")
async def get_media_content(
    assetId: UUID = Path(..., description="Media asset ID"),
    thumbnail: bool = Query(False, description="Return thumbnail instead of full content"),
    size: str = Query("medium", description="Thumbnail size (small, medium, large)"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Download media asset content.

    Args:
        assetId: Asset identifier
        thumbnail: Return thumbnail instead of full content
        size: Thumbnail size (only when thumbnail=true)
        db: Database session
        user_id: Current user ID

    Returns:
        FileResponse with media content

    Raises:
        HTTPException: 404 if asset not found or file not found
    """
    from datetime import timezone

    query = select(MediaAsset).where(
        MediaAsset.asset_id == assetId,
        MediaAsset.user_id == user_id
    )
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media asset {assetId} not found"
        )

    # Determine file path
    if thumbnail and asset.thumbnail_path:
        file_path = asset.thumbnail_path
        # Adjust thumbnail path based on size if needed
        if size != "medium":
            # Generate size-specific thumbnail
            try:
                size_map = {"small": (100, 100), "medium": (200, 200), "large": (400, 400)}
                file_path = await media_service.get_thumbnail(
                    str(assetId),
                    size=size_map.get(size, (200, 200))
                )
            except Exception as e:
                # Fall back to original thumbnail
                import logging
                logging.warning(f"Failed to get size-specific thumbnail: {e}")
    else:
        file_path = asset.file_path

    # Check file exists
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media file not found at {file_path}"
        )

    # Update access tracking
    asset.access_count += 1
    asset.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()

    # Determine content disposition
    content_disposition = "inline" if asset.media_type in [MediaType.IMAGE, MediaType.VIDEO] else "attachment"

    # Return file
    return FileResponse(
        path=file_path,
        media_type=asset.mime_type,
        filename=asset.file_name if not thumbnail else f"thumbnail_{asset.file_name}",
        headers={
            "Content-Disposition": f'{content_disposition}; filename="{asset.file_name}"'
        }
    )
