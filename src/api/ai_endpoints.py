"""AI assistant REST API endpoints.

This module provides HTTP endpoints for AI assistant functionality including:
- Text chat with AI assistant
- Voice input processing
- Command suggestions
- Output explanation
- Context management
"""

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
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from src.models.ai_context import AIContext
from src.services.ai_service import AIService, AIConfig, AIProvider
from src.database.base import get_db
from src.config import settings

# Initialize router
router = APIRouter(prefix="/api/v1/ai", tags=["AI Assistant"])

# Initialize AI service (singleton) with configuration from environment
ai_service = AIService(config=settings.get_ai_config())


# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    """Request model for chat message."""
    message: str = Field(..., description="User message")
    stream: bool = Field(default=False, description="Enable streaming response")
    includeContext: bool = Field(default=True, description="Include conversation context")


class ChatResponse(BaseModel):
    """Response model for chat."""
    messageId: str
    response: str
    responseTime: float
    tokenCount: int
    confidence: float


class VoiceRequest(BaseModel):
    """Request model for voice processing."""
    language: str = Field(default="en-US", description="Language code for speech recognition")
    enableTTS: bool = Field(default=False, description="Return text-to-speech audio response")
    voiceSettings: Optional[dict] = Field(default=None, description="Voice synthesis settings")


class VoiceResponse(BaseModel):
    """Response model for voice processing."""
    messageId: str
    transcription: str
    response: str
    responseTime: float
    audioUrl: Optional[str] = None


class SuggestionRequest(BaseModel):
    """Request model for command suggestions."""
    partialCommand: Optional[str] = Field(default=None, description="Partial command to complete")
    goal: Optional[str] = Field(default=None, description="Desired outcome description")
    maxSuggestions: int = Field(default=5, ge=1, le=20, description="Maximum suggestions")


class CommandSuggestion(BaseModel):
    """Individual command suggestion."""
    command: str
    description: str
    confidence: float
    category: str


class SuggestionResponse(BaseModel):
    """Response model for suggestions."""
    suggestions: List[CommandSuggestion]
    responseTime: float


class ExplainRequest(BaseModel):
    """Request model for output explanation."""
    command: str = Field(..., description="Command that was executed")
    output: str = Field(..., description="Command output or error message")
    explainErrors: bool = Field(default=True, description="Focus on error explanation")


class ExplainResponse(BaseModel):
    """Response model for explanation."""
    explanation: str
    suggestedFixes: List[str]
    relatedCommands: List[str]
    responseTime: float


class AIContextMessage(BaseModel):
    """AI context message."""
    messageId: str
    role: str
    content: str
    timestamp: datetime
    messageType: str


class AIContextResponse(BaseModel):
    """Response model for AI context."""
    sessionId: UUID
    messages: List[AIContextMessage]
    totalMessages: int
    contextTokens: int


# Dependency to get current user ID (placeholder for auth)
async def get_current_user_id() -> UUID:
    """Get current authenticated user ID.

    TODO: Replace with actual authentication logic.
    """
    # Placeholder - in production this would verify JWT/session token
    return UUID("00000000-0000-0000-0000-000000000001")


