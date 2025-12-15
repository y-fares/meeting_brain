"""
Tests for API error handling.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def test_internal_error_returns_json_envelope(client, monkeypatch):
    """Test that internal errors return standardized JSON error envelope."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    
    # Force repository to raise an exception - patch where it's used
    with patch("api.routes.meetings.list_meetings", side_effect=Exception("boom")):
        response = client.get("/meetings")
        assert response.status_code == 500
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "internal_error"
        assert response.json()["error"]["message"] == "Unexpected error"


def test_validation_error_returns_json_envelope(client, monkeypatch):
    """Test that validation errors return standardized JSON error envelope."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    
    # Invalid query parameter (limit must be >= 1)
    # No need to patch - validation happens before the route handler
    response = client.get("/meetings?limit=0")
    assert response.status_code == 422
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "validation_error"


def test_csv_export_error_returns_json(client, monkeypatch):
    """Test that CSV export errors return JSON envelope (not CSV)."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    
    # Force repository to raise an exception - patch where it's used
    import pandas as pd
    with patch("api.routes.exports.export_meetings_df", side_effect=Exception("boom")):
        response = client.get("/exports/meetings.csv")
        assert response.status_code == 500
        # Should return JSON, not CSV
        assert response.headers["content-type"] == "application/json"
        assert "error" in response.json()


def test_csv_export_success_returns_csv(client, monkeypatch):
    """Test that successful CSV exports return CSV content."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    
    import pandas as pd
    
    # Mock repository to return DataFrame with columns - patch where it's used
    df = pd.DataFrame({"id": [1], "title": ["Test"]})
    with patch("api.routes.exports.export_meetings_df", return_value=df):
        response = client.get("/exports/meetings.csv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        # Check that CSV headers are present
        assert "id" in response.text
        assert "title" in response.text


def test_http_exception_returns_json_envelope(client, monkeypatch):
    """Test that HTTPException returns standardized JSON envelope."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    # Missing auth header should return 401 with JSON envelope
    # No need to patch - auth check happens before route handler
    response = client.get("/meetings")
    assert response.status_code == 401
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "http_error"
    assert response.json()["error"]["message"] == "Unauthorized"

