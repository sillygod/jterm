"""Performance monitoring REST API endpoints.

This module provides HTTP endpoints for performance metrics including:
- Getting current performance snapshot
- Retrieving historical performance data
- Submitting client-side metrics
- Managing user performance preferences
"""

from typing import List, Optional
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.models.performance_snapshot import PerformanceSnapshot
from src.models.user_profile import UserProfile
from src.services.performance_service import get_performance_service, PerformanceServiceError
from src.database.base import get_db

# Initialize router
router = APIRouter(prefix="/api/performance", tags=["Performance"])

# Get performance service instance
performance_service = get_performance_service()


# Pydantic models for request/response validation
class PerformanceSnapshotResponse(BaseModel):
    """Response model for performance snapshot."""
    id: str
    session_id: str
    timestamp: str
    cpu_percent: float = Field(..., ge=0, le=100)
    memory_mb: float = Field(..., gt=0)
    active_websockets: int = Field(..., ge=0)
    terminal_updates_per_sec: float = Field(..., ge=0)
    client_fps: Optional[float] = Field(None, ge=0)
    client_memory_mb: Optional[float] = Field(None, ge=0)

    class Config:
        from_attributes = True


class PerformanceHistoryResponse(BaseModel):
    """Response model for performance history."""
    snapshots: List[PerformanceSnapshotResponse]
    count: int


class ClientMetricsRequest(BaseModel):
    """Request model for client-side metrics submission."""
    session_id: str
    client_fps: Optional[float] = Field(None, ge=0, le=240)
    client_memory_mb: Optional[float] = Field(None, ge=0, le=4096)


class SnapshotRecordedResponse(BaseModel):
    """Response model for snapshot recording confirmation."""
    recorded: bool


class PerformancePreferencesRequest(BaseModel):
    """Request model for performance preferences update."""
    show_performance_metrics: Optional[bool] = None
    performance_metric_refresh_interval: Optional[int] = Field(None, ge=1000, le=60000)


class PerformancePreferencesResponse(BaseModel):
    """Response model for performance preferences."""
    show_performance_metrics: bool
    performance_metric_refresh_interval: int = Field(..., ge=1000, le=60000)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str


@router.get(
    "/current",
    response_model=PerformanceSnapshotResponse,
    responses={
        200: {"description": "Current performance metrics"}
    },
    summary="Get current performance snapshot"
)
async def get_current_performance(
    db: AsyncSession = Depends(get_db)
) -> PerformanceSnapshotResponse:
    """
    Get current performance snapshot.

    Returns latest performance metrics for current session.

    Args:
        db: Database session

    Returns:
        PerformanceSnapshotResponse with current metrics
    """
    try:
        # For now, use default session ID (would come from WebSocket context in production)
        session_id = "00000000-0000-0000-0000-000000000001"

        # Get current snapshot
        snapshot_data = await performance_service.get_current_snapshot(session_id)

        # Create temporary snapshot object for response
        # In production, you might want to store this
        return PerformanceSnapshotResponse(
            id="current",  # Temporary ID for current snapshot
            session_id=snapshot_data['session_id'],
            timestamp=snapshot_data['timestamp'],
            cpu_percent=snapshot_data['cpu_percent'],
            memory_mb=snapshot_data['memory_mb'],
            active_websockets=snapshot_data['active_websockets'],
            terminal_updates_per_sec=snapshot_data['terminal_updates_per_sec'],
            client_fps=None,
            client_memory_mb=None
        )

    except PerformanceServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PERFORMANCE_ERROR",
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
    "/history",
    response_model=PerformanceHistoryResponse,
    responses={
        200: {"description": "Historical snapshots"}
    },
    summary="Get historical performance snapshots"
)
async def get_performance_history(
    minutes: int = Query(60, ge=1, le=1440, description="Time range in minutes (max 24 hours)"),
    session_id: Optional[str] = Query(None, description="Filter by specific terminal session"),
    db: AsyncSession = Depends(get_db)
) -> PerformanceHistoryResponse:
    """
    Get historical performance snapshots over a time range.

    Args:
        minutes: Time range in minutes (default 60, max 1440)
        session_id: Optional session filter
        db: Database session

    Returns:
        PerformanceHistoryResponse with historical data
    """
    try:
        # Get historical snapshots
        snapshots = await performance_service.get_history(
            minutes=minutes,
            session_id=session_id,
            db=db
        )

        # Convert to response models
        snapshot_responses = [
            PerformanceSnapshotResponse(
                id=snap.id,
                session_id=snap.session_id,
                timestamp=snap.timestamp.isoformat(),
                cpu_percent=snap.cpu_percent,
                memory_mb=snap.memory_mb,
                active_websockets=snap.active_websockets,
                terminal_updates_per_sec=snap.terminal_updates_per_sec,
                client_fps=snap.client_fps,
                client_memory_mb=snap.client_memory_mb
            )
            for snap in snapshots
        ]

        return PerformanceHistoryResponse(
            snapshots=snapshot_responses,
            count=len(snapshot_responses)
        )

    except PerformanceServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PERFORMANCE_ERROR",
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


