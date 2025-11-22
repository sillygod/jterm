"""Integration test for text formatting workflow (T128).

This test verifies the complete end-to-end workflow for User Story 8:
Text Annotations with Formatting.

Workflow:
1. Load image from file
2. Add text annotation
3. Apply font size formatting
4. Apply bold formatting
5. Apply italic formatting
6. Enable text background
7. Edit text content
8. Save image with formatted text
9. Verify text formatting persisted

This integration test ensures all components work together correctly:
- Text creation with formatting options
- Format updates on existing text
- Database persistence of formatted text
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from PIL import Image
import json

# Import app and services
try:
    from src.main import app
    from src.database.base import get_db, AsyncSessionLocal
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


@pytest.mark.asyncio
class TestTextFormattingWorkflowIntegration:
    """Integration test for text formatting workflow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def test_image_file(self, tmp_path):
        """Create a test image file for loading."""
        image_path = tmp_path / "test_document.png"
        img = Image.new('RGB', (800, 600), color='white')
        img.save(image_path, 'PNG')
        return str(image_path)

    async def test_text_formatting_workflow(self, client, test_image_file):
        """Test complete text formatting workflow: load → add text → format → edit → save.

        This is the primary integration test for User Story 8.

        Steps:
        1. Load image from file
        2. Add text with default formatting
        3. Change font size to 24pt
        4. Apply bold formatting
        5. Apply italic formatting
        6. Enable text background with color
        7. Verify formatting persisted in annotation layer
        8. Save image with formatted text
        """
        # ===== Step 1: Load image from file =====
        load_response = client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_image_file,
                "terminal_session_id": "text-format-test-session"
            }
        )

        assert load_response.status_code == 200
        load_data = load_response.json()

        session_id = load_data["session_id"]
        assert session_id is not None

        # ===== Step 2: Add text with default formatting =====
        text_default_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Bug here",
                    "fontSize": 18,
                    "fontWeight": "normal",
                    "fontStyle": "normal",
                    "fill": "#ff0000",
                    "fontFamily": "Arial, sans-serif"
                }
            ]
        }

        save_response = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(text_default_state)
            }
        )

        assert save_response.status_code == 200

        # ===== Step 3: Change font size to 24pt =====
        text_font_size_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Bug here",
                    "fontSize": 24,  # Updated from 18
                    "fontWeight": "normal",
                    "fontStyle": "normal",
                    "fill": "#ff0000",
                    "fontFamily": "Arial, sans-serif"
                }
            ]
        }

        save_response_2 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(text_font_size_state)
            }
        )

        assert save_response_2.status_code == 200

        # ===== Step 4: Apply bold formatting =====
        text_bold_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Bug here",
                    "fontSize": 24,
                    "fontWeight": "bold",  # Updated from normal
                    "fontStyle": "normal",
                    "fill": "#ff0000",
                    "fontFamily": "Arial, sans-serif"
                }
            ]
        }

        save_response_3 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(text_bold_state)
            }
        )

        assert save_response_3.status_code == 200

        # ===== Step 5: Apply italic formatting =====
        text_italic_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Bug here",
                    "fontSize": 24,
                    "fontWeight": "bold",
                    "fontStyle": "italic",  # Updated from normal
                    "fill": "#ff0000",
                    "fontFamily": "Arial, sans-serif"
                }
            ]
        }

        save_response_4 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(text_italic_state)
            }
        )

        assert save_response_4.status_code == 200

        # ===== Step 6: Enable text background with yellow color =====
        text_background_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Bug here",
                    "fontSize": 24,
                    "fontWeight": "bold",
                    "fontStyle": "italic",
                    "fill": "#ff0000",
                    "fontFamily": "Arial, sans-serif",
                    "backgroundColor": "rgba(255, 255, 0, 0.8)"  # Yellow background
                }
            ]
        }

        save_response_5 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(text_background_state)
            }
        )

        assert save_response_5.status_code == 200

        # ===== Step 7: Edit text content =====
        text_edited_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Critical Bug Found!",  # Updated text
                    "fontSize": 24,
                    "fontWeight": "bold",
                    "fontStyle": "italic",
                    "fill": "#ff0000",
                    "fontFamily": "Arial, sans-serif",
                    "backgroundColor": "rgba(255, 255, 0, 0.8)"
                }
            ]
        }

        save_response_6 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(text_edited_state)
            }
        )

        assert save_response_6.status_code == 200

        # ===== Step 8: Verify formatting persisted in annotation layer =====
        session_response = client.get(
            f"/api/v1/image-editor/session/{session_id}"
        )

        assert session_response.status_code == 200
        session_data = session_response.json()

        # Verify annotation layer exists
        assert "annotation_layer" in session_data
        annotation_layer = session_data["annotation_layer"]
        assert annotation_layer is not None

        # Parse canvas JSON
        canvas_state = json.loads(annotation_layer["canvas_json"])
        assert len(canvas_state["objects"]) == 1

        # Verify text object
        text_obj = canvas_state["objects"][0]
        assert text_obj["type"] == "i-text"
        assert text_obj["text"] == "Critical Bug Found!"
        assert text_obj["fontSize"] == 24
        assert text_obj["fontWeight"] == "bold"
        assert text_obj["fontStyle"] == "italic"
        assert "rgba(255, 255, 0" in text_obj["backgroundColor"]

        # ===== Step 9: Save final image with formatted text =====
        export_response = client.post(
            f"/api/v1/image-editor/session/{session_id}/export",
            json={
                "format": "png",
                "quality": 95
            }
        )

        assert export_response.status_code == 200
        export_data = export_response.json()

        # Verify export path exists
        assert "file_path" in export_data
        assert Path(export_data["file_path"]).exists()

    async def test_multiple_text_objects_with_different_formatting(self, client, test_image_file):
        """Test multiple text objects with different formatting."""
        # Load image
        load_response = client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_image_file,
                "terminal_session_id": "multi-text-test-session"
            }
        )

        assert load_response.status_code == 200
        session_id = load_response.json()["session_id"]

        # Create multiple text objects with different formatting
        multi_text_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 50,
                    "top": 50,
                    "text": "Title",
                    "fontSize": 48,
                    "fontWeight": "bold",
                    "fill": "#000000"
                },
                {
                    "type": "i-text",
                    "left": 50,
                    "top": 120,
                    "text": "Subtitle",
                    "fontSize": 28,
                    "fontStyle": "italic",
                    "fill": "#666666"
                },
                {
                    "type": "i-text",
                    "left": 50,
                    "top": 180,
                    "text": "Important Note",
                    "fontSize": 20,
                    "fontWeight": "bold",
                    "fontStyle": "italic",
                    "fill": "#ff0000",
                    "backgroundColor": "rgba(255, 255, 0, 0.6)"
                }
            ]
        }

        client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={"canvas_json": json.dumps(multi_text_state)}
        )

        # Verify all text objects persisted with correct formatting
        session_response = client.get(f"/api/v1/image-editor/session/{session_id}")
        canvas_state = json.loads(session_response.json()["annotation_layer"]["canvas_json"])

        assert len(canvas_state["objects"]) == 3

        # Verify title
        title = canvas_state["objects"][0]
        assert title["fontSize"] == 48
        assert title["fontWeight"] == "bold"

        # Verify subtitle
        subtitle = canvas_state["objects"][1]
        assert subtitle["fontSize"] == 28
        assert subtitle["fontStyle"] == "italic"

        # Verify note
        note = canvas_state["objects"][2]
        assert note["fontWeight"] == "bold"
        assert note["fontStyle"] == "italic"
        assert "backgroundColor" in note

    async def test_text_formatting_undo_redo(self, client, test_image_file):
        """Test that text formatting changes are properly tracked in undo/redo."""
        # Load image
        load_response = client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_image_file,
                "terminal_session_id": "text-undo-test-session"
            }
        )

        assert load_response.status_code == 200
        session_id = load_response.json()["session_id"]

        # Add text (state 1)
        state_1 = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Test",
                    "fontSize": 18,
                    "fontWeight": "normal"
                }
            ]
        }

        client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={"canvas_json": json.dumps(state_1)}
        )

        # Apply bold (state 2)
        state_2 = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "i-text",
                    "left": 100,
                    "top": 100,
                    "text": "Test",
                    "fontSize": 18,
                    "fontWeight": "bold"
                }
            ]
        }

        client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={"canvas_json": json.dumps(state_2)}
        )

        # Verify current state has bold
        session_response = client.get(f"/api/v1/image-editor/session/{session_id}")
        current_state = json.loads(session_response.json()["annotation_layer"]["canvas_json"])
        assert current_state["objects"][0]["fontWeight"] == "bold"

        # Note: Actual undo/redo would be tested through undo/redo endpoints
        # which would be implemented in T137
