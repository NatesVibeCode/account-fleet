"""Route catalog and dynamic circuit-breaker management with automated free-schema discovery."""
import hashlib
import json
import re
import shutil
import subprocess
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx

from .models import RouteInfo
from .store import BulkLanesStore

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "data" / "routes.seed.json"

class RouteCircuitBreaker(Exception):
    pass

class PriceState(str, Enum):
    CANDIDATE = "candidate"
    PRICE_OBSERVED_ZERO = "price_observed_zero"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


def _observed_prices(model_data: dict) -> list[float] | None:
    pricing = model_data.get("pricing") or model_data.get("cost")
    if isinstance(pricing, dict):
        input_value = pricing.get("prompt", pricing.get("input"))
        output_value = pricing.get("completion", pricing.get("output"))
        if input_value is None or output_value is None:
            return None
        raw_values: list[Any] = []

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect(nested)
            elif value is not None:
                raw_values.append(value)

        collect(pricing)
        try:
            return [float(value) for value in raw_values]
        except (TypeError, ValueError):
            return None
    return None


def classify_price_state(model_data: dict) -> PriceState:
    """Classify evidence without treating marketing text as observed pricing."""
    prices = _observed_prices(model_data)
    if prices is not None:
        return PriceState.PRICE_OBSERVED_ZERO if all(value == 0 for value in prices) else PriceState.UNKNOWN
    schema_dump = json.dumps(model_data).lower()
    if re.search(r"(\bfree\b|:free|-free|_free)", schema_dump):
        return PriceState.CANDIDATE
    return PriceState.UNKNOWN


def is_free_in_schema(model_data: dict) -> bool:
    """Compatibility predicate: true only for explicit observed zero pricing."""
    return classify_price_state(model_data) is PriceState.PRICE_OBSERVED_ZERO

