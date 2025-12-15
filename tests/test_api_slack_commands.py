"""
Tests for Slack command API endpoints.
"""

import time
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def _build_slack_signature(timestamp: str, body: bytes, secret: str) -> str:
    """Build a valid Slack signature for testing."""
    sig_basestring = f"v0:{timestamp}:".encode("utf-8") + body
    computed = hmac.new(
        secret.encode("utf-8"),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    return f"v0={computed}"


def test_slack_commands_without_text(monkeypatch):
    """Test that /slack/commands returns usage message when text is empty."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    
    timestamp = str(int(time.time()))
    body = b"command=/insights&text=&user_name=test"
    signature = _build_slack_signature(timestamp, body, "test-secret")
    
    response = client.post(
        "/slack/commands",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "ephemeral"
    assert "Usage" in data.get("text", "") or "blocks" in data


def test_slack_commands_with_question(monkeypatch):
    """Test that /slack/commands processes a question correctly."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    
    # Mock insights engine
    mock_result = {
        "intent": "overdue",
        "answer": "Il y a 2 tâches en retard.",
        "evidence": {
            "overdue_count": 2,
            "overdue_todos": [
                {"id": 1, "task": "Task 1", "owner": "Alice", "due_date": "2025-01-01", "status": "pending"}
            ]
        },
        "recommended_actions": ["Contacter Alice"]
    }
    
    timestamp = str(int(time.time()))
    body = b"command=/insights&text=Quelles%20taches%20sont%20en%20retard%20%3F&user_name=test"
    signature = _build_slack_signature(timestamp, body, "test-secret")
    
    with patch("api.routes.slack.answer_insights_question", return_value=mock_result):
        response = client.post(
            "/slack/commands",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "ephemeral"
    assert "text" in data or "blocks" in data
    assert "Il y a 2 tâches" in data.get("text", "") or any(
        "Il y a 2 tâches" in str(block) for block in data.get("blocks", [])
    )


def test_slack_commands_with_llm_flag(monkeypatch):
    """Test that --llm flag is parsed correctly."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    
    mock_result = {
        "intent": "overdue",
        "answer": "Test answer",
        "evidence": {},
        "recommended_actions": []
    }
    
    timestamp = str(int(time.time()))
    body = b"command=/insights&text=test%20--llm&user_name=test"
    signature = _build_slack_signature(timestamp, body, "test-secret")
    
    with patch("api.routes.slack.answer_insights_question", return_value=mock_result) as mock_func:
        response = client.post(
            "/slack/commands",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature
            }
        )
    
    assert response.status_code == 200
    # Verify that answer_insights_question was called with use_llm=True
    assert mock_func.called
    call_kwargs = mock_func.call_args[1]
    assert call_kwargs.get("use_llm") is True
    assert call_kwargs.get("question") == "test"


def test_slack_commands_invalid_signature(monkeypatch):
    """Test that invalid signature returns 401."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    
    timestamp = str(int(time.time()))
    body = b"command=/insights&text=test&user_name=test"
    
    response = client.post(
        "/slack/commands",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": "v0=wrong_signature"
        }
    )
    
    assert response.status_code == 401
    assert "error" in response.json()


def test_slack_commands_no_secret_dev_mode(monkeypatch):
    """Test that commands work without secret in dev mode."""
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    
    mock_result = {
        "intent": "overdue",
        "answer": "Test answer",
        "evidence": {},
        "recommended_actions": []
    }
    
    body = b"command=/insights&text=test&user_name=test"
    
    with patch("api.routes.slack.answer_insights_question", return_value=mock_result):
        response = client.post(
            "/slack/commands",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Request-Timestamp": str(int(time.time())),
                "X-Slack-Signature": "v0=anything"
            }
        )
    
    assert response.status_code == 200


def test_slack_events_url_verification(monkeypatch):
    """Test that /slack/events handles URL verification."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    
    import json
    payload = {
        "type": "url_verification",
        "challenge": "test_challenge_123"
    }
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = _build_slack_signature(timestamp, body, "test-secret")
    
    response = client.post(
        "/slack/events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["challenge"] == "test_challenge_123"


def test_slack_events_other_event(monkeypatch):
    """Test that /slack/events handles other event types."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    
    import json
    payload = {
        "type": "event_callback",
        "event": {"type": "message"}
    }
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = _build_slack_signature(timestamp, body, "test-secret")
    
    response = client.post(
        "/slack/events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data.get("ok") is True

