"""Session History Service for tracking recently viewed/edited images.

This service handles:
- Adding images to session history (LRU cache)
- Retrieving history for a terminal session
- Cleaning up expired history entries
"""

import logging
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.sql import func

from src.models.image_editor import SessionHistory, ImageSourceType


logger = logging.getLogger(__name__)


class SessionHistoryError(Exception):
    """Base exception for session history operations."""
    pass


class SessionHistoryService:
    """
    Service for managing session history of viewed/edited images.

    Implements LRU cache with maximum 20 entries per terminal session.
    Uses in-memory OrderedDict for fast access with SQLite backup.
    """

    # Maximum history entries per terminal session
    MAX_HISTORY_SIZE = 20

    # History retention period in days
    RETENTION_DAYS = 7

    def __init__(self):
        """Initialize the session history service."""
        # In-memory cache: {terminal_session_id: OrderedDict({image_path: SessionHistory})}
        self._cache: Dict[str, OrderedDict] = {}

    async def add_to_history(
        self,
        terminal_session_id: str,
        image_path: str,
        source_type: ImageSourceType,
        is_edited: bool,
        thumbnail_path: Optional[str],
        db: AsyncSession
    ) -> SessionHistory:
        """
        Add or update image in session history.

        Implements LRU eviction when limit is reached.

        Args:
            terminal_session_id: Terminal session ID
            image_path: Image file path or URL
            source_type: Source type (file, clipboard, url)
            is_edited: Whether image was edited
            thumbnail_path: Optional thumbnail path
            db: Database session

        Returns:
            SessionHistory: Created or updated history entry
        """
        logger.info(f"Adding to history: {image_path} for session {terminal_session_id}")

        # TODO: Implement add_to_history logic
        # - Check if entry exists in database (terminal_session_id + image_path)
        # - If exists: update last_viewed_at, increment view_count, update is_edited
        # - If new: create new SessionHistory record
        # - Update in-memory cache (move to end for LRU)
        # - If cache exceeds MAX_HISTORY_SIZE, evict oldest entry
        # - Return history entry

        raise NotImplementedError("add_to_history not yet implemented")

    async def get_history(
        self,
        terminal_session_id: str,
        db: AsyncSession,
        limit: int = 20
    ) -> List[SessionHistory]:
        """
        Retrieve session history for a terminal session.

        Returns entries ordered by most recently viewed.

        Args:
            terminal_session_id: Terminal session ID
            db: Database session
            limit: Maximum number of entries to return

        Returns:
            List[SessionHistory]: History entries, most recent first
        """
        logger.info(f"Retrieving history for session: {terminal_session_id}")

        # TODO: Implement get_history logic
        # - Check in-memory cache first
        # - If cache miss, query database
        # - Order by last_viewed_at DESC
        # - Limit to specified count (default 20)
        # - Populate cache for future access
        # - Return list of SessionHistory entries

        raise NotImplementedError("get_history not yet implemented")

    async def get_history_entry(
        self,
        entry_id: str,
        db: AsyncSession
    ) -> Optional[SessionHistory]:
        """
        Get a specific history entry by ID.

        Args:
            entry_id: History entry ID
            db: Database session

        Returns:
            Optional[SessionHistory]: History entry if found
        """
        logger.info(f"Retrieving history entry: {entry_id}")

        # TODO: Implement get_history_entry logic
        # - Query SessionHistory by id
        # - Return entry or None

        raise NotImplementedError("get_history_entry not yet implemented")

    async def cleanup_expired(
        self,
        db: AsyncSession,
        days: int = RETENTION_DAYS
    ) -> int:
        """
        Clean up history entries older than specified days.

        Args:
            db: Database session
            days: Age threshold in days

        Returns:
            int: Number of entries deleted
        """
        logger.info(f"Cleaning up history entries older than {days} days")

        # TODO: Implement cleanup logic
        # - Calculate cutoff timestamp (now - days)
        # - Delete SessionHistory records where last_viewed_at < cutoff
        # - Clear corresponding entries from in-memory cache
        # - Return count of deleted entries

        raise NotImplementedError("cleanup_expired not yet implemented")

    async def restore_cache_from_db(
        self,
        terminal_session_id: str,
        db: AsyncSession
    ) -> None:
        """
        Restore in-memory cache from database on server start or cache miss.

        Args:
            terminal_session_id: Terminal session ID to restore
            db: Database session
        """
        logger.info(f"Restoring cache for session: {terminal_session_id}")

        # TODO: Implement cache restoration logic
        # - Query SessionHistory for terminal_session_id
        # - Order by last_viewed_at DESC
        # - Populate in-memory OrderedDict
        # - Limit to MAX_HISTORY_SIZE entries

        raise NotImplementedError("restore_cache_from_db not yet implemented")

    def _evict_oldest_from_cache(
        self,
        terminal_session_id: str,
        db: AsyncSession
    ) -> None:
        """
        Evict oldest entry from in-memory cache when limit is reached.

        Args:
            terminal_session_id: Terminal session ID
            db: Database session
        """
        # TODO: Implement LRU eviction logic
        # - Get OrderedDict for terminal session
        # - Pop oldest entry (first item)
        # - Database record remains (not deleted, just removed from cache)

        raise NotImplementedError("_evict_oldest_from_cache not yet implemented")

    def clear_cache(self, terminal_session_id: Optional[str] = None) -> None:
        """
        Clear in-memory cache.

        Args:
            terminal_session_id: Optional specific session to clear, or all if None
        """
        if terminal_session_id:
            self._cache.pop(terminal_session_id, None)
            logger.info(f"Cleared cache for session: {terminal_session_id}")
        else:
            self._cache.clear()
            logger.info("Cleared all session history cache")
