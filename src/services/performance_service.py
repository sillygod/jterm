"""Performance monitoring service for system metrics collection.

This service handles server-side and client-side performance metrics collection,
storage, cleanup, and real-time WebSocket push notifications.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.models.performance_snapshot import PerformanceSnapshot
from src.models.user_profile import UserProfile
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class PerformanceServiceError(Exception):
    """Base exception for performance service operations."""
    pass


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration."""
    default_refresh_interval: int = 5000  # milliseconds
    snapshot_retention_hours: int = 24
    cleanup_interval_hours: int = 1
    enable_server_metrics: bool = True
    enable_client_metrics: bool = True


class PerformanceService:
    """
    Service for collecting and managing performance metrics.

    Features:
    - Server-side metrics collection (CPU, memory) using psutil
    - Client-side metrics submission (FPS, memory)
    - Snapshot storage in database
    - Automatic cleanup (24-hour retention)
    - WebSocket push for real-time updates
    - JSON caching for optimization
    """

    def __init__(self, config: Optional[PerformanceConfig] = None):
        """Initialize performance service with configuration."""
        self.config = config or PerformanceConfig()
        self._active_websocket_connections: List[Any] = []
        self._cached_snapshots: Dict[str, Tuple[str, float]] = {}  # (json_string, cache_time)
        self._cleanup_task: Optional[asyncio.Task] = None

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available - server metrics collection will be limited")

    def collect_server_metrics(self) -> Dict[str, Any]:
        """
        Collect server-side performance metrics with psutil.

        Returns:
            Dictionary with CPU%, memory MB, WebSocket count, terminal updates/sec

        Raises:
            PerformanceServiceError: If metrics collection fails
        """
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, returning default values")
            return {
                'cpu_percent': 0.0,
                'memory_mb': 0.0,
                'active_websockets': 0,
                'terminal_updates_per_sec': 0.0
            }

        try:
            # Get CPU percentage (non-blocking, interval=None uses cached value)
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Get memory usage in MB
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)

            # Count active WebSocket connections
            active_websockets = len(self._active_websocket_connections)

            # Terminal updates per second (would be calculated from actual terminal activity)
            # For now, return 0.0 - this would be updated by terminal service
            terminal_updates_per_sec = 0.0

            return {
                'cpu_percent': round(cpu_percent, 2),
                'memory_mb': round(memory_mb, 2),
                'active_websockets': active_websockets,
                'terminal_updates_per_sec': terminal_updates_per_sec
            }

        except Exception as e:
            logger.error(f"Error collecting server metrics: {e}")
            raise PerformanceServiceError(f"Failed to collect server metrics: {str(e)}")

    async def store_snapshot(
        self,
        session_id: str,
        metrics: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> PerformanceSnapshot:
        """
        Store performance snapshot in database.

        Args:
            session_id: Terminal session ID
            metrics: Dictionary with performance metrics
            db: Optional database session

        Returns:
            Created PerformanceSnapshot object

        Raises:
            PerformanceServiceError: If storage fails
        """
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            # Validate timestamp if provided
            timestamp = metrics.get('timestamp')
            if timestamp:
                # Convert ISO string to datetime if needed
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)

            # Create snapshot
            snapshot = PerformanceSnapshot(
                session_id=session_id,
                timestamp=timestamp,
                cpu_percent=metrics.get('cpu_percent', 0.0),
                memory_mb=metrics.get('memory_mb', 0.0),
                active_websockets=metrics.get('active_websockets', 0),
                terminal_updates_per_sec=metrics.get('terminal_updates_per_sec', 0.0),
                client_fps=metrics.get('client_fps'),
                client_memory_mb=metrics.get('client_memory_mb')
            )

            db.add(snapshot)
            await db.commit()
            await db.refresh(snapshot)

            logger.debug(f"Stored performance snapshot: {snapshot.id}")
            return snapshot

        except Exception as e:
            logger.error(f"Error storing performance snapshot: {e}")
            if db:
                await db.rollback()
            raise PerformanceServiceError(f"Failed to store snapshot: {str(e)}")
        finally:
            if close_session:
                await db.close()

    async def cleanup_old_snapshots(self, db: Optional[AsyncSession] = None):
        """
        Background task to delete snapshots older than retention period.

        Args:
            db: Optional database session

        Raises:
            PerformanceServiceError: If cleanup fails
        """
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            # Calculate cutoff time (24 hours ago)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.config.snapshot_retention_hours)

            # Delete old snapshots
            delete_query = delete(PerformanceSnapshot).where(
                PerformanceSnapshot.timestamp < cutoff_time
            )
            result = await db.execute(delete_query)
            await db.commit()

            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old performance snapshots")

        except Exception as e:
            logger.error(f"Error cleaning up old snapshots: {e}")
            if db:
                await db.rollback()
            raise PerformanceServiceError(f"Cleanup failed: {str(e)}")
        finally:
            if close_session:
                await db.close()

    async def start_cleanup_task(self):
        """Start background cleanup task (runs periodically)."""
        if self._cleanup_task is not None:
            logger.warning("Cleanup task already running")
            return

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                    await self.cleanup_old_snapshots()
                except asyncio.CancelledError:
                    logger.info("Cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started performance snapshot cleanup task")

    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped performance snapshot cleanup task")

    def register_websocket(self, ws_connection: Any):
        """
        Register a WebSocket connection for metric updates.

        Args:
            ws_connection: WebSocket connection object
        """
        if ws_connection not in self._active_websocket_connections:
            self._active_websocket_connections.append(ws_connection)
            logger.debug(f"Registered WebSocket connection (total: {len(self._active_websocket_connections)})")

    def unregister_websocket(self, ws_connection: Any):
        """
        Unregister a WebSocket connection.

        Args:
            ws_connection: WebSocket connection object
        """
        if ws_connection in self._active_websocket_connections:
            self._active_websocket_connections.remove(ws_connection)
            logger.debug(f"Unregistered WebSocket connection (total: {len(self._active_websocket_connections)})")

    def get_cached_json(self, snapshot: PerformanceSnapshot, max_age_seconds: float = 1.0) -> Optional[str]:
        """
        Get cached JSON serialization of snapshot.

        Args:
            snapshot: PerformanceSnapshot object
            max_age_seconds: Maximum age of cache in seconds

        Returns:
            Cached JSON string if available and not expired, None otherwise
        """
        cache_key = snapshot.id
        if cache_key not in self._cached_snapshots:
            return None

        json_str, cache_time = self._cached_snapshots[cache_key]

        # Check if expired
        if datetime.now(timezone.utc).timestamp() - cache_time > max_age_seconds:
            del self._cached_snapshots[cache_key]
            return None

        return json_str

    def cache_json(self, snapshot: PerformanceSnapshot, json_str: str):
        """
        Cache JSON serialization of snapshot.

        Args:
            snapshot: PerformanceSnapshot object
            json_str: JSON string to cache
        """
        cache_key = snapshot.id
        cache_time = datetime.now(timezone.utc).timestamp()
        self._cached_snapshots[cache_key] = (json_str, cache_time)

    async def push_metrics_to_clients(self, snapshot: PerformanceSnapshot):
        """
        Push performance metrics via WebSocket to connected clients.

        Args:
            snapshot: PerformanceSnapshot to push

        Implementation:
        - Serialize to JSON (with caching)
        - Broadcast to all active WebSocket connections
        - Handle disconnected clients gracefully
        """
        if not self._active_websocket_connections:
            return

        # Check cache first
        cached_json = self.get_cached_json(snapshot)

        if cached_json:
            json_data = cached_json
        else:
            # Serialize to JSON
            json_data = json.dumps(snapshot.to_dict())
            self.cache_json(snapshot, json_data)

        # Broadcast to active clients
        disconnected = []
        for ws in self._active_websocket_connections:
            try:
                # Assume WebSocket has a send_text method (actual implementation depends on framework)
                if hasattr(ws, 'send_text'):
                    await ws.send_text(json_data)
                elif hasattr(ws, 'send'):
                    await ws.send(json_data)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(ws)

        # Remove disconnected clients
        for ws in disconnected:
            self.unregister_websocket(ws)

    async def get_current_snapshot(
        self,
        session_id: str,
        include_client_metrics: bool = False
    ) -> Dict[str, Any]:
        """
        Get current performance snapshot.

        Args:
            session_id: Terminal session ID
            include_client_metrics: Whether to wait for/include client metrics

        Returns:
            Dictionary with current metrics

        Raises:
            PerformanceServiceError: If metrics collection fails
        """
        try:
            # Collect server metrics
            server_metrics = self.collect_server_metrics()

            # Add session_id and timestamp
            snapshot_data = {
                'session_id': session_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **server_metrics
            }

            return snapshot_data

        except Exception as e:
            logger.error(f"Error getting current snapshot: {e}")
            raise PerformanceServiceError(f"Failed to get current snapshot: {str(e)}")

    async def get_history(
        self,
        minutes: int = 60,
        session_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> List[PerformanceSnapshot]:
        """
        Get historical performance snapshots.

        Args:
            minutes: Time range in minutes (default 60)
            session_id: Optional filter by session ID
            db: Optional database session

        Returns:
            List of PerformanceSnapshot objects

        Raises:
            PerformanceServiceError: If retrieval fails
        """
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            # Calculate time range
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

            # Build query
            query = select(PerformanceSnapshot).where(
                PerformanceSnapshot.timestamp >= cutoff_time
            )

            if session_id:
                query = query.where(PerformanceSnapshot.session_id == session_id)

            query = query.order_by(PerformanceSnapshot.timestamp.desc())

            result = await db.execute(query)
            snapshots = result.scalars().all()

            return list(snapshots)

        except Exception as e:
            logger.error(f"Error getting performance history: {e}")
            raise PerformanceServiceError(f"Failed to get history: {str(e)}")
        finally:
            if close_session:
                await db.close()

    async def update_user_preferences(
        self,
        user_id: str,
        show_metrics: Optional[bool] = None,
        refresh_interval: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> UserProfile:
        """
        Update user performance metrics preferences.

        Args:
            user_id: User ID
            show_metrics: Whether to show performance metrics
            refresh_interval: Refresh interval in milliseconds (1000-60000)
            db: Optional database session

        Returns:
            Updated UserProfile object

        Raises:
            PerformanceServiceError: If update fails
        """
        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            # Get user profile
            query = select(UserProfile).where(UserProfile.user_id == user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise PerformanceServiceError(f"User not found: {user_id}")

            # Update preferences
            if show_metrics is not None:
                user.show_performance_metrics = show_metrics

            if refresh_interval is not None:
                user.performance_metric_refresh_interval = refresh_interval

            await db.commit()
            await db.refresh(user)

            logger.info(f"Updated performance preferences for user: {user_id}")
            return user

        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            if db:
                await db.rollback()
            raise PerformanceServiceError(f"Failed to update preferences: {str(e)}")
        finally:
            if close_session:
                await db.close()


# Global service instance
_performance_service: Optional[PerformanceService] = None


def get_performance_service() -> PerformanceService:
    """Get or create global performance service instance."""
    global _performance_service
    if _performance_service is None:
        _performance_service = PerformanceService()
    return _performance_service
