"""Route catalog and dynamic circuit-breaker management."""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "routes.json"

class RouteCircuitBreaker(Exception):
    pass

class RouteCatalog:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.data = self._load()

    def _load(self) -> dict:
        if not self.config_path.exists():
            return {"revision": 1, "routes": []}
        return json.loads(self.config_path.read_text())

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.config_path)

    def get_routes(self, provider: Optional[str] = None, free_only: bool = True) -> List[dict]:
        routes = self.data.get("routes", [])
        matched = []
        for r in routes:
            if not r.get("enabled", False):
                continue
            if provider and r.get("provider") != provider:
                continue
            if free_only and not r.get("zero_price_verified", False):
                continue
            matched.append(r)
        return matched

    def get_ladder(self, task_seed: str = "", provider: Optional[str] = None, free_only: bool = True) -> List[str]:
        """Returns a prioritized list of route IDs distributed evenly via task_seed."""
        routes = self.get_routes(provider=provider, free_only=free_only)
        if not routes:
            return []
        ids = [r["id"] for r in routes]
        if not task_seed:
            return ids
        h = int(hashlib.sha256(task_seed.encode()).hexdigest()[:8], 16)
        start = h % len(ids)
        return ids[start:] + ids[:start]

    def record_cost(self, route_id: str, reported_cost: Optional[float]):
        """Trip circuit breaker and disable route if non-zero cost is reported on a zero-price route."""
        if reported_cost is not None and reported_cost > 0:
            for r in self.data.get("routes", []):
                if r["id"] == route_id and r.get("zero_price_verified"):
                    r["enabled"] = False
                    r["disabled_reason"] = f"Circuit breaker tripped: reported cost {reported_cost} > 0 on free route."
                    r["disabled_at"] = time.time()
                    self.save()
                    raise RouteCircuitBreaker(f"Non-zero cost {reported_cost} reported on {route_id}! Route disabled.")

    def mark_verified(self, route_id: str, zero_price: bool = True, source: str = "smoke_test"):
        for r in self.data.get("routes", []):
            if r["id"] == route_id:
                r["enabled"] = True
                r["zero_price_verified"] = zero_price
                r["last_verified"] = time.strftime("%Y-%m-%d")
                r["verification_source"] = source
                self.save()
                return

    def refresh_from_opencode(self) -> int:
        """Queries OpenCode CLI catalogue, parses zero-cost metadata, and registers free routes."""
        if not shutil.which("opencode"):
            raise RuntimeError("opencode CLI not found in PATH")

        res = subprocess.run(
            ["opencode", "models", "opencode", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if res.returncode != 0:
            raise RuntimeError(f"Failed to query opencode models: {res.stderr}")

        text = res.stdout
        models = {}
        decoder = json.JSONDecoder()
        while text.strip():
            text = text.lstrip()
            header, sep, rest = text.partition("\n")
            if not sep:
                break
            if header.startswith("opencode/"):
                try:
                    obj, end = decoder.raw_decode(rest.lstrip())
                    models[header] = obj
                    text = rest.lstrip()[end:]
                except Exception:
                    text = rest
            else:
                text = rest

        known = {r["id"]: r for r in self.data.get("routes", [])}
        updated_count = 0

        for model_id, model in models.items():
            cost = model.get("cost", {})
            cache = cost.get("cache", {})
            is_zero = (
                cost.get("input") == 0
                and cost.get("output") == 0
                and cache.get("read", 0) == 0
                and cache.get("write", 0) == 0
            )
            is_active = model.get("status") == "active"

            if model_id in known:
                r = known[model_id]
                r["zero_price_verified"] = is_zero
                r["enabled"] = is_zero and is_active
                r["last_verified"] = time.strftime("%Y-%m-%d")
                r["verification_source"] = "opencode models opencode --verbose"
            elif is_zero and is_active:
                self.data["routes"].append({
                    "id": model_id,
                    "provider": "opencode",
                    "enabled": True,
                    "zero_price_verified": True,
                    "auth": "hosted-free",
                    "last_verified": time.strftime("%Y-%m-%d"),
                    "verification_source": "opencode models opencode --verbose"
                })
            updated_count += 1

        self.save()
        return updated_count
