"""Completion REST API endpoints.

This module provides HTTP endpoints for terminal command completion including:
- Shell-native completions (bash/zsh)
- AI-powered suggestions
- Custom command completions
- Unified hybrid completions
"""

import os
import asyncio
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status
)
from pydantic import BaseModel, Field

from src.services.completion_service import get_completion_service
from src.services.pty_service import pty_service  # Import the singleton directly
from src.config import settings

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/completions", tags=["Completions"])

# Initialize completion service (singleton)
completion_service = get_completion_service(enable_ai=True)


async def get_pty_cwd(session_id: str) -> Optional[str]:
    """Get the current working directory of a PTY session.

    Args:
        session_id: Terminal session ID

    Returns:
        Current working directory or None if not found
    """
    try:
        print(f"[get_pty_cwd] Starting for session {session_id}")

        # Get PTY instance (async)
        pty_instance = await pty_service.get_pty(session_id)
        print(f"[get_pty_cwd] PTY instance: {pty_instance}")

        if not pty_instance:
            print(f"[get_pty_cwd] No PTY instance found")
            return None

        if not pty_instance.process:
            print(f"[get_pty_cwd] PTY instance has no process")
            return None

        pid = pty_instance.process.pid
        print(f"[get_pty_cwd] Got PID: {pid}")
        logger.info(f"[PTY CWD] Getting cwd for session {session_id}, PID {pid}")

        # On macOS/Linux, try to get cwd from /proc/<pid>/cwd
        proc_cwd = f"/proc/{pid}/cwd"
        print(f"[get_pty_cwd] Checking {proc_cwd}")
        if os.path.islink(proc_cwd):
            cwd = os.readlink(proc_cwd)
            print(f"[get_pty_cwd] Found via /proc: {cwd}")
            logger.info(f"[PTY CWD] Found via /proc: {cwd}")
            return cwd
        else:
            print(f"[get_pty_cwd] /proc not available (macOS)")

        # macOS alternative: use lsof (async)
        print(f"[get_pty_cwd] Trying lsof for PID {pid}")
        try:
            process = await asyncio.create_subprocess_exec(
                'lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=0.5
            )

            print(f"[get_pty_cwd] lsof return code: {process.returncode}")
            if process.returncode == 0:
                # Parse lsof output: n/path/to/dir
                output = stdout.decode()
                print(f"[get_pty_cwd] lsof stdout: {repr(output)}")
                logger.debug(f"[PTY CWD] lsof output: {output}")

                for line in output.split('\n'):
                    if line.startswith('n'):
                        cwd = line[1:]  # Remove 'n' prefix
                        print(f"[get_pty_cwd] Found via lsof: {cwd}")
                        logger.info(f"[PTY CWD] Found via lsof: {cwd}")
                        return cwd

                print(f"[get_pty_cwd] No line starting with 'n' found in lsof output")
            else:
                stderr_str = stderr.decode()
                print(f"[get_pty_cwd] lsof failed: {stderr_str}")
                logger.debug(f"[PTY CWD] lsof failed with code {process.returncode}: {stderr_str}")

        except asyncio.TimeoutError:
            print(f"[get_pty_cwd] lsof timed out")
            logger.warning("[PTY CWD] lsof timed out")
        except Exception as e:
            print(f"[get_pty_cwd] lsof exception: {e}")
            logger.debug(f"[PTY CWD] lsof failed: {e}")

        print(f"[get_pty_cwd] Could not determine cwd")
        logger.warning(f"[PTY CWD] Could not determine cwd for session {session_id}")
        return None

    except Exception as e:
        print(f"[get_pty_cwd] Exception: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Error getting PTY cwd: {e}")
        return None


# Pydantic models for request/response validation
class CompletionRequest(BaseModel):
    """Request model for command completion."""
    line: str = Field(..., description="Full command line text")
    cursorPos: int = Field(..., ge=0, description="Cursor position in the line")
    sessionId: str = Field(..., description="Terminal session ID")
    shellPath: str = Field(default="/bin/bash", description="Path to shell executable")
    cwd: str = Field(default=".", description="Current working directory")
    enableAI: bool = Field(default=True, description="Enable AI-powered suggestions")
    userId: str = Field(default="default", description="User ID")


class CompletionItem(BaseModel):
    """Single completion suggestion."""
    text: str = Field(..., description="Completion text to insert")
    display: str = Field(..., description="Display text (may include icons/formatting)")
    type: str = Field(..., description="Type: command, file, directory, option, custom, etc.")
    description: Optional[str] = Field(None, description="Additional description")
    source: str = Field(..., description="Source: shell, ai, custom")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    priority: int = Field(default=0, description="Sort priority")


