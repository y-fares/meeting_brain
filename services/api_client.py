"""
HTTP client helpers for Streamlit views that consume the FastAPI backend.
"""

import os
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_API_BASE_URL = "http://localhost:8000"


class ApiClientError(Exception):
    """Raised when the API returns an error or cannot be reached."""


def get_api_base_url() -> str:
    """Read the FastAPI base URL for Streamlit-to-API calls."""
    url = os.getenv("MEETING_BRAIN_API_URL", DEFAULT_API_BASE_URL)
    if url.lower() == "disabled":
        return ""
    return url.rstrip("/")


def get_default_api_token() -> Optional[str]:
    """Read a default bearer token from env for local/service-token mode."""
    token = os.getenv("MEETING_BRAIN_API_TOKEN") or os.getenv("API_AUTH_TOKEN")
    if token and token.strip():
        return token.strip()
    return None


class MeetingBrainApiClient:
    """Small requests-based client for the Meeting Brain API."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or get_api_base_url()).rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
        try:
            response = requests.request(method, url, headers=headers, timeout=15, **kwargs)
        except requests.RequestException as exc:
            raise ApiClientError(f"API unavailable at {self.base_url}: {exc}") from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
                detail = payload.get("error", {}).get("message") or payload.get("detail")
            except ValueError:
                detail = response.text
            raise ApiClientError(detail or f"API request failed with status {response.status_code}")

        if not response.content:
            return None
        return response.json()

    def login(self, email: str, password: str) -> str:
        payload = self._request("POST", "/auth/login", json={"email": email, "password": password})
        return payload["access_token"]

    def get_current_user(self) -> dict[str, Any]:
        return self._request("GET", "/auth/me")

    def list_todos(self) -> list[dict[str, Any]]:
        return self._request("GET", "/todos")

    def update_todo_status(self, todo_id: int, status: str, note: str = "") -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/todos/{todo_id}/status",
            json={"status": status, "note": note},
        )

    def assign_todo(self, todo_id: int, assigned_user_id: Optional[int]) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/todos/{todo_id}/assignee",
            json={"assigned_user_id": assigned_user_id},
        )
