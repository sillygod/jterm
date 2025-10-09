"""WebSocket connection manager for Web Terminal.

This module manages WebSocket connections with lifecycle management, connection pooling,
health checks, and broadcast capabilities for multiple clients.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Set, Optional, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect


logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """WebSocket connection state enumeration."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """WebSocket connection information."""
    connection_id: str
    websocket: WebSocket
    user_id: Optional[str]
    session_id: Optional[str]
    state: ConnectionState
    connected_at: datetime
    last_ping: float = field(default_factory=time.time)
    last_pong: float = field(default_factory=time.time)
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_alive(self) -> bool:
        """Check if connection is alive based on ping/pong."""
        return time.time() - self.last_pong < 60.0  # 60 second timeout

    def to_dict(self) -> Dict[str, Any]:
        """Convert connection info to dictionary."""
        return {
            "connectionId": self.connection_id,
            "userId": self.user_id,
            "sessionId": self.session_id,
            "state": self.state.value,
            "connectedAt": self.connected_at.isoformat(),
            "messagesSent": self.messages_sent,
            "messagesReceived": self.messages_received,
            "bytesSent": self.bytes_sent,
            "bytesReceived": self.bytes_received,
            "isAlive": self.is_alive(),
            "metadata": self.metadata
        }


class WebSocketManager:
    """Manages WebSocket connections with lifecycle and health monitoring."""

    def __init__(self):
        """Initialize WebSocket manager."""
        self._connections: Dict[str, ConnectionInfo] = {}
        self._user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self._session_connections: Dict[str, Set[str]] = {}  # session_id -> connection_ids
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the WebSocket manager."""
        if not self._running:
            self._running = True
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        # Disconnect all connections
        await self.disconnect_all()
        logger.info("WebSocket manager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Register a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Optional connection metadata

        Returns:
            Connection ID
        """
        connection_id = str(uuid4())

        async with self._lock:
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                websocket=websocket,
                user_id=user_id,
                session_id=session_id,
                state=ConnectionState.CONNECTING,
                connected_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )

            # Accept the WebSocket connection
            try:
                await websocket.accept()
                connection_info.state = ConnectionState.CONNECTED
            except Exception as e:
                logger.error(f"Failed to accept WebSocket connection: {e}")
                connection_info.state = ConnectionState.ERROR
                raise

            # Store connection
            self._connections[connection_id] = connection_info

            # Index by user and session
            if user_id:
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = set()
                self._user_connections[user_id].add(connection_id)

            if session_id:
                if session_id not in self._session_connections:
                    self._session_connections[session_id] = set()
                self._session_connections[session_id].add(connection_id)

            logger.info(
                f"WebSocket connected: {connection_id} "
                f"(user: {user_id}, session: {session_id})"
            )

        return connection_id

    async def disconnect(self, connection_id: str, code: int = 1000) -> None:
        """
        Disconnect a WebSocket connection.

        Args:
            connection_id: Connection identifier
            code: WebSocket close code
        """
        async with self._lock:
            connection_info = self._connections.get(connection_id)
            if not connection_info:
                return

            # Close WebSocket
            try:
                await connection_info.websocket.close(code=code)
            except Exception as e:
                logger.error(f"Error closing WebSocket {connection_id}: {e}")

            connection_info.state = ConnectionState.DISCONNECTED

            # Remove from indices
            if connection_info.user_id:
                if connection_info.user_id in self._user_connections:
                    self._user_connections[connection_info.user_id].discard(connection_id)
                    if not self._user_connections[connection_info.user_id]:
                        del self._user_connections[connection_info.user_id]

            if connection_info.session_id:
                if connection_info.session_id in self._session_connections:
                    self._session_connections[connection_info.session_id].discard(connection_id)
                    if not self._session_connections[connection_info.session_id]:
                        del self._session_connections[connection_info.session_id]

            # Remove connection
            del self._connections[connection_id]

            logger.info(f"WebSocket disconnected: {connection_id}")

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocket connections."""
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)

    async def send_json(
        self,
        connection_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Send JSON message to a specific connection.

        Args:
            connection_id: Connection identifier
            data: JSON-serializable data

        Returns:
            True if sent successfully, False otherwise
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info or connection_info.state != ConnectionState.CONNECTED:
            return False

        try:
            await connection_info.websocket.send_json(data)
            connection_info.messages_sent += 1
            connection_info.bytes_sent += len(str(data).encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Error sending to WebSocket {connection_id}: {e}")
            connection_info.state = ConnectionState.ERROR
            await self.disconnect(connection_id)
            return False

    async def send_text(
        self,
        connection_id: str,
        text: str
    ) -> bool:
        """
        Send text message to a specific connection.

        Args:
            connection_id: Connection identifier
            text: Text message

        Returns:
            True if sent successfully, False otherwise
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info or connection_info.state != ConnectionState.CONNECTED:
            return False

        try:
            await connection_info.websocket.send_text(text)
            connection_info.messages_sent += 1
            connection_info.bytes_sent += len(text.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Error sending to WebSocket {connection_id}: {e}")
            connection_info.state = ConnectionState.ERROR
            await self.disconnect(connection_id)
            return False

    async def send_bytes(
        self,
        connection_id: str,
        data: bytes
    ) -> bool:
        """
        Send binary message to a specific connection.

        Args:
            connection_id: Connection identifier
            data: Binary data

        Returns:
            True if sent successfully, False otherwise
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info or connection_info.state != ConnectionState.CONNECTED:
            return False

        try:
            await connection_info.websocket.send_bytes(data)
            connection_info.messages_sent += 1
            connection_info.bytes_sent += len(data)
            return True
        except Exception as e:
            logger.error(f"Error sending to WebSocket {connection_id}: {e}")
            connection_info.state = ConnectionState.ERROR
            await self.disconnect(connection_id)
            return False

    async def broadcast_json(
        self,
        data: Dict[str, Any],
        connection_ids: Optional[List[str]] = None
    ) -> int:
        """
        Broadcast JSON message to multiple connections.

        Args:
            data: JSON-serializable data
            connection_ids: Optional list of specific connection IDs (broadcasts to all if None)

        Returns:
            Number of successful sends
        """
        if connection_ids is None:
            connection_ids = list(self._connections.keys())

        success_count = 0
        for connection_id in connection_ids:
            if await self.send_json(connection_id, data):
                success_count += 1

        return success_count

    async def broadcast_to_session(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Broadcast message to all connections in a session.

        Args:
            session_id: Session identifier
            data: JSON-serializable data

        Returns:
            Number of successful sends
        """
        connection_ids = self._session_connections.get(session_id, set())
        return await self.broadcast_json(data, list(connection_ids))

    async def broadcast_to_user(
        self,
        user_id: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Broadcast message to all connections for a user.

        Args:
            user_id: User identifier
            data: JSON-serializable data

        Returns:
            Number of successful sends
        """
        connection_ids = self._user_connections.get(user_id, set())
        return await self.broadcast_json(data, list(connection_ids))

    async def ping(self, connection_id: str) -> bool:
        """
        Send ping to a connection.

        Args:
            connection_id: Connection identifier

        Returns:
            True if ping sent successfully
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info or connection_info.state != ConnectionState.CONNECTED:
            return False

        try:
            # Send ping frame
            await connection_info.websocket.send_json({
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            connection_info.last_ping = time.time()
            return True
        except Exception as e:
            logger.error(f"Error sending ping to {connection_id}: {e}")
            return False

    async def update_connection_metadata(
        self,
        connection_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update connection metadata.

        Args:
            connection_id: Connection identifier
            metadata: Metadata to update

        Returns:
            True if updated successfully
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info:
            return False

        connection_info.metadata.update(metadata)
        return True

    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """
        Get connection information.

        Args:
            connection_id: Connection identifier

        Returns:
            ConnectionInfo or None
        """
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> List[ConnectionInfo]:
        """
        Get all connections for a user.

        Args:
            user_id: User identifier

        Returns:
            List of ConnectionInfo objects
        """
        connection_ids = self._user_connections.get(user_id, set())
        return [
            self._connections[conn_id]
            for conn_id in connection_ids
            if conn_id in self._connections
        ]

    def get_session_connections(self, session_id: str) -> List[ConnectionInfo]:
        """
        Get all connections for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of ConnectionInfo objects
        """
        connection_ids = self._session_connections.get(session_id, set())
        return [
            self._connections[conn_id]
            for conn_id in connection_ids
            if conn_id in self._connections
        ]

    def get_all_connections(self) -> List[ConnectionInfo]:
        """
        Get all active connections.

        Returns:
            List of ConnectionInfo objects
        """
        return list(self._connections.values())

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Statistics dictionary
        """
        total_messages_sent = sum(c.messages_sent for c in self._connections.values())
        total_messages_received = sum(c.messages_received for c in self._connections.values())
        total_bytes_sent = sum(c.bytes_sent for c in self._connections.values())
        total_bytes_received = sum(c.bytes_received for c in self._connections.values())

        return {
            "total_connections": len(self._connections),
            "total_users": len(self._user_connections),
            "total_sessions": len(self._session_connections),
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received,
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
            "connections": [c.to_dict() for c in self._connections.values()]
        }

    async def _health_check_loop(self) -> None:
        """Background task for health checking connections."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check for dead connections
                dead_connections = []
                for connection_id, connection_info in self._connections.items():
                    if not connection_info.is_alive():
                        dead_connections.append(connection_id)
                        logger.warning(
                            f"Connection {connection_id} appears dead "
                            f"(last pong: {time.time() - connection_info.last_pong:.1f}s ago)"
                        )

                # Disconnect dead connections
                for connection_id in dead_connections:
                    await self.disconnect(connection_id, code=1001)

                # Send ping to all connections
                for connection_id in list(self._connections.keys()):
                    await self.ping(connection_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")


# Global WebSocket manager instance
ws_manager = WebSocketManager()


async def get_websocket_manager() -> WebSocketManager:
    """
    Dependency injection for WebSocket manager.

    Returns:
        WebSocketManager instance
    """
    return ws_manager