"""Resumable campaign manifest and attempt budget manager."""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

class ManifestManager:
    def __init__(self, run_dir: Path, total_items: int = 0, max_attempts: int = 200):
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.run_dir / "manifest.json"
        self.data = self._load(total_items, max_attempts)

    def _load(self, total_items: int, max_attempts: int) -> dict:
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text())
            except Exception:
                pass
        return {
            "run_id": self.run_dir.name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "running",
            "total_items": total_items,
            "max_attempts": max_attempts,
            "attempts_used": 0,
            "batches": {}
        }

    def save(self):
        tmp = self.manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.manifest_path)

    def get_remaining_attempts(self) -> int:
        return max(0, self.data["max_attempts"] - self.data["attempts_used"])

    def reserve_batch(self, batch_id: str, item_ids: List[str]) -> bool:
        """Reserves budget attempts for a batch before execution to guard against runaway retries."""
        if self.get_remaining_attempts() < 1:
            return False
        if batch_id not in self.data["batches"]:
            self.data["batches"][batch_id] = {
                "batch_id": batch_id,
                "item_ids": item_ids,
                "status": "pending",
                "attempts": 0,
                "result": None,
                "error": None
            }
        self.data["batches"][batch_id]["attempts"] += 1
        self.data["attempts_used"] += 1
        self.save()
        return True

    def record_batch_success(self, batch_id: str, results: List[Dict[str, Any]], receipt: dict):
        if batch_id in self.data["batches"]:
            self.data["batches"][batch_id]["status"] = "verified"
            self.data["batches"][batch_id]["result"] = results
            self.data["batches"][batch_id]["receipt"] = receipt
            self.data["batches"][batch_id]["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.save()

    def record_batch_failure(self, batch_id: str, error: str, receipt: Optional[dict] = None):
        if batch_id in self.data["batches"]:
            self.data["batches"][batch_id]["status"] = "failed"
            self.data["batches"][batch_id]["error"] = error
            self.data["batches"][batch_id]["receipt"] = receipt
            self.save()

    def finalize(self):
        statuses = [b.get("status") for b in self.data["batches"].values()]
        if all(s == "verified" for s in statuses) and statuses:
            self.data["status"] = "completed"
        elif any(s == "failed" for s in statuses):
            self.data["status"] = "completed_with_failures"
        else:
            self.data["status"] = "budget_exhausted"
        self.data["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save()
