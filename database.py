"""
Database models and helpers for Meeting Brain.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

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
    date = Column(String, nullable=False)
    summary = Column(String, nullable=True)
    raw_text = Column(String, nullable=True)


class Decision(Base):
    """Decision model."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    text = Column(String, nullable=False)


class Participant(Base):
    """Participant model."""
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    name = Column(String, nullable=False)


class Todo(Base):
    """Todo model."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    task = Column(String, nullable=False)
    owner = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    trello_card_id = Column(String, nullable=True)


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


# Create tables
Base.metadata.create_all(engine)

