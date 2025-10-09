"""Session recording WebSocket proxy for transparent event capture.

This handler acts as a transparent proxy between terminal and recording service,
intercepting terminal I/O events with minimal performance impact (<5% overhead),
supporting recording start/stop commands and checkpoint creation.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from src.services.recording_service import (
    RecordingService,
    RecordingError,
    get_recording_service
)
from src.websockets.manager import WebSocketManager, get_websocket_manager


logger = logging.getLogger(__name__)


class RecordingWebSocketMessage(BaseModel):
    """Recording WebSocket message structure."""
    type: str
    data: Any
    sessionId: Optional[str] = None
    recordingId: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StartRecordingData(BaseModel):
    """Data for starting recording."""
    sessionId: str
    compression: bool = True
    checkpointInterval: int = 50


class CheckpointData(BaseModel):
    """Data for creating checkpoint."""
    description: str
    terminalState: Optional[str] = None


class RecordingStatus(str, Enum):
    """Recording status enumeration."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class ProxyStats:
    """Proxy performance statistics."""
    events_proxied: int = 0
    bytes_proxied: int = 0
    proxy_overhead_ms: float = 0.0
    start_time: float = 0.0

    def calculate_overhead_percentage(self, total_time_ms: float) -> float:
        """Calculate overhead as percentage of total time."""
        if total_time_ms == 0:
            return 0.0
        return (self.proxy_overhead_ms / total_time_ms) * 100