@router.post(
    "/snapshot",
    response_model=SnapshotRecordedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Snapshot recorded"}
    },
    summary="Submit client-side performance metrics"
)
async def submit_client_metrics(
    request: ClientMetricsRequest,
    db: AsyncSession = Depends(get_db)
) -> SnapshotRecordedResponse:
    """
    Submit client-side performance metrics (FPS, memory).

    Client posts browser-side metrics for storage.

    Args:
        request: ClientMetricsRequest with session_id and metrics
        db: Database session

    Returns:
        SnapshotRecordedResponse confirming storage
    """
    try:
        # Collect server metrics
        server_metrics = performance_service.collect_server_metrics()

        # Combine with client metrics
        combined_metrics = {
            **server_metrics,
            'client_fps': request.client_fps,
            'client_memory_mb': request.client_memory_mb
        }

        # Store snapshot
        snapshot = await performance_service.store_snapshot(
            session_id=request.session_id,
            metrics=combined_metrics,
            db=db
        )

        # Push to WebSocket clients (if any connected)
        await performance_service.push_metrics_to_clients(snapshot)

        return SnapshotRecordedResponse(recorded=True)

    except PerformanceServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PERFORMANCE_ERROR",
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


@router.put(
    "/user/preferences",
    response_model=PerformancePreferencesResponse,
    responses={
        200: {"description": "Preferences updated"},
        400: {"description": "Invalid preferences", "model": ErrorResponse}
    },
    summary="Update performance metrics preferences"
)
async def update_performance_preferences(
    request: PerformancePreferencesRequest,
    db: AsyncSession = Depends(get_db)
) -> PerformancePreferencesResponse:
    """
    Update user's performance metrics preferences.

    User configures metrics display and refresh interval.

    Args:
        request: PerformancePreferencesRequest with preferences
        db: Database session

    Returns:
        PerformancePreferencesResponse with updated preferences

    Raises:
        HTTPException 400: If preferences invalid
    """
    try:
        # For now, use default user ID (would come from auth in production)
        user_id = "00000000-0000-0000-0000-000000000001"

        # Update preferences
        user = await performance_service.update_user_preferences(
            user_id=user_id,
            show_metrics=request.show_performance_metrics,
            refresh_interval=request.performance_metric_refresh_interval,
            db=db
        )

        return PerformancePreferencesResponse(
            show_performance_metrics=user.show_performance_metrics,
            performance_metric_refresh_interval=user.performance_metric_refresh_interval
        )

    except PerformanceServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_PREFERENCES",
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
    "/user/preferences",
    response_model=PerformancePreferencesResponse,
    responses={
        200: {"description": "Current preferences"}
    },
    summary="Get performance metrics preferences"
)
async def get_performance_preferences(
    db: AsyncSession = Depends(get_db)
) -> PerformancePreferencesResponse:
    """
    Get user's current performance metrics preferences.

    Args:
        db: Database session

    Returns:
        PerformancePreferencesResponse with current preferences
    """
    try:
        # For now, use default user ID (would come from auth in production)
        user_id = "00000000-0000-0000-0000-000000000001"

        # Get user profile
        from sqlalchemy import select
        query = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "USER_NOT_FOUND",
                    "message": f"User not found: {user_id}"
                }
            )

        return PerformancePreferencesResponse(
            show_performance_metrics=user.show_performance_metrics,
            performance_metric_refresh_interval=user.performance_metric_refresh_interval
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
