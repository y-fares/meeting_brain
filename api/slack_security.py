"""
Slack signature verification utilities.
"""

import os
import hmac
import hashlib
import time
import logging
from typing import Mapping

LOGGER = logging.getLogger(__name__)


def get_slack_signing_secret() -> str | None:
    """
    Read SLACK_SIGNING_SECRET from environment.
    
    Returns:
        Signing secret string if set, None otherwise
    """
    secret = os.getenv("SLACK_SIGNING_SECRET")
    if secret and secret.strip():
        return secret.strip()
    return None


def verify_slack_signature(headers: Mapping[str, str], raw_body: bytes) -> bool:
    """
    Verify Slack request signature.
    
    Implements Slack's signature verification:
    - Check timestamp is within 5 minute window
    - Compute HMAC SHA256 of "v0:{timestamp}:{raw_body}"
    - Compare with X-Slack-Signature header
    
    Args:
        headers: Request headers dict
        raw_body: Raw request body bytes
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        signing_secret = get_slack_signing_secret()
        
        # If no secret configured, allow (dev mode) but log warning
        if signing_secret is None:
            LOGGER.warning(
                "SLACK_SIGNING_SECRET is not set. Slack signature verification disabled (dev mode)."
            )
            return True
        
        # Get required headers
        timestamp = headers.get("X-Slack-Request-Timestamp", "")
        signature = headers.get("X-Slack-Signature", "")
        
        if not timestamp or not signature:
            LOGGER.warning("Missing Slack signature headers")
            return False
        
        # Check timestamp (prevent replay attacks)
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            
            # Reject if timestamp is more than 5 minutes old
            if abs(current_time - request_time) > 300:
                LOGGER.warning("Slack request timestamp too old or too far in future")
                return False
        except ValueError:
            LOGGER.warning("Invalid Slack timestamp format")
            return False
        
        # Build base string
        sig_basestring = f"v0:{timestamp}:".encode("utf-8") + raw_body
        
        # Compute HMAC SHA256
        computed_signature = hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        # Build expected signature format: "v0={hexdigest}"
        expected_signature = f"v0={computed_signature}"
        
        # Compare using constant-time comparison
        if not hmac.compare_digest(expected_signature, signature):
            LOGGER.warning("Slack signature verification failed")
            return False
        
        return True
    
    except Exception as exc:
        LOGGER.exception("Error verifying Slack signature: %s", exc)
        return False

