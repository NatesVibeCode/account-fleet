"""Abstract base provider interface."""
import re
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

def clean_llm_json(text: str) -> Optional[Any]:
    """Robustly extracts and parses JSON from LLM responses.
    
    Handles:
    - Pure JSON strings
    - Markdown fenced blocks (```json ... ``` or ``` ... ```) anywhere in the text
    - Conversational preambles and postambles (e.g. 'Here is the JSON: ... Hope this helps!')
    - Trailing commas before closing braces/brackets
    """
    if not text:
        return None
    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Markdown code fences anywhere in the output
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        cand = fenced.group(1).strip()
        try:
            return json.loads(cand)
        except Exception:
            pass
        cand_fixed = re.sub(r",\s*([\]}])", r"\1", cand)
        try:
            return json.loads(cand_fixed)
        except Exception:
            pass

    # 3. Outermost JSON object or array substring
    for open_char, close_char in (("{", "}"), ("[", "]")):
        first = text.find(open_char)
        last = text.rfind(close_char)
        if first != -1 and last > first:
            cand = text[first:last + 1]
            try:
                return json.loads(cand)
            except Exception:
                pass
            cand_fixed = re.sub(r",\s*([\]}])", r"\1", cand)
            try:
                return json.loads(cand_fixed)
            except Exception:
                pass

    return None

class BaseProvider(ABC):
    @abstractmethod
    def run_prompt(
        self,
        route_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout_sec: int = 120,
        session_id: Optional[str] = None,
        policy: Optional[Any] = None,
    ) -> Tuple[bool, Optional[str], dict]:
        """Executes a prompt in a session. Returns (success, text_response, receipt_dict)."""
        pass
