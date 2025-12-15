"""
Slack integration endpoints for Insights queries.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import get_db
from api.slack_security import verify_slack_signature, get_slack_signing_secret
from services.insights_engine import answer_insights_question, get_project_kpis

LOGGER = logging.getLogger(__name__)

router = APIRouter()


def _parse_llm_flag(text: str) -> tuple[str, bool]:
    """
    Parse LLM flag from question text.
    
    Args:
        text: Question text
    
    Returns:
        Tuple of (cleaned_text, use_llm)
    """
    use_llm = False
    cleaned = text
    
    # Check for --llm flag
    if "--llm" in cleaned:
        use_llm = True
        cleaned = cleaned.replace("--llm", "").strip()
    
    # Check for llm:true
    if "llm:true" in cleaned.lower():
        use_llm = True
        cleaned = cleaned.replace("llm:true", "").replace("llm:True", "").strip()
    
    return cleaned, use_llm


def _build_slack_blocks(result: dict, question: str) -> list:
    """
    Build Slack message blocks from insights result.
    
    Args:
        result: Insights answer dict
        question: Original question
    
    Returns:
        List of Slack block dicts
    """
    blocks = []
    
    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "Meeting Brain — Insights"
        }
    })
    
    # Question and intent
    intent_text = result.get("intent", "unknown")
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Question:* {question}\n*Intent:* `{intent_text}`"
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Answer
    answer = result.get("answer", "No answer available")
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Réponse:*\n{answer}"
        }
    })
    
    # KPIs context
    evidence = result.get("evidence", {})
    if isinstance(evidence, dict):
        kpis = evidence.get("total_todos") or evidence.get("overdue_todos")
        if kpis is not None:
            # Try to get full KPIs
            kpi_text = ""
            if "total_todos" in evidence:
                kpi_text += f"• Total tâches: {evidence['total_todos']}\n"
            if "overdue_todos" in evidence:
                kpi_text += f"• En retard: {evidence['overdue_todos']}\n"
            elif "overdue_count" in evidence:
                kpi_text += f"• En retard: {evidence['overdue_count']}\n"
            if "completion_rate" in evidence:
                kpi_text += f"• Taux de complétion: {evidence['completion_rate']:.1f}%"
            
            if kpi_text:
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": kpi_text
                    }]
                })
    
    # Recommended actions
    actions = result.get("recommended_actions", [])
    if actions:
        blocks.append({"type": "divider"})
        actions_text = "\n".join([f"• {action}" for action in actions[:5]])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Actions recommandées:*\n{actions_text}"
            }
        })
    
    # Evidence summary (if available and not too large)
    if isinstance(evidence, dict):
        evidence_summary = []
        
        if "overdue_todos" in evidence and evidence["overdue_todos"]:
            todos = evidence["overdue_todos"][:3]
            for todo in todos:
                task = todo.get("task", "")[:50]
                owner = todo.get("owner", "Unassigned")
                evidence_summary.append(f"• {task} ({owner})")
        
        if "stale_tasks" in evidence and evidence["stale_tasks"]:
            stale = evidence["stale_tasks"][:3]
            for task in stale:
                task_text = task.get("task", "")[:50]
                age = task.get("age_days", 0)
                evidence_summary.append(f"• {task_text} (stagnant {age}j)")
        
        if evidence_summary:
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": "*Détails:*\n" + "\n".join(evidence_summary)
                }]
            })
    
    return blocks


@router.post("/slack/commands")
async def slack_commands(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Slack slash command for Insights queries.
    
    Accepts Slack slash command payload and returns formatted response.
    """
    try:
        # Get raw body for signature verification (must be done before parsing)
        raw_body = await request.body()
        
        # Verify signature
        if not verify_slack_signature(dict(request.headers), raw_body):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid Slack signature"}
            )
        
        # Parse form data from raw body
        from urllib.parse import unquote
        form_data_str = raw_body.decode("utf-8")
        form_data = {}
        for pair in form_data_str.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                form_data[unquote(key)] = unquote(value)
        
        command = form_data.get("command", "")
        text = form_data.get("text", "").strip()
        user_name = form_data.get("user_name", "")
        channel_name = form_data.get("channel_name", "")
        team_domain = form_data.get("team_domain", "")
        response_url = form_data.get("response_url", "")
        
        LOGGER.info(
            "Slack command received: %s from %s in %s",
            command, user_name, channel_name
        )
        
        # If no question provided, return usage
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Usage: /insights <question>",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Usage:* `/insights <question>`\n\n"
                                    "Exemples:\n"
                                    "• `/insights Quelles tâches sont en retard ?`\n"
                                    "• `/insights Qui est surchargé ?`\n"
                                    "• `/insights Qu'est-ce qui est bloqué ?`\n"
                                    "• `/insights Quel est l'avancement ?`\n\n"
                                    "Ajoutez `--llm` pour une réponse améliorée par IA."
                        }
                    }
                ]
            }
        
        # Parse LLM flag
        question, use_llm = _parse_llm_flag(text)
        
        if not question:
            return {
                "response_type": "ephemeral",
                "text": "Veuillez fournir une question valide."
            }
        
        # Call insights engine
        try:
            result = answer_insights_question(
                session=db,
                question=question,
                use_llm=use_llm
            )
        except Exception as exc:
            LOGGER.exception("Error calling insights engine: %s", exc)
            return {
                "response_type": "ephemeral",
                "text": f"Erreur lors du traitement de la question: {exc}"
            }
        
        # Build Slack response
        blocks = _build_slack_blocks(result, question)
        
        return {
            "response_type": "ephemeral",
            "text": result.get("answer", "Réponse générée"),
            "blocks": blocks
        }
    
    except Exception as exc:
        LOGGER.exception("Error handling Slack command: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"}
        )


@router.post("/slack/events")
async def slack_events(request: Request):
    """
    Handle Slack Events API payloads.
    
    Supports URL verification and validates signatures.
    """
    try:
        # Get raw body for signature verification
        raw_body = await request.body()
        
        # Verify signature
        if not verify_slack_signature(dict(request.headers), raw_body):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid Slack signature"}
            )
        
        # Parse JSON payload
        import json
        payload = json.loads(raw_body.decode("utf-8"))
        
        # Handle URL verification
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge")
            if challenge:
                return {"challenge": challenge}
        
        # For other event types, just acknowledge
        # Future: could handle mentions, DMs, etc.
        return {"ok": True}
    
    except Exception as exc:
        LOGGER.exception("Error handling Slack event: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"}
        )

