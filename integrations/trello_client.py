"""
Trello client for creating cards from TODOs.
"""

import logging
import os
from typing import Optional

import requests

from database import Todo, Meeting

# Module-level logger
LOGGER = logging.getLogger(__name__)

# Global configuration - read from environment variables
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_API_TOKEN = os.getenv("TRELLO_API_TOKEN")
TRELLO_LIST_ID = os.getenv("TRELLO_LIST_ID")


def _check_trello_config() -> bool:
    """
    Check that Trello configuration is present.
    Logs an error if any of the required env variables is missing.
    Returns True if config is OK, False otherwise.
    """
    missing = []
    
    if not TRELLO_API_KEY:
        missing.append("TRELLO_API_KEY")
    if not TRELLO_API_TOKEN:
        missing.append("TRELLO_API_TOKEN")
    if not TRELLO_LIST_ID:
        missing.append("TRELLO_LIST_ID")
    
    if missing:
        LOGGER.error("Missing Trello configuration: %s", ", ".join(missing))
        return False
    
    return True


def create_card_for_todo(todo: Todo, meeting: Meeting) -> Optional[str]:
    """
    Create a Trello card from a TODO and its associated meeting.
    
    - Uses Trello REST API endpoint: POST https://api.trello.com/1/cards
    - Uses query parameters:
        key, token, idList, name, desc, (optional) due
    - The card name should be the TODO task truncated to 100 chars.
    - The description should include:
        - Task
        - Owner (or 'Unassigned')
        - Meeting ID
        - Meeting date (if set)
    - If todo.due_date is non-empty, pass it as 'due'.
    
    Returns:
        - The created Trello card id (string) on success
        - None on failure
    """
    # Check configuration first
    if not _check_trello_config():
        return None
    
    # Prepare card name (truncate to 100 chars)
    card_name = todo.task[:100] if todo.task else "Untitled Task"
    
    # Build description
    desc_parts = [
        f"Task: {todo.task}",
        f"Owner: {todo.owner or 'Unassigned'}",
        f"Meeting ID: {meeting.id}",
    ]
    
    if meeting.date:
        desc_parts.append(f"Meeting date: {meeting.date}")
    
    card_desc = "\n".join(desc_parts)
    
    # Prepare query parameters
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN,
        "idList": TRELLO_LIST_ID,
        "name": card_name,
        "desc": card_desc,
    }
    
    # Add due date if present
    if todo.due_date and todo.due_date.strip():
        params["due"] = todo.due_date.strip()
    
    # Make API request
    try:
        response = requests.post(
            "https://api.trello.com/1/cards",
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            LOGGER.error(
                "Failed to create Trello card. Status: %d, Response: %s",
                response.status_code,
                response.text
            )
            return None
        
        # Parse response JSON
        try:
            card_data = response.json()
            card_id = card_data.get("id")
            
            if not card_id:
                LOGGER.error("Trello API response missing 'id' field. Response: %s", response.text)
                return None
            
            LOGGER.info("Created Trello card %s for TODO %d", card_id, todo.id)
            return card_id
            
        except ValueError as json_err:
            LOGGER.error("Failed to parse Trello API response as JSON: %s", json_err)
            LOGGER.error("Response text: %s", response.text)
            return None
            
    except requests.exceptions.RequestException as req_err:
        LOGGER.exception("Request error while creating Trello card: %s", req_err)
        return None
    except Exception as exc:
        LOGGER.exception("Unexpected error while creating Trello card: %s", exc)
        return None

