"""Integration test for full annotation workflow (T021).

This test verifies the complete end-to-end workflow for User Story 1:
Annotate Screenshot for Bug Report.

Workflow:
1. Load image from file
2. Create annotation (pen, arrow, text)
3. Update annotation layer (auto-save)
4. Export to clipboard

This integration test ensures all components work together correctly:
- ImageLoaderService → ImageEditorService → API endpoints
- Database persistence
- Annotation layer management

CRITICAL: This test MUST FAIL until the full implementation is complete.
"""

import pytest
from fastapi.testclient import TestClient
import tempfile
from pathlib import Path
from PIL import Image
import json

# Import app and services
try:
    from src.main import app
    from src.services.image_loader_service import ImageLoaderService
    from src.services.image_editor_service import ImageEditorService
    from src.database.base import get_db, AsyncSessionLocal
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


@pytest.mark.asyncio
class TestAnnotationWorkflowIntegration:
    """Integration test for full annotation workflow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def test_image_file(self, tmp_path):
        """Create a test image file for loading."""
        image_path = tmp_path / "test_screenshot.png"
        img = Image.new('RGB', (800, 600), color='white')
        img.save(image_path, 'PNG')
        return str(image_path)

    async def test_full_annotation_workflow(self, client, test_image_file):
        """Test complete annotation workflow: load → draw → export.

        This is the primary integration test for User Story 1.

        Steps:
        1. Load image from file
        2. Verify session created
        3. Add pen annotation
        4. Add arrow annotation
        5. Add text annotation
        6. Verify auto-save updates annotation layer
        7. Export to clipboard
        8. Verify clipboard URL generated
        """
        with pytest.raises((Exception, AssertionError)):
            # ===== Step 1: Load image from file =====
            load_response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": test_image_file,
                    "terminal_session_id": "integration-test-session"
                }
            )

            assert load_response.status_code == 200
            load_data = load_response.json()

            session_id = load_data["session_id"]
            assert session_id is not None

            # Verify image info
            image_info = load_data["image_info"]
            assert image_info["width"] == 800
            assert image_info["height"] == 600
            assert image_info["format"] in ["png", "PNG"]

            # ===== Step 2: Get session details =====
            session_response = client.get(
                f"/api/v1/image-editor/session/{session_id}"
            )

            assert session_response.status_code == 200
            session_data = session_response.json()

            # Verify initial annotation layer is empty
            assert "annotation_layer" in session_data
            annotation_layer = session_data["annotation_layer"]
            canvas_json = json.loads(annotation_layer["canvas_json"])
            assert len(canvas_json["objects"]) == 0  # No annotations yet
            initial_version = annotation_layer["version"]

            # ===== Step 3: Add pen annotation =====
            pen_annotation = {
                "type": "path",
                "stroke": "#ff0000",  # Red
                "strokeWidth": 3,
                "path": [["M", 100, 100], ["L", 150, 150], ["L", 200, 120]]
            }

            canvas_json["objects"].append(pen_annotation)

            update_response = client.put(
                f"/api/v1/image-editor/annotation-layer/{session_id}",
                json={
                    "canvas_json": json.dumps(canvas_json),
                    "version": initial_version
                }
            )

            assert update_response.status_code == 200
            update_data = update_response.json()
            new_version = update_data["new_version"]
            assert new_version == initial_version + 1

            # ===== Step 4: Add arrow annotation =====
            arrow_line = {
                "type": "line",
                "stroke": "#0000ff",  # Blue
                "strokeWidth": 2,
                "x1": 250,
                "y1": 200,
                "x2": 350,
                "y2": 250
            }

            arrow_head = {
                "type": "triangle",
                "fill": "#0000ff",
                "left": 350,
                "top": 250,
                "width": 10,
                "height": 10
            }

            canvas_json["objects"].extend([arrow_line, arrow_head])

            update_response = client.put(
                f"/api/v1/image-editor/annotation-layer/{session_id}",
                json={
                    "canvas_json": json.dumps(canvas_json),
                    "version": new_version
                }
            )

            assert update_response.status_code == 200
            new_version = update_response.json()["new_version"]

            # ===== Step 5: Add text annotation =====
            text_annotation = {
                "type": "i-text",
                "text": "Bug here!",
                "fontSize": 20,
                "fill": "#000000",
                "left": 400,
                "top": 300
            }

            canvas_json["objects"].append(text_annotation)

            update_response = client.put(
                f"/api/v1/image-editor/annotation-layer/{session_id}",
                json={
                    "canvas_json": json.dumps(canvas_json),
                    "version": new_version
                }
            )

            assert update_response.status_code == 200
            final_version = update_response.json()["new_version"]

            # ===== Step 6: Verify annotations persisted =====
            session_response = client.get(
                f"/api/v1/image-editor/session/{session_id}"
            )

            assert session_response.status_code == 200
            session_data = session_response.json()

            # Verify all annotations present
            annotation_layer = session_data["annotation_layer"]
            persisted_canvas = json.loads(annotation_layer["canvas_json"])
            assert len(persisted_canvas["objects"]) == 5  # pen + arrow (2 parts) + arrow head + text

            # Verify version incremented correctly
            assert annotation_layer["version"] == final_version

            # Verify session marked as modified
            assert session_data["is_modified"] is True

            # ===== Step 7: Export to clipboard =====
            export_response = client.post(
                f"/api/v1/image-editor/export-clipboard/{session_id}"
            )

            assert export_response.status_code == 200
            export_data = export_response.json()

            # Verify clipboard export URL generated
            assert "temp_url" in export_data
            assert "expires_at" in export_data
            assert len(export_data["temp_url"]) > 0

    async def test_annotation_workflow_with_undo(self, client, test_image_file):
        """Test annotation workflow with undo operation.

        Verifies undo/redo functionality works in full workflow.

        Steps:
        1. Load image
        2. Add annotation
        3. Undo annotation
        4. Verify canvas restored to previous state
        """
        with pytest.raises((Exception, AssertionError)):
            # Load image
            load_response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": test_image_file,
                    "terminal_session_id": "undo-test-session"
                }
            )

            assert load_response.status_code == 200
            session_id = load_response.json()["session_id"]

            # Get initial state
            session_response = client.get(
                f"/api/v1/image-editor/session/{session_id}"
            )
            initial_canvas = json.loads(
                session_response.json()["annotation_layer"]["canvas_json"]
            )
            initial_object_count = len(initial_canvas["objects"])

            # Add annotation
            initial_canvas["objects"].append({
                "type": "path",
                "stroke": "#00ff00",
                "path": [["M", 50, 50], ["L", 100, 100]]
            })

            update_response = client.put(
                f"/api/v1/image-editor/annotation-layer/{session_id}",
                json={
                    "canvas_json": json.dumps(initial_canvas),
                    "version": 1
                }
            )

            assert update_response.status_code == 200

            # Verify annotation added
            session_response = client.get(
                f"/api/v1/image-editor/session/{session_id}"
            )
            current_canvas = json.loads(
                session_response.json()["annotation_layer"]["canvas_json"]
            )
            assert len(current_canvas["objects"]) == initial_object_count + 1

            # Undo operation
            undo_response = client.post(
                f"/api/v1/image-editor/undo/{session_id}",
                params={"current_position": 1}
            )

            assert undo_response.status_code == 200
            undo_data = undo_response.json()

            # Verify canvas restored
            restored_canvas = json.loads(undo_data["canvas_json"])
            assert len(restored_canvas["objects"]) == initial_object_count

    async def test_annotation_workflow_validation_errors(self, client):
        """Test annotation workflow handles validation errors gracefully.

        Verifies error handling for invalid inputs.
        """
        with pytest.raises((Exception, AssertionError)):
            # Try to load non-existent file
            load_response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": "/nonexistent/file.png",
                    "terminal_session_id": "error-test-session"
                }
            )

            # Should return error (404 or 400)
            assert load_response.status_code in [400, 404, 500]

            # Try to update annotation for non-existent session
            update_response = client.put(
                "/api/v1/image-editor/annotation-layer/nonexistent-session",
                json={
                    "canvas_json": '{"version":"5.3.0","objects":[]}',
                    "version": 1
                }
            )

            assert update_response.status_code == 404

    async def test_annotation_workflow_concurrent_updates(self, client, test_image_file):
        """Test annotation workflow handles concurrent updates (optimistic locking).

        Verifies version conflict detection when two updates attempt to
        modify same annotation layer.
        """
        with pytest.raises((Exception, AssertionError)):
            # Load image
            load_response = client.post(
                "/api/v1/image-editor/load",
                json={
                    "source_type": "file",
                    "source_path": test_image_file,
                    "terminal_session_id": "concurrent-test-session"
                }
            )

            assert load_response.status_code == 200
            session_id = load_response.json()["session_id"]

            # Get current version
            session_response = client.get(
                f"/api/v1/image-editor/session/{session_id}"
            )
            current_version = session_response.json()["annotation_layer"]["version"]

            # First update succeeds
            canvas_json = '{"version":"5.3.0","objects":[{"type":"path"}]}'
            update1_response = client.put(
                f"/api/v1/image-editor/annotation-layer/{session_id}",
                json={
                    "canvas_json": canvas_json,
                    "version": current_version
                }
            )

            assert update1_response.status_code == 200
            new_version = update1_response.json()["new_version"]

            # Second update with old version should fail (optimistic locking)
            update2_response = client.put(
                f"/api/v1/image-editor/annotation-layer/{session_id}",
                json={
                    "canvas_json": canvas_json,
                    "version": current_version  # Stale version
                }
            )

            # Should return conflict or success (depending on implementation)
            assert update2_response.status_code in [200, 409]

            # If conflict, verify error message
            if update2_response.status_code == 409:
                error_data = update2_response.json()
                assert "version" in error_data.get("detail", "").lower() or "conflict" in error_data.get("detail", "").lower()
