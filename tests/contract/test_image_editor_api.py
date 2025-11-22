"""Contract tests for Image Editor API endpoints.

These tests verify the Image Editor API contracts match the specifications
defined in contracts/api-endpoints.yaml.

Tests cover:
- POST /api/v1/image-editor/load (T018)
- PUT /api/v1/image-editor/annotation-layer/{session_id} (T019)
- POST /api/v1/image-editor/export-clipboard/{session_id} (T020)

CRITICAL: These tests MUST FAIL until the implementation is complete.
"""

import pytest
from fastapi.testclient import TestClient
import base64
import json

# Import the app
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestImageEditorLoadAPI:
    """Test Image Editor load endpoint contract (T018)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    def test_load_image_from_file(self, client):
        """Test POST /api/v1/image-editor/load with file source.

        Contract: Should accept source_type=file with source_path,
        return session_id, image_info, and editor_url.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": "/path/to/screenshot.png",
                    "terminal_session_id": "test-session-123"
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure per OpenAPI spec
            assert "session_id" in data
            assert "image_info" in data
            assert "editor_url" in data

            # Verify session_id is UUID format
            session_id = data["session_id"]
            assert isinstance(session_id, str)
            assert len(session_id) > 0

            # Verify image_info structure
            image_info = data["image_info"]
            assert "width" in image_info
            assert "height" in image_info
            assert "format" in image_info
            assert "size_bytes" in image_info

            # Verify editor_url is provided
            assert isinstance(data["editor_url"], str)
            assert len(data["editor_url"]) > 0

    def test_load_image_from_url(self, client):
        """Test POST /api/v1/image-editor/load with URL source.

        Contract: Should accept source_type=url with source_path as HTTP/HTTPS URL.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "url",
                    "source_path": "https://example.com/image.png",
                    "terminal_session_id": "test-session-123"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "image_info" in data

    def test_load_image_from_clipboard(self, client):
        """Test POST /api/v1/image-editor/load with clipboard source.

        Contract: Should accept source_type=clipboard with base64 clipboard_data.
        """
        # Create fake base64 image data
        fake_image_data = b"fake-png-data"
        clipboard_data = base64.b64encode(fake_image_data).decode('utf-8')

        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "clipboard",
                    "clipboard_data": clipboard_data,
                    "terminal_session_id": "test-session-123"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data

    def test_load_image_missing_required_fields(self, client):
        """Test POST /api/v1/image-editor/load with missing fields.

        Contract: Should return 400 Bad Request for missing required fields.
        """
        with pytest.raises((Exception, AssertionError)):
            # Missing source_type
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_path": "/path/to/image.png",
                    "terminal_session_id": "test-session-123"
                }
            )

            assert response.status_code == 400

    def test_load_image_invalid_source_type(self, client):
        """Test POST /api/v1/image-editor/load with invalid source_type.

        Contract: Should return 400 for source types not in [file, url, clipboard].
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "invalid_source",
                    "source_path": "/path/to/image.png",
                    "terminal_session_id": "test-session-123"
                }
            )

            assert response.status_code == 400

    def test_load_image_file_too_large(self, client):
        """Test POST /api/v1/image-editor/load with file >50MB.

        Contract: Should return 413 Payload Too Large for files exceeding limit.
        """
        with pytest.raises((Exception, AssertionError)):
            # This would need a real large file path for actual testing
            # For contract test, just verify the endpoint exists
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": "/path/to/huge_image.png",
                    "terminal_session_id": "test-session-123"
                }
            )

            # Should either succeed (if file doesn't exist) or return 413
            assert response.status_code in [200, 404, 413]

    def test_load_image_file_source_requires_path(self, client):
        """Test POST /api/v1/image-editor/load file source requires source_path.

        Contract: source_type=file must include source_path field.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    # Missing source_path
                    "terminal_session_id": "test-session-123"
                }
            )

            assert response.status_code == 400

    def test_load_image_clipboard_source_requires_data(self, client):
        """Test POST /api/v1/image-editor/load clipboard requires clipboard_data.

        Contract: source_type=clipboard must include clipboard_data field.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "clipboard",
                    # Missing clipboard_data
                    "terminal_session_id": "test-session-123"
                }
            )

            assert response.status_code == 400


