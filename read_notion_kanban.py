"""
Read and display a Notion Kanban board using MCP Notion connection or Notion API.

Usage:
    python read_notion_kanban.py <DATABASE_ID>
    
    Or set NOTION_DATABASE_ID in .env file and run:
    python read_notion_kanban.py

This script can use:
1. MCP Notion (if available via assistant)
2. Notion API REST (notion-client) as fallback
"""

import sys
import json
import re
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Try to import Notion client for API fallback
try:
    from notion_client import Client
    from dotenv import load_dotenv
    load_dotenv()
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_CLIENT_AVAILABLE = NOTION_API_KEY is not None
    if NOTION_CLIENT_AVAILABLE:
        notion_client = Client(auth=NOTION_API_KEY)
    else:
        notion_client = None
except ImportError:
    NOTION_CLIENT_AVAILABLE = False
    notion_client = None


def parse_database_schema(mcp_response: str) -> Dict[str, Any]:
    """
    Parse database schema from MCP Notion fetch response.
    
    Args:
        mcp_response: Raw response from MCP Notion fetch
        
    Returns:
        Parsed schema dictionary
    """
    schema = {}
    
    # Extract data-source-state which contains the schema
    match = re.search(r'<data-source-state>\s*({.*?})\s*</data-source-state>', mcp_response, re.DOTALL)
    if match:
        try:
            state_json = match.group(1)
            state = json.loads(state_json)
            schema = state.get("schema", {})
        except json.JSONDecodeError:
            pass
    
    return schema


def parse_page_properties(page_response: str) -> Dict[str, Any]:
    """
    Parse page properties from MCP Notion fetch response.
    
    Args:
        page_response: Raw response from MCP Notion fetch
        
    Returns:
        Parsed properties dictionary
    """
    props = {}
    
    # Extract properties from <properties> tag
    match = re.search(r'<properties>\s*({.*?})\s*</properties>', page_response, re.DOTALL)
    if match:
        try:
            props_json = match.group(1)
            props = json.loads(props_json)
        except json.JSONDecodeError:
            pass
    
    return props


