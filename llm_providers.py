"""
LLM provider abstraction for Meeting Brain.
Supports: Groq, Mistral, Gemini.

Provider selection via LLM_PROVIDER env var, or auto-detected from available keys.
Priority: groq → mistral → gemini
"""

import logging
import os
import json
from typing import Optional, Tuple
from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)
load_dotenv()

# --- Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

# --- Provider initialization ---

groq_available = False
groq_client = None
try:
    if GROQ_API_KEY:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        groq_available = True
    else:
        LOGGER.warning("GROQ_API_KEY not set — Groq unavailable.")
except Exception as exc:
    LOGGER.error("Failed to initialize Groq: %s", exc)

mistral_available = False
mistral_client = None
try:
    if MISTRAL_API_KEY:
        from mistralai import Mistral
        mistral_client = Mistral(api_key=MISTRAL_API_KEY)
        mistral_available = True
    else:
        LOGGER.warning("MISTRAL_API_KEY not set — Mistral unavailable.")
except Exception as exc:
    LOGGER.error("Failed to initialize Mistral: %s", exc)

gemini_available = False
try:
    if GOOGLE_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_available = True
    else:
        LOGGER.warning("GOOGLE_API_KEY not set — Gemini unavailable.")
except Exception as exc:
    LOGGER.error("Failed to initialize Gemini: %s", exc)


def get_active_provider() -> Optional[str]:
    """
    Return the active LLM provider name.
    Uses LLM_PROVIDER env var if set and available, otherwise auto-detects.
    Priority: groq → mistral → gemini
    """
    if LLM_PROVIDER:
        if LLM_PROVIDER == "groq" and groq_available:
            return "groq"
        if LLM_PROVIDER == "mistral" and mistral_available:
            return "mistral"
        if LLM_PROVIDER == "gemini" and gemini_available:
            return "gemini"
        LOGGER.warning("Requested provider '%s' unavailable — falling back to auto-detect.", LLM_PROVIDER)

    if groq_available:
        return "groq"
    if mistral_available:
        return "mistral"
    if gemini_available:
        return "gemini"

    return None


def load_groq_client() -> Optional[Tuple[object, str]]:
    """Return Groq client and model name, or None if unavailable."""
    if not groq_available or not groq_client:
        LOGGER.warning("GROQ_API_KEY not set")
        return None
    return (groq_client, GROQ_MODEL)


def llm_generate(provider: str, prompt: str, temperature: float = 0.3) -> str:
    """
    Generate text using the specified LLM provider.

    Args:
        provider: "groq" | "mistral" | "gemini"
        prompt: The prompt text
        temperature: Generation temperature (default 0.3)

    Returns:
        Generated text, or an error string prefixed with "Error:" on failure.
    """
    if provider == "groq":
        if not groq_available or not groq_client:
            return "Error: Groq API key is not configured. Please set GROQ_API_KEY."
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            answer = response.choices[0].message.content.strip() if response.choices else ""
            return answer or "Error: Empty response from Groq."
        except Exception as exc:
            LOGGER.exception("Groq error: %s", exc)
            return f"Error: Groq call failed. {exc}"

    elif provider == "mistral":
        if not mistral_available or not mistral_client:
            return "Error: Mistral API key is not configured. Please set MISTRAL_API_KEY."
        try:
            response = mistral_client.chat.complete(
                model=MISTRAL_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            answer = response.choices[0].message.content.strip() if response.choices else ""
            return answer or "Error: Empty response from Mistral."
        except Exception as exc:
            LOGGER.exception("Mistral error: %s", exc)
            return f"Error: Mistral call failed. {exc}"

    elif provider == "gemini":
        if not gemini_available or not GOOGLE_API_KEY:
            return "Error: Gemini API key is not configured. Please set GOOGLE_API_KEY."
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            return "Error: Empty response from Gemini."
        except Exception as exc:
            LOGGER.exception("Gemini error: %s", exc)
            return f"Error: Gemini call failed. {exc}"

    return f"Error: Unknown provider '{provider}'."


def llm_generate_json(provider: str, prompt: str, temperature: float = 0.2) -> dict:
    """
    Generate and parse a JSON response from the specified provider.

    Returns:
        Parsed dict, or empty dict on failure.
    """
    try:
        json_prompt = f"{prompt}\n\nReturn ONLY valid JSON. No prose. No explanation."
        raw = llm_generate(provider, json_prompt, temperature)

        if raw.startswith("Error:"):
            LOGGER.error("LLM generation failed: %s", raw)
            return {}

        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}

    except json.JSONDecodeError as err:
        LOGGER.error("JSON parse error: %s", err)
        return {}
    except Exception as exc:
        LOGGER.exception("Unexpected error in llm_generate_json: %s", exc)
        return {}
