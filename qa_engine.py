"""
Q&A engine for Meeting Brain.
Provides functions to answer questions about meetings, decisions, and TODOs using LLM providers.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Meeting, Todo, Decision
from llm_providers import llm_generate

# Setup logging
LOGGER = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def build_qa_context(session: Session, question: str) -> Dict[str, Any]:
    """
    Query the database and build a structured context used to answer the question.
    
    Args:
        session: SQLAlchemy session
        question: User's question string
        
    Returns:
        Dictionary with structured context containing meetings, todos, and decisions
    """
    context = {
        "question": question,
        "generated_at": datetime.utcnow().isoformat(),
        "meetings": [],
        "todos": [],
        "decisions": [],
    }
    
    try:
        question_lower = question.lower()
        
        # Fetch last 10 meetings ordered by date desc
        try:
            meetings = session.query(Meeting).order_by(Meeting.date.desc()).limit(10).all()
            for meeting in meetings:
                context["meetings"].append({
                    "id": meeting.id,
                    "date": meeting.date.isoformat() if meeting.date else None,
                    "title": meeting.title or "",
                    "summary": meeting.summary or "",
                })
        except Exception as exc:
            LOGGER.error("Error fetching meetings: %s", exc)
        
        # Fetch todos with optional filtering
        try:
            todos_query = session.query(Todo).order_by(Todo.created_at.desc())
            
            # Filter by late/overdue if question mentions it
            if any(keyword in question_lower for keyword in ["retard", "late", "en retard", "overdue", "dépassé"]):
                today = datetime.utcnow().date()
                todos_query = todos_query.filter(
                    Todo.due_date.isnot(None),
                    Todo.status != "completed"
                )
                # Note: due_date is stored as string, so we'd need to parse it
                # For simplicity, we'll fetch all and filter in Python if needed
            
            # Try to extract owner name from question (simple heuristic)
            # Look for common names or "owner" keywords
            owner_keywords = ["owner", "propriétaire", "assigné", "assigned"]
            potential_owner = None
            for keyword in owner_keywords:
                if keyword in question_lower:
                    # Try to extract name after the keyword
                    parts = question_lower.split(keyword)
                    if len(parts) > 1:
                        potential_name = parts[1].strip().split()[0] if parts[1].strip() else None
                        if potential_name and len(potential_name) > 2:
                            potential_owner = potential_name.capitalize()
                            break
            
            todos = todos_query.limit(30).all()
            
            for todo in todos:
                # Simple owner filtering if potential_owner found
                if potential_owner and todo.owner:
                    if potential_owner.lower() not in todo.owner.lower():
                        continue
                
                context["todos"].append({
                    "id": todo.id,
                    "meeting_id": todo.meeting_id,
                    "task": todo.task or "",
                    "owner": todo.owner or "",
                    "status": todo.status or "",
                    "due_date": todo.due_date or "",
                    "created_at": todo.created_at.isoformat() if todo.created_at else None,
                    "acknowledged_at": todo.acknowledged_at.isoformat() if todo.acknowledged_at else None,
                    "completed_at": todo.completed_at.isoformat() if todo.completed_at else None,
                })
        except Exception as exc:
            LOGGER.error("Error fetching todos: %s", exc)
        
        # Fetch last 30 decisions ordered by created_at desc
        try:
            decisions = session.query(Decision).order_by(Decision.id.desc()).limit(30).all()
            for decision in decisions:
                context["decisions"].append({
                    "id": decision.id,
                    "meeting_id": decision.meeting_id,
                    "text": decision.text or "",
                    "created_at": decision.id,  # Using id as proxy for ordering
                })
        except Exception as exc:
            LOGGER.error("Error fetching decisions: %s", exc)
    
    except Exception as exc:
        LOGGER.exception("Unexpected error in build_qa_context: %s", exc)
    
    return context


def render_context_as_text(context: Dict[str, Any]) -> str:
    """
    Take the structured context dict and format it as a text block suitable for an LLM prompt.
    
    Args:
        context: Dictionary with meetings, todos, and decisions
        
    Returns:
        Formatted text string
    """
    lines = []
    
    lines.append("QUESTION:")
    lines.append(f'"{context.get("question", "")}"')
    lines.append("")
    
    # Meetings section
    meetings = context.get("meetings", [])
    if meetings:
        lines.append("MEETINGS:")
        for meeting in meetings:
            meeting_id = meeting.get("id", "?")
            date_str = meeting.get("date", "")[:10] if meeting.get("date") else "No date"
            title = meeting.get("title", "") or "Untitled"
            summary = meeting.get("summary", "") or "No summary"
            lines.append(f'- [#{meeting_id}] {date_str} | {title}')
            if summary:
                # Truncate long summaries
                summary_short = summary[:200] + "..." if len(summary) > 200 else summary
                lines.append(f'  Summary: {summary_short}')
        lines.append("")
    
    # Decisions section
    decisions = context.get("decisions", [])
    if decisions:
        lines.append("DECISIONS:")
        for decision in decisions:
            decision_id = decision.get("id", "?")
            meeting_id = decision.get("meeting_id", "?")
            text = decision.get("text", "")
            lines.append(f'- [D{decision_id}] (Meeting #{meeting_id}) "{text}"')
        lines.append("")
    
    # TODOs section
    todos = context.get("todos", [])
    if todos:
        lines.append("TODOS:")
        for todo in todos:
            todo_id = todo.get("id", "?")
            meeting_id = todo.get("meeting_id", "?")
            task = todo.get("task", "")
            owner = todo.get("owner", "") or "Unassigned"
            status = todo.get("status", "")
            due_date = todo.get("due_date", "") or "No due date"
            lines.append(f'- [T{todo_id}] (Meeting #{meeting_id}) Task: "{task}"')
            lines.append(f'  Owner: {owner}')
            lines.append(f'  Status: {status}')
            lines.append(f'  Due date: {due_date}')
        lines.append("")
    
    return "\n".join(lines)


def answer_question_with_llm(question: str, context_text: str, provider: str = "gemini") -> str:
    """
    Call LLM to answer the user's question based ONLY on the provided context.
    
    Args:
        question: User's question
        context_text: Formatted context text
        provider: LLM provider to use ("gemini" or "groq"), defaults to "gemini"
        
    Returns:
        Answer string from LLM, or error message if something fails
    """
    full_prompt = f"""You are an assistant answering questions based ONLY on the provided context.

