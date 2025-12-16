"""
Demo dataset loader service.
Loads sample meetings and seeds the database.
"""

import os
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from database import (
    create_meeting,
    add_decisions,
    add_todos,
    add_participants,
    Meeting,
    Todo,
    Decision,
    Participant,
    TodoEvent,
)
from services.text_pipeline import preprocess_text, extract_participants_from_raw

LOGGER = logging.getLogger(__name__)

# Path to sample data directory
SAMPLE_DATA_DIR = Path(__file__).parent.parent / "sample_data"

# Demo tag prefix for meetings
DEMO_TAG_PREFIX = "[DEMO]"


def load_demo_files() -> List[Dict[str, Any]]:
    """
    Load demo meeting files from sample_data directory.
    
    Returns:
        List of dicts with keys: title, date, raw_text
    """
    demo_files = [
        ("meeting_01_codir_produit.txt", datetime(2025, 2, 12, 10, 0), "Comité de Direction Produit"),
        ("meeting_02_comite_rh.txt", datetime(2025, 2, 6, 14, 0), "Comité RH"),
        ("meeting_03_revue_it_cloud.txt", datetime(2025, 2, 4, 9, 0), "Revue Projet IT Cloud"),
        ("meeting_04_comite_secu_infra.txt", datetime(2025, 2, 10, 15, 0), "Comité Sécurité Infrastructure"),
    ]
    
    meetings = []
    
    for filename, date, title in demo_files:
        filepath = SAMPLE_DATA_DIR / filename
        if not filepath.exists():
            LOGGER.warning("Demo file not found: %s", filepath)
            continue
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
            
            meetings.append({
                "title": f"{DEMO_TAG_PREFIX} {title}",
                "date": date,
                "raw_text": raw_text,
            })
        except Exception as exc:
            LOGGER.exception("Error loading demo file %s: %s", filename, exc)
    
    return meetings


def _compute_text_hash(text: str) -> str:
    """Compute a hash of text for duplicate detection."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _meeting_exists(session: Session, title: str, raw_text: str) -> bool:
    """
    Check if a meeting with the same title or raw_text hash already exists.
    
    Args:
        session: Database session
        title: Meeting title
        raw_text: Raw meeting text
    
    Returns:
        True if meeting exists, False otherwise
    """
    # Check by title
    existing = session.query(Meeting).filter_by(title=title).first()
    if existing:
        return True
    
    # Check by raw_text hash (store hash in a comment or check exact match)
    text_hash = _compute_text_hash(raw_text)
    # Simple check: if raw_text matches exactly
    existing = session.query(Meeting).filter_by(raw_text=raw_text).first()
    if existing:
        return True
    
    return False


def seed_demo_dataset(
    session: Session,
    generate_summary_func,
    extract_decisions_func,
    extract_todos_func,
) -> Dict[str, int]:
    """
    Seed the database with demo dataset.
    
    Args:
        session: Database session
        generate_summary_func: Function to generate summary (from app.py or mocked)
        extract_decisions_func: Function to extract decisions (from app.py or mocked)
        extract_todos_func: Function to extract todos (from app.py or mocked)
    
    Returns:
        Dictionary with counts: meetings_created, todos_created, decisions_created, participants_created
    """
    result = {
        "meetings_created": 0,
        "todos_created": 0,
        "decisions_created": 0,
        "participants_created": 0,
    }
    
    try:
        demo_meetings = load_demo_files()
        
        for meeting_data in demo_meetings:
            title = meeting_data["title"]
            date = meeting_data["date"]
            raw_text = meeting_data["raw_text"]
            
            # Check if already exists
            if _meeting_exists(session, title, raw_text):
                LOGGER.info("Demo meeting already exists, skipping: %s", title)
                continue
            
            try:
                # Preprocess text
                preprocessed = preprocess_text(raw_text)
                clean_text = preprocessed["clean_text"]
                
                # Extract data using provided functions
                summary = generate_summary_func(clean_text)
                decisions = extract_decisions_func(clean_text)
                todos = extract_todos_func(clean_text)
                participants = extract_participants_from_raw(raw_text)
                
                # Create meeting
                meeting_id = create_meeting(
                    session=session,
                    raw_text=raw_text,
                    summary=summary,
                    title=title,
                    date=date
                )
                result["meetings_created"] += 1
                
                # Add decisions
                if decisions:
                    add_decisions(session, meeting_id, decisions)
                    result["decisions_created"] += len(decisions)
                
                # Add todos
                if todos:
                    add_todos(session, meeting_id, todos)
                    result["todos_created"] += len(todos)
                    
                    # Also extract participants from todos owners
                    todo_owners = [t.get("owner", "") for t in todos if t.get("owner")]
                    participants.extend(todo_owners)
                
                # Add participants (deduplicate)
                if participants:
                    unique_participants = list(set([p.strip() for p in participants if p.strip()]))
                    if unique_participants:
                        add_participants(session, meeting_id, unique_participants)
                        result["participants_created"] += len(unique_participants)
                
                LOGGER.info("Created demo meeting: %s (ID: %d)", title, meeting_id)
                
            except Exception as exc:
                LOGGER.exception("Error processing demo meeting %s: %s", title, exc)
                session.rollback()
                continue
        
        session.commit()
        LOGGER.info("Demo dataset seeding completed: %s", result)
        
    except Exception as exc:
        LOGGER.exception("Error seeding demo dataset: %s", exc)
        session.rollback()
    
    return result


def reset_database(session: Session) -> None:
    """
    Reset database by deleting all rows (DEV-only).
    
    Deletes in correct order to respect foreign key constraints:
    TodoEvent -> Todo -> Decision -> Participant -> Meeting
    
    Args:
        session: Database session
    
    WARNING: This permanently deletes all data. Must be called with explicit confirmation.
    """
    try:
        # Delete in correct order to respect foreign keys
        deleted_counts = {}
        
        # Delete TodoEvent (if table exists)
        try:
            deleted_counts["todo_events"] = session.query(TodoEvent).delete()
        except Exception:
            # Table might not exist in older DBs
            pass
        
        # Delete Todo
        deleted_counts["todos"] = session.query(Todo).delete()
        
        # Delete Decision
        deleted_counts["decisions"] = session.query(Decision).delete()
        
        # Delete Participant
        deleted_counts["participants"] = session.query(Participant).delete()
        
        # Delete Meeting (last, as it's referenced by others)
        deleted_counts["meetings"] = session.query(Meeting).delete()
        
        session.commit()
        
        LOGGER.warning("Database reset completed. Deleted: %s", deleted_counts)
        
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error resetting database: %s", exc)
        raise

