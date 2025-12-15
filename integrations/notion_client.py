"""
Notion client for creating pages from TODOs.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

import requests
from dotenv import load_dotenv
from notion_client import Client
from sqlalchemy.orm import Session

from database import Todo, Meeting, update_todo_status

LOGGER = logging.getLogger(__name__)

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY:
    LOGGER.error("NOTION_API_KEY environment variable is not set")
if not NOTION_DATABASE_ID:
    LOGGER.error("NOTION_DATABASE_ID environment variable is not set")

# Initialize Notion client with API version 2025-09-03 for multi-source database support
notion = Client(
    auth=NOTION_API_KEY,
    notion_version="2025-09-03"
) if NOTION_API_KEY else None

# Cache for data_source_id to avoid repeated lookups
_data_source_id_cache: Optional[str] = None


def _check_notion_config() -> bool:
    """
    Check that Notion configuration is present and the client is initialized.
    Logs an error if any required configuration is missing.
    Returns True if config is OK, False otherwise.
    """
    if not NOTION_API_KEY:
        LOGGER.error("NOTION_API_KEY is missing")
        return False
    
    if not NOTION_DATABASE_ID:
        LOGGER.error("NOTION_DATABASE_ID is missing")
        return False
    
    if notion is None:
        LOGGER.error("Notion client is not initialized")
        return False
    
    return True


def _get_data_source_id() -> Optional[str]:
    """
    Get the data source ID from the database.
    Uses cache to avoid repeated API calls.
    
    Returns:
        The data source ID, or None if not found
    """
    global _data_source_id_cache
    
    if _data_source_id_cache:
        return _data_source_id_cache
    
    try:
        # Get database info with data sources list
        database_info = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        
        if isinstance(database_info, dict) and "data_sources" in database_info:
            data_sources = database_info.get("data_sources", [])
            if data_sources:
                # Use the first data source
                first_source = data_sources[0]
                if isinstance(first_source, dict):
                    source_id = first_source.get("id")
                    if source_id:
                        _data_source_id_cache = source_id
                        LOGGER.info("Found data source ID: %s", source_id)
                        return source_id
        
        LOGGER.warning("No data sources found in database")
        return None
    except Exception as exc:
        LOGGER.error("Error retrieving data source ID: %s", exc)
        return None


def resolve_properties_mapping(notion_database_schema: Dict[str, Any]) -> Dict[str, str]:
    """
    Inspect the database properties and map logical fields to actual Notion property names.
    
    Accepts multiple naming variations (case-insensitive) for each field.
    If a property does not exist in Notion, it is skipped and a warning is logged.
    
    Args:
        notion_database_schema: The schema dictionary from notion.databases.retrieve()
    
    Returns:
        Dictionary mapping logical field names to actual Notion property names
    """
    mapping: Dict[str, str] = {}
    
    properties = notion_database_schema.get("properties", {})
    if not properties:
        LOGGER.warning("No properties found in Notion database schema")
        return mapping
    
    property_names_lower = {name.lower(): name for name in properties.keys()}
    
    properties_by_type: Dict[str, list] = {}
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type")
        if prop_type not in properties_by_type:
            properties_by_type[prop_type] = []
        properties_by_type[prop_type].append(prop_name)
    
    field_definitions = {
        "task": {
            "type": "title",
            "alternatives": ["Task", "Tâche", "Name", "Title", "Titre", "Nom"]
        },
        "owner": {
            "type": "people",  # Changed from rich_text to people
            "alternatives": ["Owner", "Propriétaire", "Assigned", "Assignee", "Responsible", "Assignation", "Owners"],
            "fallback_types": ["rich_text"]  # Accept rich_text as fallback
        },
        "due_date": {
            "type": "date",
            "alternatives": ["Due date", "Due Date", "Deadline", "Due", "Date", "Échéance", "Date d'échéance"]
        },
        "status": {
            "type": "select",  # Also try status type
            "alternatives": ["Status", "Statut", "État", "State"],  # Status first, Priority as fallback
            "fallback_names": ["Priority"],  # Try Priority if Status not found
            "fallback_types": ["status"]  # Also accept status type
        },
        "meeting_id": {
            "type": "number",
            "alternatives": ["Meeting ID", "Nº Meeting ID", "N° Meeting ID", "Meeting", "ID Meeting", "MeetingId", "Meeting Number", "Identifiant", "ID"],
            "fallback_types": ["unique_id"]  # Accept unique_id as fallback (like "Nº Meeting ID")
        },
        "created_at": {
            "type": "created_time",  # Changed from date to created_time
            "alternatives": ["Created at", "Created", "Créé le", "Creation Date", "Date Created", "Date de création", "Created time", "Creation Date", "Creation"]
        }
    }
    
    used_properties = set()
    
    for logical_key, field_info in field_definitions.items():
        expected_type = field_info["type"]
        alternatives = field_info["alternatives"]
        fallback_types = field_info.get("fallback_types", [])
        fallback_names = field_info.get("fallback_names", [])
        
        found_property = None
        
        # First, try exact match with expected type
        for alt_name in alternatives:
            if alt_name in properties:
                prop_info = properties[alt_name]
                prop_type = prop_info.get("type")
                if prop_type == expected_type:
                    found_property = alt_name
                    break
        
        # If not found, try case-insensitive match with expected type
        if not found_property:
            for alt_name in alternatives:
                alt_lower = alt_name.lower()
                if alt_lower in property_names_lower:
                    actual_name = property_names_lower[alt_lower]
                    if actual_name not in used_properties:
                        prop_info = properties[actual_name]
                        prop_type = prop_info.get("type")
                        if prop_type == expected_type:
                            found_property = actual_name
                            break
        
        # Try with fallback types (e.g., people for owner, unique_id for meeting_id)
        if not found_property:
            all_types_to_try = [expected_type] + fallback_types
            for try_type in all_types_to_try:
                for alt_name in alternatives:
                    if alt_name in properties:
                        prop_info = properties[alt_name]
                        if prop_info.get("type") == try_type:
                            found_property = alt_name
                            LOGGER.info("Using '%s' (type: %s) for field '%s' (expected: %s)", alt_name, try_type, logical_key, expected_type)
                            break
                    if found_property:
                        break
                if found_property:
                    break
        
        # Try case-insensitive with fallback types
        if not found_property:
            all_types_to_try = [expected_type] + fallback_types
            for try_type in all_types_to_try:
                for alt_name in alternatives:
                    alt_lower = alt_name.lower()
                    if alt_lower in property_names_lower:
                        actual_name = property_names_lower[alt_lower]
                        if actual_name not in used_properties:
                            prop_info = properties[actual_name]
                            if prop_info.get("type") == try_type:
                                found_property = actual_name
                                LOGGER.info("Using '%s' (type: %s) for field '%s' (expected: %s)", actual_name, try_type, logical_key, expected_type)
                                break
                    if found_property:
                        break
                if found_property:
                    break
        
        # Try fallback names (e.g., Priority for status)
        if not found_property and fallback_names:
            for fallback_name in fallback_names:
                if fallback_name in properties:
                    prop_info = properties[fallback_name]
                    prop_type = prop_info.get("type")
                    if prop_type == expected_type or prop_type in fallback_types:
                        found_property = fallback_name
                        LOGGER.info("Using fallback name '%s' (type: %s) for field '%s'", fallback_name, prop_type, logical_key)
                        break
        
        # Last resort: try any property of the expected type
        if not found_property and expected_type in properties_by_type:
            for prop_name in properties_by_type[expected_type]:
                if prop_name not in used_properties:
                    found_property = prop_name
                    LOGGER.info("Using '%s' for field '%s' (type match)", prop_name, logical_key)
                    break
        
        # Try fallback types as last resort
        if not found_property:
            for fallback_type in fallback_types:
                if fallback_type in properties_by_type:
                    for prop_name in properties_by_type[fallback_type]:
                        if prop_name not in used_properties:
                            found_property = prop_name
                            LOGGER.info("Using '%s' (type: %s) for field '%s' (fallback type)", prop_name, fallback_type, logical_key)
                            break
                    if found_property:
                        break
        
        if found_property:
            mapping[logical_key] = found_property
            used_properties.add(found_property)
        else:
            all_alternatives = alternatives + fallback_names
            all_types = [expected_type] + fallback_types
            LOGGER.warning(
                "Skipping field '%s': no matching property found (tried: %s, types: %s)",
                logical_key,
                ", ".join(all_alternatives),
                ", ".join(all_types)
            )
    
    return mapping


def get_database_schema() -> Optional[dict]:
    """
    Retrieve and return the Notion database schema (databases.retrieve).
    - If NOTION_DATABASE_ID or client is missing, log and return None.
    - On success, return the full dict returned by notion.databases.retrieve(...).
    - On error, log via LOGGER.exception and return None.
    - If properties are missing, try to get schema from data source.
    """
    if not _check_notion_config():
        return None
    
    try:
        database_schema = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        
        # If properties are missing, try to get from data source (like push_todo_to_notion does)
        if not isinstance(database_schema, dict) or not database_schema.get("properties"):
            LOGGER.info("No properties in database schema, trying data source approach")
            data_source_id = _get_data_source_id()
            if data_source_id:
                try:
                    headers = {
                        "Authorization": f"Bearer {NOTION_API_KEY}",
                        "Notion-Version": "2025-09-03",
                        "Content-Type": "application/json"
                    }
                    api_url = f"https://api.notion.com/v1/data_sources/{data_source_id}"
                    response = requests.get(api_url, headers=headers)
                    response.raise_for_status()
                    database_schema = response.json()
                    LOGGER.info("Successfully retrieved data source schema via HTTP")
                except Exception as ds_err:
                    LOGGER.warning("Could not retrieve data source schema: %s", ds_err)
        
        return database_schema
    except Exception as exc:
        LOGGER.exception("Error retrieving database schema: %s", exc)
        return None


def detect_kanban_property(database_schema: dict) -> Optional[str]:
    """
    Detect which property in the Notion database is used as Kanban column.
    - Prefer properties of type 'status' or 'select'.
    - Try to match names (case-insensitive) among:
          ["Status", "Statut", "État", "Phase", "Stage"]
    - If no preferred name matches, fallback to the first 'status' or 'select' property.
    - Return the property name (string) or None if not found.
    - Do not raise; log a warning if none is found.
    """
    if not database_schema or not isinstance(database_schema, dict):
        LOGGER.warning("Invalid database schema provided to detect_kanban_property")
        return None
    
    properties = database_schema.get("properties", {})
    if not properties:
        LOGGER.warning("No properties found in database schema")
        return None
    
    preferred_names = ["Status", "Statut", "État", "Phase", "Stage"]
    property_names_lower = {name.lower(): name for name in properties.keys()}
    
    # First, try to find a property with a preferred name and correct type
    for preferred_name in preferred_names:
        preferred_lower = preferred_name.lower()
        if preferred_lower in property_names_lower:
            actual_name = property_names_lower[preferred_lower]
            prop_info = properties.get(actual_name, {})
            prop_type = prop_info.get("type")
            if prop_type in ["status", "select"]:
                LOGGER.info("Found Kanban property: '%s' (type: %s)", actual_name, prop_type)
                return actual_name
    
    # Fallback: find first status or select property
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type")
        if prop_type in ["status", "select"]:
            LOGGER.info("Using first available Kanban property: '%s' (type: %s)", prop_name, prop_type)
            return prop_name
    
    LOGGER.warning("No Kanban property found (no status or select properties with preferred names)")
    return None


def fetch_notion_kanban() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch all pages from the configured Notion database (or data source)
    and group them by Kanban column.

    Returns:
        A dict mapping column name -> list of cards.
        Example:
        {
            "To Do": [
                {"title": "...", "owner": "...", "due": "...", "status": "...", "page_id": "..."},
                ...
            ],
            "In Progress": [...],
            "Done": [...]
        }
    """
    if not _check_notion_config():
        LOGGER.error("Notion configuration is missing, cannot fetch Kanban")
        return {}

    try:
        # 1) Retrieve schema (will already try data_sources if needed)
        database_schema = get_database_schema()
        if not database_schema:
            LOGGER.error("Could not retrieve database schema")
            return {}

        # 2) Resolve property mapping
        property_mapping = resolve_properties_mapping(database_schema)

        # 3) Detect Kanban property
        kanban_property = detect_kanban_property(database_schema)

        # 4) Build list of endpoints to try (data_source first, then database)
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2025-09-03",
            "Content-Type": "application/json",
        }

        endpoints: List[Tuple[str, str]] = []

        data_source_id = _get_data_source_id()
        if data_source_id:
            endpoints.append(
                (
                    f"https://api.notion.com/v1/data_sources/{data_source_id}/query",
                    f"data_source_id={data_source_id}",
                )
            )

        # Always keep a fallback on classic /databases
        endpoints.append(
            (
                f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
                f"database_id={NOTION_DATABASE_ID}",
            )
        )

        all_pages: List[Dict[str, Any]] = []

        # 5) Try endpoints in order
        for api_url, debug_id in endpoints:
            LOGGER.info("Trying Notion query on %s (%s)", api_url, debug_id)
            all_pages.clear()
            cursor = None
            error_on_this_endpoint = False

            while True:
                try:
                    payload: Dict[str, Any] = {"page_size": 100}
                    if cursor:
                        payload["start_cursor"] = cursor

                    response = requests.post(api_url, headers=headers, json=payload)
                    try:
                        response.raise_for_status()
                    except requests.exceptions.HTTPError as http_err:
                        status_code = http_err.response.status_code if http_err.response is not None else None
                        body = http_err.response.text if http_err.response is not None else "<no body>"
                        LOGGER.error(
                            "HTTP error querying Notion (%s): %s (status: %s) body=%s",
                            debug_id,
                            http_err,
                            status_code,
                            body,
                        )
                        error_on_this_endpoint = True
                        break

                    response_data = response.json()
                    pages = response_data.get("results", [])
                    all_pages.extend(pages)

                    has_more = response_data.get("has_more", False)
                    next_cursor = response_data.get("next_cursor")

                    if not has_more or not next_cursor:
                        break

                    cursor = next_cursor

                except Exception as query_err:
                    LOGGER.error(
                        "Error querying Notion on endpoint %s (%s): %s",
                        api_url,
                        debug_id,
                        query_err,
                    )
                    error_on_this_endpoint = True
                    break

            if not error_on_this_endpoint:
                # We have successfully queried on this endpoint
                LOGGER.info(
                    "Successfully fetched %d pages from Notion using %s",
                    len(all_pages),
                    debug_id,
                )
                break
            else:
                # Try next endpoint if available
                LOGGER.warning("Failed on endpoint %s, trying next fallback if available", debug_id)
                all_pages = []

        if not all_pages:
            LOGGER.error("No pages retrieved from Notion on any endpoint")
            return {}

        # 6) Process pages and build Kanban data
        kanban_data: Dict[str, List[Dict[str, Any]]] = {}

        for page in all_pages:
            try:
                page_id = page.get("id", "")
                page_properties = page.get("properties", {})

                # Title
                title = "Untitled"
                task_prop_name = property_mapping.get("task")
                if task_prop_name and task_prop_name in page_properties:
                    task_prop = page_properties[task_prop_name]
                    if task_prop.get("type") == "title":
                        title_array = task_prop.get("title", [])
                        if title_array:
                            title = title_array[0].get("plain_text", "Untitled")
                else:
                    # Fallback: first title property
                    for prop_name, prop_info in page_properties.items():
                        if prop_info.get("type") == "title":
                            title_array = prop_info.get("title", [])
                            if title_array:
                                title = title_array[0].get("plain_text", "Untitled")
                            break

                # Status
                status_value = "No status"
                if kanban_property and kanban_property in page_properties:
                    kanban_prop = page_properties[kanban_property]
                    kanban_type = kanban_prop.get("type")
                    if kanban_type == "status":
                        status_obj = kanban_prop.get("status")
                        if status_obj:
                            status_value = status_obj.get("name", "No status")
                    elif kanban_type == "select":
                        select_obj = kanban_prop.get("select")
                        if select_obj:
                            status_value = select_obj.get("name", "No status")

                # Owner
                owner = None
                owner_prop_name = property_mapping.get("owner")
                if owner_prop_name and owner_prop_name in page_properties:
                    owner_prop = page_properties[owner_prop_name]
                    owner_type = owner_prop.get("type")
                    if owner_type == "people":
                        people_array = owner_prop.get("people", [])
                        if people_array:
                            person = people_array[0]
                            if isinstance(person, dict):
                                owner = person.get("name") or person.get("id", "")
                    elif owner_type == "rich_text":
                        rich_text_array = owner_prop.get("rich_text", [])
                        if rich_text_array:
                            owner = rich_text_array[0].get("plain_text", "")

                # Due date
                due = None
                due_prop_name = property_mapping.get("due_date")
                if due_prop_name and due_prop_name in page_properties:
                    due_prop = page_properties[due_prop_name]
                    if due_prop.get("type") == "date":
                        date_obj = due_prop.get("date")
                        if date_obj:
                            due = date_obj.get("start", "")

                card = {
                    "title": title,
                    "owner": owner,
                    "due": due,
                    "status": status_value,
                    "page_id": page_id,
                }

                if status_value not in kanban_data:
                    kanban_data[status_value] = []
                kanban_data[status_value].append(card)

            except Exception as page_err:
                LOGGER.warning("Error processing Notion page: %s", page_err)
                continue

        return kanban_data

    except Exception as exc:
        LOGGER.exception("Unexpected error in fetch_notion_kanban: %s", exc)
        return {}