class RecordingWebSocketHandler:
    """
    WebSocket handler for session recording proxy.

    Acts as a transparent proxy between terminal and recording service,
    intercepting I/O events with minimal performance impact while supporting
    recording control and status updates.
    """

    def __init__(
        self,
        recording_service: Optional[RecordingService] = None,
        ws_manager: Optional[WebSocketManager] = None
    ):
        """
        Initialize recording WebSocket handler.

        Args:
            recording_service: Recording service instance
            ws_manager: WebSocket manager instance
        """
        self.recording_service = recording_service
        self.ws_manager = ws_manager
        self._active_recordings: Dict[str, str] = {}  # session_id -> recording_id
        self._proxy_stats: Dict[str, ProxyStats] = {}  # session_id -> stats
        self._status: Dict[str, RecordingStatus] = {}  # session_id -> status

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """
        Handle a new recording WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Optional user identifier
            session_id: Optional terminal session identifier
        """
        # Get service instances
        if not self.recording_service:
            self.recording_service = await get_recording_service()
        if not self.ws_manager:
            self.ws_manager = await get_websocket_manager()

        connection_id = None

        try:
            # Register connection
            connection_id = await self.ws_manager.connect(
                websocket,
                user_id=user_id,
                session_id=session_id,
                metadata={"handler": "recording", "sessionId": session_id}
            )

            logger.info(
                f"Recording WebSocket connected: {connection_id} "
                f"(user: {user_id}, session: {session_id})"
            )

            # Send connection established message
            await self._send_message(
                connection_id,
                "connected",
                {
                    "connectionId": connection_id,
                    "sessionId": session_id,
                    "status": self._get_recording_status(session_id),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            # Main message loop
            while True:
                try:
                    # Receive message
                    raw_message = await websocket.receive_json()

                    # Parse and validate message
                    try:
                        message = RecordingWebSocketMessage(**raw_message)
                    except ValidationError as e:
                        await self._send_error(
                            connection_id,
                            f"Invalid message format: {e}",
                            session_id
                        )
                        continue

                    # Route message to appropriate handler
                    await self._route_message(connection_id, message, user_id)

                except WebSocketDisconnect:
                    logger.info(f"Recording WebSocket disconnected: {connection_id}")
                    break
                except Exception as e:
                    logger.error(f"Error processing recording message: {e}")
                    await self._send_error(
                        connection_id,
                        f"Internal error: {str(e)}",
                        session_id
                    )

        except Exception as e:
            logger.error(f"Error in recording WebSocket handler: {e}")

        finally:
            # Cleanup
            if connection_id:
                await self.ws_manager.disconnect(connection_id)

    async def _route_message(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Route message to appropriate handler.

        Args:
            connection_id: WebSocket connection identifier
            message: Parsed recording WebSocket message
            user_id: User identifier
        """
        handlers = {
            "start_recording": self._handle_start_recording,
            "stop_recording": self._handle_stop_recording,
            "pause_recording": self._handle_pause_recording,
            "resume_recording": self._handle_resume_recording,
            "add_checkpoint": self._handle_add_checkpoint,
            "get_status": self._handle_get_status,
            "get_stats": self._handle_get_stats,
            "proxy_input": self._handle_proxy_input,
            "proxy_output": self._handle_proxy_output,
            "proxy_resize": self._handle_proxy_resize,
            "ping": self._handle_ping,
            "pong": self._handle_pong,
        }

        handler = handlers.get(message.type)
        if handler:
            await handler(connection_id, message, user_id)
        else:
            await self._send_error(
                connection_id,
                f"Unknown message type: {message.type}",
                message.sessionId
            )

    async def _handle_start_recording(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Handle start recording request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        try:
            # Parse start data
            start_data = StartRecordingData(**message.data)
            session_id = start_data.sessionId

            # Check if already recording
            if session_id in self._active_recordings:
                await self._send_error(
                    connection_id,
                    f"Recording already active for session {session_id}",
                    session_id
                )
                return

            # Start recording
            recording_id = await self.recording_service.start_recording(session_id)

            # Initialize stats
            self._proxy_stats[session_id] = ProxyStats(start_time=time.time())
            self._active_recordings[session_id] = recording_id
            self._status[session_id] = RecordingStatus.RECORDING

            # Send confirmation
            await self._send_message(
                connection_id,
                "recording_started",
                {
                    "recordingId": recording_id,
                    "sessionId": session_id,
                    "status": RecordingStatus.RECORDING.value
                },
                session_id,
                recording_id
            )

            logger.info(f"Started recording {recording_id} for session {session_id}")

        except ValidationError as e:
            await self._send_error(
                connection_id,
                f"Invalid start data: {e}",
                message.sessionId
            )
        except RecordingError as e:
            await self._send_error(
                connection_id,
                f"Failed to start recording: {e}",
                message.sessionId
            )
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                message.sessionId
            )

    async def _handle_stop_recording(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Handle stop recording request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        session_id = message.sessionId
        if not session_id:
            await self._send_error(connection_id, "Session ID required")
            return

        try:
            recording_id = self._active_recordings.get(session_id)
            if not recording_id:
                await self._send_error(
                    connection_id,
                    f"No active recording for session {session_id}",
                    session_id
                )
                return

            # Stop recording
            await self.recording_service.stop_recording(session_id)

            # Calculate final stats
            stats = self._proxy_stats.get(session_id)
            overhead_pct = 0.0
            if stats:
                total_time_ms = (time.time() - stats.start_time) * 1000
                overhead_pct = stats.calculate_overhead_percentage(total_time_ms)

            # Cleanup
            del self._active_recordings[session_id]
            self._status[session_id] = RecordingStatus.IDLE
            if session_id in self._proxy_stats:
                del self._proxy_stats[session_id]

            # Send confirmation
            await self._send_message(
                connection_id,
                "recording_stopped",
                {
                    "recordingId": recording_id,
                    "sessionId": session_id,
                    "status": RecordingStatus.IDLE.value,
                    "overheadPercentage": overhead_pct
                },
                session_id,
                recording_id
            )

            logger.info(
                f"Stopped recording {recording_id} for session {session_id} "
                f"(overhead: {overhead_pct:.2f}%)"
            )

        except RecordingError as e:
            await self._send_error(
                connection_id,
                f"Failed to stop recording: {e}",
                session_id
            )
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                session_id
            )

    async def _handle_pause_recording(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle pause recording request."""
        session_id = message.sessionId
        if not session_id or session_id not in self._active_recordings:
            await self._send_error(
                connection_id,
                "No active recording to pause",
                session_id
            )
            return

        self._status[session_id] = RecordingStatus.PAUSED

        await self._send_message(
            connection_id,
            "recording_paused",
            {"status": RecordingStatus.PAUSED.value},
            session_id,
            self._active_recordings.get(session_id)
        )

    async def _handle_resume_recording(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle resume recording request."""
        session_id = message.sessionId
        if not session_id or session_id not in self._active_recordings:
            await self._send_error(
                connection_id,
                "No paused recording to resume",
                session_id
            )
            return

        self._status[session_id] = RecordingStatus.RECORDING

        await self._send_message(
            connection_id,
            "recording_resumed",
            {"status": RecordingStatus.RECORDING.value},
            session_id,
            self._active_recordings.get(session_id)
        )

    async def _handle_add_checkpoint(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Handle add checkpoint request.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        session_id = message.sessionId
        if not session_id:
            await self._send_error(connection_id, "Session ID required")
            return

        if session_id not in self._active_recordings:
            await self._send_error(
                connection_id,
                "No active recording for checkpoint",
                session_id
            )
            return

        try:
            # Parse checkpoint data
            checkpoint_data = CheckpointData(**message.data)

            # Add checkpoint
            await self.recording_service.add_checkpoint(
                session_id,
                checkpoint_data.description
            )

            # Send confirmation
            await self._send_message(
                connection_id,
                "checkpoint_added",
                {
                    "description": checkpoint_data.description,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                session_id,
                self._active_recordings.get(session_id)
            )

            logger.info(f"Added checkpoint to recording for session {session_id}")

        except ValidationError as e:
            await self._send_error(
                connection_id,
                f"Invalid checkpoint data: {e}",
                session_id
            )
        except Exception as e:
            logger.error(f"Error adding checkpoint: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                session_id
            )

    async def _handle_get_status(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle get status request."""
        session_id = message.sessionId
        if not session_id:
            await self._send_error(connection_id, "Session ID required")
            return

        status = self._get_recording_status(session_id)
        recording_id = self._active_recordings.get(session_id)

        await self._send_message(
            connection_id,
            "recording_status",
            {
                "status": status.value,
                "recordingId": recording_id,
                "isRecording": status == RecordingStatus.RECORDING
            },
            session_id,
            recording_id
        )

    async def _handle_get_stats(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle get stats request."""
        session_id = message.sessionId
        if not session_id:
            await self._send_error(connection_id, "Session ID required")
            return

        try:
            # Get recording stats from service
            service_stats = await self.recording_service.get_recording_stats(session_id)

            # Get proxy stats
            proxy_stats = self._proxy_stats.get(session_id)
            proxy_data = {}
            if proxy_stats:
                total_time_ms = (time.time() - proxy_stats.start_time) * 1000
                proxy_data = {
                    "eventsProxied": proxy_stats.events_proxied,
                    "bytesProxied": proxy_stats.bytes_proxied,
                    "overheadMs": proxy_stats.proxy_overhead_ms,
                    "overheadPercentage": proxy_stats.calculate_overhead_percentage(total_time_ms)
                }

            await self._send_message(
                connection_id,
                "recording_stats",
                {
                    "serviceStats": service_stats or {},
                    "proxyStats": proxy_data
                },
                session_id,
                self._active_recordings.get(session_id)
            )

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await self._send_error(
                connection_id,
                f"Internal error: {str(e)}",
                session_id
            )

    async def _handle_proxy_input(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Proxy terminal input event with recording.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        session_id = message.sessionId
        if not session_id:
            return

        # Check if recording is active
        if (session_id not in self._active_recordings or
            self._status.get(session_id) != RecordingStatus.RECORDING):
            return

        try:
            # Measure proxy overhead
            start_time = time.time()

            # Record input
            input_data = message.data
            if isinstance(input_data, dict):
                input_data = input_data.get("data", "")

            await self.recording_service.record_input(session_id, input_data)

            # Update stats
            overhead_ms = (time.time() - start_time) * 1000
            stats = self._proxy_stats.get(session_id)
            if stats:
                stats.events_proxied += 1
                stats.bytes_proxied += len(str(input_data).encode('utf-8'))
                stats.proxy_overhead_ms += overhead_ms

        except Exception as e:
            logger.error(f"Error proxying input: {e}")

    async def _handle_proxy_output(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Proxy terminal output event with recording.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        session_id = message.sessionId
        if not session_id:
            return

        # Check if recording is active
        if (session_id not in self._active_recordings or
            self._status.get(session_id) != RecordingStatus.RECORDING):
            return

        try:
            # Measure proxy overhead
            start_time = time.time()

            # Record output
            output_data = message.data
            if isinstance(output_data, dict):
                output_data = output_data.get("data", "")

            await self.recording_service.record_output(session_id, output_data)

            # Update stats
            overhead_ms = (time.time() - start_time) * 1000
            stats = self._proxy_stats.get(session_id)
            if stats:
                stats.events_proxied += 1
                stats.bytes_proxied += len(str(output_data).encode('utf-8'))
                stats.proxy_overhead_ms += overhead_ms

        except Exception as e:
            logger.error(f"Error proxying output: {e}")

    async def _handle_proxy_resize(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """
        Proxy terminal resize event with recording.

        Args:
            connection_id: WebSocket connection identifier
            message: WebSocket message
            user_id: User identifier
        """
        session_id = message.sessionId
        if not session_id:
            return

        # Check if recording is active
        if (session_id not in self._active_recordings or
            self._status.get(session_id) != RecordingStatus.RECORDING):
            return

        try:
            # Measure proxy overhead
            start_time = time.time()

            # Record resize
            resize_data = message.data
            cols = resize_data.get("cols", 80)
            rows = resize_data.get("rows", 24)

            await self.recording_service.resize_terminal(session_id, cols, rows)

            # Update stats
            overhead_ms = (time.time() - start_time) * 1000
            stats = self._proxy_stats.get(session_id)
            if stats:
                stats.events_proxied += 1
                stats.proxy_overhead_ms += overhead_ms

        except Exception as e:
            logger.error(f"Error proxying resize: {e}")

    async def _handle_ping(
        self,
        connection_id: str,
        message: RecordingWebSocketMessage,
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
        message: RecordingWebSocketMessage,
        user_id: Optional[str]
    ) -> None:
        """Handle pong message."""
        connection_info = self.ws_manager.get_connection(connection_id)
        if connection_info:
            connection_info.last_pong = time.time()

    def _get_recording_status(self, session_id: Optional[str]) -> RecordingStatus:
        """
        Get recording status for session.

        Args:
            session_id: Session identifier

        Returns:
            Recording status
        """
        if not session_id:
            return RecordingStatus.IDLE

        return self._status.get(session_id, RecordingStatus.IDLE)

    async def _send_message(
        self,
        connection_id: str,
        message_type: str,
        data: Any,
        session_id: Optional[str] = None,
        recording_id: Optional[str] = None
    ) -> None:
        """
        Send message to WebSocket client.

        Args:
            connection_id: WebSocket connection identifier
            message_type: Message type
            data: Message data
            session_id: Optional session identifier
            recording_id: Optional recording identifier
        """
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if session_id:
            message["sessionId"] = session_id
        if recording_id:
            message["recordingId"] = recording_id

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
        logger.error(f"Recording WebSocket error for {connection_id}: {error_message}")


# Global handler instance
recording_handler = RecordingWebSocketHandler()


async def get_recording_handler() -> RecordingWebSocketHandler:
    """
    Dependency injection for recording WebSocket handler.

    Returns:
        RecordingWebSocketHandler instance
    """
    return recording_handler