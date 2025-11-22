"""
Unit tests for SessionHistoryService.

Tests:
- T091: add_to_history() with LRU eviction and 20-item limit
- T092: get_history() with ordered retrieval and terminal session filtering
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.session_history_service import SessionHistoryService
from src.models.image_editor import SessionHistory


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def session_history_service():
    """Create SessionHistoryService instance."""
    return SessionHistoryService()


class TestAddToHistory:
    """Tests for SessionHistoryService.add_to_history()."""

    @pytest.mark.asyncio
    async def test_add_new_entry(self, session_history_service, mock_db):
        """Test adding a new entry to history."""
        # Arrange
        terminal_session_id = "test-terminal-123"
        image_path = "/path/to/image.png"

        # Mock database operations
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Act
        result = await session_history_service.add_to_history(
            terminal_session_id=terminal_session_id,
            image_path=image_path,
            db=mock_db
        )

        # Assert
        assert result is not None
        assert result.terminal_session_id == terminal_session_id
        assert result.image_path == image_path
        assert result.view_count == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_entry(self, session_history_service, mock_db):
        """Test updating an existing entry (upsert behavior)."""
        # Arrange
        terminal_session_id = "test-terminal-123"
        image_path = "/path/to/image.png"

        # Mock existing entry
        existing_entry = SessionHistory(
            id="existing-id",
            terminal_session_id=terminal_session_id,
            image_path=image_path,
            last_viewed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            view_count=5
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_entry)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act
        result = await session_history_service.add_to_history(
            terminal_session_id=terminal_session_id,
            image_path=image_path,
            db=mock_db
        )

        # Assert
        assert result.view_count == 6  # Incremented
        assert result.last_viewed_at > existing_entry.last_viewed_at
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_lru_eviction_at_20_items(self, session_history_service, mock_db):
        """Test that oldest entry is evicted when history exceeds 20 items."""
        # Arrange
        terminal_session_id = "test-terminal-123"

        # Mock 20 existing entries
        existing_entries = []
        for i in range(20):
            entry = SessionHistory(
                id=f"entry-{i}",
                terminal_session_id=terminal_session_id,
                image_path=f"/path/to/image{i}.png",
                last_viewed_at=datetime.now(timezone.utc) - timedelta(hours=20-i),
                view_count=1
            )
            existing_entries.append(entry)

        # Mock count query (20 entries)
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=20)

        # Mock oldest entry query
        oldest_result = MagicMock()
        oldest_result.scalar_one_or_none = MagicMock(return_value=existing_entries[0])

        # Mock check for existing entry (new entry doesn't exist)
        check_result = MagicMock()
        check_result.scalar_one_or_none = MagicMock(return_value=None)

        # Setup mock_db.execute to return different results based on call order
        mock_db.execute = AsyncMock(side_effect=[check_result, count_result, oldest_result])
        mock_db.delete = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Act
        result = await session_history_service.add_to_history(
            terminal_session_id=terminal_session_id,
            image_path="/path/to/new_image.png",
            db=mock_db
        )

        # Assert
        assert result is not None
        mock_db.delete.assert_called_once_with(existing_entries[0])  # Oldest entry deleted
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_lru_cache_in_memory(self, session_history_service, mock_db):
        """Test that in-memory LRU cache is maintained."""
        # Arrange
        terminal_session_id = "test-terminal-123"
        image_path1 = "/path/to/image1.png"
        image_path2 = "/path/to/image2.png"

        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Act - Add two entries
        await session_history_service.add_to_history(terminal_session_id, image_path1, mock_db)
        await session_history_service.add_to_history(terminal_session_id, image_path2, mock_db)

        # Assert - Check in-memory cache contains both entries
        cache_key1 = f"{terminal_session_id}:{image_path1}"
        cache_key2 = f"{terminal_session_id}:{image_path2}"
        assert cache_key1 in session_history_service._cache
        assert cache_key2 in session_history_service._cache


class TestGetHistory:
    """Tests for SessionHistoryService.get_history()."""

    @pytest.mark.asyncio
    async def test_get_history_ordered_by_last_viewed(self, session_history_service, mock_db):
        """Test that history is returned ordered by last_viewed_at DESC."""
        # Arrange
        terminal_session_id = "test-terminal-123"
        now = datetime.now(timezone.utc)

        entries = [
            SessionHistory(
                id="entry-1",
                terminal_session_id=terminal_session_id,
                image_path="/path/to/image1.png",
                last_viewed_at=now - timedelta(hours=3),
                view_count=1
            ),
            SessionHistory(
                id="entry-2",
                terminal_session_id=terminal_session_id,
                image_path="/path/to/image2.png",
                last_viewed_at=now - timedelta(hours=1),
                view_count=2
            ),
            SessionHistory(
                id="entry-3",
                terminal_session_id=terminal_session_id,
                image_path="/path/to/image3.png",
                last_viewed_at=now,
                view_count=3
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=entries)))
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_history_service.get_history(
            terminal_session_id=terminal_session_id,
            limit=20,
            db=mock_db
        )

        # Assert
        assert len(result) == 3
        assert result[0].image_path == "/path/to/image3.png"  # Most recent
        assert result[1].image_path == "/path/to/image2.png"
        assert result[2].image_path == "/path/to/image1.png"  # Oldest

    @pytest.mark.asyncio
    async def test_get_history_terminal_session_filtering(self, session_history_service, mock_db):
        """Test that history is filtered by terminal session ID."""
        # Arrange
        terminal_session_id = "test-terminal-123"

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_history_service.get_history(
            terminal_session_id=terminal_session_id,
            limit=20,
            db=mock_db
        )

        # Assert
        mock_db.execute.assert_called_once()
        # Verify the query filters by terminal_session_id
        call_args = mock_db.execute.call_args[0][0]
        assert terminal_session_id in str(call_args)

    @pytest.mark.asyncio
    async def test_get_history_respects_limit(self, session_history_service, mock_db):
        """Test that history respects the limit parameter."""
        # Arrange
        terminal_session_id = "test-terminal-123"

        # Create 25 entries
        entries = []
        for i in range(25):
            entries.append(SessionHistory(
                id=f"entry-{i}",
                terminal_session_id=terminal_session_id,
                image_path=f"/path/to/image{i}.png",
                last_viewed_at=datetime.now(timezone.utc),
                view_count=1
            ))

        # Return only 20 (limit)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=entries[:20])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_history_service.get_history(
            terminal_session_id=terminal_session_id,
            limit=20,
            db=mock_db
        )

        # Assert
        assert len(result) == 20

    @pytest.mark.asyncio
    async def test_get_history_empty(self, session_history_service, mock_db):
        """Test getting history when no entries exist."""
        # Arrange
        terminal_session_id = "test-terminal-123"

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await session_history_service.get_history(
            terminal_session_id=terminal_session_id,
            limit=20,
            db=mock_db
        )

        # Assert
        assert result == []
