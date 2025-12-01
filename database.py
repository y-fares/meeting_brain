"""
Database layer for Meeting Brain - Sprint 2 Feature 5 (SQLite + SQLAlchemy).

This module defines:
    - SQLAlchemy engine and session factory
    - Declarative ORM models: Meeting, Todo, Decision, Participant
    - Helper functions to insert meetings, decisions, todos, and participants

The database is a local SQLite file: meeting_brain.db
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy setup
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Base class for all ORM models."""


DATABASE_URL = "sqlite:///meeting_brain.db"

# echo=True can help debugging SQL; keep False for production
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Session factory to be used in the Streamlit app
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class Meeting(Base):
    """
    ORM model for the `meetings` table.

    Attributes:
        id: Primary key.
        date: Date and time of the meeting (optional).
        title: Optional title of the meeting.
        raw_text: Original meeting notes (required).
        summary: Generated summary of the meeting (optional).
    """

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    todos: Mapped[List["Todo"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    decisions: Mapped[List["Decision"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    participants: Mapped[List["Participant"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Meeting id={self.id!r} title={self.title!r} date={self.date!r}>"


class Todo(Base):
    """
    ORM model for the `todos` table.

    Attributes:
        id: Primary key.
        meeting_id: Foreign key referencing meetings.id.
        task: Short description of the action.
        owner: Name of the responsible person (optional).
        due_date: Due date as string (e.g., 'YYYY-MM-DD') or None.
        status: Status of the task (default 'open').
    """

    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id"), nullable=False, index=True
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")

    meeting: Mapped[Meeting] = relationship(back_populates="todos")

    def __repr__(self) -> str:
        return (
            f"<Todo id={self.id!r} meeting_id={self.meeting_id!r} "
            f"task={self.task!r} owner={self.owner!r} status={self.status!r}>"
        )


class Decision(Base):
    """
    ORM model for the `decisions` table.

    Attributes:
        id: Primary key.
        meeting_id: Foreign key referencing meetings.id.
        text: The decision text (required).
    """

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="decisions")

    def __repr__(self) -> str:
        return f"<Decision id={self.id!r} meeting_id={self.meeting_id!r}>"


class Participant(Base):
    """
    ORM model for the `participants` table.

    Attributes:
        id: Primary key.
        meeting_id: Foreign key referencing meetings.id.
        name: Participant name (required).
    """

    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meetings.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="participants")

    def __repr__(self) -> str:
        return f"<Participant id={self.id!r} meeting_id={self.meeting_id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------


def init_db() -> None:
    """
    Initialize the database schema.

    This function should be called once at application startup to ensure
    all tables are created.
    """
    try:
        Base.metadata.create_all(bind=engine)
        LOGGER.info("Database initialized (tables created if missing).")
    except SQLAlchemyError as exc:
        LOGGER.exception("Error while initializing the database: %s", exc)


# ---------------------------------------------------------------------------
# Helper functions for data insertion
# ---------------------------------------------------------------------------


def create_meeting(
    session: Session,
    raw_text: str,
    summary: Optional[str],
    title: Optional[str] = None,
    date: Optional[datetime] = None,
) -> Optional[Meeting]:
    """
    Create and persist a new Meeting row.

    Args:
        session: An active SQLAlchemy Session.
        raw_text: Original meeting notes (required).
        summary: Summary of the meeting (can be None).
        title: Optional meeting title.
        date: Optional meeting datetime.

    Returns:
        The created Meeting instance, or None if an error occurred.
    """
    meeting = Meeting(
        raw_text=raw_text,
        summary=summary,
        title=title,
        date=date,
    )
    try:
        session.add(meeting)
        session.commit()
        session.refresh(meeting)
        return meeting
    except SQLAlchemyError as exc:
        session.rollback()
        LOGGER.exception("Failed to create meeting: %s", exc)
        return None


def add_decisions(
    session: Session,
    meeting_id: int,
    decisions: Iterable[str],
) -> None:
    """
    Add one or more decisions to a given meeting.

    Args:
        session: An active SQLAlchemy Session.
        meeting_id: ID of the related Meeting.
        decisions: Iterable of decision text strings.
    """
    if not decisions:
        return

    try:
        objects = [Decision(meeting_id=meeting_id, text=txt) for txt in decisions if txt]
        if not objects:
            return
        session.add_all(objects)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        LOGGER.exception("Failed to add decisions for meeting %s: %s", meeting_id, exc)


def add_todos(
    session: Session,
    meeting_id: int,
    todos: Iterable[dict],
) -> None:
    """
    Add one or more TODO items to a given meeting.

    Each todo dict is expected to have keys:
        - "task": str (required)
        - "owner": str (optional)
        - "due_date": str (optional, e.g. 'YYYY-MM-DD')

    Args:
        session: An active SQLAlchemy Session.
        meeting_id: ID of the related Meeting.
        todos: Iterable of todo dictionaries.
    """
    if not todos:
        return

    todo_objects: List[Todo] = []
    for t in todos:
        task = (t.get("task") or "").strip()
        if not task:
            continue
        owner = (t.get("owner") or "").strip() or None
        due_date = (t.get("due_date") or "").strip() or None
        todo_objects.append(
            Todo(
                meeting_id=meeting_id,
                task=task,
                owner=owner,
                due_date=due_date,
                status="open",
            )
        )

    if not todo_objects:
        return

    try:
        session.add_all(todo_objects)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        LOGGER.exception("Failed to add todos for meeting %s: %s", meeting_id, exc)


def add_participants(
    session: Session,
    meeting_id: int,
    participants: Iterable[str],
) -> None:
    """
    Add participants to a given meeting.

    Args:
        session: An active SQLAlchemy Session.
        meeting_id: ID of the related Meeting.
        participants: Iterable of participant names.
    """
    if not participants:
        return

    objects = [
        Participant(meeting_id=meeting_id, name=name.strip())
        for name in participants
        if name and name.strip()
    ]
    if not objects:
        return

    try:
        session.add_all(objects)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        LOGGER.exception(
            "Failed to add participants for meeting %s: %s", meeting_id, exc
        )


# ---------------------------------------------------------------------------
# Optional demo usage
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize schema
    init_db()

    # Create a demo meeting with one decision, one todo, one participant
    with SessionLocal() as session:
        demo_meeting = create_meeting(
            session=session,
            raw_text="Demo meeting about Sprint 2 Feature 5.",
            summary="We discussed the new database feature and its implementation.",
            title="Sprint 2 - DB Feature Kickoff",
            date=datetime.utcnow(),
        )

        if demo_meeting is None:
            print("Failed to create demo meeting.")
        else:
            add_decisions(
                session,
                meeting_id=demo_meeting.id,
                decisions=["Use SQLite + SQLAlchemy for local persistence."],
            )
            add_todos(
                session,
                meeting_id=demo_meeting.id,
                todos=[
                    {
                        "task": "Implement database.py with models and helpers.",
                        "owner": "Yacine",
                        "due_date": "",
                    }
                ],
            )
            add_participants(
                session,
                meeting_id=demo_meeting.id,
                participants=["Yacine"],
            )

            # Reload and print everything for verification
            m = session.get(Meeting, demo_meeting.id)
            print("Created meeting:", m)
            print("Decisions:", m.decisions if m else None)
            print("Todos:", m.todos if m else None)
            print("Participants:", m.participants if m else None)


