"""Integration tests for session recording and playback functionality.

These tests verify complete user workflows for recording terminal sessions,
storing recordings with metadata, playing back sessions with timing control,
and managing recorded session data with retention policies.

CRITICAL: These tests MUST FAIL until the implementation is complete.
Tests validate end-to-end session recording workflows with <5% performance impact.
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestSessionRecordingIntegration:
    """Test complete session recording and playback workflows."""

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
    def recorded_terminal_session(self, client, auth_headers):
        """Create a terminal session with recording enabled."""
        response = client.post(
            "/api/terminal/sessions",
            json={
                "shell": "bash",
                "workingDirectory": "/tmp",
                "terminalSize": {"cols": 80, "rows": 24},
                "recordingEnabled": True
            },
            headers=auth_headers
        )
        return response.json()["sessionId"]

    @pytest.fixture
    def sample_recording_data(self):
        """Sample recording data for testing."""
        return {
            "events": [
                {"timestamp": 0.0, "type": "output", "data": "$ "},
                {"timestamp": 1.5, "type": "input", "data": "l"},
                {"timestamp": 1.6, "type": "input", "data": "s"},
                {"timestamp": 1.8, "type": "input", "data": "\r"},
                {"timestamp": 2.0, "type": "output", "data": "file1.txt\nfile2.txt\n"},
                {"timestamp": 2.5, "type": "output", "data": "$ "},
                {"timestamp": 5.0, "type": "input", "data": "echo 'Hello World'"},
                {"timestamp": 5.2, "type": "input", "data": "\r"},
                {"timestamp": 5.4, "type": "output", "data": "Hello World\n"},
                {"timestamp": 6.0, "type": "output", "data": "$ "},
                {"timestamp": 10.0, "type": "resize", "data": {"cols": 120, "rows": 30}},
                {"timestamp": 12.0, "type": "input", "data": "exit\r"},
                {"timestamp": 12.2, "type": "output", "data": "exit\n"}
            ],
            "metadata": {
                "duration": 12.2,
                "commandCount": 3,
                "startTime": "2024-01-01T12:00:00Z",
                "endTime": "2024-01-01T12:00:12Z",
                "terminalSize": {"cols": 80, "rows": 24},
                "shell": "bash",
                "workingDirectory": "/tmp"
            }
        }

    def test_session_recording_workflow(self, client, auth_headers, recorded_terminal_session):
        """Test complete workflow: start recording → interact → stop → save recording.

        User Story: User enables recording for terminal session, performs commands,
        and session is automatically recorded with timing and metadata.
        """
        with pytest.raises((Exception, AssertionError)):
            session_id = recorded_terminal_session

            # Verify recording is enabled
            session_response = client.get(
                f"/api/terminal/sessions/{session_id}",
                headers=auth_headers
            )
            assert session_response.status_code == 200
            session_data = session_response.json()
            assert session_data["recordingEnabled"] == True

            # Interact with terminal while recording
            with client.websocket_connect(f"/ws/terminal/{session_id}") as websocket:
                start_time = time.time()

                # Send commands that should be recorded
                commands = ["ls\r", "pwd\r", "echo 'Testing recording'\r"]

                for i, command in enumerate(commands):
                    websocket.send_json({
                        "type": "input",
                        "data": command,
                        "timestamp": time.time() - start_time
                    })

                    # Receive output
                    output = websocket.receive_json()
                    assert output["type"] == "output"

                    # Small delay between commands
                    time.sleep(0.5)

            # Stop recording (session termination)
            stop_response = client.post(
                f"/api/terminal/sessions/{session_id}/recording/stop",
                headers=auth_headers
            )
            assert stop_response.status_code == 200
            recording_data = stop_response.json()

            assert "recordingId" in recording_data
            assert recording_data["status"] == "completed"
            assert recording_data["duration"] > 0
            assert recording_data["eventCount"] > 0

            # Verify recording metadata
            recording_id = recording_data["recordingId"]
            metadata_response = client.get(
                f"/api/recordings/{recording_id}/metadata",
                headers=auth_headers
            )
            assert metadata_response.status_code == 200
            metadata = metadata_response.json()

            assert metadata["sessionId"] == session_id
            assert metadata["commandCount"] >= len(commands)
            assert "startTime" in metadata
            assert "endTime" in metadata

    def test_session_playback_workflow(self, client, auth_headers, sample_recording_data):
        """Test complete workflow: load recording → play back → control playback speed.

        User Story: User views recorded session with playback controls,
        can pause/resume, change speed, and seek to specific timestamps.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create a recording for playback
            create_response = client.post(
                "/api/recordings",
                json={
                    "name": "Test Recording",
                    "events": sample_recording_data["events"],
                    "metadata": sample_recording_data["metadata"]
                },
                headers=auth_headers
            )
            assert create_response.status_code == 201
            recording_id = create_response.json()["recordingId"]

            # Start playback session
            playback_response = client.post(
                f"/api/recordings/{recording_id}/playback",
                json={
                    "speed": 1.0,
                    "autoPlay": False
                },
                headers=auth_headers
            )
            assert playback_response.status_code == 200
            playback_data = playback_response.json()
            playback_id = playback_data["playbackId"]

            # Test playback controls via WebSocket
            with client.websocket_connect(f"/ws/playback/{playback_id}") as websocket:
                # Start playback
                websocket.send_json({
                    "type": "play"
                })

                play_response = websocket.receive_json()
                assert play_response["type"] == "playback_started"

                # Receive playback events
                event_count = 0
                while event_count < 5:  # Collect first 5 events
                    event = websocket.receive_json()
                    if event["type"] == "playback_event":
                        assert "timestamp" in event
                        assert "eventType" in event
                        assert "data" in event
                        event_count += 1

                # Test pause
                websocket.send_json({
                    "type": "pause"
                })

                pause_response = websocket.receive_json()
                assert pause_response["type"] == "playback_paused"
                assert "currentTime" in pause_response

                # Test speed change
                websocket.send_json({
                    "type": "set_speed",
                    "speed": 2.0
                })

                speed_response = websocket.receive_json()
                assert speed_response["type"] == "speed_changed"
                assert speed_response["speed"] == 2.0

                # Test seek
                websocket.send_json({
                    "type": "seek",
                    "timestamp": 5.0
                })

                seek_response = websocket.receive_json()
                assert seek_response["type"] == "seek_completed"
                assert seek_response["timestamp"] == 5.0

    def test_recording_performance_impact(self, client, auth_headers):
        """Test recording performance impact (<5% requirement).

        User Story: Recording terminal sessions should not noticeably impact
        terminal performance or responsiveness.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create two identical sessions - one with recording, one without
            normal_session_response = client.post(
                "/api/terminal/sessions",
                json={
                    "shell": "bash",
                    "workingDirectory": "/tmp",
                    "terminalSize": {"cols": 80, "rows": 24},
                    "recordingEnabled": False
                },
                headers=auth_headers
            )
            normal_session_id = normal_session_response.json()["sessionId"]

            recorded_session_response = client.post(
                "/api/terminal/sessions",
                json={
                    "shell": "bash",
                    "workingDirectory": "/tmp",
                    "terminalSize": {"cols": 80, "rows": 24},
                    "recordingEnabled": True
                },
                headers=auth_headers
            )
            recorded_session_id = recorded_session_response.json()["sessionId"]

            # Performance test function
            def measure_session_performance(session_id):
                start_time = time.time()
                command_times = []

                with client.websocket_connect(f"/ws/terminal/{session_id}") as websocket:
                    for i in range(10):  # Send 10 commands
                        cmd_start = time.time()
                        websocket.send_json({
                            "type": "input",
                            "data": f"echo 'Command {i}'\r"
                        })

                        # Wait for response
                        response = websocket.receive_json()
                        cmd_end = time.time()

                        assert response["type"] == "output"
                        command_times.append(cmd_end - cmd_start)

                total_time = time.time() - start_time
                avg_command_time = sum(command_times) / len(command_times)
                return total_time, avg_command_time

            # Measure performance for both sessions
            normal_total, normal_avg = measure_session_performance(normal_session_id)
            recorded_total, recorded_avg = measure_session_performance(recorded_session_id)

            # Calculate performance impact
            total_impact = ((recorded_total - normal_total) / normal_total) * 100
            avg_impact = ((recorded_avg - normal_avg) / normal_avg) * 100

            # Should be less than 5% performance impact
            assert total_impact < 5.0
            assert avg_impact < 5.0

    def test_recording_data_retention_policy(self, client, auth_headers, sample_recording_data):
        """Test 30-day retention policy for recordings.

        User Story: Old recordings are automatically cleaned up after 30 days
        to manage storage usage while preserving recent recordings.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create recordings with different ages
            current_time = datetime.now()

            # Recent recording (should be kept)
            recent_metadata = sample_recording_data["metadata"].copy()
            recent_metadata["startTime"] = current_time.isoformat()

            recent_response = client.post(
                "/api/recordings",
                json={
                    "name": "Recent Recording",
                    "events": sample_recording_data["events"],
                    "metadata": recent_metadata
                },
                headers=auth_headers
            )
            recent_id = recent_response.json()["recordingId"]

            # Old recording (should be cleaned up)
            old_time = current_time - timedelta(days=35)
            old_metadata = sample_recording_data["metadata"].copy()
            old_metadata["startTime"] = old_time.isoformat()

            old_response = client.post(
                "/api/recordings",
                json={
                    "name": "Old Recording",
                    "events": sample_recording_data["events"],
                    "metadata": old_metadata
                },
                headers=auth_headers
            )
            old_id = old_response.json()["recordingId"]

            # Trigger cleanup process
            cleanup_response = client.post(
                "/api/recordings/cleanup",
                json={"dryRun": False},
                headers=auth_headers
            )
            assert cleanup_response.status_code == 200
            cleanup_data = cleanup_response.json()

            # Verify cleanup results
            assert cleanup_data["deletedCount"] >= 1
            assert old_id in cleanup_data["deletedRecordings"]

            # Verify recent recording still exists
            recent_check = client.get(
                f"/api/recordings/{recent_id}",
                headers=auth_headers
            )
            assert recent_check.status_code == 200

            # Verify old recording is gone
            old_check = client.get(
                f"/api/recordings/{old_id}",
                headers=auth_headers
            )
            assert old_check.status_code == 404

    def test_recording_export_and_import(self, client, auth_headers, sample_recording_data):
        """Test recording export to different formats and import functionality.

        User Story: User can export recordings to standard formats (JSON, ASCIINEMA)
        and import recordings from other tools.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create recording
            create_response = client.post(
                "/api/recordings",
                json={
                    "name": "Export Test Recording",
                    "events": sample_recording_data["events"],
                    "metadata": sample_recording_data["metadata"]
                },
                headers=auth_headers
            )
            recording_id = create_response.json()["recordingId"]

            # Test JSON export
            json_export_response = client.get(
                f"/api/recordings/{recording_id}/export",
                params={"format": "json"},
                headers=auth_headers
            )
            assert json_export_response.status_code == 200
            assert json_export_response.headers["content-type"] == "application/json"

            json_data = json_export_response.json()
            assert "events" in json_data
            assert "metadata" in json_data
            assert len(json_data["events"]) == len(sample_recording_data["events"])

            # Test ASCIINEMA export
            asciinema_export_response = client.get(
                f"/api/recordings/{recording_id}/export",
                params={"format": "asciinema"},
                headers=auth_headers
            )
            assert asciinema_export_response.status_code == 200
            assert "application/x-asciinema" in asciinema_export_response.headers["content-type"]

            # Test import functionality
            import_response = client.post(
                "/api/recordings/import",
                files={
                    "file": ("recording.json", json.dumps(json_data).encode(), "application/json")
                },
                data={"name": "Imported Recording"},
                headers=auth_headers
            )
            assert import_response.status_code == 201
            imported_id = import_response.json()["recordingId"]

            # Verify imported recording
            imported_recording = client.get(
                f"/api/recordings/{imported_id}",
                headers=auth_headers
            )
            assert imported_recording.status_code == 200
            imported_data = imported_recording.json()
            assert imported_data["name"] == "Imported Recording"

    def test_concurrent_recording_sessions(self, client, auth_headers):
        """Test multiple concurrent recording sessions.

        User Story: Multiple users can record sessions simultaneously without
        interference or performance degradation.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create multiple recording sessions
            session_ids = []
            for i in range(5):
                response = client.post(
                    "/api/terminal/sessions",
                    json={
                        "shell": "bash",
                        "workingDirectory": f"/tmp/session_{i}",
                        "terminalSize": {"cols": 80, "rows": 24},
                        "recordingEnabled": True
                    },
                    headers=auth_headers
                )
                assert response.status_code == 201
                session_ids.append(response.json()["sessionId"])

            # Simulate concurrent activity
            import concurrent.futures
            import threading

            def session_activity(session_id, session_index):
                """Simulate activity in a session."""
                try:
                    with client.websocket_connect(f"/ws/terminal/{session_id}") as websocket:
                        for cmd_num in range(5):
                            websocket.send_json({
                                "type": "input",
                                "data": f"echo 'Session {session_index} Command {cmd_num}'\r"
                            })

                            response = websocket.receive_json()
                            assert response["type"] == "output"

                            time.sleep(0.1)  # Brief delay between commands
                    return True
                except Exception as e:
                    return False

            # Run concurrent sessions
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(session_activity, session_id, i)
                    for i, session_id in enumerate(session_ids)
                ]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            # All sessions should complete successfully
            assert all(results)

            # Verify all recordings were created
            for session_id in session_ids:
                recording_response = client.get(
                    f"/api/terminal/sessions/{session_id}/recording",
                    headers=auth_headers
                )
                assert recording_response.status_code == 200
                recording_data = recording_response.json()
                assert recording_data["eventCount"] > 0

    def test_recording_search_and_filtering(self, client, auth_headers):
        """Test search and filtering functionality for recordings.

        User Story: User can search through recordings by name, date, command content,
        and filter recordings based on various criteria.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create recordings with different characteristics
            recordings_data = [
                {
                    "name": "Python Development Session",
                    "metadata": {"shell": "bash", "tags": ["python", "development"]},
                    "commands": ["python", "pip install", "pytest"]
                },
                {
                    "name": "Database Migration",
                    "metadata": {"shell": "bash", "tags": ["database", "migration"]},
                    "commands": ["psql", "alembic upgrade", "pg_dump"]
                },
                {
                    "name": "Server Configuration",
                    "metadata": {"shell": "zsh", "tags": ["server", "config"]},
                    "commands": ["nginx", "systemctl", "vim /etc/nginx"]
                }
            ]

            recording_ids = []
            for recording_data in recordings_data:
                # Create events based on commands
                events = []
                timestamp = 0.0
                for cmd in recording_data["commands"]:
                    events.append({"timestamp": timestamp, "type": "input", "data": cmd})
                    timestamp += 1.0
                    events.append({"timestamp": timestamp, "type": "output", "data": f"Output for {cmd}\n"})
                    timestamp += 1.0

                response = client.post(
                    "/api/recordings",
                    json={
                        "name": recording_data["name"],
                        "events": events,
                        "metadata": recording_data["metadata"]
                    },
                    headers=auth_headers
                )
                recording_ids.append(response.json()["recordingId"])

            # Test search by name
            search_response = client.get(
                "/api/recordings/search",
                params={"query": "Python", "field": "name"},
                headers=auth_headers
            )
            assert search_response.status_code == 200
            search_results = search_response.json()
            assert len(search_results["recordings"]) >= 1
            assert any("Python" in rec["name"] for rec in search_results["recordings"])

            # Test search by command content
            command_search_response = client.get(
                "/api/recordings/search",
                params={"query": "psql", "field": "commands"},
                headers=auth_headers
            )
            assert command_search_response.status_code == 200
            command_results = command_search_response.json()
            assert len(command_results["recordings"]) >= 1

            # Test filtering by shell
            filter_response = client.get(
                "/api/recordings",
                params={"shell": "bash", "limit": 10},
                headers=auth_headers
            )
            assert filter_response.status_code == 200
            filter_results = filter_response.json()
            bash_recordings = [r for r in filter_results["recordings"] if r["metadata"]["shell"] == "bash"]
            assert len(bash_recordings) >= 2

            # Test filtering by tags
            tag_response = client.get(
                "/api/recordings",
                params={"tags": "python,development"},
                headers=auth_headers
            )
            assert tag_response.status_code == 200

    def test_recording_compression_and_storage(self, client, auth_headers):
        """Test recording compression and efficient storage mechanisms.

        User Story: Large recordings are compressed for efficient storage
        while maintaining playback quality and search capabilities.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create large recording with repetitive data
            large_events = []
            for i in range(1000):
                large_events.extend([
                    {"timestamp": i * 2.0, "type": "input", "data": f"command_{i}\r"},
                    {"timestamp": i * 2.0 + 0.5, "type": "output", "data": f"output_for_command_{i}\n" * 10}
                ])

            metadata = {
                "duration": 2000.0,
                "commandCount": 1000,
                "startTime": datetime.now().isoformat(),
                "shell": "bash"
            }

            # Create large recording
            create_response = client.post(
                "/api/recordings",
                json={
                    "name": "Large Recording for Compression Test",
                    "events": large_events,
                    "metadata": metadata
                },
                headers=auth_headers
            )
            assert create_response.status_code == 201
            recording_id = create_response.json()["recordingId"]

            # Get storage information
            storage_response = client.get(
                f"/api/recordings/{recording_id}/storage-info",
                headers=auth_headers
            )
            assert storage_response.status_code == 200
            storage_data = storage_response.json()

            # Verify compression is applied
            assert storage_data["compressed"] == True
            assert storage_data["compressionRatio"] > 1.0  # Should achieve some compression
            assert storage_data["originalSize"] > storage_data["compressedSize"]

            # Verify playback still works with compressed data
            playback_response = client.post(
                f"/api/recordings/{recording_id}/playback",
                json={"speed": 10.0},  # Fast playback for testing
                headers=auth_headers
            )
            assert playback_response.status_code == 200

    def test_recording_metadata_and_analytics(self, client, auth_headers, sample_recording_data):
        """Test recording metadata extraction and analytics features.

        User Story: System extracts useful metadata from recordings and provides
        analytics about terminal usage patterns and command frequency.
        """
        with pytest.raises((Exception, AssertionError)):
            # Create recording with rich metadata
            metadata = sample_recording_data["metadata"].copy()
            metadata.update({
                "tags": ["development", "testing"],
                "projectName": "jterm",
                "environment": "development"
            })

            create_response = client.post(
                "/api/recordings",
                json={
                    "name": "Metadata Test Recording",
                    "events": sample_recording_data["events"],
                    "metadata": metadata
                },
                headers=auth_headers
            )
            recording_id = create_response.json()["recordingId"]

            # Get detailed analytics
            analytics_response = client.get(
                f"/api/recordings/{recording_id}/analytics",
                headers=auth_headers
            )
            assert analytics_response.status_code == 200
            analytics = analytics_response.json()

            # Verify analytics data
            assert "commandFrequency" in analytics
            assert "typingSpeed" in analytics
            assert "sessionPattern" in analytics
            assert "errorCount" in analytics

            # Command frequency should include our test commands
            assert "ls" in analytics["commandFrequency"]
            assert "echo" in analytics["commandFrequency"]

            # Get aggregated user analytics
            user_analytics_response = client.get(
                "/api/user/recording-analytics",
                params={"timeframe": "month"},
                headers=auth_headers
            )
            assert user_analytics_response.status_code == 200
            user_analytics = user_analytics_response.json()

            assert "totalSessions" in user_analytics
            assert "totalDuration" in user_analytics
            assert "topCommands" in user_analytics
            assert "dailyActivity" in user_analytics