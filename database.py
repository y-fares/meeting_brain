"""
Database models and helpers for Meeting Brain.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from typing import List, Optional

# Setup logging
LOGGER = logging.getLogger(__name__)

# Database setup
Base = declarative_base()
engine = create_engine("sqlite:///meeting_brain.db", echo=False)
SessionLocal = sessionmaker(bind=engine)


def create_session() -> Session:
    """Create a new database session."""
    return SessionLocal()


class Meeting(Base):
    """Meeting model."""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    title = Column(String, nullable=True)
    
    # Relationships
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    todos = relationship("Todo", back_populates="meeting", cascade="all, delete-orphan")
    participants = relationship("Participant", back_populates="meeting", cascade="all, delete-orphan")


class Decision(Base):
    """Decision model."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    text = Column(Text, nullable=False)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="decisions")


class Participant(Base):
    """Participant model."""
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    name = Column(String, nullable=False)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="participants")


class Todo(Base):
    """Todo model."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    task = Column(Text, nullable=False)
    owner = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    trello_card_id = Column(String, nullable=True)
    notion_page_id = Column(String, nullable=True)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="todos")


class TodoEvent(Base):
    """TodoEvent model for audit trail of status changes."""
    __tablename__ = "todo_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    todo_id = Column(Integer, ForeignKey("todos.id"), nullable=False, index=True)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    source = Column(String, nullable=False, default="unknown")
    note = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship to Todo
    todo = relationship("Todo", backref="events")


def ensure_schema() -> None:
    """
    Ensure required tables exist for the current version of the app.
    For SQLite, create missing tables if they don't exist.
    Also handles schema migrations for existing tables.
    This must be idempotent.
    """
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Migrate existing tables if needed
    _migrate_todos_table()


def _migrate_todos_table() -> None:
    """
    Migrate the todos table to add missing columns.
    This handles schema changes for existing databases.
    """
    try:
        inspector = inspect(engine)
        
        # Check if todos table exists
        if not inspector.has_table("todos"):
            return
        
        # Get existing columns
        existing_columns = [col["name"] for col in inspector.get_columns("todos")]
        
        # Add trello_card_id if missing
        if "trello_card_id" not in existing_columns:
            LOGGER.info("Adding missing column 'trello_card_id' to todos table")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE todos ADD COLUMN trello_card_id TEXT"))
                conn.commit()
            LOGGER.info("Successfully added 'trello_card_id' column to todos table")
        
        # Add notion_page_id if missing
        if "notion_page_id" not in existing_columns:
            LOGGER.info("Adding missing column 'notion_page_id' to todos table")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE todos ADD COLUMN notion_page_id TEXT"))
                conn.commit()
            LOGGER.info("Successfully added 'notion_page_id' column to todos table")
        
    except Exception as exc:
        LOGGER.exception("Error while migrating todos table: %s", exc)
        # Don't raise - allow app to continue even if migration fails


def log_todo_event(
    session: Session,
    todo_id: int,
    old_status: Optional[str],
    new_status: str,
    source: str = "unknown",
    note: Optional[str] = None,
) -> Optional["TodoEvent"]:
    """
    Create a TodoEvent row recording a status transition.
    Must commit or flush safely, without breaking the caller flow.
    
    Returns:
        TodoEvent instance if successful, None on error
    """
    try:
        event = TodoEvent(
            todo_id=todo_id,
            old_status=old_status,
            new_status=new_status,
            source=source,
            note=note,
            created_at=datetime.utcnow()
        )
        session.add(event)
        session.flush()  # Flush to get event.id, but don't commit yet (caller commits)
        return event
    except Exception as exc:
        LOGGER.exception("Error while logging todo event: %s", exc)
        return None


def update_todo_status(
    session: Session,
    todo_id: int,
    new_status: str,
    source: str,
    note: Optional[str] = None,
) -> None:
    """
    Update a TODO's status and log the event.
    Handles timestamp updates based on status.
    
    Args:
        session: SQLAlchemy session
        todo_id: ID of the todo to update
        new_status: New status value
        source: Source of the change (e.g., "ui", "notion_sync")
        note: Optional note about the change
    """
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if not todo:
            LOGGER.warning("Todo with id %d not found", todo_id)
            return
        
        old_status = todo.status
        
        # Only update if status actually changed
        if old_status != new_status:
            todo.status = new_status
            
            # Update timestamps based on status
            # Consider in_progress strings
            if new_status in ["in_progress", "in progress"]:
                if todo.acknowledged_at is None:
                    todo.acknowledged_at = datetime.utcnow()
            
            # Consider done/completed strings
            if new_status in ["done", "completed"]:
                if todo.completed_at is None:
                    todo.completed_at = datetime.utcnow()
            
            # Log the event
            log_todo_event(
                session=session,
                todo_id=todo_id,
                old_status=old_status,
                new_status=new_status,
                source=source,
                note=note
            )
            
            session.commit()
            LOGGER.info(
                "Updated Todo %d status from '%s' to '%s' (source: %s)",
                todo_id, old_status, new_status, source
            )
        else:
            # Status unchanged, no event logged
            LOGGER.debug("Todo %d status unchanged (%s), skipping event", todo_id, new_status)
    
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while updating todo status: %s", exc)


def acknowledge_todo(session: Session, todo_id: int) -> None:
    """Mark a TODO as acknowledged (in progress)."""
    update_todo_status(
        session=session,
        todo_id=todo_id,
        new_status="in_progress",
        source="ui",
        note="Marked acknowledged in UI"
    )


def complete_todo(session: Session, todo_id: int) -> None:
    """Mark a TODO as completed."""
    update_todo_status(
        session=session,
        todo_id=todo_id,
        new_status="completed",
        source="ui",
        note="Marked done in UI"
    )


def set_trello_card_id(session: Session, todo_id: int, card_id: str) -> None:
    """
    Store the Trello card id for a given TODO.

    - Finds the Todo by id
    - Sets trello_card_id
    - Commits the session
    - On error: rollback and log
    """
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if todo:
            todo.trello_card_id = card_id
            session.commit()
        else:
            LOGGER.warning("Todo with id %d not found", todo_id)
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while setting trello_card_id: %s", exc)


def set_notion_page_id(session: Session, todo_id: int, page_id: str) -> None:
    """
    Store the Notion page id for a given TODO.

    - Finds the Todo by id
    - Sets notion_page_id
    - Commits the session
    - On error: rollback and log
    """
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if todo:
            todo.notion_page_id = page_id
            session.commit()
        else:
            LOGGER.warning("Todo with id %d not found", todo_id)
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while setting notion_page_id: %s", exc)


def create_meeting(session: Session, raw_text: str, summary: str, title: Optional[str], date: Optional[datetime]) -> int:
    """Create a new meeting."""
    try:
        meeting = Meeting(
            raw_text=raw_text,
            summary=summary,
            title=title,
            date=date
        )
        session.add(meeting)
        session.commit()
        session.refresh(meeting)
        LOGGER.info("Created meeting with id %d", meeting.id)
        return meeting.id
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while creating meeting: %s", exc)
        raise


def add_decisions(session: Session, meeting_id: int, decisions: List[str]) -> None:
    """Add decisions to a meeting."""
    try:
        for decision_text in decisions:
            decision = Decision(
                meeting_id=meeting_id,
                text=decision_text
            )
            session.add(decision)
        session.commit()
        LOGGER.info("Added %d decisions to meeting %d", len(decisions), meeting_id)
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while adding decisions: %s", exc)
        raise


def add_todos(session: Session, meeting_id: int, todos: List[dict]) -> None:
    """Add todos to a meeting."""
    try:
        for todo_data in todos:
            todo = Todo(
                meeting_id=meeting_id,
                task=todo_data.get("task", ""),
                owner=todo_data.get("owner"),
                due_date=todo_data.get("due_date"),
                status="pending",
                created_at=datetime.utcnow()
            )
            session.add(todo)
        session.commit()
        LOGGER.info("Added %d todos to meeting %d", len(todos), meeting_id)
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while adding todos: %s", exc)
        raise


def add_participants(session: Session, meeting_id: int, participants: List[str]) -> None:
    """Add participants to a meeting."""
    try:
        for participant_name in participants:
            participant = Participant(
                meeting_id=meeting_id,
                name=participant_name
            )
            session.add(participant)
        session.commit()
        LOGGER.info("Added %d participants to meeting %d", len(participants), meeting_id)
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while adding participants: %s", exc)
        raise


def log_todo_event(
    session: Session,
    todo_id: int,
    old_status: Optional[str],
    new_status: str,
    source: str = "unknown",
    note: Optional[str] = None,
) -> Optional["TodoEvent"]:
    """
    Create a TodoEvent row recording a status transition.
    Must commit or flush safely, without breaking the caller flow.
    
    Returns:
        TodoEvent instance if successful, None on error
    """
    try:
        event = TodoEvent(
            todo_id=todo_id,
            old_status=old_status,
            new_status=new_status,
            source=source,
            note=note,
            created_at=datetime.utcnow()
        )
        session.add(event)
        session.flush()  # Flush to get event.id, but don't commit yet (caller commits)
        return event
    except Exception as exc:
        LOGGER.exception("Error while logging todo event: %s", exc)
        return None


def update_todo_status(
    session: Session,
    todo_id: int,
    new_status: str,
    source: str,
    note: Optional[str] = None,
) -> None:
    """
    Update a TODO's status and log the event.
    Handles timestamp updates based on status.
    
    Args:
        session: SQLAlchemy session
        todo_id: ID of the todo to update
        new_status: New status value
        source: Source of the change (e.g., "ui", "notion_sync")
        note: Optional note about the change
    """
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if not todo:
            LOGGER.warning("Todo with id %d not found", todo_id)
            return
        
        old_status = todo.status
        
        # Only update if status actually changed
        if old_status != new_status:
            todo.status = new_status
            
            # Update timestamps based on status
            # Consider in_progress strings
            if new_status in ["in_progress", "in progress"]:
                if todo.acknowledged_at is None:
                    todo.acknowledged_at = datetime.utcnow()
            
            # Consider done/completed strings
            if new_status in ["done", "completed"]:
                if todo.completed_at is None:
                    todo.completed_at = datetime.utcnow()
            
            # Log the event
            log_todo_event(
                session=session,
                todo_id=todo_id,
                old_status=old_status,
                new_status=new_status,
                source=source,
                note=note
            )
            
            session.commit()
            LOGGER.info(
                "Updated Todo %d status from '%s' to '%s' (source: %s)",
                todo_id, old_status, new_status, source
            )
        else:
            # Status unchanged, no event logged
            LOGGER.debug("Todo %d status unchanged (%s), skipping event", todo_id, new_status)
    
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while updating todo status: %s", exc)


# Create tables
ensure_schema()

