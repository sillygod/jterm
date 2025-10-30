"""Session recording CRUD REST API endpoints.

This module provides HTTP endpoints for managing session recordings including:
- Creating and listing recordings
- Starting and stopping recording
- Retrieving recording events for playback
- Exporting recordings in various formats
- Deleting recordings
"""

import logging
import json
from typing import List, Optional
from uuid import UUID
from datetime import datetime

logger = logging.getLogger(__name__)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    Body,
    status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field

from src.models.recording import Recording, RecordingStatus
from src.services.recording_service import RecordingService, RecordingConfig, ExportFormat, get_recording_service
from src.database.base import get_db

# Initialize router
router = APIRouter(prefix="/api/v1/recordings", tags=["Session Recording"])

# Use the global singleton recording service
_recording_service_instance = None


async def get_recording_service_instance() -> RecordingService:
    """Get or initialize the recording service singleton."""
    global _recording_service_instance
    if _recording_service_instance is None:
        _recording_service_instance = await get_recording_service()
    return _recording_service_instance


# Pydantic models for request/response validation
class RecordingResponse(BaseModel):
    """Response model for recording."""
    recordingId: UUID
    sessionId: UUID
    userId: UUID
    status: str
    startedAt: Optional[datetime]
    stoppedAt: Optional[datetime]
    duration: Optional[int]
    eventCount: int
    fileSize: int
    filePath: Optional[str]
    compressionEnabled: bool
    terminalSize: Optional[dict]
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class RecordingListResponse(BaseModel):
    """Response model for recording list."""
    recordings: List[RecordingResponse]
    total: int
    limit: int
    offset: int


class StartRecordingRequest(BaseModel):
    """Request model for starting a recording."""
    sessionId: UUID = Field(..., description="Terminal session ID to record")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class RecordingEventResponse(BaseModel):
    """Response model for a recording event."""
    timestamp: str
    deltaTime: int
    type: str
    data: str
    size: int
    metadata: Optional[dict]


class RecordingEventsResponse(BaseModel):
    """Response model for recording events list."""
    recordingId: UUID
    events: List[RecordingEventResponse]
    total: int
    limit: int
    offset: int


class ExportRecordingRequest(BaseModel):
    """Request model for exporting a recording."""
    format: str = Field(..., description="Export format (json, asciinema, html, text)")


# Dependency to get current user ID (placeholder for auth)
async def get_current_user_id() -> UUID:
    """Get current authenticated user ID.

    TODO: Replace with actual authentication logic.
    """
    # Placeholder - in production this would verify JWT/session token
    return UUID("00000000-0000-0000-0000-000000000001")