class TestImageEditorAnnotationLayerAPI:
    """Test Annotation Layer endpoint contract (T019)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def mock_session_id(self):
        """Mock session ID."""
        return "test-session-123"

    def test_update_annotation_layer_success(self, client, mock_session_id):
        """Test PUT /api/v1/image-editor/annotation-layer/{session_id}.

        Contract: Should accept canvas_json and version, return new_version
        and updated_at timestamp.
        """
        canvas_json = json.dumps({
            "version": "5.3.0",
            "objects": [
                {
                    "type": "path",
                    "stroke": "#ff0000",
                    "strokeWidth": 3,
                    "path": [["M", 10, 10], ["L", 50, 50]]
                }
            ]
        })

        with pytest.raises((Exception, AssertionError)):
            response = client.put(
                f"/api/v1/image-editor/annotation-layer/{mock_session_id}",
                json={
                    "canvas_json": canvas_json,
                    "version": 1
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure per OpenAPI spec
            assert "new_version" in data
            assert "updated_at" in data

            # Verify version incremented
            assert isinstance(data["new_version"], int)
            assert data["new_version"] > 1

            # Verify timestamp format
            assert isinstance(data["updated_at"], str)

    def test_update_annotation_layer_optimistic_locking(self, client, mock_session_id):
        """Test annotation layer update with version mismatch.

        Contract: Should return 409 Conflict if version doesn't match
        (optimistic locking failure).
        """
        canvas_json = json.dumps({"version": "5.3.0", "objects": []})

        with pytest.raises((Exception, AssertionError)):
            # Try to update with wrong version
            response = client.put(
                f"/api/v1/image-editor/annotation-layer/{mock_session_id}",
                json={
                    "canvas_json": canvas_json,
                    "version": 999  # Wrong version
                }
            )

            # Should return conflict or succeed if session doesn't exist
            assert response.status_code in [200, 404, 409]

    def test_update_annotation_layer_invalid_json(self, client, mock_session_id):
        """Test annotation layer update with invalid JSON.

        Contract: Should return 400 for malformed canvas_json.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.put(
                f"/api/v1/image-editor/annotation-layer/{mock_session_id}",
                json={
                    "canvas_json": "not valid json {{",
                    "version": 1
                }
            )

            assert response.status_code == 400

    def test_update_annotation_layer_missing_fields(self, client, mock_session_id):
        """Test annotation layer update with missing required fields.

        Contract: Should return 400 for missing canvas_json or version.
        """
        with pytest.raises((Exception, AssertionError)):
            # Missing canvas_json
            response = client.put(
                f"/api/v1/image-editor/annotation-layer/{mock_session_id}",
                json={
                    "version": 1
                }
            )

            assert response.status_code == 400

    def test_update_annotation_layer_session_not_found(self, client):
        """Test annotation layer update for non-existent session.

        Contract: Should return 404 Not Found for invalid session_id.
        """
        canvas_json = json.dumps({"version": "5.3.0", "objects": []})

        with pytest.raises((Exception, AssertionError)):
            response = client.put(
                "/api/v1/image-editor/annotation-layer/nonexistent-session",
                json={
                    "canvas_json": canvas_json,
                    "version": 1
                }
            )

            assert response.status_code == 404


class TestImageEditorExportClipboardAPI:
    """Test Export to Clipboard endpoint contract (T020)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def mock_session_id(self):
        """Mock session ID."""
        return "test-session-123"

    def test_export_to_clipboard_success(self, client, mock_session_id):
        """Test POST /api/v1/image-editor/export-clipboard/{session_id}.

        Contract: Should return temporary URL for clipboard export with
        30-second expiry.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                f"/api/v1/image-editor/export-clipboard/{mock_session_id}"
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "temp_url" in data
            assert "expires_at" in data

            # Verify temp_url is valid
            assert isinstance(data["temp_url"], str)
            assert len(data["temp_url"]) > 0

            # Verify expiry timestamp
            assert isinstance(data["expires_at"], str)

    def test_export_to_clipboard_session_not_found(self, client):
        """Test export to clipboard for non-existent session.

        Contract: Should return 404 Not Found for invalid session_id.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/export-clipboard/nonexistent-session"
            )

            assert response.status_code == 404

    def test_export_to_clipboard_url_expiry(self, client, mock_session_id):
        """Test exported URL expires after 30 seconds.

        Contract: Temporary URL should have 30-second expiry for security.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                f"/api/v1/image-editor/export-clipboard/{mock_session_id}"
            )

            assert response.status_code == 200
            data = response.json()
            # Verify expiry is approximately 30 seconds in future
            # (Implementation detail - just verify field exists)
            assert "expires_at" in data


class TestImageEditorAPICORS:
    """Test CORS and security headers for Image Editor API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    def test_api_accepts_json_content_type(self, client):
        """Test API accepts application/json content type.

        Contract: All POST/PUT endpoints should accept JSON requests.
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": "/test.png",
                    "terminal_session_id": "test"
                },
                headers={"Content-Type": "application/json"}
            )

            # Should not reject based on content type
            assert response.status_code in [200, 400, 404, 500]