You MUST answer ONLY based on the context provided below.

If the answer is not present in the context, say that you don't have enough information.

Do not hallucinate. The answer can be in French or English depending on the question.

Structure the answer clearly using Markdown.

Context:
{context_text}

Question: {question}

Answer:"""
    
    return llm_generate(provider, full_prompt, temperature=0.3)


def answer_question(session: Session, question: str, provider: str = "gemini") -> Dict[str, Any]:
    """
    High-level function to answer a question about meetings, decisions, and TODOs.
    
    Args:
        session: SQLAlchemy session
        question: User's question string
        provider: LLM provider to use ("gemini" or "groq"), defaults to "gemini"
        
    Returns:
        Dictionary with question, answer, context, and context_text
    """
    try:
        # Step 1: Build context from database
        context = build_qa_context(session, question)
        
        # Step 2: Render context as text
        context_text = render_context_as_text(context)
        
        # Step 3: Get answer from LLM
        answer = answer_question_with_llm(question, context_text, provider)
        
        return {
            "question": question,
            "answer": answer,
            "context": context,
            "context_text": context_text,
        }
    
    except Exception as exc:
        LOGGER.exception("Unexpected error in answer_question: %s", exc)
        return {
            "question": question,
            "answer": "Error: An unexpected error occurred while processing your question. Please try again.",
            "context": {},
            "context_text": "",
        }
