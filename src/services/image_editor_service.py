"""Image Editor Service for image editing operations.

This service handles:
- Creating and managing edit sessions
- Applying filters and adjustments
- Processing crop and resize operations
- Saving edited images
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

try:
    from PIL import Image, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.image_editor import (
    ImageSession,
    AnnotationLayer,
    EditOperation,
    OperationType
)


logger = logging.getLogger(__name__)


class ImageEditorError(Exception):
    """Base exception for image editor operations."""
    pass


class SessionNotFoundError(ImageEditorError):
    """Raised when session is not found."""
    pass


def validate_uuid(uuid_string: str, param_name: str = "ID") -> str:
    """
    Validate UUID format for SQL injection prevention (T140).

    Args:
        uuid_string: UUID string to validate
        param_name: Parameter name for error messages

    Returns:
        str: Validated UUID string

    Raises:
        ValueError: If UUID format is invalid
    """
    import uuid as uuid_lib
    import re

    if not uuid_string or not isinstance(uuid_string, str):
        raise ValueError(f"Invalid {param_name}: must be a non-empty string")

    # Remove whitespace and convert to lowercase
    uuid_string = uuid_string.strip().lower()

    # Validate UUID format with regex (8-4-4-4-12 pattern)
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )
    if not uuid_pattern.match(uuid_string):
        raise ValueError(
            f"Invalid {param_name} format: must be a valid UUID "
            f"(e.g., '550e8400-e29b-41d4-a716-446655440000')"
        )

    # Additional validation: try to parse as UUID
    try:
        uuid_lib.UUID(uuid_string)
    except ValueError as e:
        raise ValueError(f"Invalid {param_name}: {str(e)}")

    return uuid_string


class ImageEditorService:
    """
    Service for image editing operations.

    Handles session management, filter application, and image transformations.
    """

    def __init__(self):
        """Initialize the image editor service."""
        if not PILLOW_AVAILABLE:
            raise RuntimeError("Pillow is required for ImageEditorService")

    async def create_session(
        self,
        image_session: ImageSession,
        db: AsyncSession
    ) -> AnnotationLayer:
        """
        Create editing session with empty annotation layer.

        Args:
            image_session: ImageSession record
            db: Database session

        Returns:
            AnnotationLayer: Created annotation layer with empty canvas
        """
        logger.info(f"Creating edit session for image session: {image_session.id}")

        import uuid
        import json

        # Create empty Fabric.js canvas JSON
        canvas_json = json.dumps({
            "version": "5.3.0",  # Fabric.js version
            "objects": [],  # Empty initially - no annotations yet
            "background": None
        })

        # Create annotation layer
        annotation_layer = AnnotationLayer(
            id=str(uuid.uuid4()),
            session_id=image_session.id,
            canvas_json=canvas_json,
            version=1
        )

        db.add(annotation_layer)
        await db.commit()
        await db.refresh(annotation_layer)

        logger.info(f"Created annotation layer for session {image_session.id}")
        return annotation_layer

    async def apply_filter(
        self,
        session_id: str,
        filter_type: str,
        parameters: Dict[str, Any],
        db: AsyncSession
    ) -> str:
        """
        Apply server-side filter to image.

        Supported filters:
        - blur: Gaussian blur with radius parameter
        - sharpen: Unsharp mask with intensity parameter

        Args:
            session_id: Image session ID
            filter_type: Filter type (blur, sharpen)
            parameters: Filter parameters (e.g., {"radius": 5})
            db: Database session

        Returns:
            str: URL to processed image

        Raises:
            SessionNotFoundError: If session not found
            ValueError: If filter_type or parameters are invalid
            ImageEditorError: If filter application fails
        """
        logger.info(f"Applying filter '{filter_type}' to session: {session_id}, params: {parameters}")

        # Validate filter_type
        supported_filters = {'blur', 'sharpen'}
        if filter_type not in supported_filters:
            raise ValueError(
                f"Unsupported filter type: {filter_type}. "
                f"Supported filters: {', '.join(supported_filters)}"
            )

        # Validate parameters
        if not parameters:
            raise ValueError(f"Missing parameters for filter: {filter_type}")

        try:
            # Apply specific filter based on type
            if filter_type == 'blur':
                radius = parameters.get('radius')
                if radius is None:
                    raise ValueError("Missing required parameter 'radius' for blur filter")
                return await self.apply_blur(session_id, radius, db)

            elif filter_type == 'sharpen':
                amount = parameters.get('amount')
                if amount is None:
                    raise ValueError("Missing required parameter 'amount' for sharpen filter")
                return await self.apply_sharpen(session_id, amount, db)

            else:
                raise ValueError(f"Filter type '{filter_type}' not implemented")

        except (SessionNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error applying filter '{filter_type}' to session {session_id}: {str(e)}")
            raise ImageEditorError(f"Failed to apply filter: {str(e)}")

    async def crop_image(
        self,
        session_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Crop image to specified bounds.

        Args:
            session_id: Image session ID
            x: Left coordinate
            y: Top coordinate
            width: Crop width
            height: Crop height
            db: Database session

        Returns:
            Dict: Updated session info with new dimensions

        Raises:
            SessionNotFoundError: If session not found
            ValueError: If session_id is not a valid UUID
            ImageEditorError: If crop fails
        """
        logger.info(f"Cropping image session {session_id}: ({x}, {y}, {width}, {height})")

        # T140: Validate UUID to prevent SQL injection
        session_id = validate_uuid(session_id, "session_id")

        try:
            # Load ImageSession from database
            session_query = select(ImageSession).where(ImageSession.id == session_id)
            session_result = await db.execute(session_query)
            image_session = session_result.scalar_one_or_none()

            if not image_session:
                raise SessionNotFoundError(f"Image session not found: {session_id}")

            # Validate crop bounds
            if x < 0 or y < 0:
                raise ImageEditorError(f"Crop coordinates cannot be negative: x={x}, y={y}")

            if width <= 0 or height <= 0:
                raise ImageEditorError(f"Crop dimensions must be positive: width={width}, height={height}")

            if x + width > image_session.image_width:
                raise ImageEditorError(
                    f"Crop exceeds image width: x={x} + width={width} > {image_session.image_width}"
                )

            if y + height > image_session.image_height:
                raise ImageEditorError(
                    f"Crop exceeds image height: y={y} + height={height} > {image_session.image_height}"
                )

            # Load image from temp file
            temp_path = Path(image_session.temp_file_path)
            if not temp_path.exists():
                raise ImageEditorError(f"Temporary file not found: {temp_path}")

            # Load and crop image with Pillow
            image = await asyncio.to_thread(Image.open, temp_path)

            # Apply crop: (left, upper, right, lower)
            crop_box = (x, y, x + width, y + height)
            cropped_image = await asyncio.to_thread(image.crop, crop_box)

            # Save cropped image back to temp file
            await asyncio.to_thread(cropped_image.save, str(temp_path))

            # Update ImageSession dimensions
            image_session.image_width = width
            image_session.image_height = height
            image_session.is_modified = True
            image_session.last_modified_at = datetime.now(timezone.utc)

            # Clear annotation layer (annotations no longer valid after crop)
            annotation_query = select(AnnotationLayer).where(AnnotationLayer.session_id == session_id)
            annotation_result = await db.execute(annotation_query)
            annotation_layer = annotation_result.scalar_one_or_none()

            if annotation_layer:
                # Reset to empty canvas
                import json
                annotation_layer.canvas_json = json.dumps({
                    "version": "5.3.0",
                    "objects": []
                })
                annotation_layer.version += 1
                annotation_layer.last_updated = datetime.now(timezone.utc)

            await db.commit()

            logger.info(
                f"Successfully cropped image session {session_id} to {width}x{height}"
            )

            return {
                "session_id": session_id,
                "image_width": width,
                "image_height": height,
                "is_modified": True
            }

        except SessionNotFoundError:
            raise
        except ImageEditorError:
            raise
        except Exception as e:
            logger.error(f"Error cropping image session {session_id}: {str(e)}")
            raise ImageEditorError(f"Failed to crop image: {str(e)}")

    async def resize_image(
        self,
        session_id: str,
        width: int,
        height: int,
        maintain_aspect_ratio: bool,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Resize image to specified dimensions.

        Args:
            session_id: Image session ID
            width: Target width
            height: Target height
            maintain_aspect_ratio: Whether to maintain aspect ratio
            db: Database session

        Returns:
            Dict: Updated session info with new dimensions

        Raises:
            SessionNotFoundError: If session not found
            ValueError: If session_id is not a valid UUID
            ImageEditorError: If resize fails
        """
        logger.info(f"Resizing image session {session_id}: {width}x{height}, aspect_ratio={maintain_aspect_ratio}")

        # T140: Validate UUID to prevent SQL injection
        session_id = validate_uuid(session_id, "session_id")

        try:
            # Load ImageSession from database
            session_query = select(ImageSession).where(ImageSession.id == session_id)
            session_result = await db.execute(session_query)
            image_session = session_result.scalar_one_or_none()

            if not image_session:
                raise SessionNotFoundError(f"Image session not found: {session_id}")

            # Validate dimensions
            MAX_DIMENSION = 32767  # Canvas API limit

            if width <= 0 or height <= 0:
                raise ImageEditorError(f"Resize dimensions must be positive: width={width}, height={height}")

            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise ImageEditorError(
                    f"Resize dimensions exceed maximum ({MAX_DIMENSION}): width={width}, height={height}"
                )

            # Calculate final dimensions if maintaining aspect ratio
            original_width = image_session.image_width
            original_height = image_session.image_height
            final_width = width
            final_height = height

            if maintain_aspect_ratio:
                # Calculate aspect ratio
                aspect_ratio = original_width / original_height

                # If width is provided, calculate height
                if width > 0:
                    final_height = int(width / aspect_ratio)
                # If height is provided and width is 0 or invalid, calculate width
                elif height > 0:
                    final_width = int(height * aspect_ratio)

                # Ensure we don't exceed max dimension
                if final_width > MAX_DIMENSION:
                    final_width = MAX_DIMENSION
                    final_height = int(final_width / aspect_ratio)
                if final_height > MAX_DIMENSION:
                    final_height = MAX_DIMENSION
                    final_width = int(final_height * aspect_ratio)

            # Load image from temp file
            temp_path = Path(image_session.temp_file_path)
            if not temp_path.exists():
                raise ImageEditorError(f"Temporary file not found: {temp_path}")

            # Load and resize image with Pillow using LANCZOS filter for quality
            image = await asyncio.to_thread(Image.open, temp_path)

            # Apply resize with LANCZOS (high-quality resampling)
            resized_image = await asyncio.to_thread(
                image.resize,
                (final_width, final_height),
                Image.Resampling.LANCZOS
            )

            # Save resized image back to temp file
            await asyncio.to_thread(resized_image.save, str(temp_path))

            # Calculate scale factors for annotation layer
            scale_x = final_width / original_width
            scale_y = final_height / original_height

            # Update ImageSession dimensions
            image_session.image_width = final_width
            image_session.image_height = final_height
            image_session.is_modified = True
            image_session.last_modified_at = datetime.now(timezone.utc)

            # Scale annotation layer coordinates
            annotation_query = select(AnnotationLayer).where(AnnotationLayer.session_id == session_id)
            annotation_result = await db.execute(annotation_query)
            annotation_layer = annotation_result.scalar_one_or_none()

            if annotation_layer:
                import json
                try:
                    canvas_data = json.loads(annotation_layer.canvas_json)

                    # Scale all objects in the canvas
                    if "objects" in canvas_data:
                        for obj in canvas_data["objects"]:
                            # Scale position
                            if "left" in obj:
                                obj["left"] *= scale_x
                            if "top" in obj:
                                obj["top"] *= scale_y

                            # Scale dimensions
                            if "width" in obj:
                                obj["width"] *= scale_x
                            if "height" in obj:
                                obj["height"] *= scale_y

                            # Scale stroke width
                            if "strokeWidth" in obj:
                                obj["strokeWidth"] *= min(scale_x, scale_y)

                            # Scale font size for text objects
                            if obj.get("type") == "text" and "fontSize" in obj:
                                obj["fontSize"] *= min(scale_x, scale_y)

                    annotation_layer.canvas_json = json.dumps(canvas_data)
                    annotation_layer.version += 1
                    annotation_layer.last_updated = datetime.now(timezone.utc)

                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse canvas JSON for session {session_id}, clearing annotations")
                    annotation_layer.canvas_json = json.dumps({"version": "5.3.0", "objects": []})

            await db.commit()

            logger.info(
                f"Successfully resized image session {session_id} to {final_width}x{final_height}"
            )

            return {
                "session_id": session_id,
                "image_width": final_width,
                "image_height": final_height,
                "is_modified": True,
                "scale_x": scale_x,
                "scale_y": scale_y
            }

        except SessionNotFoundError:
            raise
        except ImageEditorError:
            raise
        except Exception as e:
            logger.error(f"Error resizing image session {session_id}: {str(e)}")
            raise ImageEditorError(f"Failed to resize image: {str(e)}")

    async def save_image(
        self,
        session_id: str,
        output_path: str,
        db: AsyncSession
    ) -> str:
        """
        Save edited image to filesystem.

        Args:
            session_id: Image session ID
            output_path: Target file path
            db: Database session

        Returns:
            str: Saved file path

        Raises:
            SessionNotFoundError: If session not found
            ImageEditorError: If save fails
        """
        logger.info(f"Saving image session {session_id} to: {output_path}")

        # T140: Validate UUID to prevent SQL injection
        session_id = validate_uuid(session_id, "session_id")

        try:
            # Load ImageSession from database
            session_query = select(ImageSession).where(ImageSession.id == session_id)
            session_result = await db.execute(session_query)
            image_session = session_result.scalar_one_or_none()

            if not image_session:
                raise SessionNotFoundError(f"Image session not found: {session_id}")

            # T139: Validate and prepare output path
            output_file = Path(output_path)

            # Security: Prevent directory traversal and path injection
            if '..' in str(output_file):
                raise ImageEditorError("Invalid output path: path traversal detected ('..')")

            if '~' in str(output_file):
                raise ImageEditorError("Invalid output path: home directory expansion detected ('~')")

            # Block null bytes
            if '\x00' in output_path:
                raise ImageEditorError("Invalid output path: null byte detected")

            # Validate file extension
            extension = output_file.suffix.lower().lstrip('.')
            valid_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
            if extension and extension not in valid_extensions:
                raise ImageEditorError(
                    f"Invalid output file extension: .{extension}. "
                    f"Allowed extensions: {', '.join('.' + ext for ext in sorted(valid_extensions))}"
                )

            # Convert to absolute path to prevent relative path issues
            try:
                output_file = output_file.resolve()
            except (RuntimeError, OSError) as e:
                raise ImageEditorError(f"Cannot resolve output path: {str(e)}")

            # Ensure parent directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Load image from temp file
            temp_path = Path(image_session.temp_file_path)
            if not temp_path.exists():
                raise ImageEditorError(f"Temporary file not found: {temp_path}")

            # Load image with Pillow
            image = await asyncio.to_thread(Image.open, temp_path)

            # Note: Annotations are rendered on the frontend canvas.
            # The frontend will need to export the canvas as an image and send it
            # to this endpoint if annotations should be included.
            # For now, we save the base image.
            # In a future enhancement, we could accept canvas_data_url parameter
            # to merge annotations.

            # Save image to output path
            await asyncio.to_thread(image.save, str(output_file))

            # Update session metadata
            image_session.is_modified = False
            image_session.last_modified_at = datetime.now(timezone.utc)

            await db.commit()

            # Get file size
            file_size = output_file.stat().st_size

            logger.info(
                f"Successfully saved image session {session_id} to {output_path} "
                f"({file_size} bytes)"
            )

            return str(output_file.absolute())

        except SessionNotFoundError:
            raise
        except ImageEditorError:
            raise
        except Exception as e:
            logger.error(f"Error saving image session {session_id}: {str(e)}")
            raise ImageEditorError(f"Failed to save image: {str(e)}")

    async def apply_blur(
        self,
        session_id: str,
        radius: float,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Apply Gaussian blur filter to image.

        Args:
            session_id: Image session ID
            radius: Blur radius (0-20 pixels)
            db: Database session

        Returns:
            dict: Result with blur info and image dimensions

        Raises:
            SessionNotFoundError: If session not found
            ValueError: If radius is invalid
            ImageEditorError: If blur application fails
        """
        logger.info(f"Applying blur filter to session {session_id} with radius {radius}")

        # T140: Validate UUID to prevent SQL injection
        session_id = validate_uuid(session_id, "session_id")

        # Validate radius parameter
        if not isinstance(radius, (int, float)) or radius < 0 or radius > 20:
            raise ValueError("Blur radius must be between 0 and 20 pixels")

        try:
            # Load ImageSession from database
            session_query = select(ImageSession).where(ImageSession.id == session_id)
            session_result = await db.execute(session_query)
            image_session = session_result.scalar_one_or_none()

            if not image_session:
                raise SessionNotFoundError(f"Image session not found: {session_id}")

            # Load image from temp file
            temp_path = Path(image_session.temp_file_path)
            if not temp_path.exists():
                raise ImageEditorError(f"Temp file not found: {temp_path}")

            # Load image using Pillow
            image = await asyncio.to_thread(Image.open, temp_path)

            # Apply Gaussian blur filter
            # GaussianBlur radius parameter controls blur intensity
            blurred_image = await asyncio.to_thread(
                image.filter,
                ImageFilter.GaussianBlur(radius=radius)
            )

            # Save blurred image back to temp file
            await asyncio.to_thread(blurred_image.save, temp_path)

            # Update image session metadata
            image_session.is_modified = True
            image_session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(image_session)

            # Record operation in history
            operation = EditOperation(
                session_id=session_id,
                operation_type=OperationType.FILTER,
                parameters={'filter': 'blur', 'radius': radius},
                timestamp=datetime.now(timezone.utc)
            )
            db.add(operation)
            await db.commit()

            logger.info(
                f"Successfully applied blur (radius={radius}) to session {session_id}"
            )

            return {
                "message": "Blur applied successfully",
                "radius": radius,
                "width": image_session.image_width,
                "height": image_session.image_height,
                "session_id": session_id
            }

        except SessionNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error applying blur to session {session_id}: {str(e)}")
            raise ImageEditorError(f"Failed to apply blur: {str(e)}")

    async def apply_sharpen(
        self,
        session_id: str,
        amount: float,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Apply sharpen filter to image.

        Args:
            session_id: Image session ID
            amount: Sharpen amount/intensity (0-10, converted to 0-1 for UnsharpMask)
            db: Database session

        Returns:
            dict: Result with sharpen info and image dimensions

        Raises:
            SessionNotFoundError: If session not found
            ValueError: If amount is invalid
            ImageEditorError: If sharpen application fails
        """
        logger.info(f"Applying sharpen filter to session {session_id} with amount {amount}")

        # T140: Validate UUID to prevent SQL injection
        session_id = validate_uuid(session_id, "session_id")

        # Validate amount parameter
        if not isinstance(amount, (int, float)) or amount < 0 or amount > 10:
            raise ValueError("Sharpen amount must be between 0 and 10")

        try:
            # Load ImageSession from database
            session_query = select(ImageSession).where(ImageSession.id == session_id)
            session_result = await db.execute(session_query)
            image_session = session_result.scalar_one_or_none()

            if not image_session:
                raise SessionNotFoundError(f"Image session not found: {session_id}")

            # Load image from temp file
            temp_path = Path(image_session.temp_file_path)
            if not temp_path.exists():
                raise ImageEditorError(f"Temp file not found: {temp_path}")

            # Load image using Pillow
            image = await asyncio.to_thread(Image.open, temp_path)

            # Apply UnsharpMask filter for sharpening
            # UnsharpMask parameters:
            # - radius: blur radius (default 2)
            # - percent: sharpening strength (we scale amount 0-10 to 0-150%)
            # - threshold: minimum brightness change (default 3)
            sharpen_percent = int(amount * 15)  # 0-10 → 0-150%
            sharpened_image = await asyncio.to_thread(
                image.filter,
                ImageFilter.UnsharpMask(
                    radius=2,
                    percent=sharpen_percent,
                    threshold=3
                )
            )

            # Save sharpened image back to temp file
            await asyncio.to_thread(sharpened_image.save, temp_path)

            # Update image session metadata
            image_session.is_modified = True
            image_session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(image_session)

            # Record operation in history
            operation = EditOperation(
                session_id=session_id,
                operation_type=OperationType.FILTER,
                parameters={'filter': 'sharpen', 'amount': amount},
                timestamp=datetime.now(timezone.utc)
            )
            db.add(operation)
            await db.commit()

            logger.info(
                f"Successfully applied sharpen (amount={amount}) to session {session_id}"
            )

            return {
                "message": "Sharpen applied successfully",
                "amount": amount,
                "width": image_session.image_width,
                "height": image_session.image_height,
                "session_id": session_id
            }

        except SessionNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error applying sharpen to session {session_id}: {str(e)}")
            raise ImageEditorError(f"Failed to apply sharpen: {str(e)}")

    async def update_annotation_layer(
        self,
        session_id: str,
        canvas_json: str,
        db: AsyncSession
    ) -> int:
        """
        Update annotation layer with new canvas state.

        Args:
            session_id: Image session ID
            canvas_json: Fabric.js canvas JSON
            db: Database session

        Returns:
            int: New version number

        Raises:
            SessionNotFoundError: If session not found
        """
        logger.info(f"Updating annotation layer for session: {session_id}")

        # T140: Validate UUID to prevent SQL injection
        session_id = validate_uuid(session_id, "session_id")

        # Load annotation layer
        query = select(AnnotationLayer).where(AnnotationLayer.session_id == session_id)
        result = await db.execute(query)
        annotation_layer = result.scalar_one_or_none()

        if not annotation_layer:
            raise SessionNotFoundError(f"Annotation layer not found for session: {session_id}")

        # Update canvas JSON
        annotation_layer.canvas_json = canvas_json

        # Increment version (optimistic locking)
        annotation_layer.version += 1
        new_version = annotation_layer.version

        # Update timestamp
        annotation_layer.last_updated = datetime.now(timezone.utc)

        # Mark session as modified
        session_query = select(ImageSession).where(ImageSession.id == session_id)
        session_result = await db.execute(session_query)
        image_session = session_result.scalar_one_or_none()

        if image_session:
            image_session.is_modified = True
            image_session.last_modified_at = datetime.now(timezone.utc)

        await db.commit()

        logger.info(f"Updated annotation layer for session {session_id}, new version: {new_version}")
        return new_version

    async def store_undo_snapshot(
        self,
        session_id: str,
        operation_type: OperationType,
        canvas_snapshot: str,
        position: int,
        db: AsyncSession
    ) -> None:
        """
        Store edit operation snapshot for undo/redo.

        Args:
            session_id: Image session ID
            operation_type: Type of operation
            canvas_snapshot: Fabric.js canvas state JSON
            position: Position in circular buffer (0-49)
            db: Database session
        """
        logger.info(f"Storing undo snapshot for session {session_id} at position {position}")

        # TODO: Implement snapshot storage logic
        # - Create or update EditOperation record
        # - Store canvas_snapshot at given position
        # - Handle circular buffer (overwrite old snapshots)

        raise NotImplementedError("store_undo_snapshot not yet implemented")

    async def get_undo_snapshot(
        self,
        session_id: str,
        position: int,
        db: AsyncSession
    ) -> Optional[str]:
        """
        Retrieve undo snapshot at position.

        Args:
            session_id: Image session ID
            position: Position in circular buffer (0-49)
            db: Database session

        Returns:
            Optional[str]: Canvas snapshot JSON, or None if not found
        """
        logger.info(f"Retrieving undo snapshot for session {session_id} at position {position}")

        # TODO: Implement snapshot retrieval logic
        # - Query EditOperation by session_id and position
        # - Return canvas_snapshot if found

        raise NotImplementedError("get_undo_snapshot not yet implemented")

    async def cleanup_expired_sessions(self, db: AsyncSession, hours: int = 24) -> int:
        """
        Clean up expired image sessions and temporary files (T141).

        Args:
            db: Database session
            hours: Session age threshold in hours (default 24)

        Returns:
            int: Number of sessions cleaned up
        """
        from datetime import timedelta
        import asyncio

        logger.info(f"Cleaning up sessions older than {hours} hours")

        # Calculate cutoff datetime
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        try:
            # Query ImageSession records older than threshold
            query = select(ImageSession).where(ImageSession.created_at < cutoff_time)
            result = await db.execute(query)
            expired_sessions = result.scalars().all()

            cleaned_count = 0
            temp_files_deleted = 0

            for session in expired_sessions:
                try:
                    # Delete temporary file if it exists
                    temp_path = Path(session.temp_file_path)
                    if temp_path.exists():
                        try:
                            await asyncio.to_thread(temp_path.unlink)
                            temp_files_deleted += 1
                            logger.debug(f"Deleted temp file: {temp_path}")
                        except OSError as e:
                            logger.warning(f"Failed to delete temp file {temp_path}: {str(e)}")

                    # Delete session record (CASCADE will delete related annotation_layers and edit_operations)
                    await db.delete(session)
                    cleaned_count += 1

                except Exception as e:
                    logger.error(f"Error cleaning up session {session.id}: {str(e)}")
                    continue

            # Commit all deletions
            await db.commit()

            logger.info(
                f"Cleaned up {cleaned_count} expired sessions "
                f"(deleted {temp_files_deleted} temp files)"
            )

            return cleaned_count

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            await db.rollback()
            raise ImageEditorError(f"Failed to clean up expired sessions: {str(e)}")

    async def cleanup_orphaned_temp_files(
        self,
        temp_dir: Path,
        db: AsyncSession,
        max_age_hours: int = 48
    ) -> int:
        """
        Clean up orphaned temporary files that have no associated session (T142).

        Args:
            temp_dir: Directory containing temporary files
            db: Database session
            max_age_hours: Maximum age for orphaned files in hours (default 48)

        Returns:
            int: Number of orphaned files deleted
        """
        import asyncio
        from datetime import timedelta
        import time

        logger.info(f"Cleaning up orphaned temp files in {temp_dir}")

        if not temp_dir.exists():
            logger.warning(f"Temp directory does not exist: {temp_dir}")
            return 0

        try:
            # Get all temp files with imgcat prefix
            temp_files = list(temp_dir.glob("imgcat_*"))
            logger.info(f"Found {len(temp_files)} potential temp files")

            # Get all active temp file paths from database
            query = select(ImageSession.temp_file_path)
            result = await db.execute(query)
            active_temp_paths = {Path(row[0]) for row in result.all()}

            orphaned_count = 0
            cutoff_time = time.time() - (max_age_hours * 3600)

            for temp_file in temp_files:
                try:
                    # Skip if file is associated with an active session
                    if temp_file in active_temp_paths:
                        continue

                    # Check file age
                    file_stat = temp_file.stat()
                    if file_stat.st_mtime > cutoff_time:
                        # File is recent, might be actively being created
                        continue

                    # Delete orphaned file
                    await asyncio.to_thread(temp_file.unlink)
                    orphaned_count += 1
                    logger.debug(f"Deleted orphaned temp file: {temp_file}")

                except FileNotFoundError:
                    # File already deleted
                    continue
                except OSError as e:
                    logger.warning(f"Failed to delete orphaned file {temp_file}: {str(e)}")
                    continue

            logger.info(f"Cleaned up {orphaned_count} orphaned temp files")
            return orphaned_count

        except Exception as e:
            logger.error(f"Error during orphaned file cleanup: {str(e)}")
            raise ImageEditorError(f"Failed to clean up orphaned temp files: {str(e)}")

    async def downsample_for_editing(
        self,
        image_path: Path,
        max_dimension: int = 4096
    ) -> Optional[Path]:
        """
        Downsample large images for editing performance (T143).

        Large images are downsampled to a maximum dimension while preserving aspect ratio.
        The original image is preserved and upsampled on save.

        Args:
            image_path: Path to image file
            max_dimension: Maximum width or height (default 4096px)

        Returns:
            Optional[Path]: Path to downsampled image, or None if downsampling not needed
        """
        import asyncio

        logger.info(f"Checking if image needs downsampling: {image_path}")

        try:
            # Load image
            image = await asyncio.to_thread(Image.open, image_path)
            width, height = image.size

            # Check if downsampling is needed
            if width <= max_dimension and height <= max_dimension:
                logger.info(f"Image {width}x{height} does not need downsampling")
                return None

            # Calculate new dimensions (preserve aspect ratio)
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))

            logger.info(f"Downsampling image from {width}x{height} to {new_width}x{new_height}")

            # Downsample with LANCZOS filter for quality
            downsampled = await asyncio.to_thread(
                image.resize,
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )

            # Save downsampled version to temp file
            import tempfile
            temp_fd, temp_path_str = tempfile.mkstemp(suffix='.png', prefix='imgcat_downsampled_')
            temp_path = Path(temp_path_str)

            await asyncio.to_thread(downsampled.save, temp_path, format='PNG')

            logger.info(f"Saved downsampled image to: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Error downsampling image: {str(e)}")
            raise ImageEditorError(f"Failed to downsample image: {str(e)}")

    async def upsample_on_save(
        self,
        edited_image_path: Path,
        original_image_path: Path,
        output_path: Path
    ) -> None:
        """
        Upsample edited image back to original dimensions on save (T143).

        Args:
            edited_image_path: Path to edited downsampled image
            original_image_path: Path to original full-resolution image
            output_path: Path where upsampled image should be saved
        """
        import asyncio

        logger.info(f"Upsampling edited image back to original dimensions")

        try:
            # Load original image to get target dimensions
            original = await asyncio.to_thread(Image.open, original_image_path)
            target_width, target_height = original.size
            original.close()

            # Load edited image
            edited = await asyncio.to_thread(Image.open, edited_image_path)

            # Upsample to original dimensions
            upsampled = await asyncio.to_thread(
                edited.resize,
                (target_width, target_height),
                Image.Resampling.LANCZOS
            )

            # Save upsampled image
            await asyncio.to_thread(upsampled.save, output_path)

            logger.info(f"Saved upsampled image ({target_width}x{target_height}) to: {output_path}")

        except Exception as e:
            logger.error(f"Error upsampling image: {str(e)}")
            raise ImageEditorError(f"Failed to upsample image: {str(e)}")

    @staticmethod
    def compress_canvas_json(canvas_json: str) -> bytes:
        """
        Compress canvas JSON data using gzip (T144).

        Args:
            canvas_json: Uncompressed Fabric.js canvas JSON string

        Returns:
            bytes: Gzip-compressed JSON data
        """
        import gzip

        try:
            compressed = gzip.compress(canvas_json.encode('utf-8'), compresslevel=6)
            compression_ratio = len(compressed) / len(canvas_json.encode('utf-8'))

            logger.debug(
                f"Compressed canvas JSON: {len(canvas_json)} -> {len(compressed)} bytes "
                f"({compression_ratio:.1%} size)"
            )

            return compressed

        except Exception as e:
            logger.error(f"Error compressing canvas JSON: {str(e)}")
            raise ImageEditorError(f"Failed to compress canvas JSON: {str(e)}")

    @staticmethod
    def decompress_canvas_json(compressed_data: bytes) -> str:
        """
        Decompress gzip-compressed canvas JSON data (T144).

        Args:
            compressed_data: Gzip-compressed JSON data

        Returns:
            str: Decompressed Fabric.js canvas JSON string
        """
        import gzip

        try:
            decompressed = gzip.decompress(compressed_data).decode('utf-8')

            logger.debug(f"Decompressed canvas JSON: {len(compressed_data)} -> {len(decompressed)} bytes")

            return decompressed

        except Exception as e:
            logger.error(f"Error decompressing canvas JSON: {str(e)}")
            raise ImageEditorError(f"Failed to decompress canvas JSON: {str(e)}")
