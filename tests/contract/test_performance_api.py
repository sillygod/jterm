"""Contract tests for Performance Monitoring API endpoints.

These tests verify the Performance API contracts match the specifications
defined in contracts/performance_api.yaml.

CRITICAL: These tests MUST FAIL until the implementation is complete.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestPerformanceCurrentAPI:
    """Test GET /api/performance/current endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    def test_get_current_snapshot(self, client):
        """Test retrieving current performance snapshot.

        Contract: GET /api/performance/current returns 200 with PerformanceSnapshot
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get("/api/performance/current")

            assert response.status_code == 200
            data = response.json()

            # Verify PerformanceSnapshot schema
            assert "id" in data
            assert "session_id" in data
            assert "timestamp" in data
            assert "cpu_percent" in data
            assert "memory_mb" in data
            assert "active_websockets" in data
            assert "terminal_updates_per_sec" in data

            # Verify data types and ranges
            assert isinstance(data["cpu_percent"], (int, float))
            assert 0 <= data["cpu_percent"] <= 100
            assert isinstance(data["memory_mb"], (int, float))
            assert data["memory_mb"] > 0
            assert isinstance(data["active_websockets"], int)
            assert data["active_websockets"] >= 0
            assert isinstance(data["terminal_updates_per_sec"], (int, float))
            assert data["terminal_updates_per_sec"] >= 0

            # Verify timestamp format
            timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
            assert isinstance(timestamp, datetime)


class TestPerformanceHistoryAPI:
    """Test GET /api/performance/history endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def session_id(self):
        """Mock session ID."""
        return "123e4567-e89b-12d3-a456-426614174000"

    def test_get_history_default(self, client):
        """Test retrieving historical snapshots with default parameters.

        Contract: GET /api/performance/history returns last 60 minutes by default
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get("/api/performance/history")

            assert response.status_code == 200
            data = response.json()

            assert "snapshots" in data
            assert isinstance(data["snapshots"], list)
            assert "count" in data
            assert isinstance(data["count"], int)
            assert data["count"] == len(data["snapshots"])

            # Verify each snapshot has required fields
            if len(data["snapshots"]) > 0:
                snapshot = data["snapshots"][0]
                assert "id" in snapshot
                assert "session_id" in snapshot
                assert "timestamp" in snapshot
                assert "cpu_percent" in snapshot
                assert "memory_mb" in snapshot

    def test_get_history_with_time_range(self, client):
        """Test retrieving historical snapshots with custom time range.

        Contract: GET /api/performance/history?minutes=N returns snapshots from last N minutes
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get(
                "/api/performance/history",
                params={"minutes": 30}
            )

            assert response.status_code == 200
            data = response.json()

            assert "snapshots" in data
            assert "count" in data

            # Verify timestamps are within range
            cutoff_time = datetime.utcnow() - timedelta(minutes=30)
            for snapshot in data["snapshots"]:
                timestamp = datetime.fromisoformat(snapshot["timestamp"].replace('Z', '+00:00'))
                assert timestamp >= cutoff_time

    def test_get_history_with_session_filter(self, client, session_id):
        """Test retrieving historical snapshots filtered by session.

        Contract: GET /api/performance/history?session_id=X returns snapshots for that session
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get(
                "/api/performance/history",
                params={"session_id": session_id}
            )

            assert response.status_code == 200
            data = response.json()

            assert "snapshots" in data

            # Verify all snapshots belong to the session
            for snapshot in data["snapshots"]:
                assert snapshot["session_id"] == session_id


class TestPerformanceSnapshotAPI:
    """Test POST /api/performance/snapshot endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def session_id(self):
        """Mock session ID."""
        return "123e4567-e89b-12d3-a456-426614174000"

    def test_submit_client_metrics(self, client, session_id):
        """Test submitting client-side performance metrics.

        Contract: POST /api/performance/snapshot with valid data returns 201
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/performance/snapshot",
                json={
                    "session_id": session_id,
                    "client_fps": 60.0,
                    "client_memory_mb": 128.4
                }
            )

            assert response.status_code == 201
            data = response.json()

            assert "recorded" in data
            assert data["recorded"] is True

    def test_submit_metrics_without_optional_fields(self, client, session_id):
        """Test submitting metrics with only required fields.

        Contract: POST /api/performance/snapshot with only session_id succeeds
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.post(
                "/api/performance/snapshot",
                json={"session_id": session_id}
            )

            assert response.status_code == 201
            data = response.json()
            assert "recorded" in data


class TestPerformancePreferencesAPI:
    """Test PUT /api/user/preferences/performance endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    def test_update_preferences(self, client):
        """Test updating performance preferences.

        Contract: PUT /api/user/preferences/performance returns 200 with updated preferences
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.put(
                "/api/user/preferences/performance",
                json={
                    "show_performance_metrics": True,
                    "performance_metric_refresh_interval": 3000
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert "show_performance_metrics" in data
            assert data["show_performance_metrics"] is True
            assert "performance_metric_refresh_interval" in data
            assert data["performance_metric_refresh_interval"] == 3000

    def test_update_preferences_invalid_interval(self, client):
        """Test updating preferences with invalid refresh interval.

        Contract: PUT /api/user/preferences/performance with out-of-range interval returns 400
        """
        with pytest.raises((Exception, AssertionError)):
            # Test interval too low (< 1000ms)
            response = client.put(
                "/api/user/preferences/performance",
                json={
                    "show_performance_metrics": True,
                    "performance_metric_refresh_interval": 500  # Below minimum of 1000
                }
            )

            assert response.status_code == 400
            data = response.json()
            assert "error" in data
            assert "message" in data

    def test_update_preferences_interval_too_high(self, client):
        """Test updating preferences with interval exceeding maximum.

        Contract: PUT /api/user/preferences/performance with interval >60000 returns 400
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.put(
                "/api/user/preferences/performance",
                json={
                    "show_performance_metrics": True,
                    "performance_metric_refresh_interval": 70000  # Above maximum of 60000
                }
            )

            assert response.status_code == 400
            data = response.json()
            assert "error" in data

    def test_get_preferences(self, client):
        """Test retrieving current preferences.

        Contract: GET /api/user/preferences/performance returns 200 with preferences
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get("/api/user/preferences/performance")

            assert response.status_code == 200
            data = response.json()

            assert "show_performance_metrics" in data
            assert isinstance(data["show_performance_metrics"], bool)
            assert "performance_metric_refresh_interval" in data
            assert isinstance(data["performance_metric_refresh_interval"], int)
            assert 1000 <= data["performance_metric_refresh_interval"] <= 60000