def push_todo_to_notion(todo: Todo, meeting: Meeting) -> Optional[str]:
    """
    Create a Notion page in the configured database from a TODO and its meeting context.
    
    Retrieves the Notion database schema, resolves property mappings dynamically,
    and creates a page with the TODO data. Handles all exceptions gracefully.
    
    Args:
        todo: The Todo object to create a page for
        meeting: The associated Meeting object
    
    Returns:
        The created page ID (string) on success, None on failure
    """
    if not _check_notion_config():
        return None
    
    try:
        # Step 1: Get data source ID from database
        data_source_id = _get_data_source_id()
        if not data_source_id:
            LOGGER.error("Could not retrieve data source ID from database")
            return None
        
        # Step 2: Retrieve data source schema using new API endpoint
        # Use the data_sources API endpoint (GET /v1/data_sources/:data_source_id)
        try:
            # Try using notion.request() if available (SDK v5+)
            if hasattr(notion, 'request'):
                LOGGER.info("Using notion.request() to retrieve data source")
                response = notion.request(
                    path=f"data_sources/{data_source_id}",
                    method="GET"
                )
                database_schema = response if isinstance(response, dict) else {}
            else:
                # Fallback: Use direct HTTP request for data_sources endpoint
                # This is necessary because SDK v2.7.0 doesn't have data_sources methods
                LOGGER.info("Using direct HTTP request to retrieve data source (SDK doesn't support data_sources endpoint)")
                headers = {
                    "Authorization": f"Bearer {NOTION_API_KEY}",
                    "Notion-Version": "2025-09-03",
                    "Content-Type": "application/json"
                }
                api_url = f"https://api.notion.com/v1/data_sources/{data_source_id}"
                LOGGER.debug("Requesting: %s", api_url)
                response = requests.get(api_url, headers=headers)
                response.raise_for_status()
                database_schema = response.json()
                LOGGER.info("Successfully retrieved data source schema via HTTP")
        except requests.exceptions.HTTPError as http_err:
            error_msg = str(http_err)
            status_code = http_err.response.status_code if hasattr(http_err, 'response') else None
            LOGGER.error("HTTP error retrieving data source schema: %s (status: %s)", error_msg, status_code)
            
            if status_code == 403:
                LOGGER.error("Data source not shared with integration. Please share the database in Notion.")
            elif status_code == 404:
                LOGGER.error("Data source ID not found: %s. Check that the ID is correct.", data_source_id)
            elif status_code == 401:
                LOGGER.error("Authentication failed. Check your NOTION_API_KEY.")
            
            return None
        except Exception as api_err:
            LOGGER.error("Error retrieving data source schema: %s", api_err)
            LOGGER.exception("Full traceback:")
            return None
        
        if not isinstance(database_schema, dict) or "properties" not in database_schema:
            LOGGER.error("Could not retrieve properties from data source")
            return None
        
        property_mapping = resolve_properties_mapping(database_schema)
        
        if not property_mapping:
            LOGGER.error("No matching properties found in Notion database. Cannot create page.")
            return None
        
        properties: Dict[str, Any] = {}
        db_properties = database_schema.get("properties", {})
        
        if "task" in property_mapping:
            prop_name = property_mapping["task"]
            properties[prop_name] = {
                "title": [
                    {
                        "text": {
                            "content": todo.task or "Untitled Task"
                        }
                    }
                ]
            }
        
        if "owner" in property_mapping:
            prop_name = property_mapping["owner"]
            prop_info = db_properties.get(prop_name, {})
            prop_type = prop_info.get("type")
            
            if prop_type == "people":
                # People type requires user IDs, not text
                # For now, we'll skip it as we don't have user IDs
                # TODO: Implement user lookup if needed
                LOGGER.info("Skipping owner: people type requires user IDs, not text")
            else:
                # Fallback to rich_text for other types
                owner_text = todo.owner or "Unassigned"
                properties[prop_name] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": owner_text
                            }
                        }
                    ]
                }
        
        if "due_date" in property_mapping:
            prop_name = property_mapping["due_date"]
            if todo.due_date and todo.due_date.strip():
                properties[prop_name] = {
                    "date": {
                        "start": todo.due_date.strip()
                    }
                }
            else:
                properties[prop_name] = {
                    "date": None
                }
        
        if "status" in property_mapping:
            prop_name = property_mapping["status"]
            prop_info = db_properties.get(prop_name, {})
            prop_type = prop_info.get("type")
            
            # Map Todo status to Notion status name first
            todo_status = todo.status or "pending"
            # Get available options for better matching
            available_options = []
            if prop_type == "status":
                # Try different possible structures for status options
                status_config = prop_info.get("status", {})
                if isinstance(status_config, dict):
                    status_options = status_config.get("options", [])
                    if status_options:
                        available_options = [opt.get("name", "") if isinstance(opt, dict) else str(opt) for opt in status_options]
                # Also try direct access if options are at property level
                if not available_options and "options" in prop_info:
                    status_options = prop_info.get("options", [])
                    if status_options:
                        available_options = [opt.get("name", "") if isinstance(opt, dict) else str(opt) for opt in status_options]
            elif prop_type == "select":
                # Try different possible structures for select options
                select_config = prop_info.get("select", {})
                if isinstance(select_config, dict):
                    select_options = select_config.get("options", [])
                    if select_options:
                        available_options = [opt.get("name", "") if isinstance(opt, dict) else str(opt) for opt in select_options]
                # Also try direct access if options are at property level
                if not available_options and "options" in prop_info:
                    select_options = prop_info.get("options", [])
                    if select_options:
                        available_options = [opt.get("name", "") if isinstance(opt, dict) else str(opt) for opt in select_options]
            
            if not available_options:
                LOGGER.warning(
                    "Could not retrieve status options from property '%s' (type: %s). "
                    "Property structure: %s. "
                    "This may prevent setting the status when creating the page.",
                    prop_name, prop_type, prop_info
                )
            
            desired_notion_status = map_todo_status_to_notion(todo_status, available_options)
            
            # Only set status if we have a valid mapped status
            if desired_notion_status:
                if prop_type == "status":
                    properties[prop_name] = {
                        "status": {
                            "name": desired_notion_status
                        }
                    }
                elif prop_type == "select":
                    properties[prop_name] = {
                        "select": {
                            "name": desired_notion_status
                        }
                    }
                else:
                    LOGGER.warning("Status field type '%s' not supported, skipping", prop_type)
            else:
                # No valid status found - skip setting it
                LOGGER.warning(
                    "Could not map status '%s' to a valid Notion status option. "
                    "Skipping status property. Page will be created with default status.",
                    todo_status
                )
            else:
                LOGGER.warning("Status field type '%s' not supported, skipping", prop_type)
        
        if "meeting_id" in property_mapping:
            prop_name = property_mapping["meeting_id"]
            prop_info = db_properties.get(prop_name, {})
            prop_type = prop_info.get("type")
            
            if prop_type == "unique_id":
                # Unique ID is auto-generated, cannot be set manually
                LOGGER.info("Skipping meeting_id: unique_id type is auto-generated by Notion")
            else:
                # Use number type
                properties[prop_name] = {
                    "number": meeting.id
                }
        
        if "created_at" in property_mapping:
            prop_name = property_mapping["created_at"]
            prop_info = db_properties.get(prop_name, {})
            prop_type = prop_info.get("type")
            
            if prop_type == "created_time":
                # created_time is automatically set by Notion, cannot be set manually
                LOGGER.info("Skipping Created at: created_time is automatically set by Notion")
            elif prop_type == "date":
                # Use date type
                if todo.created_at:
                    created_date = todo.created_at.strftime("%Y-%m-%d")
                    properties[prop_name] = {
                        "date": {
                            "start": created_date
                        }
                    }
                else:
                    properties[prop_name] = {
                        "date": None
                    }
            else:
                LOGGER.warning("Skipping created_at: unsupported type '%s'", prop_type)
        
        if not properties:
            LOGGER.error("No valid properties found in Notion database. Cannot create page.")
            return None
        
        # Use data_source_id for creating pages (API 2025-09-03)
        if not data_source_id:
            LOGGER.error("Data source ID not available. Cannot create page.")
            return None
        
        # Create page using data_source_id as parent
        try:
            response = notion.pages.create(
                parent={
                    "type": "data_source_id",
                    "data_source_id": data_source_id
                },
                properties=properties
            )
        except TypeError:
            # Fallback: try with database_id if data_source_id format not supported
            LOGGER.warning("data_source_id format not supported, trying database_id fallback")
            response = notion.pages.create(
                parent={
                    "database_id": NOTION_DATABASE_ID
                },
                properties=properties
            )
        
        page_id = response.get("id")
        
        if not page_id:
            LOGGER.error("Notion API response missing 'id' field. Response: %s", response)
            return None
        
        LOGGER.info("Created Notion page %s for TODO %d", page_id, todo.id)
        return page_id
        
    except Exception as exc:
        LOGGER.exception("Error while creating Notion page: %s", exc)
        return None


