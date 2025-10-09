"""Terminal session management REST API endpoints.

This module provides HTTP endpoints for managing terminal sessions including:
- Creating/listing/retrieving terminal sessions
- Updating session configuration
- Resizing terminal dimensions
- Terminating sessions
- WebSocket endpoint for PTY I/O (upgrade handled by WebSocket handler)
"""

import os
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from pydantic import BaseModel, Field

from src.models.terminal_session import TerminalSession, SessionStatus
from src.services.pty_service import PTYService, PTYConfig
from src.database.base import get_db

# Initialize router
router = APIRouter(prefix="/api/v1/sessions", tags=["Terminal Sessions"])

# Initialize PTY service (singleton)
pty_service = PTYService()


# Pydantic models for request/response validation
class TerminalSize(BaseModel):
    """Terminal dimensions."""
    cols: int = Field(..., ge=20, le=500, description="Number of columns")
    rows: int = Field(..., ge=5, le=200, description="Number of rows")


class CreateSessionRequest(BaseModel):
    """Request model for creating a new terminal session."""
    terminalSize: Optional[TerminalSize] = Field(
        default=TerminalSize(cols=80, rows=24),
        description="Initial terminal dimensions"
    )
    workingDirectory: Optional[str] = Field(
        default=None,
        description="Initial working directory path"
    )
    shellType: Optional[str] = Field(
        default="/bin/bash",
        description="Shell type (bash, zsh, fish, etc.)"
    )
    environmentVariables: Optional[dict] = Field(
        default=None,
        description="Session environment variables"
    )
    recordingEnabled: bool = Field(
        default=False,
        description="Enable session recording"
    )
    aiAssistantEnabled: bool = Field(
        default=False,
        description="Enable AI assistant"
    )
    themeId: Optional[UUID] = Field(
        default=None,
        description="Theme ID to apply"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional session metadata"
    )


class UpdateSessionRequest(BaseModel):
    """Request model for updating a terminal session."""
    recordingEnabled: Optional[bool] = None
    aiAssistantEnabled: Optional[bool] = None
    themeId: Optional[UUID] = None
    metadata: Optional[dict] = None


class ResizeRequest(BaseModel):
    """Request model for resizing terminal."""
    terminalSize: TerminalSize


