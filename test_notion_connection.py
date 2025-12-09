"""
Test script for Notion integration validation.
Tests connection, database access, and page creation capabilities.
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from notion_client import Client


def validate_api_key(api_key: str) -> bool:
    """
    Validate that the API key appears to be a valid Notion token.
    Notion API keys typically start with 'ntn_'.
    """
    if not api_key:
        return False
    return api_key.startswith('ntn_')


def validate_database_id(database_id: str) -> bool:
    """
    Validate that the database ID is a 32-character hexadecimal string.
    """
    if not database_id:
        return False
    if len(database_id) != 32:
        return False
    try:
        int(database_id, 16)
        return True
    except ValueError:
        return False


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
    # Updated with exact property names from the user's Notion database
    field_definitions = {
        "task": {
            "type": "title",
            "alternatives": ["Task", "Tâche", "Name", "Title", "Titre", "Nom", "Texte"]
        },
        "owner": {
            "type": "people",  # Changed from rich_text to people (Owner is a person field)
            "alternatives": ["Owner", "Propriétaire", "Assigned", "Assignee", "Responsible", "Assignation", "Personne"]
        },
        "due_date": {
            "type": "date",
            "alternatives": ["Due Date", "Due date", "Date", "Deadline", "Due", "Échéance", "Date d'échéance"]
        },
        "status": {
            "type": "select",
            "alternatives": ["Status", "Statut", "État", "State"]
        },
        "meeting_id": {
            "type": "number",
            "alternatives": ["Meeting ID", "Meeting", "ID Meeting", "MeetingId", "Meeting Number", "Identifiant", "Nº Identifiant", "ID"]
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
                    print(f"  INFO: Using '{prop_name}' for field '{logical_key}' (type match)")
                    break
        
        if found_property:
            mapping[logical_key] = found_property
            used_properties.add(found_property)
        else:
            print(f"  WARNING: Skipping field '{logical_key}': no matching property found (tried: {', '.join(alternatives)}, type: {expected_type})")
    
    return mapping


def main():
    """Main test function."""
    print("=" * 60)
    print("Notion Integration Test")
    print("=" * 60)
    
    # Step 1: Load environment variables
    print("\n[1/6] Loading environment variables...")
    load_dotenv()
    
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    
    if not NOTION_API_KEY:
        print("ERROR: NOTION_API_KEY environment variable is not set")
        sys.exit(1)
    
    if not NOTION_DATABASE_ID:
        print("ERROR: NOTION_DATABASE_ID environment variable is not set")
        sys.exit(1)
    
    print("✓ Environment variables loaded")
    
    # Step 2: Validate environment variables
    print("\n[2/6] Validating environment variables...")
    
    if not validate_api_key(NOTION_API_KEY):
        print("ERROR: NOTION_API_KEY does not appear to be valid (should start with 'ntn_')")
        sys.exit(1)
    
    if not validate_database_id(NOTION_DATABASE_ID):
        print("ERROR: NOTION_DATABASE_ID is invalid (should be 32 hex characters)")
        sys.exit(1)
    
    print("✓ Environment variables validated")
    
    # Step 3: Initialize Notion Client
    print("\n[3/6] Initializing Notion client...")
    try:
        notion = Client(auth=NOTION_API_KEY)
        print("✓ Notion client initialized")
    except Exception as exc:
        print(f"ERROR: Failed to initialize Notion client: {exc}")
        sys.exit(1)
    
    # Step 4: Test database access
    print("\n[4/6] Testing database access...")
    database_schema = None
    try:
        # Try retrieving with explicit parameters
        # Note: Some Notion API versions may require explicit parameter passing
        database_schema = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        print("✓ Database access OK")
        
        # Debug: Check if it's a dict or an object with attributes
        print(f"  Schema type: {type(database_schema)}")
        if hasattr(database_schema, 'properties'):
            print("  Schema has 'properties' attribute (object access)")
            properties = database_schema.properties
        elif isinstance(database_schema, dict):
            properties = database_schema.get("properties", {})
        else:
            # Try to convert to dict
            try:
                database_schema_dict = dict(database_schema) if hasattr(database_schema, '__dict__') else database_schema
                properties = database_schema_dict.get("properties", {}) if isinstance(database_schema_dict, dict) else {}
            except:
                properties = {}
        
        # Extract title safely
        title_obj = database_schema.get('title', [])
        if title_obj and isinstance(title_obj, list) and len(title_obj) > 0:
            title_text = title_obj[0].get('plain_text', 'N/A')
        else:
            title_text = str(title_obj) if title_obj else 'N/A'
        print(f"  Database title: {title_text}")
        
        # Show available properties with their types
        # Properties should already be extracted above, but fallback here
        if 'properties' not in locals():
            if isinstance(database_schema, dict):
                properties = database_schema.get("properties", {})
            elif hasattr(database_schema, 'properties'):
                properties = database_schema.properties
            else:
                properties = {}
        
        # Debug: Print what we actually got
        print(f"  Available properties ({len(properties) if isinstance(properties, dict) else 0}):")
        if isinstance(properties, dict) and len(properties) > 0:
            print("  Properties found in schema:")
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get("type", "unknown") if isinstance(prop_info, dict) else "unknown"
                print(f"    - {prop_name} ({prop_type})")
        
        if len(properties) == 0:
            print("    ⚠️  WARNING: No properties found in database!")
            print("    Debugging info:")
            print(f"    - Full schema keys: {list(database_schema.keys())}")
            if "properties" in database_schema:
                print(f"    - Properties value type: {type(database_schema['properties'])}")
                print(f"    - Properties value: {database_schema['properties']}")
            else:
                print("    - 'properties' key not found in schema")
                print("    - Trying alternative access methods...")
                
                # Try to access properties through different paths
                if hasattr(database_schema, 'get'):
                    # Check if properties might be nested
                    for key in ['properties', 'schema', 'columns', 'fields']:
                        if key in database_schema:
                            print(f"    - Found '{key}': {type(database_schema[key])}")
                
                # Print a sample of the full response for debugging
                import json
                print("\n    Full API response (first 2000 chars):")
                response_str = json.dumps(database_schema, indent=2, default=str)
                print(response_str[:2000])
                if len(response_str) > 2000:
                    print("    ... (truncated)")
            
            print("\n    ⚠️  CRITICAL: The API response is missing the 'properties' key!")
            print("    This is unusual - even with proper sharing, properties should be visible.")
            print("\n    Possible causes:")
            print("    1. The database might be empty (no properties defined yet)")
            print("    2. There might be a delay in Notion's API synchronization")
            print("    3. The integration might need to be reconnected")
            print("\n    TROUBLESHOOTING STEPS:")
            print("\n    Step 1: Verify database has properties in Notion UI")
            print("    - Open 'Meeting Brain Integration' in Notion")
            print("    - Make sure you can see columns like 'Nom', 'Assignation', 'État', etc.")
            print("    - If you don't see any columns, add at least one property")
            print("\n    Step 2: Reconnect the integration")
            print("    - In Notion, click '...' menu → 'Connexions'")
            print("    - Find 'Meeting Brain Integration' and disconnect it")
            print("    - Wait 10 seconds, then reconnect it")
            print("    - Make sure all capabilities are checked")
            print("\n    Step 3: Check integration capabilities")
            print("    - Go to https://www.notion.so/my-integrations")
            print("    - Click on your integration")
            print("    - Verify it has: 'Read content', 'Insert content', 'Update content'")
            print("\n    Step 4: Try querying a page instead")
            print("    - If properties still don't appear, try creating a test page")
            print("    - The error message might reveal the actual property names")
        else:
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get("type", "unknown")
                print(f"    - {prop_name} ({prop_type})")
    except Exception as exc:
        error_msg = str(exc)
        if "403" in error_msg or "Forbidden" in error_msg:
            print("ERROR: Access denied (403). The database may not be shared with your integration.")
            print("  Make sure to share the database with your Notion integration in the database settings.")
        elif "404" in error_msg or "Not Found" in error_msg or "Could not find database" in error_msg:
            print("ERROR: Database not found or not shared with integration.")
            print(f"  Database ID used: {NOTION_DATABASE_ID}")
            print("\n  SOLUTION:")
            print("  1. Verify the database ID is correct:")
            print("     - Open your Notion database")
            print("     - Copy the URL from your browser")
            print("     - The ID is the 32-character hex string in the URL")
            print("     - Format: https://www.notion.so/[workspace]/[32-char-id]?v=...")
            print("     - Example: https://www.notion.so/abc123...def456 → abc123...def456")
            print("\n  2. Share the database with your integration:")
            print("     - Open the database in Notion")
            print("     - Click '...' (three dots) menu → 'Connexions' or 'Add connections'")
            print("     - Search for and select your integration")
            print("     - Make sure it has 'Read' and 'Update' permissions")
            print("\n  3. Verify the integration has access:")
            print("     - Go to https://www.notion.so/my-integrations")
            print("     - Click on your integration")
            print("     - Check 'Connected databases' section")
            print("     - Your database should be listed there")
        else:
            print(f"ERROR: Failed to retrieve database: {exc}")
        sys.exit(1)
    
    # Step 5: Create test page
    print("\n[5/6] Creating test page...")
    test_page_id = None
    
    # WORKAROUND: If properties are not in schema, try to discover them from existing pages
    properties = database_schema.get("properties", {})
    if len(properties) == 0:
        print("  ⚠️  Properties not found in schema. Trying to discover from existing pages...")
        
        try:
            # Try to query existing pages in the database
            print("  Querying existing pages in database...")
            # Use search method which works more reliably
            try:
                search_response = notion.search(
                    filter={"property": "object", "value": "page"},
                    page_size=10
                )
                all_results = search_response.get("results", [])
                # Filter to only pages in this database
                results = [
                    r for r in all_results 
                    if r.get("parent", {}).get("database_id") == NOTION_DATABASE_ID
                ]
                print(f"  Found {len(results)} page(s) in this database")
            except Exception as search_err:
                print(f"  Search failed: {search_err}")
                # Try databases.query as fallback (might not exist in this version)
                try:
                    pages_response = notion.databases.query(database_id=NOTION_DATABASE_ID, page_size=1)
                    results = pages_response.get("results", [])
                except (AttributeError, Exception) as query_err:
                    print(f"  Query also failed: {query_err}")
                    results = []
            
            print(f"  Found {len(results)} existing page(s)")
            
            if results and len(results) > 0:
                # Get properties from the first page
                first_page = results[0]
                print(f"  First page ID: {first_page.get('id', 'N/A')}")
                print(f"  First page keys: {list(first_page.keys())}")
                
                page_properties = first_page.get("properties", {})
                print(f"  Properties in page: {len(page_properties) if isinstance(page_properties, dict) else 0}")
                
                if page_properties and isinstance(page_properties, dict) and len(page_properties) > 0:
                    print(f"  ✓ Found {len(page_properties)} properties from existing pages:")
                    for prop_name, prop_info in page_properties.items():
                        prop_type = prop_info.get("type", "unknown") if isinstance(prop_info, dict) else "unknown"
                        print(f"    - {prop_name} ({prop_type})")
                    # Use these properties as the schema
                    properties = page_properties
                    database_schema["properties"] = properties
                    print(f"  ✓ Successfully extracted {len(properties)} properties from page!")
                else:
                    print("  ⚠️  No properties found in existing pages")
                    print(f"  Page properties type: {type(page_properties)}")
                    print(f"  Page properties value: {page_properties}")
                    print(f"  Full page structure (first 500 chars):")
                    import json
                    page_str = json.dumps(first_page, indent=2, default=str)
                    print(page_str[:500])
            else:
                print("  ⚠️  No existing pages found. Will try to create a test page...")
                # Fallback: try creating a page with common property names
                try:
                    response = notion.pages.create(
                        parent={"database_id": NOTION_DATABASE_ID},
                        properties={
                            "Name": {
                                "title": [{"text": {"content": "Test Discovery"}}]
                            }
                        }
                    )
                    test_page_id = response.get("id")
                    page_data = notion.pages.retrieve(page_id=test_page_id)
                    page_properties = page_data.get("properties", {})
                    if page_properties:
                        properties = page_properties
                        database_schema["properties"] = properties
                        print(f"  ✓ Discovered {len(properties)} properties from test page")
                except Exception as create_error:
                    error_msg = str(create_error)
                    print(f"  Error: {error_msg}")
                    # The error message might contain property names
                    if "property" in error_msg.lower() and "does not exist" in error_msg.lower():
                        print("  The error suggests properties exist but with different names.")
                        print("  Please check your Notion database and verify property names.")
                        
        except Exception as query_error:
            print(f"  Error querying pages: {query_error}")
            print("  Will attempt to create page anyway and see what happens...")
    
    print("  Resolving property mappings...")
    try:
        # Resolve property mappings dynamically (with flexible matching)
        property_mapping = resolve_properties_mapping(database_schema, flexible=True)
        
        if not property_mapping:
            print("\n⚠️  No matching properties found via mapping.")
            print("  Using known property names from your Notion database (discovered via MCP):")
            print("    - Title (title)")
            print("    - Status (status)")
            print("    - Owner (person)")
            print("    - Due Date (date)")
            print("    - Meeting ID (number)")
            print("    - Created at (created_time)")
            print("    - Texte (text)")
            print("\n  Creating page with these exact property names...")
            
            # Create a minimal property mapping using known names
            property_mapping = {
                "task": "Title",
                "status": "Status",
                "meeting_id": "Meeting ID",
                "due_date": "Due Date"
            }
            
            # Also add properties to schema for consistency
            if "properties" not in database_schema:
                database_schema["properties"] = {
                    "Title": {"type": "title"},
                    "Status": {"type": "status"},
                    "Owner": {"type": "people"},
                    "Due Date": {"type": "date"},
                    "Meeting ID": {"type": "number"},
                    "Created at": {"type": "created_time"},
                    "Texte": {"type": "text"}
                }
        
        print(f"  Found {len(property_mapping)} matching properties:")
        for logical_key, prop_name in property_mapping.items():
            print(f"    - {logical_key} -> {prop_name}")
        
        # Get current date in YYYY-MM-DD format
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Build properties for the test page using resolved mapping
        properties: Dict[str, Any] = {}
        
        # Task (title)
        if "task" in property_mapping:
            prop_name = property_mapping["task"]
            properties[prop_name] = {
                "title": [
                    {
                        "text": {
                            "content": "Test connection from Meeting Brain"
                        }
                    }
                ]
            }
        
        # Owner (rich_text)
        if "owner" in property_mapping:
            prop_name = property_mapping["owner"]
            properties[prop_name] = {
                "rich_text": [
                    {
                        "text": {
                            "content": "System"
                        }
                    }
                ]
            }
        
        # Status (select)
        if "status" in property_mapping:
            prop_name = property_mapping["status"]
            properties[prop_name] = {
                "select": {
                    "name": "open"
                }
            }
        
        # Meeting ID (number)
        if "meeting_id" in property_mapping:
            prop_name = property_mapping["meeting_id"]
            properties[prop_name] = {
                "number": 0
            }
        
        # Created at (date)
        if "created_at" in property_mapping:
            prop_name = property_mapping["created_at"]
            properties[prop_name] = {
                "date": {
                    "start": current_date
                }
            }
        
        # Check if we have at least one property
        if not properties:
            print("ERROR: No valid properties found to create test page.")
            sys.exit(1)
        
        # Create the page
        response = notion.pages.create(
            parent={
                "database_id": NOTION_DATABASE_ID
            },
            properties=properties
        )
        
        test_page_id = response.get("id")
        
        if not test_page_id:
            print("ERROR: Created page but no page ID returned")
            sys.exit(1)
        
        print(f"✓ Page successfully created: {test_page_id}")
        
    except Exception as exc:
        error_msg = str(exc)
        if "property" in error_msg.lower() and "does not exist" in error_msg.lower():
            print("ERROR: Database structure incompatible. One or more properties are missing.")
            print(f"  Details: {exc}")
            print("  Please check that your database has compatible properties.")
        elif "403" in error_msg or "Forbidden" in error_msg:
            print("ERROR: Access denied (403). Check integration permissions.")
        else:
            print(f"ERROR: Failed to create test page: {exc}")
        sys.exit(1)
    
    # Step 6: Cleanup - Archive the test page
    print("\n[6/6] Cleaning up test page...")
    try:
        if test_page_id:
            notion.pages.update(
                page_id=test_page_id,
                archived=True
            )
            print("✓ Cleanup complete (page archived).")
    except Exception as exc:
        print(f"WARNING: Failed to archive test page: {exc}")
        print(f"  You may need to manually delete page: {test_page_id}")
    
    # Final success message
    print("\n" + "=" * 60)
    print("✓ All tests passed! Notion integration is working correctly.")
    print("=" * 60)


if __name__ == "__main__":
    main()

