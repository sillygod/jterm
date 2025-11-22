"""Image Editor REST API endpoints.

This module provides HTTP endpoints for image editing operations including:
- Loading images from various sources
- Applying filters and transformations
- Managing annotation layers
- Undo/redo operations
- Session history management
"""

import logging
import time
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    Body,
    status
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.database.base import get_db
from src.services.image_loader_service import ImageLoaderService
from src.services.image_editor_service import (
    ImageEditorService,
    ImageEditorError,
    SessionNotFoundError
)
from src.services.session_history_service import SessionHistoryService


logger = logging.getLogger(__name__)


# Initialize router
router = APIRouter(prefix="/api/v1/image-editor", tags=["Image Editor"])


# Initialize services (singletons)
image_loader_service = ImageLoaderService()
image_editor_service = ImageEditorService()
session_history_service = SessionHistoryService()


# ==================== Request/Response Models ====================


class LoadImageRequest(BaseModel):
    """Request model for loading an image."""
    source_type: str = Field(..., description="Source type: file, url, clipboard")
    source_path: Optional[str] = Field(None, description="File path or URL (null for clipboard)")
    clipboard_data: Optional[str] = Field(None, description="Base64 encoded clipboard data")
    terminal_session_id: str = Field(..., description="Terminal session ID")


class LoadImageResponse(BaseModel):
    """Response model for image load."""
    session_id: str = Field(..., description="Image session ID")
    editor_url: str = Field(..., description="URL to editor interface")
    image_width: int = Field(..., description="Image width in pixels")
    image_height: int = Field(..., description="Image height in pixels")
    image_format: str = Field(..., description="Image format")


class UpdateAnnotationRequest(BaseModel):
    """Request model for updating annotation layer."""
    canvas_json: str = Field(..., description="Fabric.js canvas JSON")
    version: int = Field(..., description="Current version (optimistic locking)")


class UpdateAnnotationResponse(BaseModel):
    """Response model for annotation update."""
    new_version: int = Field(..., description="New version number")
    updated_at: str = Field(..., description="Update timestamp")


class ApplyFilterRequest(BaseModel):
    """Request model for applying filter."""
    filter_type: str = Field(..., description="Filter type: blur, sharpen")
    parameters: Dict[str, Any] = Field(..., description="Filter parameters")


class ApplyFilterResponse(BaseModel):
    """Response model for filter application."""
    processed_image_url: str = Field(..., description="URL to processed image")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class ProcessImageRequest(BaseModel):
    """Request model for image processing operations."""
    operation: str = Field(..., description="Operation: crop, resize, blur, sharpen")
    parameters: Dict[str, Any] = Field(..., description="Operation-specific parameters")


class ProcessImageResponse(BaseModel):
    """Response model for image processing."""
    session_id: str
    operation: str
    processed_image_url: str
    new_dimensions: Optional[Dict[str, int]] = None


class SaveImageRequest(BaseModel):
    """Request model for saving image."""
    output_path: str = Field(..., description="Target file path")


class SaveImageResponse(BaseModel):
    """Response model for save operation."""
    saved_path: str = Field(..., description="Saved file path")
    file_size: int = Field(..., description="File size in bytes")


class HistoryEntryResponse(BaseModel):
    """Response model for history entry."""
    id: str
    image_path: str
    source_type: str
    thumbnail_path: Optional[str]
    last_viewed_at: str
    view_count: int
    is_edited: bool


class HistoryListResponse(BaseModel):
    """Response model for history list."""
    entries: List[HistoryEntryResponse]
    total: int


class CropImageRequest(BaseModel):
    """Request model for cropping image."""
    x: int = Field(..., description="Left coordinate", ge=0)
    y: int = Field(..., description="Top coordinate", ge=0)
    width: int = Field(..., description="Crop width", gt=0)
    height: int = Field(..., description="Crop height", gt=0)


class CropImageResponse(BaseModel):
    """Response model for crop operation."""
    session_id: str
    image_width: int
    image_height: int
    is_modified: bool


class ResizeImageRequest(BaseModel):
    """Request model for resizing image."""
    width: int = Field(..., description="Target width", gt=0)
    height: int = Field(..., description="Target height", gt=0)
    maintain_aspect_ratio: bool = Field(False, description="Maintain aspect ratio")


class ResizeImageResponse(BaseModel):
    """Response model for resize operation."""
    session_id: str
    image_width: int
    image_height: int
    is_modified: bool
    scale_x: float
    scale_y: float


# ==================== Endpoints ====================