class TerminalSessionResponse(BaseModel):
    """Response model for terminal session."""
    sessionId: UUID
    userId: UUID
    status: str
    createdAt: datetime
    lastActiveAt: datetime
    terminatedAt: Optional[datetime]
    terminalSize: TerminalSize
    workingDirectory: str
    environmentVariables: Optional[dict]
    shellType: str
    shellPid: Optional[int]
    recordingEnabled: bool
    aiAssistantEnabled: bool
    themeId: Optional[UUID]
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response model for session list."""
    sessions: List[TerminalSessionResponse]
    total: int
    limit: int
    offset: int


# Dependency to get current user ID (placeholder for auth)
async def get_current_user_id() -> UUID:
    """Get current authenticated user ID.

    TODO: Replace with actual authentication logic.
    """
    # Placeholder - in production this would verify JWT/session token
    return UUID("00000000-0000-0000-0000-000000000001")


# API Endpoints
@router.get("", response_model=SessionListResponse)
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List terminal sessions for the authenticated user.

    Args:
        status: Optional status filter (active, inactive, terminated, recording)
        limit: Maximum number of sessions to return (1-100)
        offset: Number of sessions to skip for pagination
        db: Database session
        user_id: Current user ID

    Returns:
        SessionListResponse with sessions array, total count, limit, and offset
    """
    # Build query
    query = select(TerminalSession).where(TerminalSession.user_id == user_id)

    # Apply status filter if provided
    if status:
        try:
            session_status = SessionStatus(status)
            query = query.where(TerminalSession.status == session_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid values: active, inactive, terminated, recording"
            )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and execute
    query = query.limit(limit).offset(offset).order_by(TerminalSession.created_at.desc())
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Convert to response models
    session_responses = [
        TerminalSessionResponse(
            sessionId=s.session_id,
            userId=s.user_id,
            status=s.status.value,
            createdAt=s.created_at,
            lastActiveAt=s.last_active_at,
            terminatedAt=s.terminated_at,
            terminalSize=TerminalSize(cols=s.terminal_cols, rows=s.terminal_rows),
            workingDirectory=s.working_directory,
            environmentVariables=s.environment_variables,
            shellType=s.shell_type,
            shellPid=s.shell_pid,
            recordingEnabled=s.recording_enabled,
            aiAssistantEnabled=s.ai_assistant_enabled,
            themeId=s.theme_id,
            metadata=s.metadata
        )
        for s in sessions
    ]

    return SessionListResponse(
        sessions=session_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=TerminalSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new terminal session.

    Args:
        request: Session creation parameters
        db: Database session
        user_id: Current user ID

    Returns:
        Created terminal session details
    """
    # Create PTY configuration
    pty_config = PTYConfig(
        shell=request.shellType or "/bin/bash",
        cols=request.terminalSize.cols if request.terminalSize else 80,
        rows=request.terminalSize.rows if request.terminalSize else 24,
        cwd=request.workingDirectory or os.getcwd(),
        env=request.environmentVariables
    )

    # Create database session record
    session = TerminalSession(
        user_id=user_id,
        status=SessionStatus.ACTIVE,
        terminal_cols=pty_config.cols,
        terminal_rows=pty_config.rows,
        working_directory=pty_config.cwd,
        environment_variables=pty_config.env or {},
        shell_type=pty_config.shell,
        recording_enabled=request.recordingEnabled,
        ai_assistant_enabled=request.aiAssistantEnabled,
        theme_id=request.themeId,
        metadata=request.metadata or {}
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Start PTY process
    try:
        await pty_service.create_session(str(session.session_id), pty_config)

        # Get shell PID
        pty_instance = pty_service.get_session(str(session.session_id))
        if pty_instance and pty_instance.process:
            session.shell_pid = pty_instance.process.pid
            await db.commit()
            await db.refresh(session)

    except Exception as e:
        # Cleanup database record if PTY creation fails
        await db.delete(session)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create PTY process: {str(e)}"
        )

    return TerminalSessionResponse(
        sessionId=session.session_id,
        userId=session.user_id,
        status=session.status.value,
        createdAt=session.created_at,
        lastActiveAt=session.last_active_at,
        terminatedAt=session.terminated_at,
        terminalSize=TerminalSize(cols=session.terminal_cols, rows=session.terminal_rows),
        workingDirectory=session.working_directory,
        environmentVariables=session.environment_variables,
        shellType=session.shell_type,
        shellPid=session.shell_pid,
        recordingEnabled=session.recording_enabled,
        aiAssistantEnabled=session.ai_assistant_enabled,
        themeId=session.theme_id,
        metadata=session.metadata
    )


@router.get("/{sessionId}", response_model=TerminalSessionResponse)
async def get_session(
    sessionId: UUID = Path(..., description="Terminal session ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get terminal session details.

    Args:
        sessionId: Session identifier
        db: Database session
        user_id: Current user ID

    Returns:
        Terminal session details

    Raises:
        HTTPException: 404 if session not found or unauthorized
    """
    query = select(TerminalSession).where(
        TerminalSession.session_id == sessionId,
        TerminalSession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {sessionId} not found"
        )

    return TerminalSessionResponse(
        sessionId=session.session_id,
        userId=session.user_id,
        status=session.status.value,
        createdAt=session.created_at,
        lastActiveAt=session.last_active_at,
        terminatedAt=session.terminated_at,
        terminalSize=TerminalSize(cols=session.terminal_cols, rows=session.terminal_rows),
        workingDirectory=session.working_directory,
        environmentVariables=session.environment_variables,
        shellType=session.shell_type,
        shellPid=session.shell_pid,
        recordingEnabled=session.recording_enabled,
        aiAssistantEnabled=session.ai_assistant_enabled,
        themeId=session.theme_id,
        metadata=session.metadata
    )


@router.patch("/{sessionId}", response_model=TerminalSessionResponse)
async def update_session(
    sessionId: UUID = Path(..., description="Terminal session ID"),
    request: UpdateSessionRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update terminal session configuration.

    Args:
        sessionId: Session identifier
        request: Update parameters
        db: Database session
        user_id: Current user ID

    Returns:
        Updated terminal session details

    Raises:
        HTTPException: 404 if session not found
    """
    query = select(TerminalSession).where(
        TerminalSession.session_id == sessionId,
        TerminalSession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {sessionId} not found"
        )

    # Update fields
    if request.recordingEnabled is not None:
        session.recording_enabled = request.recordingEnabled
    if request.aiAssistantEnabled is not None:
        session.ai_assistant_enabled = request.aiAssistantEnabled
    if request.themeId is not None:
        session.theme_id = request.themeId
    if request.metadata is not None:
        session.metadata = request.metadata

    session.last_active_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)

    return TerminalSessionResponse(
        sessionId=session.session_id,
        userId=session.user_id,
        status=session.status.value,
        createdAt=session.created_at,
        lastActiveAt=session.last_active_at,
        terminatedAt=session.terminated_at,
        terminalSize=TerminalSize(cols=session.terminal_cols, rows=session.terminal_rows),
        workingDirectory=session.working_directory,
        environmentVariables=session.environment_variables,
        shellType=session.shell_type,
        shellPid=session.shell_pid,
        recordingEnabled=session.recording_enabled,
        aiAssistantEnabled=session.ai_assistant_enabled,
        themeId=session.theme_id,
        metadata=session.metadata
    )


@router.delete("/{sessionId}", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_session(
    sessionId: UUID = Path(..., description="Terminal session ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Terminate and cleanup a terminal session.

    Args:
        sessionId: Session identifier
        db: Database session
        user_id: Current user ID

    Raises:
        HTTPException: 404 if session not found
    """
    query = select(TerminalSession).where(
        TerminalSession.session_id == sessionId,
        TerminalSession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {sessionId} not found"
        )

    # Terminate PTY process
    try:
        await pty_service.terminate_session(str(sessionId))
    except Exception as e:
        # Log error but continue with database cleanup
        import logging
        logging.error(f"Error terminating PTY for session {sessionId}: {e}")

    # Update session status
    session.status = SessionStatus.TERMINATED
    session.terminated_at = datetime.now(timezone.utc)

    await db.commit()


@router.post("/{sessionId}/resize", response_model=TerminalSessionResponse)
async def resize_session(
    sessionId: UUID = Path(..., description="Terminal session ID"),
    request: ResizeRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Resize terminal dimensions for a session.

    Args:
        sessionId: Session identifier
        request: New terminal dimensions
        db: Database session
        user_id: Current user ID

    Returns:
        Updated terminal session details

    Raises:
        HTTPException: 404 if session not found or 400 if resize fails
    """
    query = select(TerminalSession).where(
        TerminalSession.session_id == sessionId,
        TerminalSession.user_id == user_id
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {sessionId} not found"
        )

    # Resize PTY
    try:
        await pty_service.resize_terminal(
            str(sessionId),
            request.terminalSize.cols,
            request.terminalSize.rows
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to resize terminal: {str(e)}"
        )

    # Update database
    session.terminal_cols = request.terminalSize.cols
    session.terminal_rows = request.terminalSize.rows
    session.last_active_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)

    return TerminalSessionResponse(
        sessionId=session.session_id,
        userId=session.user_id,
        status=session.status.value,
        createdAt=session.created_at,
        lastActiveAt=session.last_active_at,
        terminatedAt=session.terminated_at,
        terminalSize=TerminalSize(cols=session.terminal_cols, rows=session.terminal_rows),
        workingDirectory=session.working_directory,
        environmentVariables=session.environment_variables,
        shellType=session.shell_type,
        shellPid=session.shell_pid,
        recordingEnabled=session.recording_enabled,
        aiAssistantEnabled=session.ai_assistant_enabled,
        themeId=session.theme_id,
        metadata=session.metadata
    )


# Note: WebSocket endpoint for /sessions/{sessionId}/ws is handled by
# src/websockets/terminal_handler.py and registered in main.py
