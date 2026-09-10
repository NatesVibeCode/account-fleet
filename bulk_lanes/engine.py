"""Core execution engine coordinating SQLite-leased model workers."""
import concurrent.futures
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import ValidationError
from .catalog import RouteCatalog
from .export import export_clean_packet
from .grounding import normalize_grounding
from .models import CandidateModelOutput, InputItem, PackedBatch, ProviderReceipt, TaskSpec
from .packer import pack_items
from .providers.base import clean_llm_json
from .providers.opencode import OpenCodeProvider
from .providers.openrouter import OpenRouterProvider
from .sessions import SessionPool, WorkerSession
from .store import BulkLanesStore, digest_json

class Engine:
    def __init__(
        self,
        task: TaskSpec,
        catalog: Optional[RouteCatalog] = None,
        store: BulkLanesStore | None = None,
        max_attempts_per_batch: int = 3
    ):
        self.task = task
        self.store = store or (catalog.store if catalog else BulkLanesStore())
        self.catalog = catalog or RouteCatalog(db_path=self.store.path)
        self.opencode_prov = OpenCodeProvider()
        self.openrouter_prov = OpenRouterProvider()
        self.max_attempts_per_batch = max_attempts_per_batch

    def execute_batch(
        self,
        batch: Dict[str, Any],
        session: Optional[WorkerSession] = None,
        route_offset: int = 0,
        route_attempt_limit: int | None = None,
    ) -> Tuple[bool, Optional[List[dict]], dict, Optional[str]]:
        """Executes a single multi-item batch within a worker session."""
        batch = PackedBatch.model_validate(batch).model_dump(mode="json")
        batch_id = batch["batch_id"]
        items = batch["items"]
        session_id = session.session_id if session else None
        
        # Build prompt payload
        simplified_items = []
        for itm in items:
            simplified_items.append({
                "item_id": itm["item_id"],
                "title": itm.get("title", ""),
                "sections": [
                    {
                        "slice_id": s["slice_id"],
                        "start": s["start"],
                        "end": s["end"],
                        "text": s["text"],
                    }
                    for s in itm.get("slices", [])
                ]
            })

        user_content = self.task.render_prompt(simplified_items)

        # Get route ladder; prioritize session assigned route if provided
        ladder = self.catalog.get_ladder(task_seed=batch_id, free_only=True)
        if session and session.route_id in ladder:
            ladder = [session.route_id] + [r for r in ladder if r != session.route_id]

        if ladder and route_offset:
            start = route_offset % len(ladder)
            ladder = ladder[start:] + ladder[:start]

        if not ladder:
            return False, None, {}, "No enabled route has observed zero pricing."

        last_err = "No attempts made"
        last_receipt = {}

        attempt_limit = route_attempt_limit or self.max_attempts_per_batch
        for route_id in ladder[:attempt_limit]:
            if route_id.startswith("openrouter/") or "openrouter" in route_id:
                provider = self.openrouter_prov
            else:
                provider = self.opencode_prov

            ok, response_text, receipt = provider.run_prompt(
                route_id=route_id,
                prompt=user_content,
                system_prompt=self.task.instructions,
                session_id=session_id
            )
            last_receipt = receipt

            try:
                ProviderReceipt.model_validate(receipt)
            except ValidationError as exc:
                last_err = f"Invalid provider receipt from '{route_id}': {exc}"
                if session:
                    session.record_error(last_err)
                continue

            if not ok:
                last_err = receipt.get("error", "Unknown provider error")
                if session:
                    session.record_error(f"[{route_id}] {last_err}")
                continue

            # Record cost to monitor zero-price guarantee & circuit breaker
            try:
                self.catalog.record_cost(route_id, receipt.get("cost"))
            except Exception as e:
                return False, None, receipt, str(e)

            # Parse JSON
            parsed = clean_llm_json(response_text)
            if not parsed or not isinstance(parsed, dict):
                last_err = f"Malformed JSON from route '{route_id}'"
                if session:
                    session.record_error(last_err)
                continue

            try:
                candidate_output = CandidateModelOutput.model_validate(parsed)
                for extracted_item in candidate_output.items:
                    self.task.validate_claims(extracted_item.claims)
            except (ValidationError, ValueError) as exc:
                last_err = f"Typed output validation failed for '{route_id}': {exc}"
                if session:
                    session.record_error(last_err)
                continue

            output_items, ground_err = normalize_grounding(
                extracted_items=candidate_output.items,
                raw_cards=items,
                min_quote_chars=self.task.min_quote_chars
            )

            if output_items is None:
                last_err = f"Grounding verification failed: {ground_err}"
                if session:
                    session.record_error(last_err)
                continue

            # Record session success
            if session:
                tokens = receipt.get("usage", {}).get("total_tokens", 0) if isinstance(receipt.get("usage"), dict) else 0
                cost = receipt.get("cost", 0.0) or 0.0
                session.record_batch_success(items_count=len(output_items), tokens=tokens, cost=cost)

            return True, [item.model_dump(mode="json") for item in output_items], receipt, None

        return False, None, last_receipt, last_err

    def run_campaign(
        self,
        raw_items: list[InputItem | dict[str, Any]],
        run_id: str,
        input_path: str,
        concurrency: int = 4,
        max_attempts: int = 300,
        output_packet_path: Optional[Path] = None
    ) -> dict:
        """Register a campaign in SQLite, then execute its leased batches."""
        batches = pack_items(raw_items, batch_size=self.task.batch_size, max_slice_chars=self.task.max_slice_chars)
        task_revision = self.store.register_task(self.task)
        canonical_input = [
            item.model_dump(mode="json", by_alias=True) if hasattr(item, "model_dump") else item
            for item in raw_items
        ]
        output_path = (output_packet_path or Path("runs") / run_id / "clean_packet.json").expanduser().resolve()
        self.store.create_run(
            run_id=run_id,
            task_revision_id=task_revision,
            input_path=input_path,
            input_digest=digest_json(canonical_input),
            total_items=len(raw_items),
            max_attempts=max_attempts,
            batch_size=self.task.batch_size,
            output_path=str(output_path),
        )
        self.store.enqueue_batches(run_id, batches, self.max_attempts_per_batch)
        return self.resume_campaign(run_id, concurrency=concurrency, output_packet_path=output_path)

    def resume_campaign(
        self,
        run_id: str,
        concurrency: int = 4,
        output_packet_path: Optional[Path] = None,
    ) -> dict:
        """Resume pending SQLite queue work without reconstructing it from input files."""
        self.task = self.store.get_run_task(run_id)

        available_free_routes = self.catalog.get_ladder(task_seed=str(time.time()), free_only=True)
        if not available_free_routes:
            raise RuntimeError("No enabled route has observed zero pricing.")
        session_pool = SessionPool(num_sessions=concurrency, routes=available_free_routes)
        sessions_list = session_pool.get_all_sessions()

        def session_worker(session: WorkerSession) -> None:
            while True:
                lease = self.store.lease_batch(run_id, session.session_id)
                if lease is None:
                    return
                batch = lease["batch"]
                ok, results, raw_receipt, error = self.execute_batch(
                    batch,
                    session=session,
                    route_offset=lease["attempt_number"] - 1,
                    route_attempt_limit=1,
                )
                try:
                    receipt = ProviderReceipt.model_validate(raw_receipt) if raw_receipt else None
                except ValidationError:
                    receipt = None
                if ok and results is not None and receipt is not None:
                    self.store.complete_batch(run_id, lease["attempt_id"], session.session_id, results, receipt)
                else:
                    self.store.fail_batch(
                        run_id,
                        lease["attempt_id"],
                        session.session_id,
                        error or "Unknown error",
                        receipt,
                    )

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            list(executor.map(session_worker, sessions_list))

        for s in sessions_list:
            s.finish()

        self.store.save_sessions(run_id, session_pool.to_dict())
        self.store.finalize_run(run_id)
        snapshot = self.store.run_snapshot(run_id)
        export_path = output_packet_path or Path(snapshot["output_path"])
        packet = export_clean_packet(snapshot, export_path)
        
        return packet
