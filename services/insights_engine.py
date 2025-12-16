"""
Insights engine for answering project questions using database data.
"""

import logging
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import Todo, Meeting, TodoEvent
from api.repositories import compute_kpis

LOGGER = logging.getLogger(__name__)


def _has_todo_events_table(session: Session) -> bool:
    """
    Check if TodoEvent table exists in the database.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        True if table exists, False otherwise
    """
    try:
        from sqlalchemy import inspect
        inspector = inspect(session.bind)
        return "todo_events" in inspector.get_table_names()
    except Exception:
        return False


def get_overdue_todos(session: Session) -> List[Todo]:
    """
    Get all overdue todos.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        List of Todo objects that are overdue
    """
    try:
        today = date.today()
        all_todos = session.query(Todo).all()
        overdue = []
        
        for todo in all_todos:
            if todo.due_date and todo.due_date.strip():
                try:
                    due_date = datetime.strptime(todo.due_date.strip(), "%Y-%m-%d").date()
                    status_lower = (todo.status or "").lower()
                    if due_date < today and status_lower not in ["done", "completed"]:
                        overdue.append(todo)
                except ValueError:
                    pass
        
        return overdue
    except Exception as exc:
        LOGGER.exception("Error getting overdue todos: %s", exc)
        return []


def get_stale_todos(session: Session, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get stale todos (no movement for N days).
    
    Args:
        session: SQLAlchemy session
        days: Number of days to consider stale (default: 7)
    
    Returns:
        List of dicts with todo info and age_days
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_date_only = cutoff_date.date()
        
        all_todos = session.query(Todo).filter(
            Todo.status.notin_(["done", "completed"])
        ).all()
        
        stale = []
        has_events = _has_todo_events_table(session)
        
        for todo in all_todos:
            last_activity = None
            
            if has_events:
                # Get last event for this todo
                last_event = session.query(TodoEvent).filter(
                    TodoEvent.todo_id == todo.id
                ).order_by(desc(TodoEvent.created_at)).first()
                
                if last_event:
                    last_activity = last_event.created_at
                else:
                    # No events, use created_at
                    last_activity = todo.created_at
            else:
                # No events table, use created_at
                last_activity = todo.created_at
            
            if last_activity:
                if isinstance(last_activity, datetime):
                    activity_date = last_activity.date()
                else:
                    activity_date = last_activity
                
                if activity_date < cutoff_date_only:
                    age_days = (date.today() - activity_date).days
                    stale.append({
                        "id": todo.id,
                        "task": todo.task,
                        "owner": todo.owner,
                        "status": todo.status,
                        "age_days": age_days,
                        "last_activity": last_activity
                    })
        
        # Sort by age (oldest first) and return top 10
        stale.sort(key=lambda x: x["age_days"], reverse=True)
        return stale[:10]
    except Exception as exc:
        LOGGER.exception("Error getting stale todos: %s", exc)
        return []


def get_owner_load(session: Session) -> List[Dict[str, Any]]:
    """
    Get workload per owner.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        List of dicts with owner, counts by status, and overdue count
    """
    try:
        all_todos = session.query(Todo).all()
        owner_stats = {}
        
        today = date.today()
        
        for todo in all_todos:
            owner = todo.owner or "Unassigned"
            
            if owner not in owner_stats:
                owner_stats[owner] = {
                    "owner": owner,
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "overdue": 0,
                    "total": 0
                }
            
            status_lower = (todo.status or "").lower()
            owner_stats[owner]["total"] += 1
            
            if status_lower in ["done", "completed"]:
                owner_stats[owner]["completed"] += 1
            elif status_lower == "in_progress":
                owner_stats[owner]["in_progress"] += 1
            else:
                owner_stats[owner]["pending"] += 1
            
            # Check if overdue
            if todo.due_date and todo.due_date.strip():
                try:
                    due_date = datetime.strptime(todo.due_date.strip(), "%Y-%m-%d").date()
                    if due_date < today and status_lower not in ["done", "completed"]:
                        owner_stats[owner]["overdue"] += 1
                except ValueError:
                    pass
        
        return list(owner_stats.values())
    except Exception as exc:
        LOGGER.exception("Error getting owner load: %s", exc)
        return []


def get_bottlenecks(session: Session) -> Dict[str, Any]:
    """
    Identify project bottlenecks.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        Dict with top overdue owners, most loaded owners, and stale tasks
    """
    try:
        owner_load = get_owner_load(session)
        stale_todos = get_stale_todos(session, days=7)
        
        # Top overdue owners
        overdue_owners = sorted(
            [o for o in owner_load if o["overdue"] > 0],
            key=lambda x: x["overdue"],
            reverse=True
        )[:3]
        
        # Most loaded owners (by open + in_progress)
        loaded_owners = sorted(
            owner_load,
            key=lambda x: x["pending"] + x["in_progress"],
            reverse=True
        )[:3]
        
        return {
            "top_overdue_owners": [
                {
                    "owner": o["owner"],
                    "overdue_count": o["overdue"]
                }
                for o in overdue_owners
            ],
            "most_loaded_owners": [
                {
                    "owner": o["owner"],
                    "open_count": o["pending"] + o["in_progress"],
                    "pending": o["pending"],
                    "in_progress": o["in_progress"]
                }
                for o in loaded_owners
            ],
            "stale_tasks": stale_todos
        }
    except Exception as exc:
        LOGGER.exception("Error getting bottlenecks: %s", exc)
        return {
            "top_overdue_owners": [],
            "most_loaded_owners": [],
            "stale_tasks": []
        }


def get_project_kpis(session: Session) -> Dict[str, Any]:
    """
    Get project KPIs (wrapper around compute_kpis).
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        Dict with KPI values
    """
    try:
        return compute_kpis(session)
    except Exception as exc:
        LOGGER.exception("Error getting project KPIs: %s", exc)
        return {
            "total_meetings": 0,
            "total_todos": 0,
            "done_todos": 0,
            "overdue_todos": 0,
            "completion_rate": 0.0,
        }


def _detect_intent(question: str) -> str:
    """
    Detect question intent from keywords.
    
    Args:
        question: User question string
    
    Returns:
        Intent string: "overdue", "bottleneck", "owner_load", "stale", "status_summary", or "unknown"
    """
    question_lower = question.lower()
    
    # Overdue keywords
    if any(word in question_lower for word in ["overdue", "retard", "en retard", "late", "tard"]):
        return "overdue"
    
    # Bottleneck keywords
    if any(word in question_lower for word in ["bottleneck", "goulot", "blocker", "blocked", "stuck", "bloqué"]):
        return "bottleneck"
    
    # Owner load keywords
    if any(word in question_lower for word in ["workload", "charge", "surchargé", "owner", "qui", "who", "responsable"]):
        return "owner_load"
    
    # Stale keywords
    if any(word in question_lower for word in ["stale", "stagnant", "stuck since", "no movement", "immobile"]):
        return "stale"
    
    # Status summary keywords
    if any(word in question_lower for word in ["status", "overview", "avancement", "summary", "résumé"]):
        return "status_summary"
    
    return "unknown"


def _answer_overdue(session: Session) -> Dict[str, Any]:
    """Generate answer for overdue intent."""
    overdue = get_overdue_todos(session)
    kpis = get_project_kpis(session)
    
    if not overdue:
        answer = "Aucune tâche en retard actuellement."
        evidence = {"overdue_count": 0, "overdue_todos": []}
        actions = ["Continuer à suivre les échéances"]
    else:
        answer = f"Il y a {len(overdue)} tâche(s) en retard."
        evidence = {
            "overdue_count": len(overdue),
            "overdue_todos": [
                {
                    "id": t.id,
                    "task": t.task,
                    "owner": t.owner,
                    "due_date": t.due_date,
                    "status": t.status
                }
                for t in overdue[:10]
            ]
        }
        actions = [
            f"Contacter {t.owner} pour {t.task[:50]}..." if t.owner else f"Réviser la tâche: {t.task[:50]}..."
            for t in overdue[:3]
        ]
    
    return {
        "intent": "overdue",
        "answer": answer,
        "evidence": evidence,
        "recommended_actions": actions
    }


def _answer_bottleneck(session: Session) -> Dict[str, Any]:
    """Generate answer for bottleneck intent."""
    bottlenecks = get_bottlenecks(session)
    
    if not bottlenecks["top_overdue_owners"] and not bottlenecks["stale_tasks"]:
        answer = "Aucun goulot d'étranglement identifié actuellement."
        evidence = bottlenecks
        actions = ["Continuer le suivi"]
    else:
        parts = []
        if bottlenecks["top_overdue_owners"]:
            parts.append(f"{len(bottlenecks['top_overdue_owners'])} propriétaire(s) avec tâches en retard")
        if bottlenecks["stale_tasks"]:
            parts.append(f"{len(bottlenecks['stale_tasks'])} tâche(s) stagnantes")
        
        answer = f"Goulots d'étranglement identifiés: {', '.join(parts)}."
        evidence = bottlenecks
        actions = []
        
        if bottlenecks["top_overdue_owners"]:
            for owner_info in bottlenecks["top_overdue_owners"][:2]:
                actions.append(f"Prioriser les tâches en retard de {owner_info['owner']}")
        
        if bottlenecks["stale_tasks"]:
            actions.append(f"Réviser {bottlenecks['stale_tasks'][0]['task'][:50]}... (stagnant depuis {bottlenecks['stale_tasks'][0]['age_days']} jours)")
    
    return {
        "intent": "bottleneck",
        "answer": answer,
        "evidence": evidence,
        "recommended_actions": actions
    }


def _answer_owner_load(session: Session) -> Dict[str, Any]:
    """Generate answer for owner load intent."""
    owner_load = get_owner_load(session)
    
    if not owner_load:
        answer = "Aucune charge de travail disponible."
        evidence = {"owners": []}
        actions = []
    else:
        # Sort by total load
        sorted_load = sorted(owner_load, key=lambda x: x["total"], reverse=True)
        most_loaded = sorted_load[0] if sorted_load else None
        
        if most_loaded and most_loaded["total"] > 0:
            answer = f"{most_loaded['owner']} a la charge la plus élevée ({most_loaded['total']} tâches, {most_loaded['overdue']} en retard)."
        else:
            answer = "Charge de travail équilibrée entre les propriétaires."
        
        evidence = {"owners": sorted_load[:5]}
        actions = []
        
        if most_loaded and most_loaded["overdue"] > 0:
            actions.append(f"Alléger la charge de {most_loaded['owner']} (tâches en retard)")
        
        if len(sorted_load) > 1:
            underloaded = [o for o in sorted_load[1:] if o["total"] < most_loaded["total"] / 2]
            if underloaded:
                actions.append(f"Répartir certaines tâches vers {underloaded[0]['owner']}")
    
    return {
        "intent": "owner_load",
        "answer": answer,
        "evidence": evidence,
        "recommended_actions": actions
    }


def _answer_stale(session: Session) -> Dict[str, Any]:
    """Generate answer for stale intent."""
    stale = get_stale_todos(session, days=7)
    
    if not stale:
        answer = "Aucune tâche stagnante identifiée."
        evidence = {"stale_tasks": []}
        actions = ["Continuer le suivi"]
    else:
        answer = f"{len(stale)} tâche(s) stagnante(s) (pas de mouvement depuis 7+ jours)."
        evidence = {"stale_tasks": stale}
        actions = [
            f"Réviser {t['task'][:50]}... (stagnant depuis {t['age_days']} jours)"
            for t in stale[:3]
        ]
    
    return {
        "intent": "stale",
        "answer": answer,
        "evidence": evidence,
        "recommended_actions": actions
    }


def _answer_status_summary(session: Session) -> Dict[str, Any]:
    """Generate answer for status summary intent."""
    kpis = get_project_kpis(session)
    
    answer = (
        f"Résumé: {kpis['total_meetings']} réunion(s), "
        f"{kpis['total_todos']} tâche(s) au total, "
        f"{kpis['done_todos']} terminée(s), "
        f"{kpis['overdue_todos']} en retard. "
        f"Taux de complétion: {kpis['completion_rate']:.1f}%."
    )
    
    evidence = kpis
    actions = []
    
    if kpis["overdue_todos"] > 0:
        actions.append(f"Traiter {kpis['overdue_todos']} tâche(s) en retard")
    
    if kpis["completion_rate"] < 50:
        actions.append("Améliorer le taux de complétion")
    
    return {
        "intent": "status_summary",
        "answer": answer,
        "evidence": evidence,
        "recommended_actions": actions
    }


def _enhance_with_llm(base_answer: Dict[str, Any], context: Dict[str, Any]) -> str:
    """
    Enhance answer with LLM explanation (optional).
    
    Args:
        base_answer: Base answer dict
        context: Context data (KPIs, evidence)
    
    Returns:
        Enhanced answer string, or base answer if LLM fails
    """
    try:
        from groq import Groq
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        
        if not groq_api_key:
            return base_answer["answer"]
        
        client = Groq(api_key=groq_api_key)
        
        # Build compact context
        context_str = f"KPIs: {context.get('kpis', {})}\n"
        context_str += f"Evidence: {str(context.get('evidence', {}))[:500]}\n"
        
        prompt = (
            f"Based on this project data:\n{context_str}\n\n"
            f"Original answer: {base_answer['answer']}\n\n"
            "Provide a brief, natural explanation (2-3 sentences) in French. "
            "Be concise and actionable. Do not invent data."
        )
        
        response = client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        enhanced = response.choices[0].message.content.strip() if response.choices else None
        
        if enhanced:
            return enhanced
        else:
            return base_answer["answer"]
    except Exception as exc:
        LOGGER.exception("Error enhancing answer with LLM: %s", exc)
        return base_answer["answer"]


def answer_insights_question(
    session: Session,
    question: str,
    use_llm: bool = False
) -> Dict[str, Any]:
    """
    Answer an insights question using database data.
    
    Args:
        session: SQLAlchemy session
        question: User question string
        use_llm: Whether to use LLM to enhance the answer (optional)
    
    Returns:
        Dict with intent, answer, evidence, and recommended_actions
    """
    try:
        intent = _detect_intent(question)
        
        # Route to appropriate answer function
        if intent == "overdue":
            base_answer = _answer_overdue(session)
        elif intent == "bottleneck":
            base_answer = _answer_bottleneck(session)
        elif intent == "owner_load":
            base_answer = _answer_owner_load(session)
        elif intent == "stale":
            base_answer = _answer_stale(session)
        elif intent == "status_summary":
            base_answer = _answer_status_summary(session)
        else:
            # Unknown intent
            base_answer = {
                "intent": "unknown",
                "answer": "Je n'ai pas compris la question. Essayez de demander sur les tâches en retard, les goulots d'étranglement, la charge de travail, ou l'avancement.",
                "evidence": {},
                "recommended_actions": []
            }
        
        # Optionally enhance with LLM
        if use_llm and base_answer["intent"] != "unknown":
            context = {
                "kpis": get_project_kpis(session),
                "evidence": base_answer["evidence"]
            }
            enhanced_answer = _enhance_with_llm(base_answer, context)
            base_answer["answer"] = enhanced_answer
        
        return base_answer
    except Exception as exc:
        LOGGER.exception("Error answering insights question: %s", exc)
        return {
            "intent": "error",
            "answer": "Erreur lors du traitement de la question.",
            "evidence": {},
            "recommended_actions": []
        }

