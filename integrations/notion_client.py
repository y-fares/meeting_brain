"""
Notion client for creating pages from TODOs.
"""

import logging
import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from notion_client import Client

from database import Todo, Meeting

LOGGER = logging.getLogger(__name__)

# Load environment variables here, BEFORE reading them
load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY:
    LOGGER.warning("NOTION_API_KEY environment variable is not set")
if not NOTION_DATABASE_ID:
    LOGGER.warning("NOTION_DATABASE_ID environment variable is not set")

notion = Client(auth=NOTION_API_KEY) if NOTION_API_KEY else None


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


def resolve_properties_mapping(notion_database_schema: Dict[str, Any], flexible: bool = True) -> Dict[str, str]:
    """
    Returns a dict mapping expected logical keys ('task', 'owner', ...) 
    to actual Notion property names.
    
    Args:
        notion_database_schema: The schema dictionary from notion.databases.retrieve()
        flexible: If True, will match by type if no name match is found
    
    Returns:
        Dictionary mapping logical field names to actual Notion property names
    """
    mapping: Dict[str, str] = {}
    
    # Get all property names from the database schema (case-insensitive lookup)
    properties = notion_database_schema.get("properties", {})
    property_names_lower = {name.lower(): name for name in properties.keys()}
    
    # Group properties by type for flexible matching
    properties_by_type: Dict[str, list] = {}
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type")
        if prop_type not in properties_by_type:
            properties_by_type[prop_type] = []
        properties_by_type[prop_type].append(prop_name)
    
    # Define expected fields with their types and alternative names
    field_definitions = {
        "task": {
            "type": "title",
            "alternatives": ["Task", "Tâche", "Name", "Title", "Titre", "Nom"]
        },
        "owner": {
            "type": "people",  # Owner is typically a people/select field in Notion
            "alternatives": ["Owner", "Propriétaire", "Assigned", "Assignee", "Responsible", "Assignation", "Personne"]
        },
        "due_date": {
            "type": "date",
            "alternatives": ["Due date", "Date", "Deadline", "Due", "Échéance", "Date d'échéance"]
        },
        "status": {
            "type": "select",
            "alternatives": ["Status", "Statut", "État", "State"]
        },
        "meeting_id": {
            "type": "number",
            "alternatives": ["Meeting ID", "Meeting", "ID Meeting", "MeetingId", "Meeting Number", "Identifiant", "ID"]
        },
        "created_at": {
            "type": "date",
            "alternatives": ["Created at", "Created", "Créé le", "Creation Date", "Date Created", "Date de création"]
        }
    }
    
    # Track which properties have been used (to avoid duplicates in flexible mode)
    used_properties = set()
    
    # For each expected field, try to find a matching property
    for logical_key, field_info in field_definitions.items():
        expected_type = field_info["type"]
        alternatives = field_info["alternatives"]
        
        found_property = None
        
        # Try exact match first
        for alt_name in alternatives:
            if alt_name in properties:
                prop_info = properties[alt_name]
                if prop_info.get("type") == expected_type:
                    found_property = alt_name
                    break
        
        # Try case-insensitive match
        if not found_property:
            for alt_name in alternatives:
                alt_lower = alt_name.lower()
                if alt_lower in property_names_lower:
                    actual_name = property_names_lower[alt_lower]
                    if actual_name not in used_properties:
                        prop_info = properties[actual_name]
                        if prop_info.get("type") == expected_type:
                            found_property = actual_name
                            break
        
        # Flexible matching: if no name match, use first property of correct type
        if not found_property and flexible and expected_type in properties_by_type:
            for prop_name in properties_by_type[expected_type]:
                if prop_name not in used_properties:
                    found_property = prop_name
                    LOGGER.info("Using '%s' for field '%s' (type match)", prop_name, logical_key)
                    break
        
        if found_property:
            mapping[logical_key] = found_property
            used_properties.add(found_property)
        else:
            LOGGER.warning(
                "Skipping field '%s': no matching property found (tried: %s, type: %s)",
                logical_key,
                ", ".join(alternatives),
                expected_type
            )
    
    return mapping


