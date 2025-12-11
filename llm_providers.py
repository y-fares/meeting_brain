"""
LLM provider abstraction for Meeting Brain.
Supports multiple LLM providers: Gemini and Groq.
"""

import logging
import os
import json
from typing import Optional, Tuple
from dotenv import load_dotenv

# Setup logging
LOGGER = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Gemini configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Groq configuration
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Gemini if available
try:
    if GOOGLE_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_available = True
    else:
        gemini_available = False
        LOGGER.warning("GOOGLE_API_KEY not set. Gemini provider will not be available.")
except Exception as exc:
    gemini_available = False
    LOGGER.error("Failed to initialize Gemini: %s", exc)

# Initialize Groq if available
try:
    if GROQ_API_KEY:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        groq_available = True
    else:
        groq_client = None
        groq_available = False
        LOGGER.warning("GROQ_API_KEY not set. Groq provider will not be available.")
except Exception as exc:
    groq_client = None
    groq_available = False
    LOGGER.error("Failed to initialize Groq: %s", exc)


def load_groq_client() -> Optional[Tuple[object, str]]:
    """
    Load and initialize Groq client.
    
    Returns:
        Tuple of (client, model_name) if successful, None otherwise
    """
    if not GROQ_API_KEY:
        LOGGER.warning("GROQ_API_KEY not set")
        return None
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        return (client, GROQ_MODEL)
    except Exception as exc:
        LOGGER.error("Failed to load Groq client: %s", exc)
        return None


def llm_generate(provider: str, prompt: str, temperature: float = 0.3) -> str:
    """
    Generate text using the specified LLM provider.
    
    Args:
        provider: "gemini" or "groq"
        prompt: The prompt text
        temperature: Temperature for generation (default: 0.3)
        
    Returns:
        Generated text string, or error message if generation fails
    """
    if provider not in ["gemini", "groq"]:
        LOGGER.warning("Unknown provider '%s', defaulting to 'gemini'", provider)
        provider = "gemini"
    
    if provider == "gemini":
        if not gemini_available or not GOOGLE_API_KEY:
            error_msg = "Error: Gemini API key is not configured. Please set GOOGLE_API_KEY in your .env file."
            LOGGER.error(error_msg)
            return error_msg
        
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            else:
                LOGGER.warning("Gemini response has no text attribute or is empty")
                return "Error: Could not generate an answer. Please try again."
        
        except Exception as exc:
            LOGGER.exception("Error calling Gemini: %s", exc)
            return f"Error: Failed to generate answer with Gemini. {str(exc)}"
    
    elif provider == "groq":
        if not groq_available or not groq_client:
            error_msg = "Error: Groq API key is not configured. Please set GROQ_API_KEY in your .env file."
            LOGGER.error(error_msg)
            return error_msg
        
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
            )
            
            if response.choices and len(response.choices) > 0:
                answer = response.choices[0].message.content.strip()
                return answer if answer else "Error: Could not generate an answer. Please try again."
            else:
                LOGGER.warning("Groq response has no choices")
                return "Error: Could not generate an answer. Please try again."
        
        except Exception as exc:
            LOGGER.exception("Error calling Groq: %s", exc)
            return f"Error: Failed to generate answer with Groq. {str(exc)}"
    
    # Fallback (should not reach here)
    return "Error: Unknown provider error."


def llm_generate_json(provider: str, prompt: str, temperature: float = 0.2) -> dict:
    """
    Generate JSON output using the specified LLM provider.
    
    Args:
        provider: "gemini" or "groq"
        prompt: The prompt text (should instruct model to return JSON)
        temperature: Temperature for generation (default: 0.2 for more deterministic JSON)
        
    Returns:
        Parsed JSON dictionary, or empty dict if parsing fails
    """
    try:
        # Add JSON instruction to prompt
        json_prompt = f"""{prompt}

Return ONLY valid JSON. No prose. No explanation."""
        
        raw_output = llm_generate(provider, json_prompt, temperature)
        
        # Check if output is an error message
        if raw_output.startswith("Error:"):
            LOGGER.error("LLM generation failed: %s", raw_output)
            return {}
        
        # Try to extract JSON from response (might be wrapped in markdown code blocks)
        json_text = raw_output.strip()
        
        # Remove markdown code fences if present
        if json_text.startswith("```"):
            lines = json_text.splitlines()
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            json_text = "\n".join(lines).strip()
        
        # Parse JSON
        parsed = json.loads(json_text)
        return parsed if isinstance(parsed, dict) else {}
    
    except json.JSONDecodeError as json_err:
        LOGGER.error("Failed to parse JSON from LLM response: %s", json_err)
        LOGGER.debug("Raw LLM response: %s", raw_output)
        return {}
    
    except Exception as exc:
        LOGGER.exception("Unexpected error in llm_generate_json: %s", exc)
        return {}