class RouteCatalog:
    def __init__(self, config_path: Optional[Path] = None, db_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._lock = threading.RLock()
        resolved_db = db_path or (self.config_path.with_suffix(".db") if config_path else None)
        self.store = BulkLanesStore(resolved_db)
        if self.store.route_count() == 0:
            self._seed_from_json()
        self.data = self._load()

    def _seed_from_json(self) -> None:
        """Import packaged route hints without treating bundled history as local evidence."""
        if not self.config_path.exists():
            return
        data = json.loads(self.config_path.read_text())
        for raw_route in data.get("routes", []):
            route = dict(raw_route)
            hinted_zero = (
                route.get("price_state") == PriceState.PRICE_OBSERVED_ZERO.value
                or (route.get("cost_per_1k_input") == 0 and route.get("cost_per_1k_output") == 0)
            )
            route["enabled"] = False
            route["price_state"] = PriceState.CANDIDATE.value if hinted_zero else PriceState.UNKNOWN.value
            route["last_verified"] = None
            route["verification_source"] = "packaged route hint; refresh required"
            route.pop("zero_price_verified", None)
            self.store.upsert_route(RouteInfo.model_validate(route))

    def _load(self) -> dict:
        routes = self.store.list_routes(observed_zero_only=False, include_disabled=True)
        return {"revision": 2, "routes": [route.model_dump(mode="json") for route in routes]}

    def save(self):
        with self._lock:
            for raw_route in self.data.get("routes", []):
                self.store.upsert_route(RouteInfo.model_validate(raw_route))

    def get_routes(
        self,
        provider: Optional[str] = None,
        free_only: bool = True,
        include_disabled: bool = False,
    ) -> List[dict]:
        routes = self.data.get("routes", [])
        matched = []
        for r in routes:
            if not include_disabled and not r.get("enabled", False):
                continue
            if provider and r.get("provider") != provider:
                continue
            if free_only and r.get("price_state") != PriceState.PRICE_OBSERVED_ZERO.value:
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
        """Update state from provider-reported cost and stop any route that bills."""
        with self._lock:
            if reported_cost == 0:
                for route in self.data.get("routes", []):
                    if route["id"] == route_id:
                        if route.get("price_state") == PriceState.DISABLED.value:
                            return
                        route["price_state"] = PriceState.PRICE_OBSERVED_ZERO.value
                        route["last_price_observation"] = time.time()
                        self.save()
                        return
            if reported_cost is not None and reported_cost > 0:
                for route in self.data.get("routes", []):
                    if route["id"] == route_id:
                        route["enabled"] = False
                        route["price_state"] = PriceState.DISABLED.value
                        route["disabled_reason"] = f"Circuit breaker tripped: reported cost {reported_cost} > 0 on free route."
                        route["disabled_at"] = time.time()
                        self.save()
                        raise RouteCircuitBreaker(f"Non-zero cost {reported_cost} reported on {route_id}! Route disabled.")

    def refresh_from_opencode(self) -> int:
        """Query OpenCode and record candidates separately from observed zero prices."""
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
            price_state = classify_price_state(model_data)
            is_active = model_data.get("status") == "active"

            if model_id in known:
                r = known[model_id]
                r["price_state"] = price_state.value
                r["enabled"] = price_state is PriceState.PRICE_OBSERVED_ZERO and is_active
                r["last_verified"] = time.strftime("%Y-%m-%d")
                r["verification_source"] = "opencode models opencode --verbose"
            elif price_state in {PriceState.CANDIDATE, PriceState.PRICE_OBSERVED_ZERO} and is_active:
                self.data["routes"].append({
                    "id": model_id,
                    "provider": "opencode",
                    "enabled": price_state is PriceState.PRICE_OBSERVED_ZERO,
                    "price_state": price_state.value,
                    "auth": "hosted-free",
                    "last_verified": time.strftime("%Y-%m-%d"),
                    "verification_source": "opencode models opencode --verbose"
                })
            if price_state in {PriceState.CANDIDATE, PriceState.PRICE_OBSERVED_ZERO}:
                discovered_count += 1

        self.save()
        return discovered_count

    def refresh_from_openrouter(self) -> int:
        """Query OpenRouter and distinguish explicit zero pricing from name candidates."""
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
            price_state = classify_price_state(m)
            if price_state in {PriceState.CANDIDATE, PriceState.PRICE_OBSERVED_ZERO}:
                raw_id = m.get("id", "")
                route_id = f"openrouter/{raw_id}" if not raw_id.startswith("openrouter/") else raw_id
                
                if route_id in known:
                    r = known[route_id]
                    r["price_state"] = price_state.value
                    r["enabled"] = price_state is PriceState.PRICE_OBSERVED_ZERO
                    pricing = m.get("pricing", {})
                    if price_state is PriceState.PRICE_OBSERVED_ZERO:
                        r["cost_per_1k_input"] = float(pricing.get("prompt", pricing.get("input", 0))) * 1000
                        r["cost_per_1k_output"] = float(pricing.get("completion", pricing.get("output", 0))) * 1000
                    else:
                        r.pop("cost_per_1k_input", None)
                        r.pop("cost_per_1k_output", None)
                    r["last_verified"] = time.strftime("%Y-%m-%d")
                    r["verification_source"] = "openrouter /api/v1/models pricing"
                else:
                    route = {
                        "id": route_id,
                        "provider": "openrouter",
                        "enabled": price_state is PriceState.PRICE_OBSERVED_ZERO,
                        "price_state": price_state.value,
                        "auth": "api-key",
                        "last_verified": time.strftime("%Y-%m-%d"),
                        "verification_source": "openrouter /api/v1/models pricing"
                    }
                    if price_state is PriceState.PRICE_OBSERVED_ZERO:
                        pricing = m["pricing"]
                        route["cost_per_1k_input"] = float(pricing.get("prompt", pricing.get("input", 0))) * 1000
                        route["cost_per_1k_output"] = float(pricing.get("completion", pricing.get("output", 0))) * 1000
                    self.data["routes"].append(route)
                discovered_count += 1

        self.save()
        return discovered_count

    def refresh_all(self) -> Dict[str, int]:
        """Refresh observed-zero routes and unverified candidates."""
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
