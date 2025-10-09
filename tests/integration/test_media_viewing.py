"""Integration tests for image and video viewing in terminal.

These tests verify complete user workflows for viewing media assets inline
in terminal sessions, including image display, video playback, thumbnail
generation, and media metadata handling.

CRITICAL: These tests MUST FAIL until the implementation is complete.
Tests validate end-to-end media viewing workflows from the quickstart guide.
"""

import pytest
import base64
import io
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestMediaViewingIntegration:
    """Test complete media viewing workflows in terminal sessions."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers."""
        return {"Authorization": "Bearer mock-jwt-token"}

    @pytest.fixture
    def terminal_session(self, client, auth_headers):
        """Create a terminal session for testing."""
        response = client.post(
            "/api/terminal/sessions",
            json={
                "shell": "bash",
                "workingDirectory": "/tmp",
                "terminalSize": {"cols": 80, "rows": 24}
            },
            headers=auth_headers
        )
        return response.json()["sessionId"]

    @pytest.fixture
    def mock_image_data(self):
        """Mock image file data."""
        return {
            "filename": "test_image.png",
            "content": base64.b64encode(b"fake-png-data").decode(),
            "mimetype": "image/png",
            "size": 1024,
            "dimensions": {"width": 640, "height": 480}
        }

    @pytest.fixture
    def mock_video_data(self):
        """Mock video file data."""
        return {
            "filename": "test_video.mp4",
            "content": base64.b64encode(b"fake-video-data").decode(),
            "mimetype": "video/mp4",
            "size": 5 * 1024 * 1024,  # 5MB
            "duration": 30.5,
            "dimensions": {"width": 1920, "height": 1080}
        }

    def test_inline_image_display_workflow(self, client, auth_headers, terminal_session, mock_image_data):
        """Test complete workflow: upload image → display inline → view metadata.

        User Story: User runs 'cat image.png' in terminal and sees inline image display
        with metadata and controls for zooming/downloading.
        """
        with pytest.raises((Exception, AssertionError)):
            # Step 1: Upload image to session
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": (mock_image_data["filename"],
                           base64.b64decode(mock_image_data["content"]),
                           mock_image_data["mimetype"])
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )

            assert upload_response.status_code == 201
            media_data = upload_response.json()
            media_id = media_data["mediaId"]
            assert media_data["type"] == "image"
            assert media_data["filename"] == mock_image_data["filename"]

            # Step 2: Trigger inline display via WebSocket (simulating 'cat image.png')
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                # Send command that triggers image display
                websocket.send_json({
                    "type": "input",
                    "data": f"cat {mock_image_data['filename']}\r"
                })

                # Should receive media display message
                response = websocket.receive_json()
                assert response["type"] == "media_display"
                assert response["mediaId"] == media_id
                assert response["displayType"] == "inline"
                assert "thumbnailUrl" in response
                assert "fullImageUrl" in response

            # Step 3: Get media metadata
            metadata_response = client.get(
                f"/api/media/{media_id}",
                headers=auth_headers
            )
            assert metadata_response.status_code == 200
            metadata = metadata_response.json()
            assert metadata["type"] == "image"
            assert metadata["dimensions"]["width"] == mock_image_data["dimensions"]["width"]
            assert metadata["size"] == mock_image_data["size"]

            # Step 4: Get thumbnail for display
            thumbnail_response = client.get(
                f"/api/media/{media_id}/thumbnail",
                headers=auth_headers
            )
            assert thumbnail_response.status_code == 200
            assert thumbnail_response.headers["content-type"].startswith("image/")

    def test_video_preview_and_playback_workflow(self, client, auth_headers, terminal_session, mock_video_data):
        """Test complete workflow: upload video → show preview → control playback.

        User Story: User views video file in terminal, sees thumbnail preview with
        play controls, can play/pause/seek video inline.
        """
        with pytest.raises((Exception, AssertionError)):
            # Check video size limit (50MB max per requirements)
            assert mock_video_data["size"] <= 50 * 1024 * 1024

            # Step 1: Upload video
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": (mock_video_data["filename"],
                           base64.b64decode(mock_video_data["content"]),
                           mock_video_data["mimetype"])
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )

            assert upload_response.status_code == 201
            media_data = upload_response.json()
            media_id = media_data["mediaId"]
            assert media_data["type"] == "video"

            # Step 2: Trigger video preview display
            with client.websocket_connect(f"/ws/terminal/{terminal_session}") as websocket:
                websocket.send_json({
                    "type": "input",
                    "data": f"file {mock_video_data['filename']}\r"
                })

                # Should receive video preview
                response = websocket.receive_json()
                assert response["type"] == "media_display"
                assert response["mediaId"] == media_id
                assert response["displayType"] == "video_preview"
                assert "thumbnailUrl" in response
                assert "videoUrl" in response
                assert "duration" in response

            # Step 3: Get video metadata including duration
            metadata_response = client.get(
                f"/api/media/{media_id}",
                headers=auth_headers
            )
            assert metadata_response.status_code == 200
            metadata = metadata_response.json()
            assert metadata["type"] == "video"
            assert metadata["duration"] == mock_video_data["duration"]
            assert metadata["dimensions"]["width"] == mock_video_data["dimensions"]["width"]

            # Step 4: Test video streaming endpoint
            stream_response = client.get(
                f"/api/media/{media_id}/stream",
                headers={**auth_headers, "Range": "bytes=0-1023"}
            )
            assert stream_response.status_code == 206  # Partial content
            assert "content-range" in stream_response.headers

    def test_media_thumbnail_generation_workflow(self, client, auth_headers, terminal_session):
        """Test thumbnail generation for different media types.

        User Story: System automatically generates thumbnails for quick preview
        in terminal, with different sizes for different display contexts.
        """
        with pytest.raises((Exception, AssertionError)):
            # Test image thumbnail
            image_upload = client.post(
                f"/api/media/upload",
                files={
                    "file": ("large_image.jpg", b"fake-large-jpg-data", "image/jpeg")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            image_id = image_upload.json()["mediaId"]

            # Request different thumbnail sizes
            for size in ["small", "medium", "large"]:
                thumb_response = client.get(
                    f"/api/media/{image_id}/thumbnail",
                    params={"size": size},
                    headers=auth_headers
                )
                assert thumb_response.status_code == 200
                assert thumb_response.headers["content-type"].startswith("image/")

            # Test video thumbnail (frame extraction)
            video_upload = client.post(
                f"/api/media/upload",
                files={
                    "file": ("sample_video.mp4", b"fake-video-data", "video/mp4")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            video_id = video_upload.json()["mediaId"]

            # Video thumbnail at specific timestamp
            video_thumb_response = client.get(
                f"/api/media/{video_id}/thumbnail",
                params={"timestamp": "5.0"},  # 5 seconds in
                headers=auth_headers
            )
            assert video_thumb_response.status_code == 200
            assert video_thumb_response.headers["content-type"].startswith("image/")

    def test_media_performance_requirements(self, client, auth_headers, terminal_session):
        """Test media performance requirements: <1s image load, proper video streaming.

        User Story: Media loads quickly without blocking terminal interaction.
        Tests performance requirements from feature spec.
        """
        with pytest.raises((Exception, AssertionError)):
            import time

            # Test image load performance (<1 second requirement)
            start_time = time.time()

            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("performance_test.png", b"fake-png-data" * 100, "image/png")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )

            media_id = upload_response.json()["mediaId"]

            # Get thumbnail (should be fast)
            thumbnail_response = client.get(
                f"/api/media/{media_id}/thumbnail",
                headers=auth_headers
            )

            load_time = time.time() - start_time

            assert thumbnail_response.status_code == 200
            assert load_time < 1.0  # <1 second requirement

            # Test video streaming doesn't block
            video_upload = client.post(
                f"/api/media/upload",
                files={
                    "file": ("large_video.mp4", b"fake-video-data" * 1000, "video/mp4")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )

            video_id = video_upload.json()["mediaId"]

            # Streaming should start immediately
            start_time = time.time()
            stream_response = client.get(
                f"/api/media/{video_id}/stream",
                headers={**auth_headers, "Range": "bytes=0-1023"}
            )
            stream_start_time = time.time() - start_time

            assert stream_response.status_code == 206
            assert stream_start_time < 0.5  # Should start streaming quickly

    def test_media_file_validation_and_security(self, client, auth_headers, terminal_session):
        """Test media file validation and security measures.

        User Story: System validates file types and prevents malicious file uploads
        while maintaining security boundaries.
        """
        with pytest.raises((Exception, AssertionError)):
            # Test file size limits (50MB max for videos)
            large_video_data = b"fake-video-data" * (51 * 1024 * 1024 // 15)  # >50MB
            large_upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("too_large.mp4", large_video_data, "video/mp4")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            assert large_upload_response.status_code == 413  # Payload too large

            # Test invalid file types
            invalid_upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("malicious.exe", b"fake-exe-data", "application/x-executable")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            assert invalid_upload_response.status_code == 422  # Unsupported file type

            # Test valid file types are accepted
            valid_types = [
                ("image.png", "image/png"),
                ("image.jpg", "image/jpeg"),
                ("image.gif", "image/gif"),
                ("video.mp4", "video/mp4"),
                ("video.webm", "video/webm")
            ]

            for filename, mimetype in valid_types:
                valid_response = client.post(
                    f"/api/media/upload",
                    files={
                        "file": (filename, b"fake-data", mimetype)
                    },
                    data={"sessionId": terminal_session},
                    headers=auth_headers
                )
                assert valid_response.status_code == 201

    def test_media_session_isolation(self, client, auth_headers):
        """Test media files are properly isolated between terminal sessions.

        User Story: User's media in one terminal tab is not visible in another tab.
        Tests session-based access control for media assets.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create two separate sessions
            session1_response = client.post(
                "/api/terminal/sessions",
                json={
                    "shell": "bash",
                    "workingDirectory": "/tmp",
                    "terminalSize": {"cols": 80, "rows": 24}
                },
                headers=auth_headers
            )
            session1_id = session1_response.json()["sessionId"]

            session2_response = client.post(
                "/api/terminal/sessions",
                json={
                    "shell": "bash",
                    "workingDirectory": "/tmp",
                    "terminalSize": {"cols": 80, "rows": 24}
                },
                headers=auth_headers
            )
            session2_id = session2_response.json()["sessionId"]

            # Upload media to session1
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("session1_image.png", b"session1-data", "image/png")
                },
                data={"sessionId": session1_id},
                headers=auth_headers
            )
            media_id = upload_response.json()["mediaId"]

            # Verify media is accessible from session1
            session1_media_response = client.get(
                f"/api/media/{media_id}",
                params={"sessionId": session1_id},
                headers=auth_headers
            )
            assert session1_media_response.status_code == 200

            # Verify media is NOT accessible from session2
            session2_media_response = client.get(
                f"/api/media/{media_id}",
                params={"sessionId": session2_id},
                headers=auth_headers
            )
            assert session2_media_response.status_code == 403  # Forbidden

    def test_media_cleanup_on_session_termination(self, client, auth_headers, terminal_session):
        """Test media cleanup when terminal session is terminated.

        User Story: When user closes terminal, associated media files are cleaned up
        to prevent storage bloat.
        """
        with pytest.raises((Exception, AssertionError)):
            # Upload media to session
            upload_response = client.post(
                f"/api/media/upload",
                files={
                    "file": ("cleanup_test.png", b"cleanup-test-data", "image/png")
                },
                data={"sessionId": terminal_session},
                headers=auth_headers
            )
            media_id = upload_response.json()["mediaId"]

            # Verify media exists
            media_response = client.get(
                f"/api/media/{media_id}",
                headers=auth_headers
            )
            assert media_response.status_code == 200

            # Terminate session
            terminate_response = client.delete(
                f"/api/terminal/sessions/{terminal_session}",
                headers=auth_headers
            )
            assert terminate_response.status_code == 200

            # Verify media is cleaned up
            cleanup_response = client.get(
                f"/api/media/{media_id}",
                headers=auth_headers
            )
            assert cleanup_response.status_code == 404  # Media should be gone

    def test_concurrent_media_operations(self, client, auth_headers, terminal_session):
        """Test concurrent media uploads and viewing operations.

        User Story: Multiple users or multiple tabs can upload/view media simultaneously
        without conflicts or performance degradation.
        """
        with pytest.raises((Exception, AssertionError)):
            import concurrent.futures
            import threading

            def upload_media(index):
                """Upload media file with unique identifier."""
                response = client.post(
                    f"/api/media/upload",
                    files={
                        "file": (f"concurrent_{index}.png", f"data-{index}".encode(), "image/png")
                    },
                    data={"sessionId": terminal_session},
                    headers=auth_headers
                )
                return response.status_code, response.json()

            # Upload multiple files concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(upload_media, i) for i in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            # Verify all uploads succeeded
            successful_uploads = [r for r in results if r[0] == 201]
            assert len(successful_uploads) == 10

            # Verify all media is accessible
            for status_code, response_data in successful_uploads:
                media_id = response_data["mediaId"]
                get_response = client.get(
                    f"/api/media/{media_id}",
                    headers=auth_headers
                )
                assert get_response.status_code == 200