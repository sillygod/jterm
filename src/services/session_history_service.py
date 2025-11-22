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


def validate_uuid(uuid_string: str, param_name: str = "ID") -> str:
    """
    Validate UUID format for SQL injection prevention (T140).

    Args:
        uuid_string: UUID string to validate
        param_name: Parameter name for error messages

    Returns:
        str: Validated UUID string

    Raises:
        ValueError: If UUID format is invalid
    """
    import uuid as uuid_lib
    import re

    if not uuid_string or not isinstance(uuid_string, str):
        raise ValueError(f"Invalid {param_name}: must be a non-empty string")

    # Remove whitespace and convert to lowercase
    uuid_string = uuid_string.strip().lower()

    # Validate UUID format with regex (8-4-4-4-12 pattern)
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )
    if not uuid_pattern.match(uuid_string):
        raise ValueError(
            f"Invalid {param_name} format: must be a valid UUID "
            f"(e.g., '550e8400-e29b-41d4-a716-446655440000')"
        )

    # Additional validation: try to parse as UUID
    try:
        uuid_lib.UUID(uuid_string)
    except ValueError as e:
        raise ValueError(f"Invalid {param_name}: {str(e)}")

    return uuid_string


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
        # In-memory cache: key = "terminal_id:image_path", value = SessionHistory
        self._cache: OrderedDict[str, SessionHistory] = OrderedDict()

    def _get_cache_key(self, terminal_session_id: str, image_path: str) -> str:
        """Generate cache key from terminal session ID and image path."""
        return f"{terminal_session_id}:{image_path}"

    async def add_to_history(
        self,
        terminal_session_id: str,
        image_path: str,
        db: AsyncSession,
        image_source_type: str = "file"
    ) -> SessionHistory:
        """
        Add or update image in session history.

        Implements LRU eviction when limit is reached.

        Args:
            terminal_session_id: Terminal session ID
            image_path: Image file path or URL
            db: Database session

        Returns:
            SessionHistory: Created or updated history entry
        """
        logger.info(f"Adding to history: {image_path} for session {terminal_session_id}")

        # Check if entry already exists
        stmt = select(SessionHistory).where(
            SessionHistory.terminal_session_id == terminal_session_id,
            SessionHistory.image_path == image_path
        )
        result = await db.execute(stmt)
        existing_entry = result.scalar_one_or_none()

        if existing_entry:
            # Update existing entry (upsert behavior)
            existing_entry.view_count += 1
            existing_entry.last_viewed_at = datetime.now(timezone.utc)
            await db.commit()

            # Update in-memory cache (move to end = most recently used)
            cache_key = self._get_cache_key(terminal_session_id, image_path)
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
            self._cache[cache_key] = existing_entry

            logger.info(f"Updated existing history entry: {existing_entry.id}")
            return existing_entry

        # Check if we need to evict oldest entry (LRU)
        count_stmt = select(func.count()).select_from(SessionHistory).where(
            SessionHistory.terminal_session_id == terminal_session_id
        )
        count_result = await db.execute(count_stmt)
        current_count = count_result.scalar()

        if current_count >= self.MAX_HISTORY_SIZE:
            # Evict oldest entry
            oldest_stmt = select(SessionHistory).where(
                SessionHistory.terminal_session_id == terminal_session_id
            ).order_by(SessionHistory.last_viewed_at.asc()).limit(1)
            oldest_result = await db.execute(oldest_stmt)
            oldest_entry = oldest_result.scalar_one_or_none()

            if oldest_entry:
                logger.info(f"Evicting oldest entry: {oldest_entry.id}")
                await db.delete(oldest_entry)

                # Remove from cache
                oldest_cache_key = self._get_cache_key(
                    oldest_entry.terminal_session_id,
                    oldest_entry.image_path
                )
                self._cache.pop(oldest_cache_key, None)

        # Create new entry
        new_entry = SessionHistory(
            terminal_session_id=terminal_session_id,
            image_path=image_path,
            image_source_type=image_source_type,
            last_viewed_at=datetime.now(timezone.utc),
            view_count=1
        )
        db.add(new_entry)
        await db.commit()
        await db.refresh(new_entry)

        # Add to cache (most recently used)
        cache_key = self._get_cache_key(terminal_session_id, image_path)
        self._cache[cache_key] = new_entry

        logger.info(f"Created new history entry: {new_entry.id}")
        return new_entry

    async def get_history(
        self,
        terminal_session_id: str,
        limit: int,
        db: AsyncSession
    ) -> List[SessionHistory]:
        """
        Retrieve session history for a terminal session.

        Returns entries ordered by most recently viewed.

        Args:
            terminal_session_id: Terminal session ID
            limit: Maximum number of entries to return
            db: Database session

        Returns:
            List[SessionHistory]: History entries, most recent first
        """
        logger.info(f"Retrieving history for session: {terminal_session_id}")

        # Query database for history entries
        stmt = select(SessionHistory).where(
            SessionHistory.terminal_session_id == terminal_session_id
        ).order_by(SessionHistory.last_viewed_at.desc()).limit(limit)

        result = await db.execute(stmt)
        entries = result.scalars().all()

        logger.info(f"Retrieved {len(entries)} history entries")
        return list(entries)

    async def get_entry_by_id(
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

        # T140: Validate UUID to prevent SQL injection
        entry_id = validate_uuid(entry_id, "entry_id")

        stmt = select(SessionHistory).where(SessionHistory.id == entry_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry:
            logger.info(f"Found history entry: {entry_id}")
        else:
            logger.warning(f"History entry not found: {entry_id}")

        return entry

    async def cleanup_old_entries(
        self,
        db: AsyncSession
    ) -> int:
        """
        Clean up history entries older than RETENTION_DAYS.

        Args:
            db: Database session

        Returns:
            int: Number of entries deleted
        """
        logger.info(f"Cleaning up history entries older than {self.RETENTION_DAYS} days")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.RETENTION_DAYS)

        # Get entries to delete (for cache cleanup)
        stmt = select(SessionHistory).where(
            SessionHistory.last_viewed_at < cutoff_date
        )
        result = await db.execute(stmt)
        old_entries = result.scalars().all()

        # Remove from cache
        for entry in old_entries:
            cache_key = self._get_cache_key(entry.terminal_session_id, entry.image_path)
            self._cache.pop(cache_key, None)

        # Delete from database
        delete_stmt = delete(SessionHistory).where(
            SessionHistory.last_viewed_at < cutoff_date
        )
        await db.execute(delete_stmt)
        await db.commit()

        logger.info(f"Deleted {len(old_entries)} expired history entries")
        return len(old_entries)

    async def restore_cache(
        self,
        db: AsyncSession
    ) -> None:
        """
        Restore in-memory cache from database on server start.

        Args:
            db: Database session
        """
        logger.info("Restoring session history cache from database")

        # Load all entries ordered by last_viewed_at (oldest first for OrderedDict)
        stmt = select(SessionHistory).order_by(SessionHistory.last_viewed_at.asc())
        result = await db.execute(stmt)
        entries = result.scalars().all()

        # Rebuild cache
        self._cache.clear()
        for entry in entries:
            cache_key = self._get_cache_key(entry.terminal_session_id, entry.image_path)
            self._cache[cache_key] = entry

        logger.info(f"Restored {len(entries)} entries to cache")
