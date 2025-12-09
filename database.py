"""
Database models and helpers for Meeting Brain.
"""

import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Setup logging
LOGGER = logging.getLogger(__name__)

# Database setup
engine = create_engine("sqlite:///meeting_brain.db", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_database() -> None:
    """
    Migrate the database schema to add missing columns.
    Handles schema changes for existing databases.
    """
    try:
        from sqlalchemy import inspect, text
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "meetings" in tables:
            # Check if title column exists
            columns = [col["name"] for col in inspector.get_columns("meetings")]
            
            if "title" not in columns:
                LOGGER.info("Adding 'title' column to meetings table")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE meetings ADD COLUMN title VARCHAR"))
                    conn.commit()
                LOGGER.info("Migration completed: added 'title' column")
    except Exception as exc:
        LOGGER.exception("Error during database migration: %s", exc)
        # Don't raise - allow app to continue even if migration fails


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Also runs migrations for existing databases.
    """
    try:
        Base.metadata.create_all(engine)
        migrate_database()  # Run migrations after creating tables
        LOGGER.info("Database initialized successfully")
    except Exception as exc:
        LOGGER.exception("Error while initializing database: %s", exc)
        raise


def create_session() -> Session:
    """
    Create a new database session.
    
    Returns:
        A new SQLAlchemy session
    """
    return SessionLocal()


class Meeting(Base):
    """Meeting model."""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    title = Column(String, nullable=True)
    date = Column(DateTime, nullable=True)
    
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


class Todo(Base):
    """Todo model."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    task = Column(Text, nullable=False)
    owner = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    status = Column(String, nullable=False, default="open")  # open | in_progress | done
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    trello_card_id = Column(String, nullable=True)
    notion_page_id = Column(String, nullable=True)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="todos")


class Participant(Base):
    """Participant model."""
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    name = Column(String, nullable=False)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="participants")


def create_meeting(session: Session, raw_text: str, summary: str, title: Optional[str], date: Optional[datetime]) -> int:
    """
    Create a new meeting.
    
    Args:
        session: Database session
        raw_text: Raw text of the meeting
        summary: Summary of the meeting
        title: Title of the meeting (optional)
        date: Date of the meeting (optional)
    
    Returns:
        The ID of the created meeting
    
    Raises:
        Exception: If meeting creation fails
    """
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
    """
    Add decisions to a meeting.
    
    Args:
        session: Database session
        meeting_id: ID of the meeting
        decisions: List of decision texts
    
    Raises:
        Exception: If adding decisions fails
    """
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
    """
    Add todos to a meeting.
    
    Args:
        session: Database session
        meeting_id: ID of the meeting
        todos: List of todo dictionaries with keys: task, owner (optional), due_date (optional)
    
    Raises:
        Exception: If adding todos fails
    """
    try:
        for todo_data in todos:
            todo = Todo(
                meeting_id=meeting_id,
                task=todo_data.get("task", ""),
                owner=todo_data.get("owner"),
                due_date=todo_data.get("due_date"),
                status="open",
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
    """
    Add participants to a meeting.
    
    Args:
        session: Database session
        meeting_id: ID of the meeting
        participants: List of participant names
    
    Raises:
        Exception: If adding participants fails
    """
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


def acknowledge_todo(session: Session, todo_id: int) -> None:
    """
    Mark a TODO as acknowledged (in progress).
    
    Args:
        session: Database session
        todo_id: ID of the todo to acknowledge
    
    Raises:
        Exception: If acknowledging todo fails
    """
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if todo:
            todo.status = "in_progress"
            todo.acknowledged_at = datetime.utcnow()
            session.commit()
            LOGGER.info("Acknowledged todo %d", todo_id)
        else:
            LOGGER.warning("Todo with id %d not found", todo_id)
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while acknowledging todo: %s", exc)
        raise


def complete_todo(session: Session, todo_id: int) -> None:
    """
    Mark a TODO as completed.
    
    Args:
        session: Database session
        todo_id: ID of the todo to complete
    
    Raises:
        Exception: If completing todo fails
    """
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if todo:
            todo.status = "done"
            todo.completed_at = datetime.utcnow()
            session.commit()
            LOGGER.info("Completed todo %d", todo_id)
        else:
            LOGGER.warning("Todo with id %d not found", todo_id)
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while completing todo: %s", exc)
        raise


def set_trello_card_id(session: Session, todo_id: int, card_id: str) -> None:
    """
    Store the Trello card id for a given TODO.
    
    - Finds the Todo by id
    - Sets trello_card_id
    - Commits the session
    - On error: rollback and log
    
    Args:
        session: Database session
        todo_id: ID of the todo
        card_id: Trello card ID to store
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
    
    - Find the Todo by id
    - Set notion_page_id
    - Commit the session
    - On error: rollback and log the exception
    
    Args:
        session: Database session
        todo_id: ID of the todo
        page_id: Notion page ID to store
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


# Initialize database on import
# This will create tables if they don't exist and run migrations
try:
    init_db()
except Exception as exc:
    # If init fails, try to run migrations anyway
    LOGGER.warning("Database initialization had issues, attempting migration: %s", exc)
    try:
        migrate_database()
    except Exception:
        pass  # Ignore migration errors on import
