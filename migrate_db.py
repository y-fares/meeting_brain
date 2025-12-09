"""
Migration script to add missing columns to existing database.

Run this script once to update your database schema:
    python migrate_db.py
"""

import logging
from sqlalchemy import create_engine, inspect, text

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

engine = create_engine("sqlite:///meeting_brain.db", echo=False)

def migrate_database() -> None:
    """Add missing columns to existing database tables."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "meetings" in tables:
            # Check if title column exists
            columns = [col["name"] for col in inspector.get_columns("meetings")]
            
            if "title" not in columns:
                LOGGER.info("Adding 'title' column to meetings table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE meetings ADD COLUMN title VARCHAR"))
                    conn.commit()
                LOGGER.info("✓ Migration completed: added 'title' column")
            else:
                LOGGER.info("✓ Column 'title' already exists in meetings table")
        else:
            LOGGER.info("Table 'meetings' does not exist yet. It will be created on next app start.")
    
    except Exception as exc:
        LOGGER.exception("Error during database migration: %s", exc)
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration Script")
    print("=" * 60)
    print()
    migrate_database()
    print()
    print("Migration completed!")