# API Endpoints
@router.get("", response_model=RecordingListResponse)
async def list_recordings(
    sessionId: Optional[UUID] = Query(None, description="Filter by session ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    startDate: Optional[datetime] = Query(None, description="Filter recordings created after"),
    endDate: Optional[datetime] = Query(None, description="Filter recordings created before"),
    limit: int = Query(20, ge=1, le=100, description="Maximum recordings to return"),
    offset: int = Query(0, ge=0, description="Number of recordings to skip"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List session recordings for the authenticated user.

    Args:
        sessionId: Optional session ID filter
        status: Optional status filter
        startDate: Optional start date filter
        endDate: Optional end date filter
        limit: Maximum number of recordings to return (1-100)
        offset: Number of recordings to skip for pagination
        db: Database session
        user_id: Current user ID

    Returns:
        RecordingListResponse with recordings array, total count, limit, and offset
    """
    # Build query
    query = select(Recording).where(Recording.user_id == str(user_id))

    # Apply session filter if provided
    if sessionId:
        query = query.where(Recording.session_id == str(sessionId))

    # Apply status filter if provided
    if status:
        try:
            recording_status = RecordingStatus(status.upper())
            query = query.where(Recording.status == recording_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid values: recording, stopped, processing, ready, failed"
            )

    # Apply date filters
    if startDate:
        query = query.where(Recording.start_time >= startDate)
    if endDate:
        query = query.where(Recording.start_time <= endDate)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and execute
    query = query.limit(limit).offset(offset).order_by(Recording.start_time.desc())
    result = await db.execute(query)
    recordings = result.scalars().all()

    # Convert to response models
    recording_responses = [
        RecordingResponse(
            recordingId=r.recording_id,
            sessionId=r.session_id,
            userId=r.user_id,
            status=r.status.value.lower() if hasattr(r.status, 'value') else str(r.status).lower(),
            startedAt=r.start_time,
            stoppedAt=r.end_time,
            duration=r.duration,
            eventCount=r.event_count,
            fileSize=r.file_size,
            filePath=r.extra_metadata.get('file_path') if r.extra_metadata else None,
            compressionEnabled=r.compression_ratio > 0 if r.compression_ratio else False,
            terminalSize=r.terminal_size or {},
            metadata=r.extra_metadata or {}
        )
        for r in recordings
    ]

    return RecordingListResponse(
        recordings=recording_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{recordingId}", response_model=RecordingResponse)
async def get_recording(
    recordingId: UUID = Path(..., description="Recording ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get recording details.

    Args:
        recordingId: Recording identifier
        db: Database session
        user_id: Current user ID

    Returns:
        Recording details

    Raises:
        HTTPException: 404 if recording not found or unauthorized
    """
    query = select(Recording).where(
        Recording.recording_id == str(recordingId),
        Recording.user_id == str(user_id)
    )
    result = await db.execute(query)
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording {recordingId} not found"
        )

    return RecordingResponse(
        recordingId=recording.recording_id,
        sessionId=recording.session_id,
        userId=recording.user_id,
        status=recording.status.value.lower() if hasattr(recording.status, 'value') else str(recording.status).lower(),
        startedAt=recording.start_time,
        stoppedAt=recording.end_time,
        duration=recording.duration,
        eventCount=recording.event_count,
        fileSize=recording.file_size,
        filePath=getattr(recording, 'file_path', None),
        compressionEnabled=getattr(recording, 'compression_enabled', False),
        terminalSize=recording.terminal_size or {},
        metadata=getattr(recording, 'extra_metadata', {})
    )


@router.delete("/{recordingId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording(
    recordingId: UUID = Path(..., description="Recording ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete a recording and its associated data.

    Args:
        recordingId: Recording identifier
        db: Database session
        user_id: Current user ID

    Raises:
        HTTPException: 404 if recording not found
    """
    query = select(Recording).where(
        Recording.recording_id == str(recordingId),
        Recording.user_id == str(user_id)
    )
    result = await db.execute(query)
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording {recordingId} not found"
        )

    # Delete recording data
    try:
        recording_service = await get_recording_service_instance()
        await recording_service.delete_recording(str(recordingId), str(user_id))
    except Exception as e:
        # Log error but continue with database cleanup
        import logging
        logging.error(f"Error deleting recording files for {recordingId}: {e}")

    # Delete database record
    await db.delete(recording)
    await db.commit()


@router.post("/start", response_model=RecordingResponse)
async def start_recording(
    request: StartRecordingRequest = Body(..., description="Start recording request"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Start recording a terminal session.

    Args:
        request: Start recording parameters
        db: Database session
        user_id: Current user ID

    Returns:
        Recording details with generated recording ID

    Raises:
        HTTPException: 409 if already recording
    """
    from datetime import timezone
    from src.models.terminal_session import TerminalSession
    from sqlalchemy.exc import IntegrityError

    # Auto-create terminal session if it doesn't exist
    session_query = select(TerminalSession).where(
        TerminalSession.session_id == str(request.sessionId)
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        # Create terminal session automatically
        try:
            session = TerminalSession(
                session_id=str(request.sessionId),
                user_id=str(user_id),
                shell_type="zsh",
                terminal_size={"cols": 80, "rows": 24}
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
        except IntegrityError:
            # Session was created by another request
            await db.rollback()
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create or fetch session"
                )

    # Check if there's already an active recording for this session
    existing_by_session = select(Recording).where(
        Recording.session_id == str(request.sessionId),
        Recording.status == RecordingStatus.RECORDING
    )
    result_by_session = await db.execute(existing_by_session)
    existing_recording = result_by_session.scalar_one_or_none()

    if existing_recording:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session already has an active recording: {existing_recording.recording_id}"
        )

    # Start recording service - this will create the Recording in the database
    try:
        # RecordingService.start_recording creates the recording and returns its ID
        recording_service = await get_recording_service_instance()
        print(f"API: Starting recording for session {request.sessionId}")
        returned_recording_id = await recording_service.start_recording(
            str(request.sessionId)
        )
        print(f"API: Started recording {returned_recording_id} for session {request.sessionId}")
        logger.info(f"Started recording {returned_recording_id} for session {request.sessionId}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start recording: {str(e)}"
        )

    # Get the recording that was created by the service
    recording_query = select(Recording).where(
        Recording.session_id == str(request.sessionId),
        Recording.status == RecordingStatus.RECORDING
    )
    result = await db.execute(recording_query)
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recording was started but not found in database"
        )

    return RecordingResponse(
        recordingId=recording.recording_id,
        sessionId=recording.session_id,
        userId=recording.user_id,
        status=recording.status.value.lower() if hasattr(recording.status, 'value') else str(recording.status).lower(),
        startedAt=recording.start_time,
        stoppedAt=recording.end_time,
        duration=recording.duration,
        eventCount=recording.event_count,
        fileSize=recording.file_size,
        filePath=getattr(recording, 'file_path', None),
        compressionEnabled=getattr(recording, 'compression_enabled', False),
        terminalSize=recording.terminal_size or {},
        metadata=getattr(recording, 'extra_metadata', {})
    )


@router.post("/{recordingId}/stop", response_model=RecordingResponse)
async def stop_recording(
    recordingId: UUID = Path(..., description="Recording ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Stop recording a terminal session.

    Args:
        recordingId: Recording identifier
        db: Database session
        user_id: Current user ID

    Returns:
        Updated recording details

    Raises:
        HTTPException: 404 if recording not found, 400 if not recording
    """
    from datetime import timezone

    query = select(Recording).where(
        Recording.recording_id == str(recordingId),
        Recording.user_id == str(user_id)
    )
    result = await db.execute(query)
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording {recordingId} not found"
        )

    if recording.status != RecordingStatus.RECORDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recording {recordingId} is not currently recording"
        )

    # Stop recording service (expects session_id, not recording_id)
    try:
        recording_service = await get_recording_service_instance()
        await recording_service.stop_recording(str(recording.session_id))

        # Update recording
        recording.end_time = datetime.now(timezone.utc)
        if recording.start_time:
            # Ensure start_time is timezone-aware for proper calculation
            start_time = recording.start_time
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            recording.duration = int((recording.end_time - start_time).total_seconds() * 1000)  # milliseconds
        recording.status = RecordingStatus.READY

    except Exception as e:
        recording.status = RecordingStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to stop recording: {str(e)}"
        )

    await db.commit()
    await db.refresh(recording)

    return RecordingResponse(
        recordingId=recording.recording_id,
        sessionId=recording.session_id,
        userId=recording.user_id,
        status=recording.status.value.lower() if hasattr(recording.status, 'value') else str(recording.status).lower(),
        startedAt=recording.start_time,
        stoppedAt=recording.end_time,
        duration=recording.duration,
        eventCount=recording.event_count,
        fileSize=recording.file_size,
        filePath=getattr(recording, 'file_path', None),
        compressionEnabled=getattr(recording, 'compression_enabled', False),
        terminalSize=recording.terminal_size or {},
        metadata=getattr(recording, 'extra_metadata', {})
    )


@router.get("/{recordingId}/events", response_model=RecordingEventsResponse)
async def get_recording_events(
    recordingId: UUID = Path(..., description="Recording ID"),
    startTime: Optional[datetime] = Query(None, description="Filter events after this time"),
    endTime: Optional[datetime] = Query(None, description="Filter events before this time"),
    eventTypes: Optional[str] = Query(None, description="Comma-separated event types"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get recording events for playback.

    Args:
        recordingId: Recording identifier
        startTime: Optional start time filter
        endTime: Optional end time filter
        eventTypes: Optional comma-separated event types filter
        limit: Maximum number of events to return (1-10000)
        offset: Number of events to skip for pagination
        db: Database session
        user_id: Current user ID

    Returns:
        RecordingEventsResponse with events array

    Raises:
        HTTPException: 404 if recording not found
    """
    query = select(Recording).where(
        Recording.recording_id == str(recordingId),
        Recording.user_id == str(user_id)
    )
    result = await db.execute(query)
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording {recordingId} not found"
        )

    # Parse event types filter
    event_type_list = None
    if eventTypes:
        event_type_list = [t.strip() for t in eventTypes.split(",")]

    # Get events from recording service
    try:
        recording_service = await get_recording_service_instance()
        events_data = await recording_service.get_events(
            str(recordingId),
            start_time=startTime,
            end_time=endTime,
            event_types=event_type_list,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve events: {str(e)}"
        )

    # Convert to response models
    import zlib
    event_responses = []

    for e in events_data["events"]:
        # Handle different event formats (compressed vs uncompressed)
        if isinstance(e, dict) and e.get("compressed"):
            # Decompress the batch
            try:
                compressed_data = bytes.fromhex(e.get("data", ""))
                decompressed = zlib.decompress(compressed_data)
                decompressed_events = json.loads(decompressed.decode('utf-8'))

                # Add decompressed events
                for event in decompressed_events:
                    # Convert data to string if it's a dict
                    data = event.get("data", "")
                    if isinstance(data, dict):
                        data = json.dumps(data)

                    event_responses.append(
                        RecordingEventResponse(
                            timestamp=event.get("timestamp", ""),
                            deltaTime=event.get("deltaTime", 0),
                            type=event.get("type", "output"),
                            data=data,
                            size=event.get("size", 0),
                            metadata=event.get("metadata", {})
                        )
                    )
            except Exception as decompress_error:
                logger.error(f"Failed to decompress events: {decompress_error}")
            continue

        # Handle normal events with flexible field names
        # Convert data to string if it's a dict
        data = e.get("data", "")
        if isinstance(data, dict):
            data = json.dumps(data)

        event_responses.append(
            RecordingEventResponse(
                timestamp=e.get("timestamp", ""),
                deltaTime=e.get("deltaTime", 0),
                type=e.get("type", "output"),
                data=data,
                size=e.get("size", 0),
                metadata=e.get("metadata", {})
            )
        )

    return RecordingEventsResponse(
        recordingId=recordingId,
        events=event_responses,
        total=events_data.get("total", len(event_responses)),
        limit=limit,
        offset=offset
    )


@router.get("/{recordingId}/export")
@router.post("/{recordingId}/export")
async def export_recording(
    recordingId: UUID = Path(..., description="Recording ID"),
    format: str = Query("asciicast", description="Export format"),
    request: ExportRecordingRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Export recording in specified format.

    Args:
        recordingId: Recording identifier
        request: Export format specification
        db: Database session
        user_id: Current user ID

    Returns:
        FileResponse with exported recording

    Raises:
        HTTPException: 404 if recording not found, 400 if export fails
    """
    from fastapi.responses import FileResponse

    query = select(Recording).where(
        Recording.recording_id == str(recordingId),
        Recording.user_id == str(user_id)
    )
    result = await db.execute(query)
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording {recordingId} not found"
        )

    # Validate export format
    try:
        # For GET requests, use query parameter; for POST, use request body
        format_str = format if request is None else request.format
        export_format = ExportFormat(format_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid export format: {format_str}. Valid values: json, asciinema, html, text"
        )

    # Export recording
    try:
        recording_service = await get_recording_service_instance()
        export_path = await recording_service.export_recording(
            str(recordingId),
            export_format
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to export recording: {str(e)}"
        )

    # Determine media type and filename
    media_types = {
        ExportFormat.JSON: "application/json",
        ExportFormat.ASCIINEMA: "application/json",
        ExportFormat.HTML: "text/html",
        ExportFormat.TEXT: "text/plain"
    }

    extensions = {
        ExportFormat.JSON: ".json",
        ExportFormat.ASCIINEMA: ".cast",
        ExportFormat.HTML: ".html",
        ExportFormat.TEXT: ".txt"
    }

    filename = f"recording_{recordingId}{extensions[export_format]}"

    return FileResponse(
        path=export_path,
        media_type=media_types[export_format],
        filename=filename
    )


# Additional router for recording playback API (without /v1 prefix)
playback_router = APIRouter(prefix="/api/recordings", tags=["Recording Playback"])


class RecordingDimensionsResponse(BaseModel):
    """Response model for recording dimensions."""
    recording_id: str
    rows: int = Field(..., ge=1, description="Terminal height in rows")
    columns: int = Field(..., ge=1, description="Terminal width in columns")
    created_at: str


class RecordingDimensionsError(BaseModel):
    """Error response for recording dimensions."""
    error: str
    message: str


@playback_router.get(
    "/{id}/dimensions",
    response_model=RecordingDimensionsResponse,
    responses={
        200: {"description": "Terminal dimensions"},
        404: {"description": "Recording not found", "model": RecordingDimensionsError}
    },
    summary="Get terminal dimensions for recording"
)
async def get_recording_dimensions(
    id: str = Path(..., description="Recording ID"),
    db: AsyncSession = Depends(get_db)
) -> RecordingDimensionsResponse:
    """
    Get terminal dimensions for recording.

    Returns terminal size (rows, columns) for scaling calculations.

    Args:
        id: Recording ID
        db: Database session

    Returns:
        RecordingDimensionsResponse with dimensions

    Raises:
        HTTPException 404: If recording not found
    """
    try:
        # Query recording from database
        query = select(Recording).where(Recording.recording_id == id)
        result = await db.execute(query)
        recording = result.scalar_one_or_none()

        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "RECORDING_NOT_FOUND",
                    "message": f"No recording found with ID {id}"
                }
            )

        # Extract dimensions from terminal_size metadata
        # Recording model has terminal_size as JSON field
        terminal_size = recording.terminal_size or {"cols": 80, "rows": 24}

        return RecordingDimensionsResponse(
            recording_id=recording.recording_id,
            rows=terminal_size.get("rows", 24),
            columns=terminal_size.get("cols", 80),
            created_at=recording.started_at.isoformat() if recording.started_at else datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recording dimensions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"Failed to retrieve dimensions: {str(e)}"
            }
        )
