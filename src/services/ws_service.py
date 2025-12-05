"""WebSocket client service for wscat command."""

import asyncio
import json
import uuid
from typing import Dict, Optional, Set
from datetime import datetime
import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import WebSocketException


class WebSocketConnection:
    """Represents an active WebSocket connection."""

    def __init__(
        self,
        connection_id: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        protocol: Optional[str] = None
    ):
        """Initialize WebSocket connection."""
        self.connection_id = connection_id
        self.url = url
        self.headers = headers or {}
        self.protocol = protocol
        self.client: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.receive_task: Optional[asyncio.Task] = None

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()


class WSService:
    """Service for managing WebSocket connections."""

    def __init__(self):
        """Initialize WebSocket service."""
        self.connections: Dict[str, WebSocketConnection] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_connection_id(self) -> str:
        """Generate a unique connection ID."""
        return str(uuid.uuid4())

    async def connect(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        protocol: Optional[str] = None
    ) -> str:
        """
        Create a new WebSocket connection.

        Args:
            url: WebSocket URL (ws:// or wss://)
            headers: Optional custom headers
            protocol: Optional WebSocket subprotocol

        Returns:
            Connection ID for managing the connection

        Raises:
            WebSocketException: If connection fails
        """
        connection_id = self.create_connection_id()
        connection = WebSocketConnection(
            connection_id=connection_id,
            url=url,
            headers=headers,
            protocol=protocol
        )

        try:
            # Build connection parameters
            extra_headers = {}
            if headers:
                for header in headers:
                    if ':' in header:
                        key, value = header.split(':', 1)
                        extra_headers[key.strip()] = value.strip()

            subprotocols = [protocol] if protocol else None

            # Connect to WebSocket
            connection.client = await websockets.connect(
                url,
                extra_headers=extra_headers if extra_headers else None,
                subprotocols=subprotocols,
                ping_interval=30,
                ping_timeout=10
            )

            connection.connected = True
            connection.update_activity()

            # Store connection
            self.connections[connection_id] = connection

            # Start receiving messages
            connection.receive_task = asyncio.create_task(
                self._receive_loop(connection_id)
            )

            return connection_id

        except Exception as e:
            raise WebSocketException(f"Failed to connect: {str(e)}")

    async def disconnect(self, connection_id: str) -> bool:
        """
        Disconnect and cleanup a WebSocket connection.

        Args:
            connection_id: The connection ID to disconnect

        Returns:
            True if disconnected successfully, False if not found
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        try:
            # Cancel receive task
            if connection.receive_task and not connection.receive_task.done():
                connection.receive_task.cancel()
                try:
                    await connection.receive_task
                except asyncio.CancelledError:
                    pass

            # Close WebSocket
            if connection.client:
                await connection.client.close()

            connection.connected = False

        except Exception:
            pass  # Ignore errors during cleanup
        finally:
            # Remove from connections
            self.connections.pop(connection_id, None)

        return True

    async def send_message(self, connection_id: str, message: str) -> bool:
        """
        Send a message through a WebSocket connection.

        Args:
            connection_id: The connection ID
            message: Message to send

        Returns:
            True if sent successfully, False otherwise

        Raises:
            WebSocketException: If send fails
        """
        connection = self.connections.get(connection_id)
        if not connection or not connection.connected or not connection.client:
            raise WebSocketException("Connection not found or not connected")

        try:
            await connection.client.send(message)
            connection.update_activity()
            return True
        except Exception as e:
            connection.connected = False
            raise WebSocketException(f"Failed to send message: {str(e)}")

    async def receive_message(self, connection_id: str, timeout: float = 0.1) -> Optional[str]:
        """
        Receive a message from the queue (non-blocking).

        Args:
            connection_id: The connection ID
            timeout: Timeout in seconds

        Returns:
            Message string or None if no message available
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return None

        try:
            message = await asyncio.wait_for(
                connection.message_queue.get(),
                timeout=timeout
            )
            return message
        except asyncio.TimeoutError:
            return None

    async def _receive_loop(self, connection_id: str):
        """
        Background task to receive messages and put them in the queue.

        Args:
            connection_id: The connection ID
        """
        connection = self.connections.get(connection_id)
        if not connection or not connection.client:
            return

        try:
            async for message in connection.client:
                if isinstance(message, bytes):
                    message = message.decode('utf-8')

                await connection.message_queue.put(message)
                connection.update_activity()

        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            pass
        except WebSocketException:
            # Connection closed or error
            connection.connected = False
        except Exception:
            # Any other error
            connection.connected = False
        finally:
            connection.connected = False

    def get_connection_status(self, connection_id: str) -> Optional[Dict]:
        """
        Get connection status information.

        Args:
            connection_id: The connection ID

        Returns:
            Dictionary with connection status or None if not found
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return None

        return {
            "connection_id": connection.connection_id,
            "url": connection.url,
            "connected": connection.connected,
            "created_at": connection.created_at.isoformat(),
            "last_activity": connection.last_activity.isoformat(),
            "protocol": connection.protocol
        }

    async def cleanup_inactive_connections(self, max_age_seconds: int = 3600):
        """
        Clean up inactive connections older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup
        """
        now = datetime.utcnow()
        to_remove = []

        for connection_id, connection in self.connections.items():
            age = (now - connection.last_activity).total_seconds()
            if age > max_age_seconds or not connection.connected:
                to_remove.append(connection_id)

        for connection_id in to_remove:
            await self.disconnect(connection_id)

    async def disconnect_all(self):
        """Disconnect all active connections."""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)


# Global service instance
ws_service = WSService()
