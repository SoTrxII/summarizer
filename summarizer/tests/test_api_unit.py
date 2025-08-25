"""
Unit tests for the Summarizer API.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from summarizer.api import app, wf_client


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "message" in data


def test_audio_workflow_validation(client):
    """Test audio workflow input validation."""
    # Valid input
    valid_input = {
        "campaign_id": 1,
        "episode_id": 5,
        "audio_file_path": "test.ogg"
    }

    with patch.object(wf_client, 'schedule_new_workflow') as mock_start:
        mock_start.return_value = "test-123"

        response = client.post("/workflows/audio", json=valid_input)
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert "message" in data


def test_audio_workflow_invalid_input(client):
    """Test audio workflow with invalid input."""
    # Missing required fields
    invalid_input = {
        "campaign_id": 1,
        # Missing episode_id and audio_file_path
    }

    response = client.post("/workflows/audio", json=invalid_input)
    assert response.status_code == 422  # Validation error


def test_transcript_workflow_validation(client):
    """Test transcript workflow input validation."""
    valid_input = {
        "campaign_id": 1,
        "episode_id": 5,
        "transcript_storage_key": "test/1/transcript.json"
    }

    with patch.object(wf_client, 'schedule_new_workflow') as mock_start:
        mock_start.return_value = "test-transcript-123"

        response = client.post("/workflows/transcript", json=valid_input)
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data


def test_transcript_workflow_invalid_input(client):
    """Test transcript workflow with invalid input."""
    # Missing required fields
    invalid_input = {
        "campaign_id": 1,
        # Missing episode_id and transcript_storage_key
    }

    response = client.post("/workflows/transcript", json=invalid_input)
    assert response.status_code == 422  # Validation error
