"""AI assistant WebSocket handler for real-time chat and assistance.

This handler manages WebSocket connections for AI assistant communication,
supporting streaming responses, voice input/output, context management,
and rate limiting for concurrent AI conversations.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from src.services.ai_service import (
    AIService,
    AIConfig,
    AIProvider,
    ResponseType,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderQuotaError,
    get_ai_service
)
from src.websockets.manager import WebSocketManager, get_websocket_manager


logger = logging.getLogger(__name__)


class AIWebSocketMessage(BaseModel):
    """AI WebSocket message structure."""
    type: str
    data: Any
    sessionId: Optional[str] = None
    conversationId: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatRequestData(BaseModel):
    """Data for chat request."""
    message: str
    responseType: Optional[str] = "text"
    streaming: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None


class VoiceInputData(BaseModel):
    """Data for voice input."""
    audioData: str  # Base64 encoded audio
    format: str = "webm"
    sampleRate: int = 16000


class RateLimiter:
    """Simple rate limiter for AI requests."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._user_requests: Dict[str, list] = defaultdict(list)

    def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user is within rate limit.

        Args:
            user_id: User identifier

        Returns:
            True if within limit, False otherwise
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old requests
        self._user_requests[user_id] = [
            timestamp for timestamp in self._user_requests[user_id]
            if timestamp > cutoff
        ]

        # Check limit
        if len(self._user_requests[user_id]) >= self.max_requests:
            return False

        # Add new request
        self._user_requests[user_id].append(now)
        return True

    def get_remaining_quota(self, user_id: str) -> int:
        """
        Get remaining quota for user.

        Args:
            user_id: User identifier

        Returns:
            Number of remaining requests
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Count recent requests
        recent_requests = sum(
            1 for timestamp in self._user_requests[user_id]
            if timestamp > cutoff
        )

        return max(0, self.max_requests - recent_requests)


class AIWebSocketHandler:
    """
    WebSocket handler for AI assistant communication.

    Handles real-time AI chat, streaming responses, voice input/output,
    context management, and rate limiting.
    """

    def __init__(
        self,
        ai_service: Optional[AIService] = None,
        ws_manager: Optional[WebSocketManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize AI WebSocket handler.

        Args:
            ai_service: AI service instance
            ws_manager: WebSocket manager instance
            rate_limiter: Rate limiter instance
        """
        self.ai_service = ai_service
        self.ws_manager = ws_manager
        self.rate_limiter = rate_limiter or RateLimiter(
            max_requests=20,
            window_seconds=60
        )
        self._active_streams: Dict[str, asyncio.Task] = {}
        self._conversation_locks: Dict[str, asyncio.Lock] = {}

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """
        Handle a new AI WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Optional user identifier
            session_id: Optional terminal session identifier
        """
        # Get service instances
        if not self.ai_service:
            self.ai_service = await get_ai_service()
        if not self.ws_manager:
            self.ws_manager = await get_websocket_manager()

        connection_id = None
        conversation_id = None

        try:
            # Register connection
            connection_id = await self.ws_manager.connect(
                websocket,
                user_id=user_id,
                session_id=session_id,
                metadata={"handler": "ai", "sessionId": session_id}
            )

            logger.info(
                f"AI WebSocket connected: {connection_id} "
                f"(user: {user_id}, session: {session_id})"
            )

            # Send connection established message
            await self._send_message(
                connection_id,
                "connected",
                {
                    "connectionId": connection_id,
                    "sessionId": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "quota": self.rate_limiter.get_remaining_quota(user_id or "anonymous")
                }
            )

            # Main message loop
            while True:
                try:
                    # Receive message
                    raw_message = await websocket.receive_json()

                    # Parse and validate message
                    try:
                        message = AIWebSocketMessage(**raw_message)
                    except ValidationError as e:
                        await self._send_error(
                            connection_id,
                            f"Invalid message format: {e}",
                            conversation_id
                        )
                        continue

                    # Update conversation ID if provided
                    if message.conversationId:
                        conversation_id = message.conversationId

                    # Check rate limit
                    if not self.rate_limiter.check_rate_limit(user_id or "anonymous"):
                        await self._send_error(
                            connection_id,
                            "Rate limit exceeded. Please try again later.",
                            conversation_id
                        )
                        continue

                    # Route message to appropriate handler
                    await self._route_message(
                        connection_id,
                        message,
                        user_id,
                        session_id
                    )

                except WebSocketDisconnect:
                    logger.info(f"AI WebSocket disconnected: {connection_id}")
                    break
                except Exception as e:
                    logger.error(f"Error processing AI message: {e}")
                    await self._send_error(
                        connection_id,
                        f"Internal error: {str(e)}",
                        conversation_id
                    )

        except Exception as e:
            logger.error(f"Error in AI WebSocket handler: {e}")

        finally:
            # Cleanup
            if connection_id:
                # Cancel active streams
                if connection_id in self._active_streams:
                    self._active_streams[connection_id].cancel()
                    del self._active_streams[connection_id]

                # Remove conversation lock
                if conversation_id and conversation_id in self._conversation_locks:
                    del self._conversation_locks[conversation_id]

                # Disconnect WebSocket
                await self.ws_manager.disconnect(connection_id)

    async def _route_message(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """
        Route message to appropriate handler.

        Args:
            connection_id: WebSocket connection identifier
            message: Parsed AI WebSocket message
            user_id: User identifier
            session_id: Terminal session identifier
        """
        handlers = {
            "chat": self._handle_chat,
            "stream_chat": self._handle_stream_chat,
            "voice_input": self._handle_voice_input,
            "explain_command": self._handle_explain_command,
            "suggest_commands": self._handle_suggest_commands,
            "cancel_stream": self._handle_cancel_stream,
            "clear_context": self._handle_clear_context,
            "get_context": self._handle_get_context,
            "ping": self._handle_ping,
            "pong": self._handle_pong,
        }

        handler = handlers.get(message.type)
        if handler:
            await handler(connection_id, message, user_id, session_id)
        else:
            await self._send_error(
                connection_id,
                f"Unknown message type: {message.type}",
                message.conversationId
            )

    async def _handle_chat(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """
        Handle regular chat request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
            session_id: Terminal session identifier
        """
        if not session_id:
            await self._send_error(
                connection_id,
                "Session ID required for AI chat",
                message.conversationId
            )
            return

        try:
            # Parse chat data
            chat_data = ChatRequestData(**message.data)

            # Get conversation lock
            conversation_id = message.conversationId or session_id
            if conversation_id not in self._conversation_locks:
                self._conversation_locks[conversation_id] = asyncio.Lock()

            async with self._conversation_locks[conversation_id]:
                # Send processing status
                await self._send_message(
                    connection_id,
                    "processing",
                    {"message": "Processing your request..."},
                    conversation_id
                )

                # Generate response
                start_time = time.time()

                response = await self.ai_service.generate_response(
                    session_id=session_id,
                    user_input=chat_data.message,
                    response_type=ResponseType(chat_data.responseType or "text"),
                    provider=AIProvider(chat_data.provider) if chat_data.provider else None,
                    model=chat_data.model
                )

                processing_time = time.time() - start_time

                # Check for errors
                if response.error:
                    await self._send_error(
                        connection_id,
                        response.error,
                        conversation_id
                    )
                    return

                # Send response
                await self._send_message(
                    connection_id,
                    "chat_response",
                    {
                        "message": response.content,
                        "type": response.message_type.value,
                        "tokens": response.tokens,
                        "processingTime": processing_time,
                        "confidence": response.confidence,
                        "sources": response.sources,
                        "suggestions": response.suggestions
                    },
                    conversation_id
                )

                # Update quota
                await self._send_message(
                    connection_id,
                    "quota_update",
                    {
                        "remaining": self.rate_limiter.get_remaining_quota(
                            user_id or "anonymous"
                        )
                    },
                    conversation_id
                )

                logger.info(
                    f"AI chat completed for {connection_id} in {processing_time:.2f}s"
                )

        except ValidationError as e:
            await self._send_error(
                connection_id,
                f"Invalid chat data: {e}",
                message.conversationId
            )
        except AIProviderRateLimitError as e:
            await self._send_error(
                connection_id,
                "AI service rate limit exceeded. Please try again later.",
                message.conversationId
            )
        except AIProviderQuotaError as e:
            await self._send_error(
                connection_id,
                "AI service quota exceeded. Please upgrade your plan.",
                message.conversationId
            )
        except AIProviderError as e:
            await self._send_error(
                connection_id,
                f"AI service error: {str(e)}",
                message.conversationId
            )
        except Exception as e:
            logger.error(f"Error handling chat: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.conversationId
            )

    async def _handle_stream_chat(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """
        Handle streaming chat request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
            session_id: Terminal session identifier
        """
        if not session_id:
            await self._send_error(
                connection_id,
                "Session ID required for AI chat",
                message.conversationId
            )
            return

        try:
            # Parse chat data
            chat_data = ChatRequestData(**message.data)

            conversation_id = message.conversationId or session_id

            # Create streaming task
            stream_task = asyncio.create_task(
                self._stream_ai_response(
                    connection_id,
                    session_id,
                    chat_data,
                    conversation_id
                )
            )

            self._active_streams[connection_id] = stream_task

            # Wait for completion
            await stream_task

        except ValidationError as e:
            await self._send_error(
                connection_id,
                f"Invalid chat data: {e}",
                message.conversationId
            )
        except Exception as e:
            logger.error(f"Error handling stream chat: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.conversationId
            )

    async def _stream_ai_response(
        self,
        connection_id: str,
        session_id: str,
        chat_data: ChatRequestData,
        conversation_id: str
    ) -> None:
        """
        Stream AI response to client.

        Args:
            connection_id: WebSocket connection identifier
            session_id: Terminal session identifier
            chat_data: Chat request data
            conversation_id: Conversation identifier
        """
        try:
            # Send stream start
            await self._send_message(
                connection_id,
                "stream_start",
                {"message": "Streaming response..."},
                conversation_id
            )

            # Stream response
            async for chunk in self.ai_service.stream_response(
                session_id=session_id,
                user_input=chat_data.message,
                provider=AIProvider(chat_data.provider) if chat_data.provider else None,
                model=chat_data.model
            ):
                await self._send_message(
                    connection_id,
                    "stream_chunk",
                    {"chunk": chunk},
                    conversation_id
                )

            # Send stream end
            await self._send_message(
                connection_id,
                "stream_end",
                {"message": "Stream completed"},
                conversation_id
            )

            logger.info(f"AI streaming completed for {connection_id}")

        except asyncio.CancelledError:
            await self._send_message(
                connection_id,
                "stream_cancelled",
                {"message": "Stream cancelled by user"},
                conversation_id
            )
            logger.info(f"AI streaming cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error streaming AI response: {e}")
            await self._send_error(
                connection_id,
                f"Streaming error: {str(e)}",
                conversation_id
            )

    async def _handle_voice_input(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """
        Handle voice input message.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
            session_id: Terminal session identifier
        """
        try:
            # Parse voice data
            voice_data = VoiceInputData(**message.data)

            # Send acknowledgment
            await self._send_message(
                connection_id,
                "voice_received",
                {
                    "format": voice_data.format,
                    "sampleRate": voice_data.sampleRate,
                    "message": "Voice input processing not yet implemented"
                },
                message.conversationId
            )

            # TODO: Implement speech-to-text conversion
            # For now, just acknowledge receipt

            logger.info(f"Voice input received for {connection_id}")

        except ValidationError as e:
            await self._send_error(
                connection_id,
                f"Invalid voice data: {e}",
                message.conversationId
            )
        except Exception as e:
            logger.error(f"Error handling voice input: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.conversationId
            )

    async def _handle_explain_command(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Handle command explanation request."""
        if not session_id:
            await self._send_error(
                connection_id,
                "Session ID required",
                message.conversationId
            )
            return

        try:
            command = message.data.get("command", "")
            if not command:
                await self._send_error(
                    connection_id,
                    "Command required for explanation",
                    message.conversationId
                )
                return

            response = await self.ai_service.explain_command(session_id, command)

            if response.error:
                await self._send_error(connection_id, response.error, message.conversationId)
                return

            await self._send_message(
                connection_id,
                "explanation",
                {
                    "command": command,
                    "explanation": response.content,
                    "confidence": response.confidence
                },
                message.conversationId
            )

        except Exception as e:
            logger.error(f"Error explaining command: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.conversationId
            )

    async def _handle_suggest_commands(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Handle command suggestion request."""
        if not session_id:
            await self._send_error(
                connection_id,
                "Session ID required",
                message.conversationId
            )
            return

        try:
            goal = message.data.get("goal", "")
            if not goal:
                await self._send_error(
                    connection_id,
                    "Goal required for suggestions",
                    message.conversationId
                )
                return

            response = await self.ai_service.suggest_commands(session_id, goal)

            if response.error:
                await self._send_error(connection_id, response.error, message.conversationId)
                return

            await self._send_message(
                connection_id,
                "suggestions",
                {
                    "goal": goal,
                    "suggestions": response.suggestions or [response.content],
                    "confidence": response.confidence
                },
                message.conversationId
            )

        except Exception as e:
            logger.error(f"Error suggesting commands: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.conversationId
            )

    async def _handle_cancel_stream(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Cancel active stream."""
        if connection_id in self._active_streams:
            self._active_streams[connection_id].cancel()
            del self._active_streams[connection_id]

            await self._send_message(
                connection_id,
                "stream_cancelled",
                {"message": "Stream cancelled"},
                message.conversationId
            )

    async def _handle_clear_context(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Clear conversation context."""
        if session_id:
            self.ai_service.context_manager.clear_cache(session_id)

            await self._send_message(
                connection_id,
                "context_cleared",
                {"message": "Context cleared successfully"},
                message.conversationId
            )

    async def _handle_get_context(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Get context statistics."""
        if not session_id:
            await self._send_error(
                connection_id,
                "Session ID required",
                message.conversationId
            )
            return

        try:
            stats = await self.ai_service.get_context_stats(session_id)

            await self._send_message(
                connection_id,
                "context_stats",
                stats or {},
                message.conversationId
            )

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.conversationId
            )

    async def _handle_ping(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Handle ping message."""
        await self._send_message(
            connection_id,
            "pong",
            {"timestamp": datetime.now(timezone.utc).isoformat()},
            message.conversationId
        )

    async def _handle_pong(
        self,
        connection_id: str,
        message: AIWebSocketMessage,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Handle pong message."""
        connection_info = self.ws_manager.get_connection(connection_id)
        if connection_info:
            connection_info.last_pong = time.time()

    async def _send_message(
        self,
        connection_id: str,
        message_type: str,
        data: Any,
        conversation_id: Optional[str] = None
    ) -> None:
        """
        Send message to WebSocket client.

        Args:
            connection_id: WebSocket connection identifier
            message_type: Message type
            data: Message data
            conversation_id: Optional conversation identifier
        """
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if conversation_id:
            message["conversationId"] = conversation_id

        await self.ws_manager.send_json(connection_id, message)

    async def _send_error(
        self,
        connection_id: str,
        error_message: str,
        conversation_id: Optional[str] = None
    ) -> None:
        """
        Send error message to WebSocket client.

        Args:
            connection_id: WebSocket connection identifier
            error_message: Error message
            conversation_id: Optional conversation identifier
        """
        await self._send_message(
            connection_id,
            "error",
            {"message": error_message},
            conversation_id
        )
        logger.error(f"AI WebSocket error for {connection_id}: {error_message}")


# Global handler instance
ai_handler = AIWebSocketHandler()


async def get_ai_handler() -> AIWebSocketHandler:
    """
    Dependency injection for AI WebSocket handler.

    Returns:
        AIWebSocketHandler instance
    """
    return ai_handler