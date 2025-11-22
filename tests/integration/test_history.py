"""
Integration test for session history workflow.

Test: T093 - view multiple images → retrieve history → reopen from history
"""

import pytest
import os
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.database.base import get_db
from src.models.image_editor import SessionHistory


@pytest.fixture
async def test_images(tmp_path):
    """Create test image files."""
    from PIL import Image

    images = []
    for i in range(3):
        img_path = tmp_path / f"test_image_{i}.png"
        img = Image.new('RGB', (100, 100), color=(i * 80, i * 80, i * 80))
        img.save(img_path)
        images.append(str(img_path))

    return images


@pytest.mark.asyncio
async def test_history_workflow(test_images):
    """
    Integration test for complete history workflow:
    1. Load 3 different images via POST /api/v1/image-editor/load
    2. Retrieve history via GET /api/v1/image-editor/history
    3. Verify 3 entries returned in correct order (most recent first)
    4. Reopen second entry via POST /api/v1/image-editor/history/{entry_id}/reopen
    5. Verify new session created with correct image
    """
    terminal_session_id = "test-terminal-integration-123"

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Load 3 images
        session_ids = []
        entry_ids = []

        for i, img_path in enumerate(test_images):
            response = await client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": img_path,
                    "terminal_session_id": terminal_session_id
                }
            )
            assert response.status_code == 201, f"Failed to load image {i}: {response.text}"
            data = response.json()
            assert "session_id" in data
            session_ids.append(data["session_id"])

        # Step 2: Retrieve history
        response = await client.get(
            "/api/v1/image-editor/history",
            params={"terminal_session_id": terminal_session_id, "limit": 20}
        )
        assert response.status_code == 200, f"Failed to get history: {response.text}"

        history_data = response.json()
        assert "history" in history_data
        history = history_data["history"]

        # Step 3: Verify 3 entries in correct order
        assert len(history) == 3, f"Expected 3 history entries, got {len(history)}"

        # Most recent should be last image loaded (test_image_2.png)
        assert test_images[2] in history[0]["image_path"]
        assert test_images[1] in history[1]["image_path"]
        assert test_images[0] in history[2]["image_path"]

        # Verify each entry has required fields
        for entry in history:
            assert "id" in entry
            assert "image_path" in entry
            assert "last_viewed_at" in entry
            assert "view_count" in entry
            assert entry["view_count"] >= 1
            entry_ids.append(entry["id"])

        # Step 4: Reopen second most recent image (test_image_1.png)
        second_entry_id = entry_ids[1]
        response = await client.post(
            f"/api/v1/image-editor/history/{second_entry_id}/reopen"
        )
        assert response.status_code == 201, f"Failed to reopen from history: {response.text}"

        reopen_data = response.json()

        # Step 5: Verify new session created with correct image
        assert "session_id" in reopen_data
        assert "editor_url" in reopen_data
        assert reopen_data["session_id"] not in session_ids  # New session

        # Verify the reopened session has the correct image
        new_session_id = reopen_data["session_id"]
        response = await client.get(f"/api/v1/image-editor/session/{new_session_id}")
        assert response.status_code == 200

        session_data = response.json()
        assert test_images[1] in session_data["source_path"]


@pytest.mark.asyncio
async def test_history_empty(test_images):
    """Test that empty history returns empty array."""
    terminal_session_id = "empty-terminal-session"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/image-editor/history",
            params={"terminal_session_id": terminal_session_id, "limit": 20}
        )
        assert response.status_code == 200

        data = response.json()
        assert "history" in data
        assert data["history"] == []


@pytest.mark.asyncio
async def test_history_lru_eviction(test_images, tmp_path):
    """Test that history is limited to 20 entries (LRU eviction)."""
    from PIL import Image

    terminal_session_id = "lru-test-terminal"

    # Create 25 test images
    image_paths = []
    for i in range(25):
        img_path = tmp_path / f"lru_image_{i}.png"
        img = Image.new('RGB', (50, 50), color=(i * 10, i * 10, i * 10))
        img.save(img_path)
        image_paths.append(str(img_path))

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Load all 25 images
        for img_path in image_paths:
            response = await client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": img_path,
                    "terminal_session_id": terminal_session_id
                }
            )
            assert response.status_code == 201

        # Retrieve history
        response = await client.get(
            "/api/v1/image-editor/history",
            params={"terminal_session_id": terminal_session_id, "limit": 20}
        )
        assert response.status_code == 200

        history_data = response.json()
        history = history_data["history"]

        # Should only have 20 entries (oldest 5 evicted)
        assert len(history) <= 20

        # Most recent 20 should be present (images 5-24)
        history_paths = [entry["image_path"] for entry in history]
        for i in range(5, 25):
            assert any(f"lru_image_{i}.png" in path for path in history_paths)

        # Oldest 5 should be evicted (images 0-4)
        for i in range(5):
            assert not any(f"lru_image_{i}.png" in path for path in history_paths)


@pytest.mark.asyncio
async def test_history_view_count_increment(test_images):
    """Test that view_count increments when same image viewed multiple times."""
    terminal_session_id = "view-count-terminal"

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Load same image 3 times
        for _ in range(3):
            response = await client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": test_images[0],
                    "terminal_session_id": terminal_session_id
                }
            )
            assert response.status_code == 201

        # Retrieve history
        response = await client.get(
            "/api/v1/image-editor/history",
            params={"terminal_session_id": terminal_session_id, "limit": 20}
        )
        assert response.status_code == 200

        history_data = response.json()
        history = history_data["history"]

        # Should only have 1 entry (same image)
        assert len(history) == 1

        # View count should be 3
        assert history[0]["view_count"] == 3


@pytest.mark.asyncio
async def test_history_terminal_session_isolation(test_images):
    """Test that history is isolated per terminal session."""
    terminal_session_1 = "terminal-1"
    terminal_session_2 = "terminal-2"

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Load image in terminal session 1
        response = await client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_images[0],
                "terminal_session_id": terminal_session_1
            }
        )
        assert response.status_code == 201

        # Load different image in terminal session 2
        response = await client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_images[1],
                "terminal_session_id": terminal_session_2
            }
        )
        assert response.status_code == 201

        # Get history for terminal session 1
        response = await client.get(
            "/api/v1/image-editor/history",
            params={"terminal_session_id": terminal_session_1, "limit": 20}
        )
        assert response.status_code == 200
        history_1 = response.json()["history"]

        # Get history for terminal session 2
        response = await client.get(
            "/api/v1/image-editor/history",
            params={"terminal_session_id": terminal_session_2, "limit": 20}
        )
        assert response.status_code == 200
        history_2 = response.json()["history"]

        # Each session should only see its own history
        assert len(history_1) == 1
        assert len(history_2) == 1
        assert test_images[0] in history_1[0]["image_path"]
        assert test_images[1] in history_2[0]["image_path"]
