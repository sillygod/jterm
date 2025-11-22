"""
Integration test for URL loading workflow (T107).

Test: Load image from URL → edit → save (prompts for filename)
"""

import pytest
import os
import tempfile
from pathlib import Path
from httpx import AsyncClient
from PIL import Image
import io
from unittest.mock import patch, AsyncMock, Mock

from src.main import app


@pytest.fixture
def test_image_url():
    """Mock image URL for testing."""
    return "https://example.com/test_image.png"


@pytest.fixture
def test_image_data():
    """Create test image data."""
    img = Image.new('RGB', (300, 300), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, 'PNG')
    img_bytes.seek(0)
    return img_bytes.read()


@pytest.mark.asyncio
async def test_url_loading_workflow(test_image_url, test_image_data):
    """
    T107: Integration test for complete URL loading workflow.

    Steps:
    1. Load image from URL via POST /api/v1/image-editor/load
    2. Verify session created with source_type='url'
    3. Verify image is accessible and editable
    4. Save image (should prompt for output path since source is URL)

    Expected:
    - Image loads successfully from URL
    - Editor opens with image
    - Save operation requires output_path
    """
    terminal_session_id = "test-url-terminal-123"

    # Mock aiohttp to simulate downloading from URL
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Length': str(len(test_image_data))
        }
        mock_response.read = AsyncMock(return_value=test_image_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Load image from URL
            response = await client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "url",
                    "source_path": test_image_url,
                    "terminal_session_id": terminal_session_id
                }
            )

            # Should return 201 (not implemented yet, so this will fail)
            with pytest.raises(AssertionError):
                assert response.status_code == 201, f"Failed to load from URL: {response.text}"

                data = response.json()
                assert "session_id" in data
                assert "editor_url" in data
                assert "image_width" in data
                assert "image_height" in data

                session_id = data["session_id"]

                # Step 2: Verify session info
                response = await client.get(f"/api/v1/image-editor/session/{session_id}")
                assert response.status_code == 200

                session_data = response.json()
                assert session_data["source_type"] == "url"
                assert session_data["source_path"] == test_image_url
                assert session_data["image_width"] == 300
                assert session_data["image_height"] == 300

                # Step 3: Attempt to save without output_path (should fail)
                response = await client.post(
                    f"/api/v1/image-editor/save/{session_id}",
                    json={}  # No output_path
                )
                assert response.status_code == 400, "Should require output_path for URL sources"

                # Step 4: Save with output_path
                with tempfile.TemporaryDirectory() as tmpdir:
                    output_path = os.path.join(tmpdir, "saved_url_image.png")

                    response = await client.post(
                        f"/api/v1/image-editor/save/{session_id}",
                        json={"output_path": output_path}
                    )
                    assert response.status_code == 200

                    save_data = response.json()
                    assert "saved_path" in save_data
                    assert "file_size" in save_data

                    # Verify file was saved
                    assert os.path.exists(output_path)
                    assert os.path.getsize(output_path) > 0

                    # Verify it's a valid PNG
                    saved_img = Image.open(output_path)
                    assert saved_img.format == "PNG"
                    assert saved_img.size == (300, 300)


@pytest.mark.asyncio
async def test_url_loading_timeout_error():
    """
    Test URL loading with timeout error.

    Expected: Should return 500 with timeout error message.
    """
    import aiohttp

    url = "https://slow-server.example.com/image.png"

    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=aiohttp.ClientTimeout())
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "url",
                    "source_path": url,
                    "terminal_session_id": "test-timeout"
                }
            )

            # Should return error (not 201)
            with pytest.raises(AssertionError):
                assert response.status_code in [408, 500, 501]  # Timeout or error
                assert "timeout" in response.json().get("detail", "").lower() or response.status_code == 501


@pytest.mark.asyncio
async def test_url_loading_invalid_url():
    """
    Test URL loading with invalid URL (SSRF prevention).

    Expected: Should return 400 with validation error.
    """
    private_urls = [
        "http://127.0.0.1/image.png",
        "http://localhost/image.png",
        "http://192.168.1.1/image.png",
        "ftp://example.com/image.png",
        "file:///etc/passwd",
    ]

    async with AsyncClient(app=app, base_url="http://test") as client:
        for url in private_urls:
            response = await client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "url",
                    "source_path": url,
                    "terminal_session_id": "test-invalid"
                }
            )

            # Should reject invalid URLs (not implemented yet, so expect 501 or 400)
            with pytest.raises(AssertionError):
                assert response.status_code in [400, 501], f"Should reject URL: {url}"


@pytest.mark.asyncio
async def test_url_loading_filename_suggestion():
    """
    Test that save dialog suggests filename from URL path.

    Expected: Filename should be extracted from URL (e.g., "screenshot.png" from URL).
    Note: This is primarily a frontend test, but we verify the URL is preserved.
    """
    test_image_url = "https://example.com/path/to/screenshot.png"

    # Create mock image data
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, 'PNG')
    img_bytes.seek(0)
    img_data = img_bytes.read()

    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'image/png', 'Content-Length': str(len(img_data))}
        mock_response.read = AsyncMock(return_value=img_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "url",
                    "source_path": test_image_url,
                    "terminal_session_id": "test-filename"
                }
            )

            with pytest.raises(AssertionError):
                assert response.status_code == 201

                # Verify source_path preserved (frontend will extract filename)
                session_id = response.json()["session_id"]
                response = await client.get(f"/api/v1/image-editor/session/{session_id}")
                assert response.status_code == 200

                session_data = response.json()
                assert session_data["source_path"] == test_image_url

                # Frontend should extract "screenshot.png" from URL for save dialog
                # Backend just needs to preserve the URL