def fetch_database_schema_api(database_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch database schema using Notion API REST.
    
    Args:
        database_id: Database ID
        
    Returns:
        Schema dictionary or None on error
    """
    if not NOTION_CLIENT_AVAILABLE or not notion_client:
        return None
    
    try:
        db_response = notion_client.databases.retrieve(database_id=database_id)
        properties = db_response.get("properties", {})
        return properties
    except Exception as e:
        print(f"  Error fetching database schema: {e}")
        return None


def search_pages_api(database_id: str) -> List[Dict[str, Any]]:
    """
    Search for all pages in database using Notion API REST.
    
    Args:
        database_id: Database ID
        
    Returns:
        List of page dictionaries
    """
    if not NOTION_CLIENT_AVAILABLE or not notion_client:
        return []
    
    try:
        all_pages = []
        has_more = True
        start_cursor = None
        
        while has_more:
            if start_cursor:
                response = notion_client.databases.query(
                    database_id=database_id,
                    start_cursor=start_cursor
                )
            else:
                response = notion_client.databases.query(database_id=database_id)
            
            pages = response.get("results", [])
            all_pages.extend(pages)
            
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        return all_pages
    except Exception as e:
        print(f"  Error searching pages: {e}")
        return []


def detect_kanban_property(schema: Dict[str, Any]) -> Optional[tuple]:
    """
    Detect which property is used for Kanban grouping.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        Tuple of (property_name, property_type) or None
    """
    # Look for status or select properties (common Kanban columns)
    for prop_name, prop_info in schema.items():
        prop_type = prop_info.get("type", "")
        if prop_type in ["status", "select"]:
            return (prop_name, prop_type)
    
    return None


def detect_property_mapping(schema: Dict[str, Any]) -> Dict[str, tuple]:
    """
    Automatically detect property names for title, owner, due date.
    
    Args:
        schema: Database schema dictionary
        
    Returns:
        Dictionary mapping logical names to (property_name, property_type)
    """
    mapping = {}
    
    # Find title property (first title type)
    for prop_name, prop_info in schema.items():
        if prop_info.get("type") == "title" and "title" not in mapping:
            mapping["title"] = (prop_name, "title")
            break
    
    # Find owner property (prefer people, then rich_text, then text)
    for prop_name, prop_info in schema.items():
        prop_type = prop_info.get("type", "")
        if prop_type == "people" and "owner" not in mapping:
            mapping["owner"] = (prop_name, "people")
            break
    
    # If no people field, look for rich_text or text
    if "owner" not in mapping:
        for prop_name, prop_info in schema.items():
            prop_type = prop_info.get("type", "")
            if prop_type in ["rich_text", "text"] and "owner" not in mapping:
                mapping["owner"] = (prop_name, prop_type)
                break
    
    # Find due date property (first date type)
    for prop_name, prop_info in schema.items():
        if prop_info.get("type") == "date" and "due_date" not in mapping:
            mapping["due_date"] = (prop_name, "date")
            break
    
    return mapping


def extract_property_value(props: Dict[str, Any], prop_name: str, prop_type: str) -> Optional[str]:
    """
    Extract a property value from page properties.
    
    Args:
        props: Page properties dictionary
        prop_name: Property name
        prop_type: Property type
        
    Returns:
        Extracted value as string, or None
    """
    if prop_name not in props:
        return None
    
    prop_data = props[prop_name]
    
    if prop_type == "title":
        # Title is an array of rich text objects
        if isinstance(prop_data, dict) and "title" in prop_data:
            title_array = prop_data["title"]
            if isinstance(title_array, list) and len(title_array) > 0:
                first_item = title_array[0]
                if isinstance(first_item, dict):
                    return first_item.get("plain_text", "")
        return str(prop_data) if prop_data else None
    
    elif prop_type in ["rich_text", "text"]:
        if isinstance(prop_data, dict) and prop_type in prop_data:
            text_array = prop_data[prop_type]
            if isinstance(text_array, list) and len(text_array) > 0:
                first_item = text_array[0]
                if isinstance(first_item, dict):
                    return first_item.get("plain_text", "")
        return str(prop_data) if prop_data else None
    
    elif prop_type == "people":
        # People is an array of user objects
        if isinstance(prop_data, dict) and "people" in prop_data:
            people_array = prop_data["people"]
            if isinstance(people_array, list) and len(people_array) > 0:
                names = []
                for person in people_array:
                    if isinstance(person, dict):
                        name = person.get("name", "")
                        if name:
                            names.append(name)
                return ", ".join(names) if names else None
        return str(prop_data) if prop_data else None
    
    elif prop_type == "date":
        # Date can be a date object or expanded format
        if isinstance(prop_data, dict):
            date_obj = prop_data.get("date")
            if date_obj:
                start = date_obj.get("start", "")
                if start:
                    try:
                        # Format date nicely
                        if 'T' in start:
                            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            return dt.strftime("%Y-%m-%d")
                        else:
                            return start
                    except:
                        return start
        return str(prop_data) if prop_data else None
    
    elif prop_type in ["status", "select"]:
        if isinstance(prop_data, dict):
            status_obj = prop_data.get(prop_type)
            if status_obj:
                return status_obj.get("name", "")
        return str(prop_data) if prop_data else None
    
    return str(prop_data) if prop_data else None


def format_kanban_summary(kanban_data: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Format Kanban data into readable summary.
    
    Args:
        kanban_data: Dictionary mapping column names to lists of cards
        
    Returns:
        Formatted string
    """
    output = []
    output.append("=" * 60)
    output.append("KANBAN SUMMARY")
    output.append("=" * 60)
    
    total_cards = sum(len(cards) for cards in kanban_data.values())
    output.append(f"\nTotal columns: {len(kanban_data)}")
    output.append(f"Total cards: {total_cards}\n")
    
    # Sort columns: to_do, in_progress, complete (if status type)
    column_order = ["Pas commencé", "En cours", "Terminé", "to_do", "in_progress", "complete"]
    sorted_columns = sorted(
        kanban_data.keys(),
        key=lambda x: column_order.index(x) if x in column_order else 999
    )
    
    for column_name in sorted_columns:
        cards = kanban_data[column_name]
        output.append(f"\n## {column_name} ({len(cards)} cards)")
        
        if len(cards) == 0:
            output.append("  (No cards in this column)")
        else:
            for card in cards:
                title = card.get("title", "Untitled")
                owner = card.get("owner", "")
                due = card.get("due", "")
                
                parts = [f"  - {title}"]
                if owner:
                    parts.append(f"Owner: {owner}")
                if due:
                    parts.append(f"Due: {due}")
                
                output.append(" — ".join(parts))
    
    output.append("\n" + "=" * 60)
    return "\n".join(output)


def main():
    """Main function."""
    # Get database ID from command line or .env
    if len(sys.argv) >= 2:
        database_id = sys.argv[1]
    else:
        database_id = os.getenv("NOTION_DATABASE_ID")
        if not database_id:
            print("Usage: python read_notion_kanban.py <DATABASE_ID>")
            print("\nOr set NOTION_DATABASE_ID in .env file")
            print("\nExample:")
            print("  python read_notion_kanban.py 2c3d2096-d4c9-8078-b860-f760953a0d75")
            sys.exit(1)
    
    # Remove dashes from database ID if present
    database_id = database_id.replace("-", "")
    
    print("=" * 60)
    print("NOTION KANBAN READER")
    print("=" * 60)
    print(f"\nDatabase ID: {database_id}")
    
    try:
        # Step 1: Fetch database schema
        print("\n[1/4] Fetching database schema...")
        
        if NOTION_CLIENT_AVAILABLE:
            print("  Using Notion API REST (notion-client)")
            schema = fetch_database_schema_api(database_id)
            if not schema:
                print("  ERROR: Could not fetch database schema")
                print("  Make sure:")
                print("    - NOTION_API_KEY is set in .env")
                print("    - Database is shared with your Notion integration")
                sys.exit(1)
        else:
            print("  ⚠️  Notion API client not available")
            print("  Install: pip install notion-client python-dotenv")
            print("  Set NOTION_API_KEY in .env file")
            sys.exit(1)
        
        print(f"  ✓ Found {len(schema)} properties")
        
        # Step 2: Detect Kanban property
        print("\n[2/4] Detecting Kanban property...")
        kanban_prop = detect_kanban_property(schema)
        if not kanban_prop:
            print("  ERROR: No status or select property found for Kanban grouping")
            sys.exit(1)
        
        kanban_prop_name, kanban_prop_type = kanban_prop
        print(f"  ✓ Kanban property: {kanban_prop_name} ({kanban_prop_type})")
        
        # Step 3: Detect property mappings
        prop_mapping = detect_property_mapping(schema)
        print(f"  ✓ Detected properties: {list(prop_mapping.keys())}")
        
        # Step 4: Retrieve all pages
        print("\n[3/4] Retrieving all pages...")
        pages = search_pages_api(database_id)
        print(f"  ✓ Found {len(pages)} pages")
        
        if len(pages) == 0:
            print("\n  No pages found in database.")
            sys.exit(0)
        
        # Step 5: Group pages by Kanban column
        print("\n[4/4] Grouping pages by Kanban column...")
        kanban_data: Dict[str, List[Dict[str, Any]]] = {}
        
        for page in pages:
            page_props = page.get("properties", {})
            
            # Get Kanban column value
            status_value = extract_property_value(page_props, kanban_prop_name, kanban_prop_type)
            if not status_value:
                status_value = "Uncategorized"
            
            # Initialize column if needed
            if status_value not in kanban_data:
                kanban_data[status_value] = []
            
            # Extract card information
            card = {
                "page_id": page.get("id", ""),
                "title": "Untitled",
                "owner": "",
                "due": ""
            }
            
            # Extract title
            if "title" in prop_mapping:
                title_prop, title_type = prop_mapping["title"]
                title = extract_property_value(page_props, title_prop, title_type)
                if title:
                    card["title"] = title
            
            # Extract owner
            if "owner" in prop_mapping:
                owner_prop, owner_type = prop_mapping["owner"]
                owner = extract_property_value(page_props, owner_prop, owner_type)
                if owner:
                    card["owner"] = owner
            
            # Extract due date
            if "due_date" in prop_mapping:
                due_prop, due_type = prop_mapping["due_date"]
                due = extract_property_value(page_props, due_prop, due_type)
                if due:
                    card["due"] = due
            
            kanban_data[status_value].append(card)
        
        # Step 6: Display summary
        print("\n" + format_kanban_summary(kanban_data))
        
    except Exception as exc:
        print(f"\nERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