# API Endpoints
@router.post("/chat")
async def chat_with_ai(
    sessionId: UUID = Query(..., description="Terminal session ID for context"),
    request: ChatRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Send chat message to AI assistant.

    Args:
        sessionId: Terminal session ID for context
        request: Chat message request
        db: Database session
        user_id: Current user ID

    Returns:
        ChatResponse or StreamingResponse for streaming

    Raises:
        HTTPException: 400 if request invalid, 429 if rate limited
    """
    from datetime import timezone
    from src.models.terminal_session import TerminalSession
    from sqlalchemy.exc import IntegrityError

    # Validate session exists or create it
    session_query = select(TerminalSession).where(
        TerminalSession.session_id == str(sessionId)
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        # Auto-create session for AI chat (handle race condition)
        try:
            session = TerminalSession(
                session_id=str(sessionId),
                user_id=str(user_id),
                shell_type="zsh",
                terminal_size={"cols": 80, "rows": 24}
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
        except IntegrityError:
            # Session was created by another request (race condition)
            # Rollback and re-fetch the session
            await db.rollback()
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create or fetch session"
                )

    # Ensure AI context exists
    context_query = select(AIContext).where(AIContext.session_id == str(sessionId))
    context_result = await db.execute(context_query)
    ai_context = context_result.scalar_one_or_none()

    if not ai_context:
        # Initialize AI context
        await ai_service.initialize_session_context(
            session_id=str(sessionId),
            user_id=str(user_id)
        )

    # Get AI response
    try:
        response_data = await ai_service.chat(
            session_id=str(sessionId),
            user_id=str(user_id),
            message=request.message,
            include_context=request.includeContext,
            stream=request.stream
        )

        if request.stream:
            # Return streaming response
            async def generate():
                async for chunk in response_data:
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Return regular JSON response
            return ChatResponse(
                messageId=response_data["message_id"],
                response=response_data["response"],
                responseTime=response_data["response_time"],
                tokenCount=response_data["token_count"],
                confidence=response_data.get("confidence", 1.0)
            )

    except Exception as e:
        # Check for rate limiting
        if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI chat failed: {str(e)}"
        )


@router.post("/voice", response_model=VoiceResponse)
async def process_voice(
    sessionId: UUID = Query(..., description="Terminal session ID for context"),
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, WebM)"),
    language: str = Query("en-US", description="Language code"),
    enableTTS: bool = Query(False, description="Return TTS audio"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Process voice input.

    Args:
        sessionId: Terminal session ID for context
        audio: Audio file to process
        language: Language code for speech recognition
        enableTTS: Return text-to-speech audio response
        db: Database session
        user_id: Current user ID

    Returns:
        VoiceResponse with transcription and AI response

    Raises:
        HTTPException: 400 if processing fails, 413 if file too large
    """
    from src.models.terminal_session import TerminalSession

    # Validate session exists
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

    # Read audio file
    try:
        audio_content = await audio.read()
        if len(audio_content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file too large (max 10MB)"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read audio file: {str(e)}"
        )

    # Process voice
    try:
        result = await ai_service.process_voice(
            session_id=str(sessionId),
            user_id=str(user_id),
            audio_data=audio_content,
            language=language,
            enable_tts=enableTTS
        )

        return VoiceResponse(
            messageId=result["message_id"],
            transcription=result["transcription"],
            response=result["response"],
            responseTime=result["response_time"],
            audioUrl=result.get("audio_url")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Voice processing failed: {str(e)}"
        )


@router.post("/suggest", response_model=SuggestionResponse)
async def get_suggestions(
    sessionId: UUID = Query(..., description="Terminal session ID for context"),
    request: SuggestionRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get AI-powered command suggestions.

    Args:
        sessionId: Terminal session ID for context
        request: Suggestion request parameters
        db: Database session
        user_id: Current user ID

    Returns:
        SuggestionResponse with command suggestions

    Raises:
        HTTPException: 400 if request invalid
    """
    from src.models.terminal_session import TerminalSession

    # Validate session exists
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

    # Get suggestions
    try:
        result = await ai_service.get_suggestions(
            session_id=str(sessionId),
            user_id=str(user_id),
            partial_command=request.partialCommand,
            goal=request.goal,
            max_suggestions=request.maxSuggestions
        )

        suggestions = [
            CommandSuggestion(
                command=s["command"],
                description=s["description"],
                confidence=s["confidence"],
                category=s["category"]
            )
            for s in result["suggestions"]
        ]

        return SuggestionResponse(
            suggestions=suggestions,
            responseTime=result["response_time"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Suggestion generation failed: {str(e)}"
        )


@router.post("/explain", response_model=ExplainResponse)
async def explain_output(
    sessionId: UUID = Query(..., description="Terminal session ID for context"),
    request: ExplainRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get AI explanation of command output.

    Args:
        sessionId: Terminal session ID for context
        request: Explanation request parameters
        db: Database session
        user_id: Current user ID

    Returns:
        ExplainResponse with explanation and suggestions

    Raises:
        HTTPException: 400 if request invalid
    """
    from src.models.terminal_session import TerminalSession

    # Validate session exists
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

    # Get explanation
    try:
        result = await ai_service.explain_output(
            session_id=str(sessionId),
            user_id=str(user_id),
            command=request.command,
            output=request.output,
            explain_errors=request.explainErrors
        )

        return ExplainResponse(
            explanation=result["explanation"],
            suggestedFixes=result.get("suggested_fixes", []),
            relatedCommands=result.get("related_commands", []),
            responseTime=result["response_time"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Explanation generation failed: {str(e)}"
        )


@router.get("/context", response_model=AIContextResponse)
async def get_ai_context(
    sessionId: UUID = Query(..., description="Terminal session ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum messages to return"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get AI context and conversation history.

    Args:
        sessionId: Terminal session ID
        limit: Maximum number of messages to return
        db: Database session
        user_id: Current user ID

    Returns:
        AIContextResponse with conversation history

    Raises:
        HTTPException: 404 if context not found
    """
    from src.models.terminal_session import TerminalSession

    # Validate session exists
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

    # Get AI context
    try:
        context_data = await ai_service.get_context(
            session_id=str(sessionId),
            limit=limit
        )

        messages = [
            AIContextMessage(
                messageId=m["message_id"],
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"],
                messageType=m.get("message_type", "text")
            )
            for m in context_data["messages"]
        ]

        return AIContextResponse(
            sessionId=sessionId,
            messages=messages,
            totalMessages=context_data["total_messages"],
            contextTokens=context_data.get("context_tokens", 0)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve context: {str(e)}"
        )


@router.delete("/context", status_code=status.HTTP_204_NO_CONTENT)
async def clear_ai_context(
    sessionId: UUID = Query(..., description="Terminal session ID"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Clear AI conversation history and context.

    Args:
        sessionId: Terminal session ID
        db: Database session
        user_id: Current user ID

    Raises:
        HTTPException: 404 if session not found
    """
    from src.models.terminal_session import TerminalSession

    # Validate session exists
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

    # Clear AI context
    try:
        await ai_service.clear_context(str(sessionId))
    except Exception as e:
        # Log error but return success
        import logging
        logging.error(f"Error clearing AI context for session {sessionId}: {e}")
