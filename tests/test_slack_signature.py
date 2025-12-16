"""
Tests for Slack signature verification.
"""

import time
import hmac
import hashlib
import pytest

from api.slack_security import verify_slack_signature, get_slack_signing_secret


def test_get_slack_signing_secret_not_set(monkeypatch):
    """Test that get_slack_signing_secret returns None when not set."""
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    assert get_slack_signing_secret() is None


def test_get_slack_signing_secret_set(monkeypatch):
    """Test that get_slack_signing_secret returns value when set."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret-123")
    assert get_slack_signing_secret() == "test-secret-123"


def test_verify_slack_signature_valid(monkeypatch):
    """Test that valid Slack signature is verified correctly."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret-123")
    
    timestamp = str(int(time.time()))
    raw_body = b"token=test&text=hello"
    
    # Build base string
    sig_basestring = f"v0:{timestamp}:".encode("utf-8") + raw_body
    
    # Compute signature
    computed_signature = hmac.new(
        "test-secret-123".encode("utf-8"),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    
    signature = f"v0={computed_signature}"
    
    headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature
    }
    
    assert verify_slack_signature(headers, raw_body) is True


def test_verify_slack_signature_invalid(monkeypatch):
    """Test that invalid signature is rejected."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret-123")
    
    timestamp = str(int(time.time()))
    raw_body = b"token=test&text=hello"
    
    headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": "v0=wrong_signature"
    }
    
    assert verify_slack_signature(headers, raw_body) is False


def test_verify_slack_signature_old_timestamp(monkeypatch):
    """Test that old timestamp is rejected."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret-123")
    
    # Timestamp 10 minutes ago
    old_timestamp = str(int(time.time()) - 600)
    raw_body = b"token=test&text=hello"
    
    # Build valid signature for old timestamp
    sig_basestring = f"v0:{old_timestamp}:".encode("utf-8") + raw_body
    computed_signature = hmac.new(
        "test-secret-123".encode("utf-8"),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    signature = f"v0={computed_signature}"
    
    headers = {
        "X-Slack-Request-Timestamp": old_timestamp,
        "X-Slack-Signature": signature
    }
    
    assert verify_slack_signature(headers, raw_body) is False


def test_verify_slack_signature_missing_headers(monkeypatch):
    """Test that missing headers are rejected."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret-123")
    
    raw_body = b"token=test&text=hello"
    
    # Missing timestamp
    headers = {
        "X-Slack-Signature": "v0=test"
    }
    assert verify_slack_signature(headers, raw_body) is False
    
    # Missing signature
    headers = {
        "X-Slack-Request-Timestamp": str(int(time.time()))
    }
    assert verify_slack_signature(headers, raw_body) is False


def test_verify_slack_signature_no_secret_allowed(monkeypatch):
    """Test that requests are allowed when SLACK_SIGNING_SECRET is not set (dev mode)."""
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
    
    raw_body = b"token=test&text=hello"
    headers = {
        "X-Slack-Request-Timestamp": str(int(time.time())),
        "X-Slack-Signature": "v0=anything"
    }
    
    # Should allow in dev mode
    assert verify_slack_signature(headers, raw_body) is True

