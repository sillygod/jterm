"""Integration test for advanced shapes workflow (T117).

This test verifies the complete end-to-end workflow for User Story 7:
Advanced Drawing and Shapes.

Workflow:
1. Load image from file
2. Draw multiple shapes (rectangle, circle, line)
3. Customize shapes (fill, color, stroke width)
4. Select and manipulate shapes
5. Delete shapes
6. Save with shapes persisted

This integration test ensures all components work together correctly:
- Shape creation with Fabric.js
- Fill toggle functionality
- Selection and manipulation
- Database persistence of shapes
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
class TestShapesWorkflowIntegration:
    """Integration test for advanced shapes workflow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def test_image_file(self, tmp_path):
        """Create a test image file for loading."""
        image_path = tmp_path / "test_diagram.png"
        img = Image.new('RGB', (1024, 768), color='white')
        img.save(image_path, 'PNG')
        return str(image_path)

    async def test_shapes_workflow(self, client, test_image_file):
        """Test complete shapes workflow: load → draw shapes → customize → select → delete → save.

        This is the primary integration test for User Story 7.

        Steps:
        1. Load image from file
        2. Draw rectangle with default stroke
        3. Change color and draw another rectangle
        4. Enable fill and draw filled circle
        5. Draw line (verifying Shift snap would be manual UI test)
        6. Select shape
        7. Move selected shape
        8. Delete shape
        9. Save image with shapes
        10. Verify shapes persisted in annotation layer
        """
        # ===== Step 1: Load image from file =====
        load_response = client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_image_file,
                "terminal_session_id": "shapes-test-session"
            }
        )

        assert load_response.status_code == 200
        load_data = load_response.json()

        session_id = load_data["session_id"]
        assert session_id is not None

        # Verify image info
        image_info = load_data["image_info"]
        assert image_info["width"] == 1024
        assert image_info["height"] == 768

        # ===== Step 2: Draw rectangle with default stroke =====
        # Simulate canvas state with rectangle shape
        rectangle_canvas_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 100,
                    "top": 100,
                    "width": 200,
                    "height": 150,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                }
            ]
        }

        save_response = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(rectangle_canvas_state)
            }
        )

        assert save_response.status_code == 200

        # ===== Step 3: Draw another rectangle with different color =====
        two_rectangles_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 100,
                    "top": 100,
                    "width": 200,
                    "height": 150,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                },
                {
                    "type": "rect",
                    "left": 350,
                    "top": 100,
                    "width": 180,
                    "height": 180,
                    "fill": "transparent",
                    "stroke": "#00FF00",
                    "strokeWidth": 3
                }
            ]
        }

        save_response_2 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(two_rectangles_state)
            }
        )

        assert save_response_2.status_code == 200

        # ===== Step 4: Add filled circle =====
        with_circle_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 100,
                    "top": 100,
                    "width": 200,
                    "height": 150,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                },
                {
                    "type": "rect",
                    "left": 350,
                    "top": 100,
                    "width": 180,
                    "height": 180,
                    "fill": "transparent",
                    "stroke": "#00FF00",
                    "strokeWidth": 3
                },
                {
                    "type": "circle",
                    "left": 600,
                    "top": 150,
                    "radius": 80,
                    "fill": "rgba(0, 0, 255, 0.3)",
                    "stroke": "#0000FF",
                    "strokeWidth": 2
                }
            ]
        }

        save_response_3 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(with_circle_state)
            }
        )

        assert save_response_3.status_code == 200

        # ===== Step 5: Add line =====
        with_line_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 100,
                    "top": 100,
                    "width": 200,
                    "height": 150,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                },
                {
                    "type": "rect",
                    "left": 350,
                    "top": 100,
                    "width": 180,
                    "height": 180,
                    "fill": "transparent",
                    "stroke": "#00FF00",
                    "strokeWidth": 3
                },
                {
                    "type": "circle",
                    "left": 600,
                    "top": 150,
                    "radius": 80,
                    "fill": "rgba(0, 0, 255, 0.3)",
                    "stroke": "#0000FF",
                    "strokeWidth": 2
                },
                {
                    "type": "line",
                    "x1": 100,
                    "y1": 400,
                    "x2": 700,
                    "y2": 400,
                    "stroke": "#000000",
                    "strokeWidth": 3
                }
            ]
        }

        save_response_4 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(with_line_state)
            }
        )

        assert save_response_4.status_code == 200

        # ===== Step 6: Simulate shape manipulation (move rectangle) =====
        # In real UI, this would be done via drag-and-drop
        # Here we simulate by updating the canvas state with moved shape
        moved_shape_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 150,  # Moved from 100
                    "top": 120,   # Moved from 100
                    "width": 200,
                    "height": 150,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                },
                {
                    "type": "rect",
                    "left": 350,
                    "top": 100,
                    "width": 180,
                    "height": 180,
                    "fill": "transparent",
                    "stroke": "#00FF00",
                    "strokeWidth": 3
                },
                {
                    "type": "circle",
                    "left": 600,
                    "top": 150,
                    "radius": 80,
                    "fill": "rgba(0, 0, 255, 0.3)",
                    "stroke": "#0000FF",
                    "strokeWidth": 2
                },
                {
                    "type": "line",
                    "x1": 100,
                    "y1": 400,
                    "x2": 700,
                    "y2": 400,
                    "stroke": "#000000",
                    "strokeWidth": 3
                }
            ]
        }

        save_response_5 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(moved_shape_state)
            }
        )

        assert save_response_5.status_code == 200

        # ===== Step 7: Delete a shape (remove the green rectangle) =====
        deleted_shape_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 150,
                    "top": 120,
                    "width": 200,
                    "height": 150,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                },
                # Green rectangle deleted
                {
                    "type": "circle",
                    "left": 600,
                    "top": 150,
                    "radius": 80,
                    "fill": "rgba(0, 0, 255, 0.3)",
                    "stroke": "#0000FF",
                    "strokeWidth": 2
                },
                {
                    "type": "line",
                    "x1": 100,
                    "y1": 400,
                    "x2": 700,
                    "y2": 400,
                    "stroke": "#000000",
                    "strokeWidth": 3
                }
            ]
        }

        save_response_6 = client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={
                "canvas_json": json.dumps(deleted_shape_state)
            }
        )

        assert save_response_6.status_code == 200

        # ===== Step 8: Verify shapes persisted in annotation layer =====
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
        assert len(canvas_state["objects"]) == 3  # Rect, circle, line (green rect deleted)

        # Verify shape types
        shape_types = [obj["type"] for obj in canvas_state["objects"]]
        assert "rect" in shape_types
        assert "circle" in shape_types
        assert "line" in shape_types

        # Verify red rectangle position was updated
        red_rect = next(obj for obj in canvas_state["objects"] if obj["type"] == "rect")
        assert red_rect["left"] == 150
        assert red_rect["top"] == 120

        # Verify circle has fill
        circle = next(obj for obj in canvas_state["objects"] if obj["type"] == "circle")
        assert "rgba" in circle["fill"]  # Filled circle

        # ===== Step 9: Save final image with shapes =====
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

    async def test_shape_undo_redo_integration(self, client, test_image_file):
        """Test undo/redo functionality with shapes.

        This verifies that shape creation is properly added to undo/redo stack.
        """
        # Load image
        load_response = client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_image_file,
                "terminal_session_id": "undo-redo-test-session"
            }
        )

        assert load_response.status_code == 200
        session_id = load_response.json()["session_id"]

        # Draw rectangle (operation 1)
        state_1 = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 100,
                    "top": 100,
                    "width": 150,
                    "height": 100,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                }
            ]
        }

        client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={"canvas_json": json.dumps(state_1)}
        )

        # Draw circle (operation 2)
        state_2 = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 100,
                    "top": 100,
                    "width": 150,
                    "height": 100,
                    "fill": "transparent",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                },
                {
                    "type": "circle",
                    "left": 300,
                    "top": 150,
                    "radius": 60,
                    "fill": "transparent",
                    "stroke": "#0000FF",
                    "strokeWidth": 2
                }
            ]
        }

        client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={"canvas_json": json.dumps(state_2)}
        )

        # Verify current state has both shapes
        session_response = client.get(f"/api/v1/image-editor/session/{session_id}")
        current_state = json.loads(session_response.json()["annotation_layer"]["canvas_json"])
        assert len(current_state["objects"]) == 2

        # Note: Actual undo/redo would be tested through the undo/redo endpoints
        # which would be implemented in T125

    async def test_fill_toggle_persistence(self, client, test_image_file):
        """Test that fill toggle setting is properly persisted in shapes."""
        # Load image
        load_response = client.post(
            "/api/v1/image-editor/load",
            json={
                "source_type": "file",
                "source_path": test_image_file,
                "terminal_session_id": "fill-toggle-test-session"
            }
        )

        assert load_response.status_code == 200
        session_id = load_response.json()["session_id"]

        # Create shape with fill enabled
        filled_state = {
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "left": 100,
                    "top": 100,
                    "width": 200,
                    "height": 150,
                    "fill": "rgba(255, 0, 0, 0.3)",
                    "stroke": "#FF0000",
                    "strokeWidth": 2
                }
            ]
        }

        client.post(
            f"/api/v1/image-editor/session/{session_id}/annotation",
            json={"canvas_json": json.dumps(filled_state)}
        )

        # Verify fill persisted
        session_response = client.get(f"/api/v1/image-editor/session/{session_id}")
        canvas_state = json.loads(session_response.json()["annotation_layer"]["canvas_json"])

        rect = canvas_state["objects"][0]
        assert rect["fill"] != "transparent"
        assert "rgba" in rect["fill"]
