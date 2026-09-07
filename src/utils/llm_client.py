from __future__ import annotations

import json
import os
import time
import logging
from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from google.api_core.exceptions import ResourceExhausted

# Configure basic logging for key rotation
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Global index to track which Gemini API key is currently active
_ACTIVE_KEY_INDEX = 0

def get_gemini_keys() -> list[str]:
    """Parse comma-separated GEMINI_API_KEYS from env."""
    keys_str = os.getenv("GEMINI_API_KEYS", "")
    if not keys_str:
        # Fallback to single key if set
        single = os.getenv("GEMINI_API_KEY")
        if single:
            return [single.strip()]
        return []
    return [k.strip() for k in keys_str.split(",") if k.strip()]

def llm_enabled() -> bool:
    if os.getenv("USE_LLM", "1").strip().lower() in ("0", "false", "no"):
        return False
    return len(get_gemini_keys()) > 0

def get_chat_model(api_key: str) -> ChatGoogleGenerativeAI:
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    temperature = float(os.getenv("GEMINI_TEMPERATURE", "0"))
    return ChatGoogleGenerativeAI(
        model=model, 
        temperature=temperature,
        google_api_key=api_key
    )

def _invoke_with_cycling(callback):
    """
    Executes the given callback, cycling through available Gemini API keys 
    if a ResourceExhausted (rate limit) error is encountered.
    """
    global _ACTIVE_KEY_INDEX
    keys = get_gemini_keys()
    if not keys:
        raise RuntimeError("LLM not configured (set GEMINI_API_KEYS or USE_LLM=0 for rule-based path)")

    num_keys = len(keys)
    attempts = 0

    while attempts < num_keys:
        current_key = keys[_ACTIVE_KEY_INDEX]
        try:
            return callback(current_key)
        except ResourceExhausted as e:
            logger.warning(f"Key at index {_ACTIVE_KEY_INDEX} exhausted. Trying next key...")
            _ACTIVE_KEY_INDEX = (_ACTIVE_KEY_INDEX + 1) % num_keys
            attempts += 1
            # Slight delay before retry to ensure clean handoff
            time.sleep(1)
        except Exception as e:
            # Re-raise any other exceptions (e.g. invalid key, parsing error)
            raise e

    # If we tried all keys and all are exhausted
    raise RuntimeError(f"All {num_keys} Gemini API keys have exhausted their rate limits.")

def invoke_structured(
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
) -> T:
    if not llm_enabled():
        raise RuntimeError("LLM not configured (set GEMINI_API_KEYS or USE_LLM=0 for rule-based path)")
    
    def _do_invoke(api_key: str) -> T:
        llm = get_chat_model(api_key).with_structured_output(schema)
        return llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
    
    return _invoke_with_cycling(_do_invoke)

def invoke_json(system_prompt: str, user_prompt: str) -> dict:
    if not llm_enabled():
        raise RuntimeError("LLM not configured")
    
    def _do_invoke(api_key: str) -> dict:
        llm = get_chat_model(api_key)
        text = llm.invoke(
            [
                SystemMessage(content=system_prompt + "\nRespond with valid JSON only."),
                HumanMessage(content=user_prompt),
            ]
        ).content
        if isinstance(text, list):
            text = "".join(str(part) for part in text)
        
        # Clean markdown code block if present
        text_str = str(text).strip()
        if text_str.startswith("```json"):
            text_str = text_str[7:]
        if text_str.startswith("```"):
            text_str = text_str[3:]
        if text_str.endswith("```"):
            text_str = text_str[:-3]
            
        return json.loads(text_str.strip())
        
    return _invoke_with_cycling(_do_invoke)