def map_notion_status_to_todo(notion_status: str) -> str:
    """
    Map a Notion Kanban column name to a normalized Todo.status value.
    
    Args:
        notion_status: Notion column name (e.g., "To Do", "In Progress", "Done", "En attente", etc.)
    
    Returns:
        Normalized status string: "pending", "in_progress", or "completed"
    """
    if not notion_status:
        return "pending"
    
    status_lower = notion_status.lower()
    
    # Remove accents and normalize
    status_normalized = status_lower
    # Simple accent removal for common French characters
    accent_map = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c'
    }
    for accented, unaccented in accent_map.items():
        status_normalized = status_normalized.replace(accented, unaccented)
    
    # Check for "done" / "completed" status
    done_keywords = ["done", "terminé", "termine", "fini", "fait", "closed", "complete", "complet"]
    if any(keyword in status_normalized for keyword in done_keywords):
        return "completed"  # Match database status value
    
    # Check for "in progress" / "doing" status
    in_progress_keywords = ["in progress", "doing", "en cours", "encours", "inprogress", "progress"]
    if any(keyword in status_normalized for keyword in in_progress_keywords):
        return "in_progress"
    
    # Check for "open" / "todo" / "pending" status
    open_keywords = ["todo", "to do", "backlog", "à faire", "a faire", "pending", "open", "ouvert"]
    if any(keyword in status_normalized for keyword in open_keywords):
        return "pending"  # Use "pending" to match database default
    
    # Default to "pending" (matches database default)
    return "pending"


