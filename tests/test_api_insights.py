"""
Tests for insights API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def test_insights_answer_without_auth_when_token_set(client, monkeypatch):
    """Test that /insights/answer requires auth when token is set."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    # Mock insights engine
    mock_result = {
        "intent": "overdue",
        "answer": "Test answer",
        "evidence": {},
        "recommended_actions": []
    }
    
    with patch("api.routes.insights.answer_insights_question", return_value=mock_result):
        response = client.get("/insights/answer?q=test")
        assert response.status_code == 401


def test_insights_answer_with_correct_token(client, monkeypatch):
    """Test that /insights/answer works with correct token."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    # Mock insights engine
    mock_result = {
        "intent": "overdue",
        "answer": "Test answer",
        "evidence": {"overdue_count": 0},
        "recommended_actions": []
    }
    
    with patch("api.routes.insights.answer_insights_question", return_value=mock_result):
        response = client.get(
            "/insights/answer?q=test",
            headers={"Authorization": "Bearer test-token-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "overdue"
        assert "answer" in data


def test_insights_answer_without_auth_when_token_not_set(client, monkeypatch):
    """Test that /insights/answer is accessible without auth when token is not set."""
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    
    # Mock insights engine
    mock_result = {
        "intent": "overdue",
        "answer": "Test answer",
        "evidence": {},
        "recommended_actions": []
    }
    
    with patch("api.routes.insights.answer_insights_question", return_value=mock_result):
        response = client.get("/insights/answer?q=test")
        assert response.status_code == 200


def test_insights_owner_load_without_auth_when_token_set(client, monkeypatch):
    """Test that /insights/owner_load requires auth when token is set."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    with patch("api.routes.insights.get_owner_load", return_value=[]):
        response = client.get("/insights/owner_load")
        assert response.status_code == 401


def test_insights_owner_load_with_correct_token(client, monkeypatch):
    """Test that /insights/owner_load works with correct token."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    mock_load = [
        {"owner": "Alice", "pending": 2, "in_progress": 1, "completed": 0, "overdue": 1, "total": 3}
    ]
    
    with patch("api.routes.insights.get_owner_load", return_value=mock_load):
        response = client.get(
            "/insights/owner_load",
            headers={"Authorization": "Bearer test-token-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1


def test_insights_bottlenecks_without_auth_when_token_set(client, monkeypatch):
    """Test that /insights/bottlenecks requires auth when token is set."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    with patch("api.routes.insights.get_bottlenecks", return_value={
        "top_overdue_owners": [],
        "most_loaded_owners": [],
        "stale_tasks": []
    }):
        response = client.get("/insights/bottlenecks")
        assert response.status_code == 401


def test_insights_bottlenecks_with_correct_token(client, monkeypatch):
    """Test that /insights/bottlenecks works with correct token."""
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token-123")
    
    mock_bottlenecks = {
        "top_overdue_owners": [{"owner": "Alice", "overdue_count": 2}],
        "most_loaded_owners": [{"owner": "Bob", "open_count": 5}],
        "stale_tasks": []
    }
    
    with patch("api.routes.insights.get_bottlenecks", return_value=mock_bottlenecks):
        response = client.get(
            "/insights/bottlenecks",
            headers={"Authorization": "Bearer test-token-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "top_overdue_owners" in data
        assert "most_loaded_owners" in data
        assert "stale_tasks" in data