@router.post("/load", response_model=LoadImageResponse, status_code=status.HTTP_201_CREATED)
async def load_image(
    request: LoadImageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Load an image from file, URL, or clipboard.

    Creates an ImageSession and initializes annotation layer.
    """
    logger.info(f"Load image request: source_type={request.source_type}")

    try:
        # Load image based on source type
        if request.source_type == "file":
            if not request.source_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_path is required for file source"
                )

            # Load from file
            image_session = await image_loader_service.load_from_file(
                file_path=request.source_path,
                terminal_session_id=request.terminal_session_id,
                db=db
            )

        elif request.source_type == "url":
            # T110: Add URL source handling
            if not request.source_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_path is required for url source"
                )

            # Load from URL
            from src.services.image_loader_service import ImageValidationError, ImageLoaderError
            try:
                image_session = await image_loader_service.load_from_url(
                    url=request.source_path,
                    terminal_session_id=request.terminal_session_id,
                    db=db
                )
            except ImageValidationError as e:
                # T113: Handle validation errors (invalid URL, private IPs, wrong content type)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except ImageLoaderError as e:
                # T113: Handle connection/timeout errors
                error_msg = str(e).lower()
                if 'timeout' in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail=f"Request timeout: {str(e)}"
                    )
                elif 'connection' in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Connection error: {str(e)}"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=str(e)
                    )

        elif request.source_type == "clipboard":
            if not request.clipboard_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="clipboard_data is required for clipboard source"
                )

            # Decode base64 clipboard data
            import base64
            try:
                clipboard_bytes = base64.b64decode(request.clipboard_data)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid clipboard_data encoding: {str(e)}"
                )

            # Load from clipboard (stdin data)
            from src.services.image_loader_service import ImageValidationError, ImageLoaderError
            try:
                image_session = await image_loader_service.load_from_stdin(
                    stdin_data=clipboard_bytes,
                    terminal_session_id=request.terminal_session_id,
                    db=db
                )
            except ImageValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except ImageLoaderError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source_type: {request.source_type}"
            )

        # Create annotation layer
        annotation_layer = await image_editor_service.create_session(
            image_session=image_session,
            db=db
        )

        # Add to session history (T096)
        await session_history_service.add_to_history(
            terminal_session_id=request.terminal_session_id,
            image_path=image_session.image_source_path,
            db=db,
            image_source_type=image_session.image_source_type
        )

        # Generate editor URL
        editor_url = f"/editor/{image_session.id}"

        # Return response
        return LoadImageResponse(
            session_id=image_session.id,
            editor_url=editor_url,
            image_width=image_session.image_width,
            image_height=image_session.image_height,
            image_format=image_session.image_format
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load image: {str(e)}"
        )


@router.put("/annotation-layer/{session_id}", response_model=UpdateAnnotationResponse)
async def update_annotation_layer(
    session_id: str = Path(..., description="Image session ID"),
    request: UpdateAnnotationRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Update annotation layer with new canvas state.

    Supports optimistic locking via version field.
    """
    logger.info(f"Update annotation layer for session: {session_id}")

    try:
        # Validate JSON
        import json
        try:
            json.loads(request.canvas_json)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid canvas JSON: {str(e)}"
            )

        # Check current version (optimistic locking)
        from sqlalchemy import select
        from src.models.image_editor import AnnotationLayer

        query = select(AnnotationLayer).where(AnnotationLayer.session_id == session_id)
        result = await db.execute(query)
        annotation_layer = result.scalar_one_or_none()

        if not annotation_layer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        # Verify version for optimistic locking
        if annotation_layer.version != request.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Version conflict: expected {annotation_layer.version}, got {request.version}"
            )

        # Update annotation layer
        new_version = await image_editor_service.update_annotation_layer(
            session_id=session_id,
            canvas_json=request.canvas_json,
            db=db
        )

        return UpdateAnnotationResponse(
            new_version=new_version,
            updated_at=datetime.now(timezone.utc).isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating annotation layer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update annotation layer: {str(e)}"
        )


@router.post("/crop/{session_id}", response_model=CropImageResponse)
async def crop_image_endpoint(
    session_id: str = Path(..., description="Image session ID"),
    request: CropImageRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Crop image to specified bounds.

    Applies crop operation and updates image dimensions.
    """
    logger.info(f"Crop image session {session_id}: ({request.x}, {request.y}, {request.width}x{request.height})")

    try:
        from src.services.image_editor_service import SessionNotFoundError, ImageEditorError

        result = await image_editor_service.crop_image(
            session_id=session_id,
            x=request.x,
            y=request.y,
            width=request.width,
            height=request.height,
            db=db
        )

        return CropImageResponse(**result)

    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ImageEditorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cropping image session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to crop image: {str(e)}"
        )


@router.post("/resize/{session_id}", response_model=ResizeImageResponse)
async def resize_image_endpoint(
    session_id: str = Path(..., description="Image session ID"),
    request: ResizeImageRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Resize image to specified dimensions.

    Supports aspect ratio locking and high-quality LANCZOS resampling.
    """
    logger.info(f"Resize image session {session_id}: {request.width}x{request.height}, aspect={request.maintain_aspect_ratio}")

    try:
        from src.services.image_editor_service import SessionNotFoundError, ImageEditorError

        result = await image_editor_service.resize_image(
            session_id=session_id,
            width=request.width,
            height=request.height,
            maintain_aspect_ratio=request.maintain_aspect_ratio,
            db=db
        )

        return ResizeImageResponse(**result)

    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ImageEditorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error resizing image session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resize image: {str(e)}"
        )


