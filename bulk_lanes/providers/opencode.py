"""OpenCode CLI provider running in sandbox isolation."""
import json
import time
import uuid
from typing import Optional, Tuple
from .base import BaseProvider
from ..sandbox import SandboxRunner

class OpenCodeProvider(BaseProvider):
    def __init__(self, sandbox: Optional[SandboxRunner] = None):
        self.sandbox = sandbox or SandboxRunner()

    def run_prompt(
        self,
        route_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout_sec: int = 120
    ) -> Tuple[bool, Optional[str], dict]:
        started = time.time()
        rid = uuid.uuid4().hex
        receipt = {
            "id": rid,
            "provider": "opencode",
            "requested_route": route_id,
            "status": "failed",
            "cost": None,
            "cost_status": "unknown",
            "usage": None,
            "error": None,
            "duration_seconds": None,
        }

        full_prompt = (system_prompt + "\n\n" if system_prompt else "") + prompt
        
        # Hardened opencode configuration: zero permissions, no tools, no MCP, no telemetry sharing
        task_config = {
            "$schema": "https://opencode.ai/config.json",
            "model": route_id,
            "permission": {"*": "deny"},
            "mcp": {},
            "share": "disabled"
        }

        args = ["run", "--format", "json", "--model", route_id, full_prompt]

        try:
            code, stdout, stderr = self.sandbox.run_opencode_task(
                task_config=task_config,
                args=args,
                timeout_sec=timeout_sec
            )

            texts = []
            finished = False
            costs = []
            last_err = None

            for line in stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")
                part = event.get("part", {})

                if event_type == "text":
                    texts.append(part.get("text", ""))
                elif event_type == "step_finish":
                    finished = True
                    c = part.get("cost")
                    if c is not None:
                        costs.append(c)
                    receipt["usage"] = part.get("tokens")
                elif event_type == "error":
                    last_err = str(event.get("error", ""))[:500]

            if code != 0 or not finished or not texts:
                err_msg = last_err or (stderr or stdout)[-500:] or f"Exit code {code}"
                receipt["error"] = err_msg
                receipt["duration_seconds"] = time.time() - started
                return False, None, receipt

            total_cost = sum(costs) if costs and all(isinstance(c, (int, float)) for c in costs) else 0.0
            receipt["cost"] = total_cost
            receipt["cost_status"] = "reported_zero" if total_cost == 0 else "billed"
            receipt["status"] = "complete"
            receipt["duration_seconds"] = time.time() - started
            
            return True, "\n".join(texts), receipt

        except Exception as e:
            receipt["error"] = str(e)
            receipt["duration_seconds"] = time.time() - started
            return False, None, receipt
