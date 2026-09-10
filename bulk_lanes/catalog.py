"""Route catalog and dynamic circuit-breaker management with automated free-schema discovery."""
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "routes.json"

class RouteCircuitBreaker(Exception):
    pass

def is_free_in_schema(model_data: dict) -> bool:
    """Detects if a model qualifies as free by checking if 'free' appears in its schema or if cost is 0."""
    # 1. Direct pricing check if available
    pricing = model_data.get("pricing") or model_data.get("cost") or {}
    try:
        p_in = float(pricing.get("prompt") or pricing.get("input") or 0)
        p_out = float(pricing.get("completion") or pricing.get("output") or 0)
        cache_read = float(pricing.get("cache", {}).get("read") or 0)
        cache_write = float(pricing.get("cache", {}).get("write") or 0)
        if p_in == 0 and p_out == 0 and cache_read == 0 and cache_write == 0 and ("pricing" in model_data or "cost" in model_data):
            return True
    except (ValueError, TypeError):
        pass

    # 2. Check if the word "free" appears in the model schema (id, name, description, tags, pricing strings)
    schema_dump = json.dumps(model_data).lower()
    if re.search(r"(\bfree\b|:free|-free|_free)", schema_dump):
        return True

    return False

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
        """Queries OpenCode CLI catalogue, scans for 'free' in schema, and registers matching routes."""
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
        discovered_count = 0

        for model_id, model_data in models.items():
            is_free = is_free_in_schema(model_data)
            is_active = model_data.get("status") == "active"

            if model_id in known:
                r = known[model_id]
                r["zero_price_verified"] = is_free
                r["enabled"] = is_free and is_active
                r["last_verified"] = time.strftime("%Y-%m-%d")
                r["verification_source"] = "opencode models opencode --verbose (schema scan)"
            elif is_free and is_active:
                self.data["routes"].append({
                    "id": model_id,
                    "provider": "opencode",
                    "enabled": True,
                    "zero_price_verified": True,
                    "auth": "hosted-free",
                    "last_verified": time.strftime("%Y-%m-%d"),
                    "verification_source": "opencode models opencode --verbose (schema scan)"
                })
            if is_free:
                discovered_count += 1

        self.save()
        return discovered_count

    def refresh_from_openrouter(self) -> int:
        """Queries OpenRouter API, scans all models for 'free' in schema/pricing, and registers them."""
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get("https://openrouter.ai/api/v1/models")
                if resp.status_code != 200:
                    raise RuntimeError(f"OpenRouter models API returned HTTP {resp.status_code}")
                data = resp.json().get("data", [])
        except Exception as e:
            raise RuntimeError(f"Failed to fetch OpenRouter models: {e}")

        known = {r["id"]: r for r in self.data.get("routes", [])}
        discovered_count = 0

        for m in data:
            if is_free_in_schema(m):
                raw_id = m.get("id", "")
                route_id = f"openrouter/{raw_id}" if not raw_id.startswith("openrouter/") else raw_id
                
                if route_id in known:
                    r = known[route_id]
                    r["zero_price_verified"] = True
                    r["enabled"] = True
                    r["last_verified"] = time.strftime("%Y-%m-%d")
                    r["verification_source"] = "openrouter /api/v1/models (schema scan)"
                else:
                    self.data["routes"].append({
                        "id": route_id,
                        "provider": "openrouter",
                        "enabled": True,
                        "zero_price_verified": True,
                        "auth": "api-key",
                        "cost_per_1k_input": 0.0,
                        "cost_per_1k_output": 0.0,
                        "last_verified": time.strftime("%Y-%m-%d"),
                        "verification_source": "openrouter /api/v1/models (schema scan)"
                    })
                discovered_count += 1

        self.save()
        return discovered_count

    def refresh_all(self) -> Dict[str, int]:
        """Scans all providers for free models automatically."""
        results = {}
        try:
            results["opencode"] = self.refresh_from_opencode()
        except Exception as e:
            results["opencode_error"] = str(e)
            
        try:
            results["openrouter"] = self.refresh_from_openrouter()
        except Exception as e:
            results["openrouter_error"] = str(e)

        return results
