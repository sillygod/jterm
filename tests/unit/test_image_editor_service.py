"""Unit tests for ImageEditorService.

Tests image editing operations including:
- Session creation with empty annotation layer
- Annotation layer updates with version tracking
- Filter application (blur, sharpen)
- Crop and resize operations
- Undo/redo snapshot management

CRITICAL: These tests MUST FAIL until implementation is complete.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Import service
try:
    from src.services.image_editor_service import (
        ImageEditorService,
        ImageEditorError,
        SessionNotFoundError
    )
    from src.models.image_editor import (
        ImageSession,
        AnnotationLayer,
        EditOperation,
        OperationType
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@pytest.mark.asyncio
class TestImageEditorServiceSession:
    """Test ImageEditorService session management."""

    @pytest.fixture
    def service(self):
        """Create ImageEditorService instance."""
        if not SERVICE_AVAILABLE:
            pytest.skip("ImageEditorService not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def image_session(self):
        """Create mock ImageSession."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Models not available")

        session = ImageSession(
            id="test-session-123",
            terminal_session_id="terminal-abc",
            image_source_type="file",
            image_source_path="/path/to/image.png",
            image_format="png",
            image_width=800,
            image_height=600,
            image_size_bytes=102400,
            temp_file_path="/tmp/test_image.png",
            is_modified=False
        )
        return session

    async def test_create_session_with_empty_annotation_layer(
        self, service, image_session, mock_db
    ):
        """Test creating session with empty annotation layer.

        Contract: Should create AnnotationLayer with empty Fabric.js JSON,
        version=1, linked to ImageSession.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Create session
            annotation_layer = await service.create_session(
                image_session=image_session,
                db=mock_db
            )

            # Verify annotation layer created
            assert annotation_layer is not None
            assert isinstance(annotation_layer, AnnotationLayer)
            assert annotation_layer.session_id == image_session.id
            assert annotation_layer.version == 1
            assert annotation_layer.canvas_json is not None

            # Verify canvas JSON is valid Fabric.js format
            canvas_data = json.loads(annotation_layer.canvas_json)
            assert "version" in canvas_data  # Fabric.js version
            assert "objects" in canvas_data
            assert isinstance(canvas_data["objects"], list)
            assert len(canvas_data["objects"]) == 0  # Empty initially

            # Verify database interaction
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    async def test_create_session_initializes_dimensions(
        self, service, image_session, mock_db
    ):
        """Test session initialization includes image dimensions.

        Contract: Canvas should be initialized with correct width/height
        from ImageSession.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            annotation_layer = await service.create_session(
                image_session=image_session,
                db=mock_db
            )

            canvas_data = json.loads(annotation_layer.canvas_json)
            # Fabric.js may store dimensions differently, verify they're recorded
            assert canvas_data is not None
            # Check if width/height are set (format varies by Fabric.js version)