@router.post("/process/{session_id}", response_model=ProcessImageResponse)
async def process_image(
    session_id: str = Path(..., description="Image session ID"),
    request: ProcessImageRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Process image with operation (crop, resize, blur, sharpen).

    Supports multiple operations types with operation-specific parameters.
    """
    logger.info(f"Process image session {session_id}: operation={request.operation}")

    try:
        operation = request.operation.lower()
        parameters = request.parameters

        # Route to appropriate service method based on operation
        if operation == "blur":
            # T085: Apply blur filter
            radius = parameters.get("radius")
            if radius is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameter: radius"
                )

            result = await image_editor_service.apply_blur(
                session_id=session_id,
                radius=float(radius),
                db=db
            )

            # Build processed image URL
            processed_url = f"/api/v1/image-editor/image/{session_id}?v={int(time.time())}"

            return ProcessImageResponse(
                session_id=session_id,
                operation="blur",
                processed_image_url=processed_url,
                new_dimensions={
                    "width": result["width"],
                    "height": result["height"]
                }
            )

        elif operation == "sharpen":
            # T086: Apply sharpen filter
            amount = parameters.get("amount") or parameters.get("intensity")
            if amount is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required parameter: amount or intensity"
                )

            result = await image_editor_service.apply_sharpen(
                session_id=session_id,
                amount=float(amount),
                db=db
            )

            # Build processed image URL
            processed_url = f"/api/v1/image-editor/image/{session_id}?v={int(time.time())}"

            return ProcessImageResponse(
                session_id=session_id,
                operation="sharpen",
                processed_image_url=processed_url,
                new_dimensions={
                    "width": result["width"],
                    "height": result["height"]
                }
            )

        elif operation == "crop":
            # Future: implement crop operation
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Crop operation should use /crop endpoint"
            )

        elif operation == "resize":
            # Future: implement resize operation
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Resize operation should use /resize endpoint"
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {operation}. Supported: blur, sharpen"
            )

    except ValueError as e:
        logger.error(f"Invalid parameter for {request.operation}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SessionNotFoundError as e:
        logger.error(f"Session not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ImageEditorError as e:
        logger.error(f"Image processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during processing"
        )


@router.post("/save/{session_id}", response_model=SaveImageResponse)
async def save_image(
    session_id: str = Path(..., description="Image session ID"),
    request: SaveImageRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Save edited image to filesystem.

    Applies annotations and saves final image.
    For clipboard sources, requires output_path to be specified.
    """
    logger.info(f"Save image session {session_id} to: {request.output_path}")

    try:
        # Load session to check source type
        from sqlalchemy import select
        from src.models.image_editor import ImageSession

        query = select(ImageSession).where(ImageSession.id == session_id)
        result = await db.execute(query)
        image_session = result.scalar_one_or_none()

        if not image_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image session not found: {session_id}"
            )

        # Validate output_path is provided (required for clipboard sources)
        if not request.output_path or not request.output_path.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="output_path is required to save the image"
            )

        # Validate path safety
        import os
        output_path = request.output_path.strip()

        # Security: Ensure absolute path or relative to safe directory
        if not os.path.isabs(output_path):
            # If relative, make it relative to user's home directory or cwd
            # For clipboard sources, default to Downloads or current directory
            from pathlib import Path
            output_path = str(Path.cwd() / output_path)

        # Call service to save image
        from src.services.image_editor_service import SessionNotFoundError, ImageEditorError

        try:
            saved_path = await image_editor_service.save_image(
                session_id=session_id,
                output_path=output_path,
                db=db
            )
        except SessionNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ImageEditorError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

        # Get file size
        from pathlib import Path
        file_size = Path(saved_path).stat().st_size

        return SaveImageResponse(
            saved_path=saved_path,
            file_size=file_size
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving image session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save image: {str(e)}"
        )


