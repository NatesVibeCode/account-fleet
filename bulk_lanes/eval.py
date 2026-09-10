"""Continuous automated evaluation harness measuring route capabilities across free and local models."""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from .catalog import RouteCatalog
from .grounding import normalize_grounding
from .models import CandidateModelOutput, InputItem, ProviderReceipt, RouteEvalReport, RouteEvalResult, TaskSpec
from .providers.base import clean_llm_json
from .providers.registry import ProviderRegistry
from .store import BulkLanesStore


class RouteEvaluator:
    def __init__(
        self,
        task: TaskSpec,
        store: Optional[BulkLanesStore] = None,
        catalog: Optional[RouteCatalog] = None,
        registry: Optional[ProviderRegistry] = None,
    ):
        self.task = task
        self.store = store or BulkLanesStore()
        self.catalog = catalog or RouteCatalog(db_path=self.store.path)
        self.registry = registry or ProviderRegistry()

    def evaluate_route(
        self,
        route_id: str,
        samples: List[InputItem],
        expected_claims_key: Optional[str] = None,
    ) -> RouteEvalResult:
        routes_by_id = {r["id"]: r for r in self.catalog.data.get("routes", [])}
        route_info = routes_by_id.get(route_id, {})
        provider_hint = route_info.get("provider")
        provider = self.registry.resolve(provider_hint, route_id)

        total = len(samples)
        schema_passed = 0
        grounding_passed = 0
        correct_count = 0
        rate_limits = 0
        errors = 0
        durations: List[float] = []

        # Evaluate sample by sample (or small batch)
        for item in samples:
            prompt = self.task.render_prompt([{
                "item_id": item.item_id,
                "title": item.title or "",
                "sections": [{
                    "slice_id": "full",
                    "start": 0,
                    "end": len(item.text),
                    "text": item.text,
                }]
            }])

            ok, response_text, receipt = provider.run_prompt(
                route_id=route_id,
                prompt=prompt,
                system_prompt=self.task.instructions,
            )

            dur = receipt.get("duration_seconds")
            if dur is not None and dur > 0:
                durations.append(dur)

            if not ok:
                errors += 1
                if receipt.get("error_type") == "rate_limit" or "429" in str(receipt.get("error", "")):
                    rate_limits += 1
                continue

            parsed = clean_llm_json(response_text)
            if not parsed or not isinstance(parsed, dict):
                errors += 1
                continue

            try:
                candidate = CandidateModelOutput.model_validate(parsed)
                for extracted in candidate.items:
                    self.task.validate_claims(extracted.claims)
                schema_passed += 1
            except (ValidationError, ValueError):
                errors += 1
                continue

            import hashlib
            source_digest = hashlib.sha256(item.text.encode()).hexdigest()
            output_items, ground_err = normalize_grounding(
                extracted_items=candidate.items,
                raw_cards=[{
                    "item_id": item.item_id,
                    "source_digest": source_digest,
                    "content_type": item.content_type,
                    "slices": [{"slice_id": "full", "start": 0, "end": len(item.text), "text": item.text}],
                }],
                min_quote_chars=self.task.min_quote_chars,
            )

            if output_items is None:
                errors += 1
                continue

            grounding_passed += 1

            # Check correctness if expected claims provided in item metadata
            if expected_claims_key and expected_claims_key in item.metadata:
                expected_raw = item.metadata[expected_claims_key]
                actual_claims = candidate.items[0].claims
                if isinstance(expected_raw, dict):
                    if actual_claims == expected_raw:
                        correct_count += 1
                elif str(actual_claims.get(expected_claims_key, "")).lower() == str(expected_raw).lower():
                    correct_count += 1

        avg_lat = (sum(durations) / len(durations)) if durations else 0.0
        schema_rate = (schema_passed / total) if total > 0 else 0.0
        grounding_rate = (grounding_passed / total) if total > 0 else 0.0
        accuracy = (correct_count / total) if (expected_claims_key and total > 0) else None

        # Latency score normalized (0-30s)
        lat_score = max(0.1, 1.0 - (min(30.0, avg_lat) / 30.0) * 0.5)

        # Composite score
        if accuracy is not None:
            comp = 0.35 * schema_rate + 0.35 * grounding_rate + 0.20 * accuracy + 0.10 * lat_score
        else:
            comp = 0.45 * schema_rate + 0.45 * grounding_rate + 0.10 * lat_score

        if rate_limits > 0:
            comp *= max(0.2, 1.0 - (rate_limits / total) * 0.5)

        comp = round(max(0.0, min(1.0, comp)), 3)

        result = RouteEvalResult(
            route_id=route_id,
            provider=provider_hint or "unknown",
            total_samples=total,
            schema_pass_count=schema_passed,
            grounding_pass_count=grounding_passed,
            correct_count=correct_count if expected_claims_key else None,
            rate_limit_count=rate_limits,
            error_count=errors,
            schema_pass_rate=round(schema_rate, 3),
            grounding_pass_rate=round(grounding_rate, 3),
            accuracy=round(accuracy, 3) if accuracy is not None else None,
            avg_latency_seconds=round(avg_lat, 2),
            composite_score=comp,
        )

        # Persist to database to immediately steer future routing decisions
        self.store.record_route_eval({
            "task_name": self.task.name,
            "route_id": route_id,
            "provider": provider_hint or "unknown",
            "total_samples": total,
            "schema_pass_count": schema_passed,
            "grounding_pass_count": grounding_passed,
            "correct_count": correct_count if expected_claims_key else None,
            "rate_limit_count": rate_limits,
            "error_count": errors,
            "avg_latency_seconds": avg_lat,
            "composite_score": comp,
        })

        return result

    def evaluate_all(
        self,
        samples: List[InputItem],
        routes: Optional[List[str]] = None,
        expected_claims_key: Optional[str] = None,
    ) -> RouteEvalReport:
        target_routes = routes or self.catalog.get_ladder(free_only=True)
        results = []
        for rid in target_routes:
            results.append(self.evaluate_route(rid, samples, expected_claims_key=expected_claims_key))

        # Sort by composite score descending
        results.sort(key=lambda r: r.composite_score, reverse=True)

        return RouteEvalReport(
            task=self.task.name,
            samples=len(samples),
            evaluated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            routes=results,
        )
