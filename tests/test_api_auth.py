"""
Tests for API authentication.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def test_health_is_public(client, monkeypatch):
    """Test that /health endpoint is accessible without authentication."""
    # Ensure no auth token is set
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_meetings_without_auth_when_token_set(client, monkeypatch):
    """Test that /meetings returns 401 when API_AUTH_TOKEN is set but no auth header."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    # Mock repository to avoid DB dependency - patch where it's used
    with patch("api.routes.meetings.list_meetings", return_value=[]):
        response = client.get("/meetings")
        assert response.status_code == 401
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "http_error"


def test_meetings_with_wrong_token(client, monkeypatch):
    """Test that /meetings returns 401 with wrong token."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    # Mock repository to avoid DB dependency - patch where it's used
    with patch("api.routes.meetings.list_meetings", return_value=[]):
        response = client.get(
            "/meetings",
            headers={"Authorization": "Bearer wrong-token"}
        )
        assert response.status_code == 401
        assert "error" in response.json()


def test_meetings_with_correct_token(client, monkeypatch):
    """Test that /meetings returns 200 with correct token."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    # Mock repository to return empty list - patch where it's used
    with patch("api.routes.meetings.list_meetings", return_value=[]):
        response = client.get(
            "/meetings",
            headers={"Authorization": "Bearer test-token-123"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_meetings_without_auth_when_token_not_set(client, monkeypatch):
    """Test that /meetings is accessible without auth when API_AUTH_TOKEN is not set."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    
    # Mock repository to return empty list - patch where it's used
    with patch("api.routes.meetings.list_meetings", return_value=[]):
        response = client.get("/meetings")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_todos_without_auth_when_token_set(client, monkeypatch):
    """Test that /todos requires auth when token is set."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    with patch("api.routes.todos.list_todos", return_value=[]):
        response = client.get("/todos")
        assert response.status_code == 401


def test_todos_with_correct_token(client, monkeypatch):
    """Test that /todos works with correct token."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    with patch("api.routes.todos.list_todos", return_value=[]):
        response = client.get(
            "/todos",
            headers={"Authorization": "Bearer test-token-123"}
        )
        assert response.status_code == 200


def test_decisions_without_auth_when_token_set(client, monkeypatch):
    """Test that /decisions requires auth when token is set."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    with patch("api.routes.decisions.list_decisions", return_value=[]):
        response = client.get("/decisions")
        assert response.status_code == 401


def test_analytics_without_auth_when_token_set(client, monkeypatch):
    """Test that /analytics/kpis requires auth when token is set."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    with patch("api.routes.analytics.compute_kpis", return_value={
        "total_meetings": 0,
        "total_todos": 0,
        "completed_todos": 0,
        "pending_todos": 0,
        "in_progress_todos": 0,
        "completion_rate": 0.0,
        "total_decisions": 0
    }):
        response = client.get("/analytics/kpis")
        assert response.status_code == 401


def test_exports_without_auth_when_token_set(client, monkeypatch):
    """Test that CSV export endpoints require auth when token is set."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    import pandas as pd
    
    # Mock repository to return empty DataFrame - patch where it's used
    empty_df = pd.DataFrame()
    with patch("api.routes.exports.export_meetings_df", return_value=empty_df):
        response = client.get("/exports/meetings.csv")
        assert response.status_code == 401