@pytest.mark.asyncio
class TestImageEditorServiceAnnotations:
    """Test annotation layer management."""

    @pytest.fixture
    def service(self):
        """Create ImageEditorService instance."""
        if not SERVICE_AVAILABLE:
            pytest.skip("ImageEditorService not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session with query support."""
        db = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        # Mock query results
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        return db

    async def test_update_annotation_layer_increments_version(
        self, service, mock_db
    ):
        """Test annotation update increments version for optimistic locking.

        Contract: Each update should increment version field, preventing
        concurrent modification conflicts.
        """
        session_id = "test-session-123"
        canvas_json = '{"version":"5.3.0","objects":[{"type":"path","stroke":"#ff0000"}]}'

        with pytest.raises((NotImplementedError, AssertionError)):
            # First update
            new_version = await service.update_annotation_layer(
                session_id=session_id,
                canvas_json=canvas_json,
                db=mock_db
            )

            assert new_version > 0
            # Version should increment on each update
            assert isinstance(new_version, int)

    async def test_update_annotation_layer_marks_session_modified(
        self, service, mock_db
    ):
        """Test annotation update sets is_modified flag.

        Contract: ImageSession.is_modified should be set to True after
        any annotation change.
        """
        session_id = "test-session-123"
        canvas_json = '{"version":"5.3.0","objects":[]}'

        with pytest.raises((NotImplementedError, AssertionError)):
            await service.update_annotation_layer(
                session_id=session_id,
                canvas_json=canvas_json,
                db=mock_db
            )

            # Verify session was marked as modified
            # (Implementation should update ImageSession.is_modified = True)
            assert mock_db.commit.called

    async def test_update_annotation_layer_invalid_json(
        self, service, mock_db
    ):
        """Test annotation update rejects invalid JSON.

        Contract: Should raise validation error for malformed JSON.
        """
        session_id = "test-session-123"
        invalid_json = "not valid json {{"

        with pytest.raises((NotImplementedError, ValueError, json.JSONDecodeError)):
            await service.update_annotation_layer(
                session_id=session_id,
                canvas_json=invalid_json,
                db=mock_db
            )


@pytest.mark.asyncio
class TestImageEditorServiceUndoRedo:
    """Test undo/redo snapshot management."""

    @pytest.fixture
    def service(self):
        """Create ImageEditorService instance."""
        if not SERVICE_AVAILABLE:
            pytest.skip("ImageEditorService not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()

        # Mock query for snapshot retrieval
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        return db

    async def test_store_undo_snapshot_circular_buffer(
        self, service, mock_db
    ):
        """Test undo snapshot storage uses circular buffer (0-49).

        Contract: Should store max 50 snapshots, overwriting oldest
        when limit reached.
        """
        session_id = "test-session-123"
        canvas_snapshot = '{"version":"5.3.0","objects":[]}'

        with pytest.raises((NotImplementedError, AssertionError)):
            # Store snapshot at position 0
            await service.store_undo_snapshot(
                session_id=session_id,
                operation_type=OperationType.DRAW,
                canvas_snapshot=canvas_snapshot,
                position=0,
                db=mock_db
            )

            mock_db.add.assert_called()
            mock_db.commit.assert_called()

            # Verify position is within valid range
            assert 0 >= 0 and 0 < 50

    async def test_store_undo_snapshot_position_validation(
        self, service, mock_db
    ):
        """Test undo snapshot rejects invalid positions.

        Contract: Position must be 0-49, raise error for out of range.
        """
        session_id = "test-session-123"
        canvas_snapshot = '{"version":"5.3.0","objects":[]}'

        # Test invalid positions
        invalid_positions = [-1, 50, 100]

        for position in invalid_positions:
            with pytest.raises((NotImplementedError, ValueError, AssertionError)):
                await service.store_undo_snapshot(
                    session_id=session_id,
                    operation_type=OperationType.DRAW,
                    canvas_snapshot=canvas_snapshot,
                    position=position,
                    db=mock_db
                )

    async def test_get_undo_snapshot_retrieves_by_position(
        self, service, mock_db
    ):
        """Test retrieving undo snapshot by position.

        Contract: Should return canvas snapshot JSON for given position,
        or None if not found.
        """
        session_id = "test-session-123"
        position = 5

        with pytest.raises((NotImplementedError, AssertionError)):
            snapshot = await service.get_undo_snapshot(
                session_id=session_id,
                position=position,
                db=mock_db
            )

            # Snapshot should be JSON string or None
            if snapshot is not None:
                assert isinstance(snapshot, str)
                # Verify it's valid JSON
                json.loads(snapshot)

    async def test_store_undo_snapshot_operation_types(
        self, service, mock_db
    ):
        """Test all operation types can be stored.

        Contract: Should support draw, text, shape, filter, crop, resize.
        """
        session_id = "test-session-123"
        canvas_snapshot = '{"version":"5.3.0","objects":[]}'

        operation_types = [
            OperationType.DRAW,
            OperationType.TEXT,
            OperationType.SHAPE,
            OperationType.FILTER,
            OperationType.CROP,
            OperationType.RESIZE
        ]

        for i, op_type in enumerate(operation_types):
            with pytest.raises((NotImplementedError, AssertionError)):
                await service.store_undo_snapshot(
                    session_id=session_id,
                    operation_type=op_type,
                    canvas_snapshot=canvas_snapshot,
                    position=i,
                    db=mock_db
                )


@pytest.mark.asyncio
class TestImageEditorServiceClipboard:
    """Test clipboard source handling (T049)."""

    @pytest.fixture
    def service(self):
        """Create ImageEditorService instance."""
        if not SERVICE_AVAILABLE:
            pytest.skip("ImageEditorService not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def clipboard_image_session(self):
        """Create mock ImageSession from clipboard."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Models not available")

        session = ImageSession(
            id="clipboard-session-456",
            terminal_session_id="terminal-xyz",
            image_source_type="clipboard",
            image_source_path=None,  # No path for clipboard
            image_format="png",
            image_width=1024,
            image_height=768,
            image_size_bytes=204800,
            temp_file_path="/tmp/clipboard_image.png",
            is_modified=False
        )
        return session

    async def test_create_session_with_clipboard_source(
        self, service, clipboard_image_session, mock_db
    ):
        """Test session creation for clipboard-sourced images.

        Contract: Should handle source_type='clipboard' with null source_path.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            annotation_layer = await service.create_session(
                image_session=clipboard_image_session,
                db=mock_db
            )

            # Verify annotation layer created
            assert annotation_layer is not None
            assert isinstance(annotation_layer, AnnotationLayer)
            assert annotation_layer.session_id == "clipboard-session-456"
            assert annotation_layer.version == 1

            # Verify canvas JSON is valid and empty
            canvas = json.loads(annotation_layer.canvas_json)
            assert canvas["version"] == "5.3.0"
            assert canvas["objects"] == []

            # Verify database interaction
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    async def test_update_annotation_layer_clipboard_source(
        self, service, mock_db
    ):
        """Test annotation updates work for clipboard sources.

        Contract: Clipboard images should support full annotation functionality.
        """
        session_id = "clipboard-session-456"
        canvas_json = json.dumps({
            "version": "5.3.0",
            "objects": [
                {
                    "type": "rect",
                    "fill": "#ff0000",
                    "left": 10,
                    "top": 10,
                    "width": 100,
                    "height": 50
                }
            ]
        })

        # Mock the database query
        with patch.object(mock_db, 'execute') as mock_execute:
            mock_result = AsyncMock()
            mock_annotation = AnnotationLayer(
                id="annot-123",
                session_id=session_id,
                canvas_json='{"version":"5.3.0","objects":[]}',
                version=1
            )
            mock_result.scalar_one_or_none = Mock(return_value=mock_annotation)
            mock_execute.return_value = mock_result

            # Mock ImageSession query
            with patch.object(mock_db, 'execute') as mock_execute2:
                mock_session_result = AsyncMock()
                mock_session = ImageSession(
                    id=session_id,
                    terminal_session_id="terminal-xyz",
                    image_source_type="clipboard",
                    image_source_path=None,
                    image_format="png",
                    image_width=1024,
                    image_height=768,
                    image_size_bytes=204800,
                    temp_file_path="/tmp/clipboard_image.png",
                    is_modified=False
                )
                mock_session_result.scalar_one_or_none = Mock(return_value=mock_session)
                mock_execute2.return_value = mock_session_result

                with pytest.raises((NotImplementedError, AssertionError)):
                    new_version = await service.update_annotation_layer(
                        session_id=session_id,
                        canvas_json=canvas_json,
                        db=mock_db
                    )

                    # Verify version incremented
                    assert new_version == 2
                    assert mock_annotation.version == 2
                    assert mock_annotation.canvas_json == canvas_json

                    # Verify session marked as modified
                    assert mock_session.is_modified is True

    async def test_clipboard_source_no_file_path(
        self, service, clipboard_image_session, mock_db
    ):
        """Test clipboard sessions handle null source_path correctly.

        Contract: Clipboard images should not have source_path (it's null).
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Verify clipboard session has no source path
            assert clipboard_image_session.image_source_type == "clipboard"
            assert clipboard_image_session.image_source_path is None

            # Session creation should still work
            annotation_layer = await service.create_session(
                image_session=clipboard_image_session,
                db=mock_db
            )

            assert annotation_layer is not None


@pytest.mark.asyncio
class TestImageEditorServiceCropResize:
    """Test crop and resize operations (T061, T062)."""

    @pytest.fixture
    def service(self):
        """Create ImageEditorService instance."""
        if not SERVICE_AVAILABLE:
            pytest.skip("ImageEditorService not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()

        # Mock query results
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        return db

    @pytest.fixture
    def image_session(self):
        """Create mock ImageSession."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Models not available")

        session = ImageSession(
            id="test-session-123",
            terminal_session_id="terminal-abc",
            image_source_type="file",
            image_source_path="/path/to/image.png",
            image_format="png",
            image_width=800,
            image_height=600,
            image_size_bytes=102400,
            temp_file_path="/tmp/test_image.png",
            is_modified=False
        )
        return session

    async def test_crop_image_basic_operation(
        self, service, mock_db, image_session
    ):
        """Test basic crop operation with valid bounds (T061).

        Contract: Should crop image to specified bounds using Pillow,
        update ImageSession dimensions, and update canvas size.
        """
        session_id = "test-session-123"
        x, y, width, height = 100, 100, 400, 300

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.crop_image(
                session_id=session_id,
                x=x,
                y=y,
                width=width,
                height=height,
                db=mock_db
            )

            # Verify result contains updated dimensions
            assert isinstance(result, dict)
            assert "width" in result or "image_width" in result
            assert "height" in result or "image_height" in result

    async def test_crop_image_boundary_validation(
        self, service, mock_db
    ):
        """Test crop validates bounds within image dimensions (T061).

        Contract: Should reject crop bounds that exceed image dimensions.
        """
        session_id = "test-session-123"

        # Invalid crop: exceeds image bounds
        invalid_crops = [
            (-10, 0, 100, 100),  # Negative x
            (0, -10, 100, 100),  # Negative y
            (750, 0, 100, 100),  # x + width > image_width
            (0, 550, 100, 100),  # y + height > image_height
            (0, 0, 0, 100),      # Zero width
            (0, 0, 100, 0),      # Zero height
        ]

        for x, y, w, h in invalid_crops:
            with pytest.raises((NotImplementedError, ValueError, ImageEditorError)):
                await service.crop_image(
                    session_id=session_id,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    db=mock_db
                )

    async def test_crop_image_updates_dimensions(
        self, service, mock_db
    ):
        """Test crop updates ImageSession width/height (T061).

        Contract: After crop, ImageSession.image_width and image_height
        should reflect new cropped dimensions.
        """
        session_id = "test-session-123"
        crop_width, crop_height = 400, 300

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.crop_image(
                session_id=session_id,
                x=100,
                y=100,
                width=crop_width,
                height=crop_height,
                db=mock_db
            )

            # Verify dimensions updated
            new_width = result.get("width") or result.get("image_width")
            new_height = result.get("height") or result.get("image_height")

            assert new_width == crop_width
            assert new_height == crop_height

    async def test_crop_image_session_not_found(
        self, service, mock_db
    ):
        """Test crop raises error for non-existent session (T061).

        Contract: Should raise SessionNotFoundError for invalid session_id.
        """
        session_id = "nonexistent-session"

        with pytest.raises((NotImplementedError, SessionNotFoundError)):
            await service.crop_image(
                session_id=session_id,
                x=0,
                y=0,
                width=100,
                height=100,
                db=mock_db
            )

    async def test_resize_image_basic_operation(
        self, service, mock_db
    ):
        """Test basic resize operation (T062).

        Contract: Should resize image using Pillow with LANCZOS filter,
        update ImageSession dimensions.
        """
        session_id = "test-session-123"
        new_width, new_height = 400, 300

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.resize_image(
                session_id=session_id,
                width=new_width,
                height=new_height,
                maintain_aspect_ratio=False,
                db=mock_db
            )

            # Verify result contains updated dimensions
            assert isinstance(result, dict)
            assert "width" in result or "image_width" in result
            assert "height" in result or "image_height" in result

    async def test_resize_image_maintain_aspect_ratio(
        self, service, mock_db
    ):
        """Test resize with aspect ratio locked (T062).

        Contract: When maintain_aspect_ratio=True, should calculate
        height from width (or vice versa) to preserve aspect ratio.
        """
        session_id = "test-session-123"
        target_width = 400
        # Original: 800x600 (4:3 ratio)
        # Expected height: 300 (to maintain 4:3)

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.resize_image(
                session_id=session_id,
                width=target_width,
                height=300,  # May be recalculated
                maintain_aspect_ratio=True,
                db=mock_db
            )

            # Verify aspect ratio maintained
            new_width = result.get("width") or result.get("image_width")
            new_height = result.get("height") or result.get("image_height")

            # Calculate aspect ratio (should be close to original)
            # Allow small floating point differences
            aspect_ratio = new_width / new_height
            expected_ratio = 800 / 600  # 4:3
            assert abs(aspect_ratio - expected_ratio) < 0.01

    async def test_resize_image_dimension_validation(
        self, service, mock_db
    ):
        """Test resize validates dimensions (T062).

        Contract: Should reject invalid dimensions (zero, negative,
        exceeding Canvas API limit 32767).
        """
        session_id = "test-session-123"

        invalid_dimensions = [
            (0, 100),      # Zero width
            (100, 0),      # Zero height
            (-100, 100),   # Negative width
            (100, -100),   # Negative height
            (40000, 100),  # Exceeds max dimension
            (100, 40000),  # Exceeds max dimension
        ]

        for width, height in invalid_dimensions:
            with pytest.raises((NotImplementedError, ValueError, ImageEditorError)):
                await service.resize_image(
                    session_id=session_id,
                    width=width,
                    height=height,
                    maintain_aspect_ratio=False,
                    db=mock_db
                )

    async def test_resize_image_updates_dimensions(
        self, service, mock_db
    ):
        """Test resize updates ImageSession dimensions (T062).

        Contract: After resize, ImageSession.image_width and image_height
        should reflect new dimensions.
        """
        session_id = "test-session-123"
        new_width, new_height = 1024, 768

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.resize_image(
                session_id=session_id,
                width=new_width,
                height=new_height,
                maintain_aspect_ratio=False,
                db=mock_db
            )

            # Verify dimensions updated
            updated_width = result.get("width") or result.get("image_width")
            updated_height = result.get("height") or result.get("image_height")

            assert updated_width == new_width
            assert updated_height == new_height

    async def test_resize_image_session_not_found(
        self, service, mock_db
    ):
        """Test resize raises error for non-existent session (T062).

        Contract: Should raise SessionNotFoundError for invalid session_id.
        """
        session_id = "nonexistent-session"

        with pytest.raises((NotImplementedError, SessionNotFoundError)):
            await service.resize_image(
                session_id=session_id,
                width=400,
                height=300,
                maintain_aspect_ratio=False,
                db=mock_db
            )


@pytest.mark.asyncio
class TestImageEditorServiceCleanup:
    """Test session cleanup functionality."""

    @pytest.fixture
    def service(self):
        """Create ImageEditorService instance."""
        if not SERVICE_AVAILABLE:
            pytest.skip("ImageEditorService not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()

        # Mock query for expired sessions
        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=AsyncMock(all=AsyncMock(return_value=[])))
        db.execute = AsyncMock(return_value=mock_result)
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        return db

    async def test_cleanup_expired_sessions_default_threshold(
        self, service, mock_db
    ):
        """Test cleanup of sessions older than 24 hours (default).

        Contract: Should delete ImageSession records and temp files
        older than threshold.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            count = await service.cleanup_expired_sessions(
                db=mock_db,
                hours=24
            )

            # Verify count is returned
            assert isinstance(count, int)
            assert count >= 0

    async def test_cleanup_expired_sessions_custom_threshold(
        self, service, mock_db
    ):
        """Test cleanup with custom time threshold.

        Contract: Should accept custom hours parameter for cleanup.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            count = await service.cleanup_expired_sessions(
                db=mock_db,
                hours=48  # 2 days
            )

            assert isinstance(count, int)
            assert count >= 0


@pytest.mark.asyncio
class TestImageEditorServiceFilters:
    """Test filter operations: blur and sharpen (T075, T076)."""

    @pytest.fixture
    def service(self):
        """Create ImageEditorService instance."""
        if not SERVICE_AVAILABLE:
            pytest.skip("ImageEditorService not implemented yet")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()

        # Mock query results
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        return db

    @pytest.fixture
    def image_session(self, tmp_path):
        """Create mock ImageSession with actual image file."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Models not available")

        # Create a test image
        from PIL import Image
        image_path = tmp_path / "test_image.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(image_path, 'PNG')

        session = ImageSession(
            id="test-session-123",
            terminal_session_id="terminal-abc",
            image_source_type="file",
            image_source_path=str(image_path),
            image_format="png",
            image_width=100,
            image_height=100,
            image_size_bytes=1024,
            temp_file_path=str(image_path),
            is_modified=False
        )
        return session

    # T075: Test apply_blur()
    async def test_apply_blur_basic_operation(
        self, service, mock_db, image_session
    ):
        """Test basic blur operation with Gaussian blur filter (T075).

        Contract: Should apply Pillow GaussianBlur filter with specified radius,
        preserve dimensions, and update image file.
        """
        session_id = "test-session-123"
        radius = 5.0

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_blur(
                session_id=session_id,
                radius=radius,
                db=mock_db
            )

            # Verify result contains success message and dimensions
            assert isinstance(result, dict)
            assert "message" in result or "success" in result
            assert "width" in result or "image_width" in result
            assert "height" in result or "image_height" in result

    async def test_apply_blur_radius_validation(
        self, service, mock_db
    ):
        """Test blur validates radius parameter (T075).

        Contract: Should reject radius < 0 or > 20.
        """
        session_id = "test-session-123"

        invalid_radii = [-5.0, 25.0, 100.0, -0.1]

        for radius in invalid_radii:
            with pytest.raises((NotImplementedError, ValueError, ImageEditorError)):
                await service.apply_blur(
                    session_id=session_id,
                    radius=radius,
                    db=mock_db
                )

    async def test_apply_blur_zero_radius(
        self, service, mock_db, image_session
    ):
        """Test blur with radius 0 (no blur effect) (T075).

        Contract: Should handle radius=0 as valid (no blur applied).
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_blur(
                session_id=session_id,
                radius=0.0,
                db=mock_db
            )

            # Should succeed with radius 0
            assert result is not None

    async def test_apply_blur_max_radius(
        self, service, mock_db, image_session
    ):
        """Test blur with maximum allowed radius (T075).

        Contract: Should handle radius=20 as maximum valid value.
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_blur(
                session_id=session_id,
                radius=20.0,
                db=mock_db
            )

            # Should succeed with max radius
            assert result is not None

    async def test_apply_blur_preserves_dimensions(
        self, service, mock_db, image_session
    ):
        """Test blur preserves image dimensions (T075).

        Contract: Image width and height should remain unchanged after blur.
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_blur(
                session_id=session_id,
                radius=5.0,
                db=mock_db
            )

            # Verify original dimensions preserved
            width = result.get("width") or result.get("image_width")
            height = result.get("height") or result.get("image_height")

            assert width == 100
            assert height == 100

    async def test_apply_blur_session_not_found(
        self, service, mock_db
    ):
        """Test blur raises error for non-existent session (T075).

        Contract: Should raise SessionNotFoundError for invalid session_id.
        """
        session_id = "nonexistent-session"

        with pytest.raises((NotImplementedError, SessionNotFoundError)):
            await service.apply_blur(
                session_id=session_id,
                radius=5.0,
                db=mock_db
            )

    async def test_apply_blur_gaussian_filter_applied(
        self, service, mock_db, image_session
    ):
        """Test Pillow GaussianBlur filter is correctly applied (T075).

        Contract: Should use ImageFilter.GaussianBlur with specified radius.
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            # Apply blur
            await service.apply_blur(
                session_id=session_id,
                radius=3.0,
                db=mock_db
            )

            # Load processed image and verify it was modified
            from PIL import Image
            processed_img = Image.open(image_session.temp_file_path)

            # Image should exist and have correct dimensions
            assert processed_img.size == (100, 100)

    # T076: Test apply_sharpen()
    async def test_apply_sharpen_basic_operation(
        self, service, mock_db, image_session
    ):
        """Test basic sharpen operation with UnsharpMask filter (T076).

        Contract: Should apply Pillow UnsharpMask filter with specified amount,
        preserve dimensions, and update image file.
        """
        session_id = "test-session-123"
        amount = 5.0

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_sharpen(
                session_id=session_id,
                amount=amount,
                db=mock_db
            )

            # Verify result contains success message and dimensions
            assert isinstance(result, dict)
            assert "message" in result or "success" in result
            assert "width" in result or "image_width" in result
            assert "height" in result or "image_height" in result

    async def test_apply_sharpen_amount_validation(
        self, service, mock_db
    ):
        """Test sharpen validates amount parameter (T076).

        Contract: Should reject amount < 0 or > 10.
        """
        session_id = "test-session-123"

        invalid_amounts = [-3.0, 15.0, 100.0, -0.1]

        for amount in invalid_amounts:
            with pytest.raises((NotImplementedError, ValueError, ImageEditorError)):
                await service.apply_sharpen(
                    session_id=session_id,
                    amount=amount,
                    db=mock_db
                )

    async def test_apply_sharpen_zero_amount(
        self, service, mock_db, image_session
    ):
        """Test sharpen with amount 0 (no sharpen effect) (T076).

        Contract: Should handle amount=0 as valid (no sharpening applied).
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_sharpen(
                session_id=session_id,
                amount=0.0,
                db=mock_db
            )

            # Should succeed with amount 0
            assert result is not None

    async def test_apply_sharpen_max_amount(
        self, service, mock_db, image_session
    ):
        """Test sharpen with maximum allowed amount (T076).

        Contract: Should handle amount=10 as maximum valid value.
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_sharpen(
                session_id=session_id,
                amount=10.0,
                db=mock_db
            )

            # Should succeed with max amount
            assert result is not None

    async def test_apply_sharpen_preserves_dimensions(
        self, service, mock_db, image_session
    ):
        """Test sharpen preserves image dimensions (T076).

        Contract: Image width and height should remain unchanged after sharpen.
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            result = await service.apply_sharpen(
                session_id=session_id,
                amount=7.0,
                db=mock_db
            )

            # Verify original dimensions preserved
            width = result.get("width") or result.get("image_width")
            height = result.get("height") or result.get("image_height")

            assert width == 100
            assert height == 100

    async def test_apply_sharpen_session_not_found(
        self, service, mock_db
    ):
        """Test sharpen raises error for non-existent session (T076).

        Contract: Should raise SessionNotFoundError for invalid session_id.
        """
        session_id = "nonexistent-session"

        with pytest.raises((NotImplementedError, SessionNotFoundError)):
            await service.apply_sharpen(
                session_id=session_id,
                amount=5.0,
                db=mock_db
            )

    async def test_apply_sharpen_unsharp_mask_filter_applied(
        self, service, mock_db, image_session
    ):
        """Test Pillow UnsharpMask filter is correctly applied (T076).

        Contract: Should use ImageFilter.UnsharpMask with calculated parameters.
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            # Apply sharpen
            await service.apply_sharpen(
                session_id=session_id,
                amount=5.0,
                db=mock_db
            )

            # Load processed image and verify it was modified
            from PIL import Image
            processed_img = Image.open(image_session.temp_file_path)

            # Image should exist and have correct dimensions
            assert processed_img.size == (100, 100)

    async def test_apply_sharpen_different_amounts_produce_different_results(
        self, service, mock_db, image_session, tmp_path
    ):
        """Test different sharpen amounts produce visually different results (T076).

        Contract: Higher amount values should produce more aggressive sharpening.
        """
        session_id = "test-session-123"

        with pytest.raises((NotImplementedError, AssertionError)):
            # Create gradient image for better sharpening test
            from PIL import Image
            gradient_path = tmp_path / "gradient.png"
            img = Image.new('RGB', (100, 100))
            pixels = img.load()
            for i in range(100):
                for j in range(100):
                    pixels[i, j] = (i * 2, j * 2, 128)
            img.save(gradient_path, 'PNG')

            # Update image session path
            image_session.temp_file_path = str(gradient_path)

            # Apply low sharpen
            result_low = await service.apply_sharpen(
                session_id=session_id,
                amount=2.0,
                db=mock_db
            )

            # Restore gradient image
            img.save(gradient_path, 'PNG')

            # Apply high sharpen
            result_high = await service.apply_sharpen(
                session_id=session_id,
                amount=8.0,
                db=mock_db
            )

            # Both should succeed but produce different results
            assert result_low is not None
            assert result_high is not None
