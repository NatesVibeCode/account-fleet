"""Abstract base provider interface."""
import re
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

def clean_llm_json(text: str) -> Optional[Any]:
    """Strips markdown code fences and returns parsed JSON object or None."""
    if not text:
        return None
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        return None

class BaseProvider(ABC):
    @abstractmethod
    def run_prompt(
        self,
        route_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout_sec: int = 120
    ) -> Tuple[bool, Optional[str], dict]:
        """Executes a prompt. Returns (success, text_response, receipt_dict)."""
        pass
