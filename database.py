"""
Database models and helpers for Meeting Brain.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
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


def acknowledge_todo(session: Session, todo_id: int) -> None:
    """Mark a TODO as acknowledged (in progress)."""
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if todo:
            todo.status = "in_progress"
            todo.acknowledged_at = datetime.utcnow()
            session.commit()
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while acknowledging todo: %s", exc)


def complete_todo(session: Session, todo_id: int) -> None:
    """Mark a TODO as completed."""
    try:
        todo = session.query(Todo).filter_by(id=todo_id).first()
        if todo:
            todo.status = "completed"
            todo.completed_at = datetime.utcnow()
            session.commit()
    except Exception as exc:
        session.rollback()
        LOGGER.exception("Error while completing todo: %s", exc)


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


# Create tables
Base.metadata.create_all(engine)