def map_todo_status_to_notion(todo_status: str, available_notion_options: Optional[List[str]] = None) -> Optional[str]:
    """
    Map a Todo.status value to a Notion status name.
    
    Args:
        todo_status: Todo.status value (e.g., "pending", "in_progress", "completed")
        available_notion_options: Optional list of available Notion status names to match against
    
    Returns:
        Notion status name to use in select/status property
    """
    if not todo_status:
        todo_status = "pending"
    
    status_lower = todo_status.lower()
    
    # If we have available options, try to find the best match
    if available_notion_options:
        # Normalize the todo status to understand what we're looking for
        if status_lower in ["done", "completed"]:
            target_normalized = "completed"
        elif status_lower in ["in_progress", "inprogress", "acknowledged"]:
            target_normalized = "in_progress"
        else:  # pending, open, etc.
            target_normalized = "pending"
        
        # Try to find a Notion option that maps to the same normalized status
        for notion_option in available_notion_options:
            if map_notion_status_to_todo(notion_option) == target_normalized:
                return notion_option
        
        # If no match found, return first option as fallback
        if available_notion_options:
            LOGGER.warning(
                "Could not find matching Notion status for '%s', using first available: '%s'",
                todo_status, available_notion_options[0]
            )
            return available_notion_options[0]
    
    # If no options provided or empty list, return None (caller should skip setting status)
    # We cannot use hardcoded values like "To Do" because they may not exist in the user's Notion database
    LOGGER.warning(
        "No Notion status options available for mapping status '%s'. "
        "Status property will not be set when creating the page.",
        todo_status
    )
    return None


