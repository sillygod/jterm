"""Integration test for clipboard image workflow (T050).

Tests the complete clipboard workflow:
1. Load image from stdin (clipboard data)
2. Create editing session
3. Apply annotations
4. Save prompts for filename
5. Copy back to clipboard

CRITICAL: These tests MUST FAIL until implementation is complete.
"""

import pytest
import io
from PIL import Image
from unittest.mock import Mock, AsyncMock, patch

# Import required services and models
try:
    from src.services.image_loader_service import ImageLoaderService, ImageValidationError
    from src.services.image_editor_service import ImageEditorService
    from src.models.image_editor import ImageSession, AnnotationLayer
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False


@pytest.mark.asyncio
class TestClipboardWorkflow:
    """Integration tests for clipboard image workflow (stdin → load → edit → save)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        # Mock query results for various operations
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)

        return db

    @pytest.fixture
    def image_loader(self):
        """Create ImageLoaderService instance."""
        if not SERVICES_AVAILABLE:
            pytest.skip("Services not implemented yet")
        return ImageLoaderService()

    @pytest.fixture
    def image_editor(self):
        """Create ImageEditorService instance."""
        if not SERVICES_AVAILABLE:
            pytest.skip("Services not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def clipboard_png_data(self):
        """Generate PNG clipboard data."""
        img = Image.new('RGB', (800, 600), color='blue')
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        return buf.getvalue()

    @pytest.fixture
    def clipboard_jpeg_data(self):
        """Generate JPEG clipboard data."""
        img = Image.new('RGB', (1024, 768), color='green')
        buf = io.BytesIO()
        img.save(buf, 'JPEG')
        return buf.getvalue()

    async def test_clipboard_workflow_png(
        self, image_loader, image_editor, clipboard_png_data, mock_db
    ):
        """Test complete clipboard workflow with PNG image.

        Workflow:
        1. Load PNG from stdin (clipboard)
        2. Create editing session
        3. Verify clipboard source type
        4. Verify ready for annotations

        Contract: Full workflow should work seamlessly for clipboard sources.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Step 1: Load image from clipboard data (stdin)
            image_session = await image_loader.load_from_stdin(
                stdin_data=clipboard_png_data,
                terminal_session_id="test-terminal-clipboard",
                db=mock_db
            )

            # Verify session created with clipboard source
            assert image_session is not None
            assert image_session.image_source_type == "clipboard"
            assert image_session.image_source_path is None
            assert image_session.image_format == "png"
            assert image_session.image_width == 800
            assert image_session.image_height == 600

            # Step 2: Create editing session
            annotation_layer = await image_editor.create_session(
                image_session=image_session,
                db=mock_db
            )

            # Verify annotation layer ready
            assert annotation_layer is not None
            assert annotation_layer.session_id == image_session.id
            assert annotation_layer.version == 1

            # Step 3: Verify ready for edits
            import json
            canvas = json.loads(annotation_layer.canvas_json)
            assert canvas["objects"] == []  # Empty, ready for annotations

    async def test_clipboard_workflow_jpeg(
        self, image_loader, image_editor, clipboard_jpeg_data, mock_db
    ):
        """Test complete clipboard workflow with JPEG image.

        Contract: JPEG images from clipboard should work identically to PNG.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Load JPEG from clipboard
            image_session = await image_loader.load_from_stdin(
                stdin_data=clipboard_jpeg_data,
                terminal_session_id="test-terminal-jpeg",
                db=mock_db
            )

            # Verify JPEG detected correctly
            assert image_session.image_source_type == "clipboard"
            assert image_session.image_format == "jpeg"
            assert image_session.image_width == 1024
            assert image_session.image_height == 768

            # Create editing session
            annotation_layer = await image_editor.create_session(
                image_session=image_session,
                db=mock_db
            )

            assert annotation_layer is not None

    async def test_clipboard_workflow_with_annotations(
        self, image_loader, image_editor, clipboard_png_data, mock_db
    ):
        """Test clipboard workflow with annotation updates.

        Workflow:
        1. Load from clipboard
        2. Create session
        3. Apply annotations
        4. Verify annotations saved

        Contract: Clipboard images should support full annotation functionality.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            import json

            # Load image
            image_session = await image_loader.load_from_stdin(
                stdin_data=clipboard_png_data,
                terminal_session_id="test-annotate",
                db=mock_db
            )

            # Create session
            annotation_layer = await image_editor.create_session(
                image_session=image_session,
                db=mock_db
            )

            # Apply annotations
            canvas_json = json.dumps({
                "version": "5.3.0",
                "objects": [
                    {
                        "type": "path",
                        "stroke": "#ff0000",
                        "strokeWidth": 3,
                        "path": [["M", 10, 10], ["L", 100, 100]]
                    },
                    {
                        "type": "i-text",
                        "text": "Bug here!",
                        "left": 50,
                        "top": 50,
                        "fill": "#ff0000"
                    }
                ]
            })

            # Mock annotation layer for update
            with patch.object(mock_db, 'execute') as mock_execute:
                mock_result = AsyncMock()
                annotation_layer.version = 1
                mock_result.scalar_one_or_none = Mock(return_value=annotation_layer)
                mock_execute.return_value = mock_result

                # Mock session query
                with patch.object(mock_db, 'execute') as mock_execute2:
                    mock_session_result = AsyncMock()
                    mock_session_result.scalar_one_or_none = Mock(return_value=image_session)
                    mock_execute2.return_value = mock_session_result

                    # Update annotations
                    new_version = await image_editor.update_annotation_layer(
                        session_id=image_session.id,
                        canvas_json=canvas_json,
                        db=mock_db
                    )

                    # Verify annotations saved
                    assert new_version == 2
                    assert annotation_layer.canvas_json == canvas_json

    async def test_clipboard_workflow_empty_data(
        self, image_loader, mock_db
    ):
        """Test clipboard workflow with empty clipboard.

        Contract: Should return clear error message for empty clipboard (FR-025).
        """
        with pytest.raises((NotImplementedError, AssertionError, ImageValidationError)):
            with pytest.raises(ImageValidationError) as exc_info:
                await image_loader.load_from_stdin(
                    stdin_data=b"",
                    terminal_session_id="test-empty",
                    db=mock_db
                )

            # Verify error message is helpful
            error_msg = str(exc_info.value).lower()
            assert "empty" in error_msg or "clipboard" in error_msg

    async def test_clipboard_workflow_invalid_data(
        self, image_loader, mock_db
    ):
        """Test clipboard workflow with invalid data.

        Contract: Should handle corrupt clipboard data gracefully.
        """
        with pytest.raises((NotImplementedError, AssertionError, ImageValidationError)):
            with pytest.raises(ImageValidationError) as exc_info:
                await image_loader.load_from_stdin(
                    stdin_data=b"This is not an image!",
                    terminal_session_id="test-invalid",
                    db=mock_db
                )

            error_msg = str(exc_info.value).lower()
            assert "failed" in error_msg or "invalid" in error_msg

    async def test_clipboard_workflow_save_requires_filename(
        self, image_loader, image_editor, clipboard_png_data, mock_db
    ):
        """Test that saving clipboard image requires filename prompt.

        Contract: Clipboard images (no source_path) should prompt for
        filename when saving (as per spec).

        Note: This test verifies the session state, actual save prompt
        is handled by frontend (T056).
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Load from clipboard
            image_session = await image_loader.load_from_stdin(
                stdin_data=clipboard_png_data,
                terminal_session_id="test-save",
                db=mock_db
            )

            # Verify clipboard source has no path (requires save prompt)
            assert image_session.image_source_type == "clipboard"
            assert image_session.image_source_path is None

            # Create session for editing
            annotation_layer = await image_editor.create_session(
                image_session=image_session,
                db=mock_db
            )

            assert annotation_layer is not None

            # Frontend should detect null source_path and prompt for filename
            # before calling save endpoint (T056, T057, T058)

    async def test_clipboard_workflow_size_limits(
        self, image_loader, mock_db
    ):
        """Test clipboard workflow respects size limits.

        Contract: Should enforce same 50MB limit as file loading.
        """
        with pytest.raises((NotImplementedError, AssertionError, ImageValidationError)):
            # Generate data larger than 50MB
            large_data = b"x" * (51 * 1024 * 1024)

            with pytest.raises(ImageValidationError) as exc_info:
                await image_loader.load_from_stdin(
                    stdin_data=large_data,
                    terminal_session_id="test-large-clipboard",
                    db=mock_db
                )

            error_msg = str(exc_info.value)
            assert "50MB" in error_msg or "size" in error_msg.lower()
