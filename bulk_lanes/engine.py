"""Core execution engine coordinating lanes, verification, and manifests."""
import concurrent.futures
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .catalog import RouteCatalog
from .export import export_clean_packet
from .grounding import verify_grounding
from .manifest import ManifestManager
from .packer import pack_items
from .providers.base import clean_llm_json
from .providers.opencode import OpenCodeProvider
from .providers.openrouter import OpenRouterProvider
from .sandbox import SandboxRunner
from .task import Task
from . import ui

class Engine:
    def __init__(
        self,
        task: Task,
        catalog: Optional[RouteCatalog] = None,
        use_docker: Optional[bool] = None,
        max_attempts_per_batch: int = 3
    ):
        self.task = task
        self.catalog = catalog or RouteCatalog()
        self.sandbox = SandboxRunner(use_docker=use_docker)
        self.opencode_prov = OpenCodeProvider(sandbox=self.sandbox)
        self.openrouter_prov = OpenRouterProvider()
        self.max_attempts_per_batch = max_attempts_per_batch

    def execute_batch(self, batch: Dict[str, Any]) -> Tuple[bool, Optional[List[dict]], dict, Optional[str]]:
        """Executes a single multi-item batch with ladder fallbacks and quote verification."""
        batch_id = batch["batch_id"]
        items = batch["items"]
        
        # Build prompt payload
        simplified_items = []
        for itm in items:
            simplified_items.append({
                "item_id": itm["item_id"],
                "title": itm.get("title", ""),
                "sections": [{"slice": s["slice_id"], "text": s["text"]} for s in itm.get("slices", [])]
            })

        user_content = self.task.user_prompt_template.format(
            items_json=json.dumps(simplified_items, indent=2)
        )

        # Get route ladder
        ladder = self.catalog.get_ladder(task_seed=batch_id, free_only=True)
        if not ladder:
            ladder = self.catalog.get_ladder(task_seed=batch_id, free_only=False)
        
        if not ladder:
            return False, None, {}, "No available routes configured in catalog."

        last_err = "No attempts made"
        last_receipt = {}

        for route_id in ladder[:self.max_attempts_per_batch]:
            # Select provider
            if route_id.startswith("openrouter/") or "openrouter" in route_id:
                provider = self.openrouter_prov
            else:
                provider = self.opencode_prov

            ok, response_text, receipt = provider.run_prompt(
                route_id=route_id,
                prompt=user_content,
                system_prompt=self.task.system_prompt
            )
            last_receipt = receipt

            if not ok:
                last_err = receipt.get("error", "Unknown provider error")
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
                continue

            extracted_items = parsed.get("items")
            if not isinstance(extracted_items, list):
                last_err = f"Missing 'items' array in response from '{route_id}'"
                continue

            # Verify mathematical grounding (exact quote match against supplied slices)
            grounded, ground_err = verify_grounding(
                extracted_items=extracted_items,
                raw_cards=items,
                quote_field=self.task.quote_field,
                min_quote_chars=self.task.min_quote_chars
            )

            if not grounded:
                last_err = f"Grounding verification failed: {ground_err}"
                continue

            # Success!
            return True, extracted_items, receipt, None

        return False, None, last_receipt, last_err

    def run_campaign(
        self,
        raw_items: List[Dict[str, Any]],
        run_dir: Path,
        concurrency: int = 4,
        max_attempts: int = 300,
        output_packet_path: Optional[Path] = None
    ) -> dict:
        """Executes full bulk run with resumption and concurrent worker lanes."""
        manifest = ManifestManager(run_dir=run_dir, total_items=len(raw_items), max_attempts=max_attempts)
        batches = pack_items(raw_items, batch_size=self.task.batch_size, max_slice_chars=self.task.max_slice_chars)

        pending_batches = []
        for b in batches:
            bid = b["batch_id"]
            existing = manifest.data["batches"].get(bid)
            if not existing or existing.get("status") != "verified":
                pending_batches.append(b)

        ui.info(f"Loaded {len(raw_items)} items packed into {len(batches)} batches.")
        if len(batches) - len(pending_batches) > 0:
            ui.info(f"Resuming: {len(batches) - len(pending_batches)} batches already verified.")

        total_pending = len(pending_batches)
        completed_count = len(batches) - total_pending

        def worker(batch):
            bid = batch["batch_id"]
            item_ids = [it["item_id"] for it in batch["items"]]
            
            # Pre-reserve attempt before execution
            reserved = manifest.reserve_batch(bid, item_ids)
            if not reserved:
                return bid, False, None, {}, "Attempt budget exceeded"

            ok, res, receipt, err = self.execute_batch(batch)
            if ok:
                manifest.record_batch_success(bid, res, receipt)
            else:
                manifest.record_batch_failure(bid, err or "Unknown error", receipt)
            return bid, ok, res, receipt, err

        if pending_batches:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(worker, b) for b in pending_batches]
                for f in concurrent.futures.as_completed(futures):
                    bid, ok, res, receipt, err = f.result()
                    completed_count += 1
                    status_text = "Verified" if ok else f"Failed ({err[:35]}...)"
                    ui.print_progress(completed_count, len(batches), prefix="Progress:", suffix=status_text)

        manifest.finalize()
        export_path = output_packet_path or (run_dir / "clean_packet.json")
        packet = export_clean_packet(manifest.data, export_path)
        
        ui.success(f"Campaign finished! Clean packet exported to: {export_path}")
        ui.info(f"Verified items: {packet['total_verified_records']} | Total tokens: {packet['audit']['total_tokens_consumed']}")
        return packet
