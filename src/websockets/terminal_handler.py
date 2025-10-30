"""Terminal session WebSocket handler for real-time PTY communication.

This handler manages WebSocket connections for terminal PTY communication,
integrating with PTYService for process management and supporting bidirectional
message routing, terminal resize events, and session lifecycle management.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from src.services.pty_service import (
    PTYService,
    PTYConfig,
    PTYError,
    PTYProcessTerminatedError,
    get_pty_service
)
from src.services.recording_service import (
    RecordingService,
    get_recording_service
)
from src.websockets.manager import WebSocketManager, get_websocket_manager


logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    type: str
    data: Any
    sessionId: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateSessionData(BaseModel):
    """Data for creating a terminal session."""
    shell: str = "/bin/bash"
    size: Dict[str, int] = Field(default={"cols": 80, "rows": 24})
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None


class ResizeData(BaseModel):
    """Data for resizing terminal."""
    cols: int
    rows: int


class TerminalWebSocketHandler:
    """
    WebSocket handler for terminal session management.

    Handles real-time bidirectional communication between frontend and PTY service,
    including input/output routing, terminal resize, and session lifecycle.
    """

    def __init__(
        self,
        pty_service: Optional[PTYService] = None,
        recording_service: Optional[RecordingService] = None,
        ws_manager: Optional[WebSocketManager] = None
    ):
        """
        Initialize terminal WebSocket handler.

        Args:
            pty_service: PTY service instance
            recording_service: Recording service instance
            ws_manager: WebSocket manager instance
        """
        self.pty_service = pty_service
        self.recording_service = recording_service
        self.ws_manager = ws_manager
        self._active_handlers: Dict[str, asyncio.Task] = {}
        self._decoders: Dict[str, Any] = {}  # UTF-8 decoders per connection

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None
    ) -> None:
        """
        Handle a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Optional user identifier for authentication
        """
        # Get service instances
        if not self.pty_service:
            self.pty_service = await get_pty_service()
        if not self.recording_service:
            self.recording_service = await get_recording_service()
        if not self.ws_manager:
            self.ws_manager = await get_websocket_manager()

        connection_id = None
        session_id = None

        try:
            # Register connection
            connection_id = await self.ws_manager.connect(
                websocket,
                user_id=user_id,
                metadata={"handler": "terminal"}
            )

            logger.info(f"Terminal WebSocket connected: {connection_id}")

            # Send connection established message
            await self._send_message(
                connection_id,
                "connected",
                {
                    "connectionId": connection_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            # Main message loop
            while True:
                try:
                    # Receive message
                    raw_message = await websocket.receive_json()
                    print(f"DEBUG: Received raw message: {raw_message}")

                    # Parse and validate message
                    try:
                        message = WebSocketMessage(**raw_message)
                    except ValidationError as e:
                        await self._send_error(
                            connection_id,
                            f"Invalid message format: {e}",
                            session_id
                        )
                        continue

                    # Update session ID if provided
                    if message.sessionId:
                        session_id = message.sessionId

                    # Route message to appropriate handler
                    await self._route_message(connection_id, message, user_id)

                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {connection_id}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    await self._send_error(
                        connection_id,
                        "Invalid JSON format",
                        session_id
                    )
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._send_error(
                        connection_id,
                        f"Internal error: {str(e)}",
                        session_id
                    )

        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")

        finally:
            # Cleanup
            if connection_id:
                # Stop output handler if exists
                if connection_id in self._active_handlers:
                    self._active_handlers[connection_id].cancel()
                    del self._active_handlers[connection_id]

                # Cleanup PTY if session exists
                if session_id:
                    try:
                        # Clean up decoder
                        if session_id in self._decoders:
                            del self._decoders[session_id]

                        # Force kill the PTY to prevent orphan processes
                        await self.pty_service.destroy_pty(session_id, force=True)
                        logger.info(f"Cleaned up PTY for session {session_id} (force=True)")
                    except Exception as e:
                        logger.error(f"Error cleaning up PTY: {e}")

                # Disconnect WebSocket
                await self.ws_manager.disconnect(connection_id)

    async def _route_message(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Route message to appropriate handler based on type.

        Args:
            connection_id: WebSocket connection identifier
            message: Parsed WebSocket message
            user_id: User identifier
        """
        handlers = {
            "create_session": self._handle_create_session,
            "input": self._handle_input,
            "resize": self._handle_resize,
            "close_session": self._handle_close_session,
            "ping": self._handle_ping,
            "pong": self._handle_pong,
            "start_recording": self._handle_start_recording,
            "stop_recording": self._handle_stop_recording,
        }

        handler = handlers.get(message.type)
        if handler:
            print(f"DEBUG: Routing to handler for message type: {message.type}")
            await handler(connection_id, message, user_id)
        else:
            print(f"DEBUG: No handler found for message type: {message.type}")
            await self._send_error(
                connection_id,
                f"Unknown message type: {message.type}",
                message.sessionId
            )

    async def _handle_create_session(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Handle session creation request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        print(f"DEBUG: _handle_create_session called for connection {connection_id}")
        try:
            # Parse session data
            print(f"DEBUG: Parsing session data: {message.data}")
            session_data = CreateSessionData(**message.data)
            print(f"DEBUG: Session data parsed successfully")

            # Generate session ID
            session_id = str(uuid4())
            print(f"DEBUG: Generated session_id: {session_id}")

            # Create PTY configuration
            import os
            config = PTYConfig(
                shell=session_data.shell,
                cols=session_data.size.get("cols", 80),
                rows=session_data.size.get("rows", 24),
                cwd=session_data.cwd or os.path.expanduser("~"),
                env=session_data.env
            )
            print(f"DEBUG: Created PTY config: shell={config.shell}, cwd={config.cwd}")

            # Create output callback before creating PTY
            print(f"DEBUG: Creating output callback")
            # Create incremental UTF-8 decoder for this session
            import codecs
            decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
            self._decoders[session_id] = decoder

            async def output_callback(data: bytes) -> None:
                """Forward PTY output to WebSocket."""
                try:
                    # Decode output using incremental decoder (handles partial UTF-8 sequences)
                    output_text = decoder.decode(data, False)
                    print(f"DEBUG CALLBACK: Sending {len(output_text)} chars to WebSocket: {repr(output_text[:50])}")

                    # Send to WebSocket
                    await self._send_message(
                        connection_id,
                        "output",
                        output_text,
                        session_id
                    )
                    print(f"DEBUG CALLBACK: Message sent successfully")

                    # Record output if recording is active
                    if self.recording_service:
                        try:
                            print(f"DEBUG: Attempting to record output for session {session_id}: {output_text[:50]}")
                            await self.recording_service.record_output(
                                session_id,
                                output_text
                            )
                        except Exception as e:
                            logger.warning(f"Failed to record output: {e}")

                except Exception as e:
                    logger.error(f"Error in output callback: {e}")

            # Create PTY instance with callback ready
            print(f"DEBUG: About to call pty_service.create_pty")
            pty_instance = await self.pty_service.create_pty(session_id, config)
            print(f"DEBUG: PTY instance created: {pty_instance}")

            # Register callback immediately after PTY creation
            print(f"DEBUG: Registering output callback")
            await self.pty_service.add_output_callback(session_id, output_callback)
            print(f"DEBUG: Output callback registered")

            # Register OSC callback for ebook viewer
            async def ebook_osc_callback(file_path: str):
                """Handle ebook OSC sequence - trigger viewer via WebSocket."""
                logger.info(f"Ebook OSC triggered for file: {file_path}")
                try:
                    # Send WebSocket message to frontend to open ebook viewer
                    await self._send_message(
                        connection_id,
                        "ebook_viewer",
                        {"file_path": file_path, "session_id": session_id},
                        session_id
                    )
                except Exception as e:
                    logger.error(f"Error sending ebook viewer message: {e}")

            await self.pty_service.register_osc_callback(session_id, 'ebook', ebook_osc_callback)
            logger.info(f"Registered ebook OSC callback for session {session_id}")

            # Update connection with session ID
            await self.ws_manager.update_connection_metadata(
                connection_id,
                {"sessionId": session_id}
            )

            # Send session created response
            await self._send_message(
                connection_id,
                "session_created",
                {
                    "sessionId": session_id,
                    "shell": session_data.shell,
                    "size": session_data.size,
                    "pid": pty_instance.process.pid if pty_instance.process else None
                },
                session_id
            )

            # Send welcome message with media commands info
            await asyncio.sleep(0.1)  # Small delay to let shell initialize
            welcome_msg = (
                "\r\n\033[36m✨ Web Terminal Ready!\033[0m\r\n"
                "\033[90mMedia commands available: \033[0m\033[33mimgcat\033[0m\033[90m, \033[0m"
                "\033[33mvidcat\033[0m\033[90m, \033[0m\033[33mmdcat\033[0m\033[90m, \033[0m"
                "\033[33mhtmlcat\033[0m\033[90m, \033[0m\033[33mbookcat\033[0m\r\n\r\n"
            )
            await self._send_message(
                connection_id,
                "output",
                welcome_msg,
                session_id
            )

            logger.info(f"Created terminal session {session_id} for connection {connection_id}")

        except ValidationError as e:
            print(f"DEBUG: ValidationError in _handle_create_session: {e}")
            await self._send_error(connection_id, f"Invalid session data: {e}")
        except PTYError as e:
            print(f"DEBUG: PTYError in _handle_create_session: {e}")
            await self._send_error(connection_id, f"Failed to create session: {e}")
        except Exception as e:
            print(f"DEBUG: Exception in _handle_create_session: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error creating session: {e}")
            await self._send_error(connection_id, f"Internal error: {str(e)}")

    async def _handle_input(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Handle terminal input from client.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        if not message.sessionId:
            await self._send_error(connection_id, "Session ID required for input")
            return

        try:
            # Get input data
            input_data = message.data
            if isinstance(input_data, dict):
                input_data = input_data.get("input", "")

            # Write to PTY
            await self.pty_service.write_to_pty(message.sessionId, input_data)

            # Record input if recording is active
            if self.recording_service:
                try:
                    await self.recording_service.record_input(
                        message.sessionId,
                        input_data
                    )
                except Exception as e:
                    logger.warning(f"Failed to record input: {e}")

        except PTYError as e:
            await self._send_error(
                connection_id,
                f"Failed to send input: {e}",
                message.sessionId
            )
        except Exception as e:
            logger.error(f"Error handling input: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.sessionId
            )

    async def _handle_resize(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Handle terminal resize request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        if not message.sessionId:
            await self._send_error(connection_id, "Session ID required for resize")
            return

        try:
            # Parse resize data
            resize_data = ResizeData(**message.data)

            # Resize PTY
            await self.pty_service.resize_pty(
                message.sessionId,
                resize_data.cols,
                resize_data.rows
            )

            # Record resize if recording is active
            if self.recording_service:
                try:
                    await self.recording_service.resize_terminal(
                        message.sessionId,
                        resize_data.cols,
                        resize_data.rows
                    )
                except Exception as e:
                    logger.warning(f"Failed to record resize: {e}")

            # Send acknowledgment
            await self._send_message(
                connection_id,
                "resize_ack",
                {"cols": resize_data.cols, "rows": resize_data.rows},
                message.sessionId
            )

            logger.debug(
                f"Resized terminal {message.sessionId} to "
                f"{resize_data.cols}x{resize_data.rows}"
            )

        except ValidationError as e:
            await self._send_error(
                connection_id,
                f"Invalid resize data: {e}",
                message.sessionId
            )
        except PTYError as e:
            await self._send_error(
                connection_id,
                f"Failed to resize: {e}",
                message.sessionId
            )
        except Exception as e:
            logger.error(f"Error handling resize: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.sessionId
            )

    async def _handle_close_session(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Handle session close request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        if not message.sessionId:
            await self._send_error(connection_id, "Session ID required")
            return

        try:
            # Stop output handler
            if connection_id in self._active_handlers:
                self._active_handlers[connection_id].cancel()
                del self._active_handlers[connection_id]

            # Destroy PTY
            await self.pty_service.destroy_pty(message.sessionId)

            # Send acknowledgment
            await self._send_message(
                connection_id,
                "session_closed",
                {"sessionId": message.sessionId},
                message.sessionId
            )

            logger.info(f"Closed terminal session {message.sessionId}")

        except PTYError as e:
            await self._send_error(
                connection_id,
                f"Failed to close session: {e}",
                message.sessionId
            )
        except Exception as e:
            logger.error(f"Error closing session: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.sessionId
            )

    async def _handle_ping(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle ping message."""
        await self._send_message(
            connection_id,
            "pong",
            {"timestamp": datetime.now(timezone.utc).isoformat()},
            message.sessionId
        )

    async def _handle_pong(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle pong message."""
        # Update last pong time in connection info
        connection_info = self.ws_manager.get_connection(connection_id)
        if connection_info:
            import time
            connection_info.last_pong = time.time()

    async def _handle_start_recording(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle start recording request."""
        if not message.sessionId:
            await self._send_error(connection_id, "Session ID required")
            return

        try:
            recording_id = await self.recording_service.start_recording(
                message.sessionId
            )

            await self._send_message(
                connection_id,
                "recording_started",
                {"recordingId": recording_id},
                message.sessionId
            )

            logger.info(f"Started recording {recording_id} for session {message.sessionId}")

        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            await self._send_error(
                connection_id,
                f"Failed to start recording: {str(e)}",
                message.sessionId
            )

    async def _handle_stop_recording(
        self,
        connection_id: str,
        message: WebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle stop recording request."""
        if not message.sessionId:
            await self._send_error(connection_id, "Session ID required")
            return

        try:
            await self.recording_service.stop_recording(message.sessionId)

            await self._send_message(
                connection_id,
                "recording_stopped",
                {"sessionId": message.sessionId},
                message.sessionId
            )

            logger.info(f"Stopped recording for session {message.sessionId}")

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            await self._send_error(
                connection_id,
                f"Failed to stop recording: {str(e)}",
                message.sessionId
            )

    async def _handle_pty_output(
        self,
        connection_id: str,
        session_id: str
    ) -> None:
        """
        Handle PTY output and forward to WebSocket.

        Args:
            connection_id: WebSocket connection identifier
            session_id: Terminal session identifier
        """
        try:
            # Create callback for PTY output
            async def output_callback(data: bytes) -> None:
                """Forward PTY output to WebSocket."""
                try:
                    # Decode output
                    output_text = data.decode('utf-8', errors='replace')

                    # Send to WebSocket
                    await self._send_message(
                        connection_id,
                        "output",
                        output_text,
                        session_id
                    )

                    # Record output if recording is active
                    if self.recording_service:
                        try:
                            print(f"DEBUG: Attempting to record output for session {session_id}: {output_text[:50]}")
                            await self.recording_service.record_output(
                                session_id,
                                output_text
                            )
                        except Exception as e:
                            logger.warning(f"Failed to record output: {e}")

                except Exception as e:
                    logger.error(f"Error in output callback: {e}")

            # Register callback with PTY service
            await self.pty_service.add_output_callback(session_id, output_callback)

            logger.debug(f"Started PTY output handler for session {session_id}")

        except Exception as e:
            logger.error(f"Error in PTY output handler: {e}")

    async def _send_message(
        self,
        connection_id: str,
        message_type: str,
        data: Any,
        session_id: Optional[str] = None
    ) -> None:
        """
        Send message to WebSocket client.

        Args:
            connection_id: WebSocket connection identifier
            message_type: Message type
            data: Message data
            session_id: Optional session identifier
        """
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if session_id:
            message["sessionId"] = session_id

        await self.ws_manager.send_json(connection_id, message)

    async def _send_error(
        self,
        connection_id: str,
        error_message: str,
        session_id: Optional[str] = None
    ) -> None:
        """
        Send error message to WebSocket client.

        Args:
            connection_id: WebSocket connection identifier
            error_message: Error message
            session_id: Optional session identifier
        """
        await self._send_message(
            connection_id,
            "error",
            {"message": error_message},
            session_id
        )
        logger.error(f"WebSocket error for {connection_id}: {error_message}")


# Global handler instance
terminal_handler = TerminalWebSocketHandler()


async def get_terminal_handler() -> TerminalWebSocketHandler:
    """
    Dependency injection for terminal WebSocket handler.

    Returns:
        TerminalWebSocketHandler instance
    """
    return terminal_handler