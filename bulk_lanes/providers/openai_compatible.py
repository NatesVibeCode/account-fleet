"""Generic OpenAI-compatible API provider supporting Ollama, LM Studio, vLLM, Groq, etc."""
from __future__ import annotations

import os
import time
import uuid
from typing import Optional, Tuple
import httpx
from .base import BaseProvider


def _parse_retry_after(header_val: Optional[str]) -> float:
    if not header_val:
        return 10.0
    try:
        return max(1.0, float(header_val))
    except (ValueError, TypeError):
        return 10.0


class OpenAICompatibleProvider(BaseProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider_name: str = "openai_compatible",
    ):
        configured_url = (
            base_url
            or os.environ.get("OPENAI_COMPATIBLE_BASE_URL")
            or os.environ.get("OLLAMA_BASE_URL")
            or os.environ.get("LMSTUDIO_BASE_URL")
            or "http://localhost:11434/v1"
        )
        self.base_url = configured_url.rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_COMPATIBLE_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        self.provider_name = provider_name

    def run_prompt(
        self,
        route_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout_sec: int = 120,
        session_id: Optional[str] = None,
        policy: Optional[Any] = None,
    ) -> Tuple[bool, Optional[str], dict]:
        started = time.time()
        rid = uuid.uuid4().hex

        # Strip provider prefix if present (e.g., ollama/llama3 -> llama3, openai/gpt-4o -> gpt-4o)
        model_name = route_id
        for prefix in ("openai_compatible/", "ollama/", "lmstudio/", "vllm/", "groq/", "cerebras/", "openai/"):
            if model_name.startswith(prefix):
                model_name = model_name[len(prefix):]
                break

        receipt = {
            "id": rid,
            "session_id": session_id,
            "provider": self.provider_name,
            "requested_route": route_id,
            "status": "failed",
            "cost": 0.0,
            "cost_status": "reported_zero",
            "usage": None,
            "error": None,
            "error_type": None,
            "retry_after": None,
            "duration_seconds": None,
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

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
                url = f"{self.base_url}/chat/completions"
                resp = client.post(url, headers=headers, json=payload)

                if resp.status_code == 429:
                    retry_sec = _parse_retry_after(resp.headers.get("retry-after"))
                    receipt["error"] = f"Rate limited (429): {resp.text[:300]}"
                    receipt["error_type"] = "rate_limit"
                    receipt["retry_after"] = retry_sec
                    receipt["duration_seconds"] = time.time() - started
                    return False, None, receipt

                if resp.status_code in (500, 502, 503, 504):
                    receipt["error"] = f"Transient HTTP {resp.status_code}: {resp.text[:300]}"
                    receipt["error_type"] = "transient_http"
                    receipt["retry_after"] = 5.0
                    receipt["duration_seconds"] = time.time() - started
                    return False, None, receipt

                if resp.status_code != 200:
                    receipt["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
                    receipt["error_type"] = "inference_error"
                    receipt["duration_seconds"] = time.time() - started
                    return False, None, receipt

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    receipt["error"] = "Empty choices in response"
                    receipt["error_type"] = "inference_error"
                    receipt["duration_seconds"] = time.time() - started
                    return False, None, receipt

                text = choices[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                receipt["usage"] = usage

                reported_cost = data.get("cost") or (usage.get("cost") if isinstance(usage, dict) else None)
                if isinstance(reported_cost, (int, float)):
                    receipt["cost"] = float(reported_cost)
                    receipt["cost_status"] = "reported_zero" if reported_cost == 0 else "billed"

                receipt["status"] = "complete"
                receipt["duration_seconds"] = time.time() - started
                return True, text, receipt

        except httpx.TimeoutException:
            receipt["error"] = f"Request timed out after {timeout_sec}s"
            receipt["error_type"] = "timeout"
            receipt["duration_seconds"] = time.time() - started
            return False, None, receipt
        except Exception as e:
            receipt["error"] = str(e)
            receipt["error_type"] = "inference_error"
            receipt["duration_seconds"] = time.time() - started
            return False, None, receipt
