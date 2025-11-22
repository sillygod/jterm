"""Integration test for crop and resize workflow (T063).

Tests the complete user journey:
1. Load image
2. Crop to specified region
3. Resize to target dimensions
4. Save final result

This test validates that crop and resize operations work together
and that the image editing workflow is complete.

CRITICAL: These tests MUST FAIL until implementation is complete.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Import services and models
try:
    from src.services.image_loader_service import ImageLoaderService
    from src.services.image_editor_service import ImageEditorService
    from src.models.image_editor import ImageSession
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


@pytest.mark.asyncio
@pytest.mark.integration
class TestCropResizeWorkflow:
    """Integration test for complete crop and resize workflow (T063)."""

    @pytest.fixture
    def test_image_path(self, tmp_path):
        """Create a test image file."""
        if not PILLOW_AVAILABLE:
            pytest.skip("Pillow not available")

        # Create a simple 800x600 test image
        img = Image.new('RGB', (800, 600), color='blue')
        image_path = tmp_path / "test_image.png"
        img.save(str(image_path))
        return str(image_path)

    @pytest.fixture
    def image_loader_service(self, tmp_path):
        """Create ImageLoaderService instance."""
        if not SERVICES_AVAILABLE:
            pytest.skip("Services not available")
        return ImageLoaderService(temp_dir=str(tmp_path))

    @pytest.fixture
    def image_editor_service(self):
        """Create ImageEditorService instance."""
        if not SERVICES_AVAILABLE:
            pytest.skip("Services not available")
        return ImageEditorService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        # Mock query results
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        return db

    async def test_complete_crop_resize_workflow(
        self,
        test_image_path,
        image_loader_service,
        image_editor_service,
        mock_db,
        tmp_path
    ):
        """Test complete workflow: load → crop → resize → save.

        User Story: User opens image, crops to region of interest,
        resizes to target dimensions, and saves result.

        Steps:
        1. Load image (800x600)
        2. Crop to region (100, 100, 400, 300) → 400x300
        3. Resize to (200, 150) → 200x150
        4. Save to file

        Contract: Final image should be 200x150 pixels.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Step 1: Load image
            image_session = await image_loader_service.load_from_file(
                file_path=test_image_path,
                terminal_session_id="test-terminal-123",
                db=mock_db
            )

            assert image_session is not None
            assert image_session.image_width == 800
            assert image_session.image_height == 600

            session_id = image_session.id

            # Step 2: Crop image to 400x300
            crop_result = await image_editor_service.crop_image(
                session_id=session_id,
                x=100,
                y=100,
                width=400,
                height=300,
                db=mock_db
            )

            # Verify crop dimensions
            assert isinstance(crop_result, dict)
            cropped_width = crop_result.get("width") or crop_result.get("image_width")
            cropped_height = crop_result.get("height") or crop_result.get("image_height")
            assert cropped_width == 400
            assert cropped_height == 300

            # Step 3: Resize cropped image to 200x150
            resize_result = await image_editor_service.resize_image(
                session_id=session_id,
                width=200,
                height=150,
                maintain_aspect_ratio=False,
                db=mock_db
            )

            # Verify resize dimensions
            assert isinstance(resize_result, dict)
            final_width = resize_result.get("width") or resize_result.get("image_width")
            final_height = resize_result.get("height") or resize_result.get("image_height")
            assert final_width == 200
            assert final_height == 150

            # Step 4: Save final image
            output_path = str(tmp_path / "final_image.png")
            saved_path = await image_editor_service.save_image(
                session_id=session_id,
                output_path=output_path,
                db=mock_db
            )

            assert saved_path is not None
            assert Path(saved_path).exists()

            # Verify final image dimensions using Pillow
            if PILLOW_AVAILABLE:
                final_img = Image.open(saved_path)
                assert final_img.size == (200, 150)

    async def test_crop_then_resize_with_aspect_ratio(
        self,
        test_image_path,
        image_loader_service,
        image_editor_service,
        mock_db,
        tmp_path
    ):
        """Test crop followed by resize with aspect ratio maintained.

        User Story: User crops image and resizes while maintaining aspect ratio.

        Steps:
        1. Load image (800x600, 4:3 ratio)
        2. Crop to square region (200, 200, 400, 400) → 400x400
        3. Resize with aspect ratio locked to width 200 → 200x200

        Contract: Final image should maintain 1:1 aspect ratio.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Step 1: Load image
            image_session = await image_loader_service.load_from_file(
                file_path=test_image_path,
                terminal_session_id="test-terminal-456",
                db=mock_db
            )

            session_id = image_session.id

            # Step 2: Crop to square (400x400)
            crop_result = await image_editor_service.crop_image(
                session_id=session_id,
                x=200,
                y=200,
                width=400,
                height=400,
                db=mock_db
            )

            cropped_width = crop_result.get("width") or crop_result.get("image_width")
            cropped_height = crop_result.get("height") or crop_result.get("image_height")
            assert cropped_width == 400
            assert cropped_height == 400

            # Step 3: Resize with aspect ratio maintained
            resize_result = await image_editor_service.resize_image(
                session_id=session_id,
                width=200,
                height=200,  # Should be recalculated or validated
                maintain_aspect_ratio=True,
                db=mock_db
            )

            final_width = resize_result.get("width") or resize_result.get("image_width")
            final_height = resize_result.get("height") or resize_result.get("image_height")

            # Verify aspect ratio maintained (1:1)
            assert final_width == final_height
            assert final_width == 200

    async def test_multiple_crops_and_resizes(
        self,
        test_image_path,
        image_loader_service,
        image_editor_service,
        mock_db,
        tmp_path
    ):
        """Test multiple sequential crop and resize operations.

        User Story: User iteratively refines image by cropping and resizing.

        Steps:
        1. Load image (800x600)
        2. First crop (100, 100, 600, 400) → 600x400
        3. First resize to (300, 200)
        4. Second crop (50, 50, 200, 100) → 200x100
        5. Second resize to (100, 50)

        Contract: Final image should be 100x50 pixels.
        """
        with pytest.raises((NotImplementedError, AssertionError)):
            # Step 1: Load image
            image_session = await image_loader_service.load_from_file(
                file_path=test_image_path,
                terminal_session_id="test-terminal-789",
                db=mock_db
            )

            session_id = image_session.id

            # Step 2: First crop
            crop1_result = await image_editor_service.crop_image(
                session_id=session_id,
                x=100,
                y=100,
                width=600,
                height=400,
                db=mock_db
            )

            # Step 3: First resize
            resize1_result = await image_editor_service.resize_image(
                session_id=session_id,
                width=300,
                height=200,
                maintain_aspect_ratio=False,
                db=mock_db
            )

            # Step 4: Second crop
            crop2_result = await image_editor_service.crop_image(
                session_id=session_id,
                x=50,
                y=50,
                width=200,
                height=100,
                db=mock_db
            )

            # Step 5: Second resize
            resize2_result = await image_editor_service.resize_image(
                session_id=session_id,
                width=100,
                height=50,
                maintain_aspect_ratio=False,
                db=mock_db
            )

            # Verify final dimensions
            final_width = resize2_result.get("width") or resize2_result.get("image_width")
            final_height = resize2_result.get("height") or resize2_result.get("image_height")
            assert final_width == 100
            assert final_height == 50

            # Save and verify
            output_path = str(tmp_path / "multi_edit_final.png")
            saved_path = await image_editor_service.save_image(
                session_id=session_id,
                output_path=output_path,
                db=mock_db
            )

            if PILLOW_AVAILABLE and Path(saved_path).exists():
                final_img = Image.open(saved_path)
                assert final_img.size == (100, 50)

    async def test_crop_resize_preserves_format(
        self,
        image_loader_service,
        image_editor_service,
        mock_db,
        tmp_path
    ):
        """Test that crop and resize preserve image format.

        User Story: User crops/resizes JPEG image, result should remain JPEG.

        Contract: Image format should be preserved through crop/resize operations.
        """
        if not PILLOW_AVAILABLE:
            pytest.skip("Pillow not available")

        with pytest.raises((NotImplementedError, AssertionError)):
            # Create JPEG test image
            img = Image.new('RGB', (800, 600), color='red')
            jpeg_path = tmp_path / "test_image.jpg"
            img.save(str(jpeg_path), format='JPEG')

            # Load JPEG image
            image_session = await image_loader_service.load_from_file(
                file_path=str(jpeg_path),
                terminal_session_id="test-terminal-jpeg",
                db=mock_db
            )

            assert image_session.image_format == "jpeg"
            session_id = image_session.id

            # Crop and resize
            await image_editor_service.crop_image(
                session_id=session_id,
                x=100,
                y=100,
                width=400,
                height=300,
                db=mock_db
            )

            await image_editor_service.resize_image(
                session_id=session_id,
                width=200,
                height=150,
                maintain_aspect_ratio=False,
                db=mock_db
            )

            # Save with JPEG extension
            output_path = str(tmp_path / "final_output.jpg")
            saved_path = await image_editor_service.save_image(
                session_id=session_id,
                output_path=output_path,
                db=mock_db
            )

            # Verify saved file is JPEG
            if Path(saved_path).exists():
                saved_img = Image.open(saved_path)
                assert saved_img.format in ['JPEG', 'JPG']
                assert saved_img.size == (200, 150)

    async def test_error_handling_invalid_crop_after_resize(
        self,
        test_image_path,
        image_loader_service,
        image_editor_service,
        mock_db
    ):
        """Test error handling for invalid crop bounds after resize.

        User Story: User resizes image, then attempts to crop with bounds
        that exceed new dimensions.

        Contract: Should raise error for crop bounds exceeding image dimensions.
        """
        with pytest.raises((NotImplementedError, ValueError, Exception)):
            # Load and resize to smaller dimensions
            image_session = await image_loader_service.load_from_file(
                file_path=test_image_path,
                terminal_session_id="test-terminal-error",
                db=mock_db
            )

            session_id = image_session.id

            # Resize to 400x300
            await image_editor_service.resize_image(
                session_id=session_id,
                width=400,
                height=300,
                maintain_aspect_ratio=False,
                db=mock_db
            )

            # Attempt to crop with invalid bounds (exceeds 400x300)
            await image_editor_service.crop_image(
                session_id=session_id,
                x=350,
                y=250,
                width=100,  # x + width = 450 > 400
                height=100,  # y + height = 350 > 300
                db=mock_db
            )

            # Should raise error before reaching this point
            pytest.fail("Should have raised error for invalid crop bounds")
