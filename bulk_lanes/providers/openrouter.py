"""OpenRouter API provider for free and low-cost model lanes."""
import os
import time
import uuid
from typing import Optional, Tuple
import httpx
from .base import BaseProvider

class OpenRouterError(Exception):
    pass

class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = base_url.rstrip("/")

    def run_prompt(
        self,
        route_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout_sec: int = 120
    ) -> Tuple[bool, Optional[str], dict]:
        started = time.time()
        rid = uuid.uuid4().hex
        
        # Route id can be "openrouter/foo/bar:free" or "foo/bar:free"
        model_name = route_id.removeprefix("openrouter/")
        
        receipt = {
            "id": rid,
            "provider": "openrouter",
            "requested_route": route_id,
            "status": "failed",
            "cost": None,
            "cost_status": "unknown",
            "usage": None,
            "error": None,
            "duration_seconds": None,
        }

        if not self.api_key:
            receipt["error"] = "OPENROUTER_API_KEY is not set"
            receipt["duration_seconds"] = time.time() - started
            return False, None, receipt

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/bulk-lanes",
            "X-Title": "bulk-lanes"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
        }

        try:
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                
                if resp.status_code == 429:
                    receipt["error"] = f"Rate limited (429): {resp.text[:300]}"
                    receipt["duration_seconds"] = time.time() - started
                    return False, None, receipt

                if resp.status_code != 200:
                    receipt["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
                    receipt["duration_seconds"] = time.time() - started
                    return False, None, receipt

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    receipt["error"] = "Empty choices in response"
                    receipt["duration_seconds"] = time.time() - started
                    return False, None, receipt

                text = choices[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                receipt["usage"] = usage
                
                # Check for reported zero cost on free models
                if ":free" in model_name:
                    receipt["cost"] = 0.0
                    receipt["cost_status"] = "reported_zero"
                else:
                    receipt["cost"] = None
                    receipt["cost_status"] = "budget_billable"

                receipt["status"] = "complete"
                receipt["duration_seconds"] = time.time() - started
                return True, text, receipt

        except Exception as e:
            receipt["error"] = str(e)
            receipt["duration_seconds"] = time.time() - started
            return False, None, receipt