def update_notion_status(page_id: str, new_status: str) -> bool:
    """
    Update the status of a Notion page by setting its Kanban property.
    
    Args:
        page_id: The Notion page ID to update
        new_status: The new status name (e.g., "To Do", "In Progress", "Done")
    
    Returns:
        True on success, False on failure
    """
    if not _check_notion_config():
        LOGGER.error("Notion configuration is missing, cannot update status")
        return False
    
    if not page_id or not new_status:
        LOGGER.error("Invalid page_id or new_status provided")
        return False
    
    try:
        # Get database schema to find Kanban property
        database_schema = get_database_schema()
        if not database_schema:
            LOGGER.error("Could not retrieve database schema for status update")
            return False
        
        kanban_property = detect_kanban_property(database_schema)
        if not kanban_property:
            LOGGER.error("Could not detect Kanban property for status update")
            return False
        
        # Get property info to determine type
        properties = database_schema.get("properties", {})
        prop_info = properties.get(kanban_property, {})
        prop_type = prop_info.get("type")
        
        if prop_type not in ["status", "select"]:
            LOGGER.error("Kanban property '%s' is not of type 'status' or 'select' (type: %s)", kanban_property, prop_type)
            return False
        
        # Find the best matching status from available options
        if prop_type == "status":
            status_options = prop_info.get("status", {}).get("options", [])
            status_names = [opt.get("name", "") for opt in status_options]
            
            # Try exact match first
            if new_status in status_names:
                actual_status = new_status
            else:
                # Try case-insensitive match
                status_names_lower = {name.lower(): name for name in status_names}
                actual_status = status_names_lower.get(new_status.lower())
                
                if not actual_status:
                    # Try to find a similar status using the mapping function
                    # Map the desired status back to a normalized form, then find closest match
                    normalized = map_notion_status_to_todo(new_status)
                    # Find the first option that maps to the same normalized status
                    for opt_name in status_names:
                        if map_notion_status_to_todo(opt_name) == normalized:
                            actual_status = opt_name
                            break
                    
                    # If still no match, use the first available option
                    if not actual_status and status_names:
                        actual_status = status_names[0]
                        LOGGER.warning(
                            "Status '%s' not found, using first available option: '%s' (available: %s)",
                            new_status, actual_status, status_names
                        )
                    elif not actual_status:
                        LOGGER.error("No status options available in Notion property")
                        return False
                else:
                    LOGGER.info("Using case-insensitive match: '%s' → '%s'", new_status, actual_status)
            
            property_value = {
                "status": {
                    "name": actual_status
                }
            }
        else:  # select
            select_options = prop_info.get("select", {}).get("options", [])
            option_names = [opt.get("name", "") for opt in select_options]
            
            # Try exact match first
            if new_status in option_names:
                actual_status = new_status
            else:
                # Try case-insensitive match
                option_names_lower = {name.lower(): name for name in option_names}
                actual_status = option_names_lower.get(new_status.lower())
                
                if not actual_status:
                    # Try to find a similar status using the mapping function
                    normalized = map_notion_status_to_todo(new_status)
                    for opt_name in option_names:
                        if map_notion_status_to_todo(opt_name) == normalized:
                            actual_status = opt_name
                            break
                    
                    # If still no match, use the first available option
                    if not actual_status and option_names:
                        actual_status = option_names[0]
                        LOGGER.warning(
                            "Status '%s' not found, using first available option: '%s' (available: %s)",
                            new_status, actual_status, option_names
                        )
                    elif not actual_status:
                        LOGGER.error("No select options available in Notion property")
                        return False
                else:
                    LOGGER.info("Using case-insensitive match: '%s' → '%s'", new_status, actual_status)
            
            property_value = {
                "select": {
                    "name": actual_status
                }
            }
        
        # Build request payload
        payload = {
            "properties": {
                kanban_property: property_value
            }
        }
        
        # Make PATCH request
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": "2025-09-03",
            "Content-Type": "application/json"
        }
        
        api_url = f"https://api.notion.com/v1/pages/{page_id}"
        
        LOGGER.debug("Updating Notion page %s: property='%s', status='%s'", page_id, kanban_property, new_status)
        LOGGER.debug("Payload: %s", payload)
        
        response = requests.patch(api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        LOGGER.info("Successfully updated Notion page %s status to '%s'", page_id, new_status)
        return True
        
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if hasattr(http_err, 'response') and http_err.response else None
        error_body = ""
        if hasattr(http_err, 'response') and http_err.response:
            try:
                error_body = http_err.response.text
            except Exception:
                pass
        LOGGER.error(
            "HTTP error updating Notion page status: %s (status: %s, body: %s)",
            http_err, status_code, error_body
        )
        return False
    except Exception as exc:
        LOGGER.exception("Error updating Notion page status: %s", exc)
        return False


def sync_from_notion(session: Session) -> int:
    """
    Synchronize Todo statuses from Notion Kanban board to local database.
    
    Reads the current Kanban state from Notion and updates matching TODOs in the database.
    Only updates TODOs that are already linked to Notion pages (have notion_page_id set).
    
    Args:
        session: SQLAlchemy session for database operations
    
    Returns:
        Number of TODOs successfully updated
    """
    if not _check_notion_config():
        LOGGER.error("Notion configuration is missing, cannot sync from Notion")
        return 0
    
    try:
        # Fetch Kanban data from Notion
        kanban_data = fetch_notion_kanban()
        if not kanban_data:
            LOGGER.warning("No Kanban data retrieved from Notion")
            return 0
        
        updated_count = 0
        
        # Flatten and process each card
        for status_name, cards in kanban_data.items():
            for card in cards:
                try:
                    page_id = card.get("page_id")
                    if not page_id:
                        continue
                    
                    # Find matching Todo in database
                    todo = session.query(Todo).filter_by(notion_page_id=page_id).first()
                    if not todo:
                        continue
                    
                    # Map Notion status to Todo status
                    new_status = map_notion_status_to_todo(status_name)
                    
                    # Update if status changed using centralized function
                    if new_status != todo.status:
                        update_todo_status(
                            session=session,
                            todo_id=todo.id,
                            new_status=new_status,
                            source="notion_sync",
                            note=f"Synced from Notion column '{status_name}'"
                        )
                        updated_count += 1
                
                except Exception as card_err:
                    LOGGER.warning("Error processing Notion card: %s", card_err)
                    continue
        
        # Note: update_todo_status already commits each change
        if updated_count > 0:
            LOGGER.info("Synced %d TODOs from Notion", updated_count)
        else:
            LOGGER.info("No TODOs needed updating from Notion")
        
        return updated_count
        
    except Exception as exc:
        LOGGER.exception("Unexpected error in sync_from_notion: %s", exc)
        try:
            session.rollback()
        except Exception:
            pass
        return 0


def sync_to_notion(session: Session) -> int:
    """
    Synchronize Todo statuses from local database to Notion Kanban board.
    
    Updates Notion pages for all TODOs that have a notion_page_id set.
    
    Args:
        session: SQLAlchemy session for database operations
    
    Returns:
        Number of Notion pages successfully updated
    """
    if not _check_notion_config():
        LOGGER.error("Notion configuration is missing, cannot sync to Notion")
        return 0
    
    try:
        # Query all TODOs with notion_page_id set
        todos = session.query(Todo).filter(Todo.notion_page_id.isnot(None)).all()
        
        if not todos:
            LOGGER.info("No TODOs with notion_page_id found, nothing to sync")
            return 0
        
        updated_count = 0
        
        for todo in todos:
            try:
                if not todo.notion_page_id:
                    continue
                
                # Get available Notion options for better matching
                database_schema = get_database_schema()
                available_options = None
                if database_schema:
                    kanban_prop = detect_kanban_property(database_schema)
                    if kanban_prop:
                        properties = database_schema.get("properties", {})
                        prop_info = properties.get(kanban_prop, {})
                        prop_type = prop_info.get("type")
                        if prop_type == "status":
                            status_options = prop_info.get("status", {}).get("options", [])
                            available_options = [opt.get("name", "") for opt in status_options]
                        elif prop_type == "select":
                            select_options = prop_info.get("select", {}).get("options", [])
                            available_options = [opt.get("name", "") for opt in select_options]
                
                # Map Todo status to Notion status
                new_status_name = map_todo_status_to_notion(todo.status or "pending", available_options)
                
                # Update Notion page
                success = update_notion_status(todo.notion_page_id, new_status_name)
                if success:
                    updated_count += 1
                    LOGGER.info(
                        "Updated Notion page %s (Todo %d) status to '%s'",
                        todo.notion_page_id, todo.id, new_status_name
                    )
                else:
                    LOGGER.warning(
                        "Failed to update Notion page %s (Todo %d) status",
                        todo.notion_page_id, todo.id
                    )
            
            except Exception as todo_err:
                LOGGER.warning("Error syncing Todo %d to Notion: %s", todo.id, todo_err)
                continue
        
        LOGGER.info("Synced %d TODOs to Notion", updated_count)
        return updated_count
        
    except Exception as exc:
        LOGGER.exception("Unexpected error in sync_to_notion: %s", exc)
        return 0