class CompletionResponse(BaseModel):
    """Response model for completions."""
    completions: List[CompletionItem]
    totalCount: int
    sources: List[str]  # Which sources contributed (shell, ai, custom)


class DescriptionRequest(BaseModel):
    """Request model for command description."""
    command: str = Field(..., description="Command to describe")
    preferAI: bool = Field(default=False, description="Prefer AI-generated description")
    sessionId: Optional[str] = Field(None, description="Terminal session ID (for AI)")


class DescriptionResponse(BaseModel):
    """Response model for command description."""
    command: str
    description: Optional[str]
    source: str  # shell, ai, custom


@router.post("/suggest", response_model=CompletionResponse, status_code=status.HTTP_200_OK)
async def get_completions(request: CompletionRequest) -> CompletionResponse:
    """Get command completions from all sources.

    This endpoint provides intelligent completions by combining:
    1. Shell-native completions (fast, < 100ms)
    2. AI-powered suggestions (slower, < 2s)
    3. Custom jterm commands (instant)

    Args:
        request: Completion request with line, cursor position, etc.

    Returns:
        Unified list of completions sorted by priority

    Raises:
        HTTPException: If completion fails
    """
    try:
        print(f"\n=== COMPLETION ENDPOINT CALLED ===")
        print(f"Session ID: {request.sessionId}")
        print(f"Line: {request.line}")
        print(f"Client CWD: {request.cwd}")

        # Try to get real cwd from PTY session first
        real_cwd = await get_pty_cwd(request.sessionId)
        print(f"Real CWD from PTY: {real_cwd}")

        if real_cwd:
            logger.info(f"[Completion] Using real PTY cwd: {real_cwd} (client sent: {request.cwd})")
            cwd = real_cwd
        else:
            logger.info(f"[Completion] Could not get PTY cwd, using client cwd: {request.cwd}")
            cwd = request.cwd

        print(f"Final CWD to use: {cwd}")
        print(f"=================================\n")

        completions = await completion_service.get_completions(
            line=request.line,
            cursor_pos=request.cursorPos,
            session_id=request.sessionId,
            shell_path=request.shellPath,
            cwd=cwd,
            enable_ai=request.enableAI,
            user_id=request.userId
        )

        # Extract unique sources
        sources = list(set(comp.get('source', 'unknown') for comp in completions))

        return CompletionResponse(
            completions=[CompletionItem(**comp) for comp in completions],
            totalCount=len(completions),
            sources=sources
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get completions: {str(e)}"
        )


@router.post("/describe", response_model=DescriptionResponse, status_code=status.HTTP_200_OK)
async def get_command_description(request: DescriptionRequest) -> DescriptionResponse:
    """Get description for a command.

    Tries multiple sources in order:
    1. Custom commands (jterm built-ins)
    2. Shell whatis/man
    3. AI-generated description (if enabled)

    Args:
        request: Description request with command name

    Returns:
        Command description and source

    Raises:
        HTTPException: If description lookup fails
    """
    try:
        description = await completion_service.get_completion_description(
            command=request.command,
            prefer_ai=request.preferAI,
            session_id=request.sessionId
        )

        # Determine source
        from src.services.completion_service import CUSTOM_COMMANDS
        if request.command in CUSTOM_COMMANDS:
            source = "custom"
        elif description and not request.preferAI:
            source = "shell"
        elif description and request.preferAI:
            source = "ai"
        else:
            source = "unknown"

        return DescriptionResponse(
            command=request.command,
            description=description,
            source=source
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get description: {str(e)}"
        )


@router.get("/custom-commands", status_code=status.HTTP_200_OK)
async def get_custom_commands() -> dict:
    """Get list of all custom jterm commands.

    Returns:
        Dictionary of command names to descriptions
    """
    from src.services.completion_service import CUSTOM_COMMANDS
    return {"commands": CUSTOM_COMMANDS}


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """Health check endpoint for completion service.

    Returns:
        Service status and capabilities
    """
    return {
        "status": "healthy",
        "service": "completion",
        "capabilities": {
            "shell_completion": True,
            "ai_completion": completion_service.enable_ai,
            "custom_commands": True
        },
        "shell_service": completion_service.shell_service is not None,
        "ai_service": completion_service.ai_service is not None
    }
