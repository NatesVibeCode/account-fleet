from __future__ import annotations

import os
import time
import uuid
from typing import Any, Optional, Tuple
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
        timeout_sec: int = 120,
        session_id: Optional[str] = None,
        policy: Optional[Any] = None,
    ) -> Tuple[bool, Optional[str], dict]:
        started = time.time()
        rid = uuid.uuid4().hex
        
        # Route id can be "openrouter/foo/bar:free" or "foo/bar:free"
        model_name = route_id.removeprefix("openrouter/")
        
        receipt = {
            "id": rid,
            "session_id": session_id,
            "provider": "openrouter",
            "requested_route": route_id,
            "status": "failed",
            "cost": None,
            "cost_status": "unknown",
            "usage": None,
            "error": None,
            "error_type": None,
            "retry_after": None,
            "duration_seconds": None,
        }

        if not self.api_key:
            receipt["error"] = "OPENROUTER_API_KEY is not set"
            receipt["error_type"] = "auth_error"
            receipt["duration_seconds"] = time.time() - started
            return False, None, receipt

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/NatesVibeCode/free-fleet",
            "X-Title": "free-fleet",
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

        provider_cfg = {}
        if policy:
            if getattr(policy, "zdr", False) or not getattr(policy, "allow_data_collection", True):
                provider_cfg["data_collection"] = "deny"
            if getattr(policy, "zdr", False):
                provider_cfg["zdr"] = True
            if getattr(policy, "openrouter_order", None):
                provider_cfg["order"] = policy.openrouter_order
            elif getattr(policy, "openrouter_providers", None):
                provider_cfg["order"] = policy.openrouter_providers
            elif getattr(policy, "allowed_providers", None):
                transports = {"openrouter", "opencode", "openai_compatible", "ollama", "lmstudio", "vllm", "groq", "cerebras"}
                upstream = [p for p in policy.allowed_providers if p.lower() not in transports]
                if upstream:
                    provider_cfg["order"] = upstream
            if getattr(policy, "openrouter_ignore", None):
                provider_cfg["ignore"] = policy.openrouter_ignore
            if hasattr(policy, "openrouter_allow_fallbacks") and not policy.openrouter_allow_fallbacks:
                provider_cfg["allow_fallbacks"] = False
        if provider_cfg:
            payload["provider"] = provider_cfg

        try:
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                
                if resp.status_code == 429:
                    retry_hdr = resp.headers.get("retry-after")
                    try:
                        retry_sec = max(1.0, float(retry_hdr)) if retry_hdr else 10.0
                    except (ValueError, TypeError):
                        retry_sec = 10.0
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
                
                reported_cost = usage.get("cost") if isinstance(usage, dict) else None
                if reported_cost is None:
                    reported_cost = data.get("cost")
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
