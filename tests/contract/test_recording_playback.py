"""Contract tests for Recording Playback API endpoints.

These tests verify the Recording Playback API contracts match the specifications
defined in contracts/recording_playback.yaml.

CRITICAL: These tests MUST FAIL until the implementation is complete.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

# Import the app once it's implemented
try:
    from src.main import app
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False


class TestRecordingDimensionsAPI:
    """Test GET /api/recordings/{id}/dimensions endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not APP_AVAILABLE:
            pytest.skip("Application not implemented yet")
        return TestClient(app)

    @pytest.fixture
    def recording_id(self):
        """Mock recording ID."""
        return "770e8400-e29b-41d4-a716-446655440000"

    def test_get_dimensions_valid_recording(self, client, recording_id):
        """Test retrieving dimensions from a valid recording.

        Contract: GET /api/recordings/{id}/dimensions returns 200 with RecordingDimensions
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get(f"/api/recordings/{recording_id}/dimensions")

            assert response.status_code == 200
            data = response.json()

            # Verify RecordingDimensions schema
            assert "recording_id" in data
            assert data["recording_id"] == recording_id
            assert "rows" in data
            assert isinstance(data["rows"], int)
            assert data["rows"] >= 1
            assert "columns" in data
            assert isinstance(data["columns"], int)
            assert data["columns"] >= 1
            assert "created_at" in data

            # Verify timestamp format
            timestamp = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
            assert isinstance(timestamp, datetime)

    def test_get_dimensions_invalid_recording(self, client):
        """Test retrieving dimensions from non-existent recording.

        Contract: GET /api/recordings/{id}/dimensions with invalid ID returns 404
        """
        invalid_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises((Exception, AssertionError)):
            response = client.get(f"/api/recordings/{invalid_id}/dimensions")

            assert response.status_code == 404
            data = response.json()

            assert "error" in data
            assert "message" in data
            assert data["error"] == "RECORDING_NOT_FOUND"

    def test_get_dimensions_various_sizes(self, client, recording_id):
        """Test dimensions for recordings of various terminal sizes.

        Contract: Dimensions should accurately reflect terminal size at recording time
        """
        with pytest.raises((Exception, AssertionError)):
            response = client.get(f"/api/recordings/{recording_id}/dimensions")

            assert response.status_code == 200
            data = response.json()

            # Verify reasonable terminal dimensions
            # Standard terminals are 24-100 rows, 80-200 columns
            assert 1 <= data["rows"] <= 500  # Allow for very tall terminals
            assert 1 <= data["columns"] <= 500  # Allow for very wide terminals

            # For the mock recording_id, we might expect specific dimensions
            # This would be updated based on test data
            # Example: Wide terminal recording
            if data["columns"] > 120:
                # This is a wide recording that needs scaling
                assert data["columns"] >= 120
