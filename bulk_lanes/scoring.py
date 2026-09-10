"""Intelligent route scoring engine integrating historical receipts and continuous eval data."""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional
from .models import RoutePolicy
from .store import BulkLanesStore


class RouteScorer:
    def __init__(self, store: BulkLanesStore):
        self.store = store

    def score_routes(
        self,
        routes: List[Dict[str, Any]],
        task_name: Optional[str] = None,
    ) -> Dict[str, float]:
        """Compute rolling composite quality score for each route in [0.0, 1.0]."""
        history_stats = self.store.get_route_history_stats(task_name)
        evals = self.store.get_route_evals(task_name)
        active_cooldowns = self.store.get_active_cooldowns()

        # Map latest eval composite_score per route
        latest_evals: Dict[str, float] = {}
        for ev in evals:
            rid = ev["route_id"]
            if rid not in latest_evals:
                latest_evals[rid] = float(ev.get("composite_score", 0.5))

        scores: Dict[str, float] = {}
        now = time.time()

        for r in routes:
            rid = r["id"]

            # If actively cooled down, assign zero score
            if rid in active_cooldowns and active_cooldowns[rid] > now:
                scores[rid] = 0.0
                continue

            stat = history_stats.get(rid)
            if not stat or stat["total"] == 0:
                # Untested route: optimistic exploration prior
                base_score = 0.55
            else:
                total = stat["total"]
                completed = stat["completed"]
                rate_limits = stat["rate_limits"]
                avg_duration = stat["avg_duration"]

                # Laplace-smoothed success rate
                success_rate = (completed + 1.0) / (total + 2.0)

                # Rate limit penalty
                rl_ratio = rate_limits / max(1, total)
                rate_limit_factor = max(0.2, 1.0 - (rl_ratio * 0.5))

                # Latency factor (penalize slow models over 30s)
                latency_factor = max(0.3, 1.0 - (min(30.0, avg_duration) / 30.0) * 0.4)

                base_score = success_rate * rate_limit_factor * latency_factor

            # Combine with benchmark evaluation score if available
            if rid in latest_evals:
                final_score = 0.6 * latest_evals[rid] + 0.4 * base_score
            else:
                final_score = base_score

            scores[rid] = round(max(0.01, min(1.0, final_score)), 4)

        return scores


def filter_and_rank_routes(
    routes: List[Dict[str, Any]],
    store: BulkLanesStore,
    task_name: Optional[str] = None,
    policy: Optional[RoutePolicy] = None,
    seed: str = "",
) -> List[str]:
    """Filter routes by policy and rank by intelligent composite score."""
    filtered: List[Dict[str, Any]] = []

    for r in routes:
        rid = r["id"]
        prov = (r.get("provider") or rid.split("/", 1)[0]).lower()

        if policy:
            if policy.allowed_providers and prov not in [p.lower() for p in policy.allowed_providers]:
                continue
            if policy.excluded_providers and prov in [p.lower() for p in policy.excluded_providers]:
                continue
            if policy.allowed_routes and rid not in policy.allowed_routes:
                continue
            if policy.excluded_routes and rid in policy.excluded_routes:
                continue
            if policy.max_cost_per_1k_input > 0 or policy.max_cost_per_1k_output > 0:
                cost_in = r.get("cost_per_1k_input", 0.0) or 0.0
                cost_out = r.get("cost_per_1k_output", 0.0) or 0.0
                if cost_in > policy.max_cost_per_1k_input or cost_out > policy.max_cost_per_1k_output:
                    continue

        filtered.append(r)

    if not filtered:
        return []

    scorer = RouteScorer(store)
    score_map = scorer.score_routes(filtered, task_name=task_name)

    def sort_key(route_dict: Dict[str, Any]) -> tuple[float, int]:
        rid = route_dict["id"]
        score = score_map.get(rid, 0.0)
        # Secondary tie breaker: deterministic hash of (seed, route_id) for load distribution among peers
        tie_breaker = 0
        if seed:
            tie_breaker = int(hashlib.sha256(f"{seed}:{rid}".encode()).hexdigest()[:6], 16)
        return (score, tie_breaker)

    sorted_routes = sorted(filtered, key=sort_key, reverse=True)
    return [r["id"] for r in sorted_routes]