def push_todo_to_notion(todo: Todo, meeting: Meeting) -> Optional[str]:
    """
    Create a Notion page in the configured database from a TODO and its meeting context.
    
    This function dynamically adapts to the actual property names in the Notion database
    by retrieving the database schema and mapping expected fields to actual property names.
    
    Args:
        todo: The Todo object to create a page for
        meeting: The associated Meeting object
    
    Returns:
        The created page ID (string) on success, None on failure
    """
    # Check configuration first
    if not _check_notion_config():
        return None
    
    try:
        # Retrieve database schema to get actual property names
        database_schema = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        
        # Resolve mapping between logical fields and actual property names
        property_mapping = resolve_properties_mapping(database_schema)
        
        # Build properties for the Notion page using the resolved mapping
        properties: Dict[str, Any] = {}
        
        # Task (title)
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
        
        # Owner (people) - Note: people fields require user IDs, not text
        # For now, we'll skip owner if it's a people field as we'd need user IDs
        if "owner" in property_mapping:
            prop_name = property_mapping["owner"]
            # Check if it's a people field - if so, we need user IDs which we don't have
            # For people fields, we'll skip setting it for now
            # TODO: Implement user lookup if needed
            owner_text = todo.owner or "Unassigned"
            # Only set if it's not a people field (people fields need special handling)
            prop_info = database_schema.get("properties", {}).get(prop_name, {})
            if prop_info.get("type") != "people":
                properties[prop_name] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": owner_text
                            }
                        }
                    ]
                }
            else:
                LOGGER.warning("Skipping Owner field: people fields require user IDs, not text")
        
        # Due date (date)
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
        
        # Status (status or select)
        if "status" in property_mapping:
            prop_name = property_mapping["status"]
            status_value = todo.status or "Pas commencé"  # Default to your DB's status option
            
            # Map common status values to your DB's status options
            status_mapping = {
                "pending": "Pas commencé",
                "in_progress": "En cours",
                "completed": "Terminé",
                "open": "Pas commencé",
                "done": "Terminé"
            }
            mapped_status = status_mapping.get(status_value.lower(), status_value)
            
            # Check if it's a status field or select field
            prop_info = database_schema.get("properties", {}).get(prop_name, {})
            if prop_info.get("type") == "status":
                properties[prop_name] = {
                    "status": {
                        "name": mapped_status
                    }
                }
            else:
                properties[prop_name] = {
                    "select": {
                        "name": mapped_status
                    }
                }
        
        # Meeting ID (number)
        if "meeting_id" in property_mapping:
            prop_name = property_mapping["meeting_id"]
            properties[prop_name] = {
                "number": meeting.id
            }
        
        # Created at (created_time or date)
        # Note: created_time is automatically set by Notion, so we might skip it
        if "created_at" in property_mapping:
            prop_name = property_mapping["created_at"]
            prop_info = database_schema.get("properties", {}).get(prop_name, {})
            
            # If it's created_time, Notion sets it automatically, so we skip
            if prop_info.get("type") == "created_time":
                LOGGER.info("Skipping Created at: created_time is automatically set by Notion")
            elif todo.created_at:
                # Format datetime as YYYY-MM-DD for date fields
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
        
        # Check if we have at least one property (required for page creation)
        if not properties:
            LOGGER.error("No valid properties found in Notion database. Cannot create page.")
            return None
        
        # Create the page
        response = notion.pages.create(
            parent={
                "database_id": NOTION_DATABASE_ID
            },
            properties=properties
        )
        
        # Extract page ID from response
        page_id = response.get("id")
        
        if not page_id:
            LOGGER.error("Notion API response missing 'id' field. Response: %s", response)
            return None
        
        LOGGER.info("Created Notion page %s for TODO %d", page_id, todo.id)
        return page_id
        
    except Exception as exc:
        LOGGER.exception("Error while creating Notion page: %s", exc)
        return None