@router.post("/export-clipboard/{session_id}")
async def export_to_clipboard(
    session_id: str = Path(..., description="Image session ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Prepare image for clipboard export.

    Returns temporary URL for clipboard operation (30s expiry).
    """
    logger.info(f"Export to clipboard for session: {session_id}")

    # TODO: Implement clipboard export logic
    # - Generate temporary URL
    # - Return URL with expiry time

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="export_to_clipboard endpoint not yet implemented"
    )


@router.post("/undo/{session_id}")
async def undo_operation(
    session_id: str = Path(..., description="Image session ID"),
    current_position: int = Query(..., description="Current undo/redo position"),
    db: AsyncSession = Depends(get_db)
):
    """
    Undo last edit operation.

    Returns previous canvas snapshot.
    """
    logger.info(f"Undo operation for session {session_id} at position {current_position}")

    # TODO: Implement undo logic
    # - Get previous snapshot from edit_operations
    # - Return canvas JSON and new position

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="undo_operation endpoint not yet implemented"
    )


@router.post("/redo/{session_id}")
async def redo_operation(
    session_id: str = Path(..., description="Image session ID"),
    current_position: int = Query(..., description="Current undo/redo position"),
    db: AsyncSession = Depends(get_db)
):
    """
    Redo previously undone operation.

    Returns next canvas snapshot.
    """
    logger.info(f"Redo operation for session {session_id} at position {current_position}")

    # TODO: Implement redo logic
    # - Get next snapshot from edit_operations
    # - Return canvas JSON and new position

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="redo_operation endpoint not yet implemented"
    )


@router.get("/history")
async def get_session_history(
    terminal_session_id: str = Query(..., description="Terminal session ID"),
    limit: int = Query(20, ge=1, le=50, description="Maximum entries to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get session history for terminal session.

    Returns list of recently viewed/edited images.
    """
    logger.info(f"Get history for terminal session: {terminal_session_id}, limit: {limit}")

    try:
        # Get history entries from service
        entries = await session_history_service.get_history(
            terminal_session_id=terminal_session_id,
            limit=limit,
            db=db
        )

        # Convert to response format
        history_entries = []
        for entry in entries:
            history_entries.append({
                "id": entry.id,
                "image_path": entry.image_path,
                "last_viewed_at": entry.last_viewed_at.isoformat(),
                "view_count": entry.view_count
            })

        return {
            "history": history_entries,
            "total": len(history_entries)
        }

    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.post("/history/{entry_id}/reopen", response_model=LoadImageResponse)
async def reopen_from_history(
    entry_id: str = Path(..., description="History entry ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Reopen image from session history.

    Loads image and creates new editing session.
    """
    logger.info(f"Reopen from history: {entry_id}")

    try:
        # Get history entry
        history_entry = await session_history_service.get_entry_by_id(
            entry_id=entry_id,
            db=db
        )

        if not history_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"History entry not found: {entry_id}"
            )

        # Load image from stored path
        image_session = await image_loader_service.load_from_file(
            file_path=history_entry.image_path,
            terminal_session_id=history_entry.terminal_session_id,
            db=db
        )

        # Create annotation layer for new session
        annotation_layer = await image_editor_service.create_session(
            image_session=image_session,
            db=db
        )

        # Update history (increment view count, update last_viewed_at)
        await session_history_service.add_to_history(
            terminal_session_id=history_entry.terminal_session_id,
            image_path=history_entry.image_path,
            db=db
        )

        # Generate editor URL
        editor_url = f"/editor/{image_session.id}"

        # Return response
        return LoadImageResponse(
            session_id=image_session.id,
            editor_url=editor_url,
            image_width=image_session.image_width,
            image_height=image_session.image_height,
            image_format=image_session.image_format
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reopening from history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reopen from history: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str = Path(..., description="Image session ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about an image session.

    Returns session details and annotation layer.
    """
    logger.info(f"Get session info: {session_id}")

    try:
        from sqlalchemy import select
        from src.models.image_editor import ImageSession, AnnotationLayer

        # Load ImageSession
        session_query = select(ImageSession).where(ImageSession.id == session_id)
        session_result = await db.execute(session_query)
        image_session = session_result.scalar_one_or_none()

        if not image_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )

        # Load AnnotationLayer
        annotation_query = select(AnnotationLayer).where(AnnotationLayer.session_id == session_id)
        annotation_result = await db.execute(annotation_query)
        annotation_layer = annotation_result.scalar_one_or_none()

        # Return session details
        return {
            "session_id": image_session.id,
            "source_type": image_session.image_source_type,
            "source_path": image_session.image_source_path,
            "image_width": image_session.image_width,
            "image_height": image_session.image_height,
            "image_format": image_session.image_format,
            "terminal_session_id": image_session.terminal_session_id,
            "created_at": image_session.created_at.isoformat(),
            "annotation_layer": {
                "version": annotation_layer.version if annotation_layer else 0,
                "canvas_json": annotation_layer.canvas_json if annotation_layer else None
            } if annotation_layer else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session info: {str(e)}"
        )
