"""SQLite control plane adapted from the proven career research worker queue."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ExtractedItem, ID_PATTERN, PackedBatch, ProviderReceipt, RouteInfo, TaskSpec, WorkerSessionRecord


SCHEMA_VERSION = "1"

SCHEMA_PATH = Path(__file__).resolve().parent / "migrations" / "001_control_plane.sql"
SCHEMA_SQL = SCHEMA_PATH.read_text()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def default_db_path() -> Path:
    configured = os.environ.get("BULK_LANES_DB")
    return Path(configured).expanduser() if configured else Path.cwd() / "bulk-lanes.db"


class BulkLanesStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            connection.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            pass
        return connection

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                "INSERT INTO bulk_meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (SCHEMA_VERSION,),
            )

    def schema_version(self) -> str:
        with self.connect() as connection:
            row = connection.execute("SELECT value FROM bulk_meta WHERE key='schema_version'").fetchone()
        return str(row["value"])

    def register_task(self, spec: TaskSpec) -> str:
        payload = spec.model_dump(mode="json", by_alias=True)
        revision_id = digest_json(payload)
        with self.connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO task_revisions(
                    revision_id,task_name,format_version,instructions,batch_size,max_slice_chars,
                    min_quote_chars,claims_schema_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    revision_id, spec.name, spec.format_version, spec.instructions, spec.batch_size,
                    spec.max_slice_chars, spec.min_quote_chars,
                    json.dumps(spec.claims_schema, separators=(",", ":")), now_iso(),
                ),
            )
            connection.execute(
                "INSERT INTO current_tasks(task_name,revision_id) VALUES(?,?) "
                "ON CONFLICT(task_name) DO UPDATE SET revision_id=excluded.revision_id",
                (spec.name, revision_id),
            )
        return revision_id

    def get_task(self, name: str) -> TaskSpec:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT r.* FROM current_tasks c JOIN task_revisions r ON r.revision_id=c.revision_id WHERE c.task_name=?",
                (name,),
            ).fetchone()
        if row is None:
            raise KeyError(f"task not found: {name}")
        return self._task_from_row(row)

    def get_task_revision(self, revision_id: str) -> TaskSpec:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM task_revisions WHERE revision_id=?", (revision_id,)).fetchone()
        if row is None:
            raise KeyError(f"task revision not found: {revision_id}")
        return self._task_from_row(row)

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> TaskSpec:
        return TaskSpec.model_validate({
            "format_version": row["format_version"],
            "name": row["task_name"],
            "instructions": row["instructions"],
            "batch_size": row["batch_size"],
            "max_slice_chars": row["max_slice_chars"],
            "min_quote_chars": row["min_quote_chars"],
            "claims_schema": json.loads(row["claims_schema_json"]),
        })

    def get_run_task(self, run_id: str) -> TaskSpec:
        with self.connect() as connection:
            row = connection.execute("SELECT task_revision_id FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"run not found: {run_id}")
        return self.get_task_revision(str(row["task_revision_id"]))

    def current_task_revision(self, name: str) -> str:
        with self.connect() as connection:
            row = connection.execute("SELECT revision_id FROM current_tasks WHERE task_name=?", (name,)).fetchone()
        if row is None:
            raise KeyError(f"task not found: {name}")
        return str(row["revision_id"])

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT c.task_name,c.revision_id,r.created_at FROM current_tasks c "
                "JOIN task_revisions r ON r.revision_id=c.revision_id ORDER BY c.task_name"
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_route(self, route: RouteInfo) -> None:
        value = route.model_dump(mode="json")
        observed_at = now_iso()
        observation_id = digest_json({"route": value, "observed_at": observed_at})
        with self.connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO route_observations(
                    observation_id,route_id,route_json,price_state,enabled,provider,observed_at
                ) VALUES(?,?,?,?,?,?,?)""",
                (
                    observation_id, route.id, json.dumps(value, separators=(",", ":")), route.price_state,
                    int(route.enabled), route.provider, observed_at,
                ),
            )
            connection.execute(
                """INSERT INTO current_routes(route_id,observation_id) VALUES(?,?)
                   ON CONFLICT(route_id) DO UPDATE SET observation_id=excluded.observation_id""",
                (route.id, observation_id),
            )
    def route_count(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("SELECT count(*) FROM current_routes").fetchone()[0])

    def list_routes(
        self,
        provider: str | None = None,
        observed_zero_only: bool = True,
        include_disabled: bool = False,
    ) -> list[RouteInfo]:
        query = """SELECT o.route_json FROM current_routes c
                   JOIN route_observations o ON o.observation_id=c.observation_id WHERE 1=1"""
        params: list[Any] = []
        if not include_disabled:
            query += " AND o.enabled=1"
        if provider:
            query += " AND o.provider=?"
            params.append(provider)
        if observed_zero_only:
            query += " AND o.price_state='price_observed_zero'"
        query += " ORDER BY o.route_id"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [RouteInfo.model_validate_json(row["route_json"]) for row in rows]

    def create_run(
        self,
        run_id: str,
        task_revision_id: str,
        input_path: str,
        input_digest: str,
        total_items: int,
        max_attempts: int,
        batch_size: int,
        output_path: str,
    ) -> None:
        if not re.fullmatch(ID_PATTERN, run_id) or len(run_id) > 128:
            raise ValueError("run_id must use 1-128 letters, numbers, dots, underscores, or hyphens")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if existing is not None:
                expected = (task_revision_id, input_digest, total_items, max_attempts, batch_size)
                actual = (
                    existing["task_revision_id"], existing["input_digest"], existing["total_items"],
                    existing["max_attempts"], existing["batch_size"],
                )
                if actual != expected:
                    raise ValueError(f"run_id already exists with different inputs or limits: {run_id}")
                return
            connection.execute(
                """INSERT INTO runs(
                    run_id,task_revision_id,input_path,input_digest,status,total_items,max_attempts,
                    attempts_used,batch_size,output_path,created_at
                ) VALUES(?,?,?,?, 'running',?,?,0,?,?,?)""",
                (run_id, task_revision_id, input_path, input_digest, total_items, max_attempts, batch_size, output_path, now_iso()),
            )

    def enqueue_batches(self, run_id: str, batches: list[dict[str, Any]], max_attempts_per_batch: int) -> None:
        with self.connect() as connection:
            for position, raw_batch in enumerate(batches):
                batch = PackedBatch.model_validate(raw_batch).model_dump(mode="json")
                connection.execute(
                    """INSERT OR IGNORE INTO batches(
                        run_id,batch_id,position,item_ids_json,payload_json,status,attempts,max_attempts
                    ) VALUES(?,?,?,?,?,'pending',0,?)""",
                    (
                        run_id, batch["batch_id"], position,
                        json.dumps([item["item_id"] for item in batch["items"]]),
                        json.dumps(batch, ensure_ascii=False, separators=(",", ":")), max_attempts_per_batch,
                    ),
                )

    def lease_batch(self, run_id: str, worker_id: str, lease_timeout_seconds: int = 300) -> dict[str, Any] | None:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            run = connection.execute("SELECT max_attempts,attempts_used FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(f"run not found: {run_id}")
            if run["attempts_used"] >= run["max_attempts"]:
                connection.commit()
                return None
            row = connection.execute(
                """SELECT * FROM batches
                   WHERE run_id=? AND attempts < max_attempts
                     AND (status='pending' OR (status='leased' AND leased_at < datetime('now', ?)))
                   ORDER BY position LIMIT 1""",
                (run_id, f"-{lease_timeout_seconds} seconds"),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            attempt_number = int(row["attempts"]) + 1
            attempt_id = f"{run_id}:{row['batch_id']}:{attempt_number}"
            connection.execute(
                """UPDATE batches SET status='leased',attempts=?,lease_owner=?,leased_at=CURRENT_TIMESTAMP,error=NULL
                   WHERE run_id=? AND batch_id=?""",
                (attempt_number, worker_id, run_id, row["batch_id"]),
            )
            connection.execute("UPDATE runs SET attempts_used=attempts_used+1,status='running' WHERE run_id=?", (run_id,))
            connection.execute(
                """INSERT INTO batch_attempts(
                    attempt_id,run_id,batch_id,attempt_number,worker_id,status,started_at
                ) VALUES(?,?,?,?,?,'leased',?)""",
                (attempt_id, run_id, row["batch_id"], attempt_number, worker_id, now_iso()),
            )
            connection.commit()
            return {
                "attempt_id": attempt_id,
                "attempt_number": attempt_number,
                "batch": json.loads(row["payload_json"]),
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _insert_receipt(
        self,
        connection: sqlite3.Connection,
        receipt: ProviderReceipt,
        run_id: str | None,
        batch_id: str | None,
    ) -> None:
        payload = receipt.model_dump(mode="json")
        connection.execute(
            """INSERT OR IGNORE INTO model_runs(
                receipt_id,run_id,batch_id,provider,requested_route,status,cost,cost_status,usage_json,
                error,duration_seconds,receipt_json,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                receipt.id, run_id, batch_id, receipt.provider, receipt.requested_route, receipt.status,
                receipt.cost, receipt.cost_status, json.dumps(payload["usage"]), receipt.error,
                receipt.duration_seconds, json.dumps(payload, separators=(",", ":")), now_iso(),
            ),
        )

    def complete_batch(
        self,
        run_id: str,
        attempt_id: str,
        worker_id: str,
        results: list[dict[str, Any]],
        receipt: ProviderReceipt,
    ) -> None:
        batch_id = attempt_id.rsplit(":", 2)[-2]
        validated_results = [ExtractedItem.model_validate(result).model_dump(mode="json") for result in results]
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT b.lease_owner,b.status,b.item_ids_json,t.* FROM batches b
                   JOIN runs r ON r.run_id=b.run_id
                   JOIN task_revisions t ON t.revision_id=r.task_revision_id
                   WHERE b.run_id=? AND b.batch_id=?""",
                (run_id, batch_id),
            ).fetchone()
            if row is None or row["status"] != "leased" or row["lease_owner"] != worker_id:
                raise ValueError("batch lease is not owned by this worker")
            if [result["item_id"] for result in validated_results] != json.loads(row["item_ids_json"]):
                raise ValueError("verified result IDs or order do not match the leased batch")
            task = self._task_from_row(row)
            for result in validated_results:
                task.validate_claims(result["claims"])
            self._insert_receipt(connection, receipt, run_id, batch_id)
            completed = now_iso()
            result_id = digest_json({"run_id": run_id, "batch_id": batch_id, "results": validated_results, "receipt_id": receipt.id})
            connection.execute(
                """INSERT OR IGNORE INTO batch_results(
                    result_id,run_id,batch_id,result_json,receipt_id,created_at
                ) VALUES(?,?,?,?,?,?)""",
                (result_id, run_id, batch_id, json.dumps(validated_results, ensure_ascii=False, separators=(",", ":")), receipt.id, completed),
            )
            connection.execute(
                """INSERT INTO current_batch_results(run_id,batch_id,result_id) VALUES(?,?,?)
                   ON CONFLICT(run_id,batch_id) DO UPDATE SET result_id=excluded.result_id""",
                (run_id, batch_id, result_id),
            )
            connection.execute(
                """UPDATE batches SET status='verified',error=NULL,completed_at=?
                   WHERE run_id=? AND batch_id=?""",
                (completed, run_id, batch_id),
            )
            connection.execute(
                """UPDATE batch_attempts SET status='verified',receipt_id=?,completed_at=? WHERE attempt_id=?""",
                (receipt.id, completed, attempt_id),
            )

    def fail_batch(
        self,
        run_id: str,
        attempt_id: str,
        worker_id: str,
        error: str,
        receipt: ProviderReceipt | None,
    ) -> None:
        batch_id = attempt_id.rsplit(":", 2)[-2]
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT attempts,max_attempts,lease_owner,status FROM batches WHERE run_id=? AND batch_id=?",
                (run_id, batch_id),
            ).fetchone()
            if row is None or row["status"] != "leased" or row["lease_owner"] != worker_id:
                raise ValueError("batch lease is not owned by this worker")
            if receipt is not None:
                self._insert_receipt(connection, receipt, run_id, batch_id)
            next_status = "failed" if row["attempts"] >= row["max_attempts"] else "pending"
            completed = now_iso()
            connection.execute(
                """UPDATE batches SET status=?,error=?,lease_owner=NULL,leased_at=NULL,
                   completed_at=CASE WHEN ?='failed' THEN ? ELSE NULL END WHERE run_id=? AND batch_id=?""",
                (next_status, error, next_status, completed, run_id, batch_id),
            )
            connection.execute(
                """UPDATE batch_attempts SET status='failed',receipt_id=?,error=?,completed_at=? WHERE attempt_id=?""",
                (receipt.id if receipt else None, error, completed, attempt_id),
            )

    def save_sessions(self, run_id: str, sessions: dict[str, dict[str, Any]]) -> None:
        with self.connect() as connection:
            for session_id, raw_payload in sessions.items():
                payload = WorkerSessionRecord.model_validate(raw_payload).model_dump(mode="json")
                if payload["session_id"] != session_id:
                    raise ValueError("worker session key does not match session_id")
                connection.execute(
                    """INSERT INTO worker_sessions(run_id,session_id,session_json) VALUES(?,?,?)
                       ON CONFLICT(run_id,session_id) DO UPDATE SET session_json=excluded.session_json""",
                    (run_id, session_id, json.dumps(payload, separators=(",", ":"))),
                )

    def finalize_run(self, run_id: str) -> str:
        with self.connect() as connection:
            counts = {row["status"]: row["count"] for row in connection.execute(
                "SELECT status,count(*) AS count FROM batches WHERE run_id=? GROUP BY status", (run_id,)
            )}
            run = connection.execute("SELECT max_attempts,attempts_used FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if counts.get("pending", 0) or counts.get("leased", 0):
                status = "budget_exhausted" if run["attempts_used"] >= run["max_attempts"] else "completed_with_failures"
            elif counts.get("failed", 0):
                status = "completed_with_failures"
            else:
                status = "completed"
            connection.execute("UPDATE runs SET status=?,finished_at=? WHERE run_id=?", (status, now_iso(), run_id))
        return status

    def run_snapshot(self, run_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            run = connection.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(f"run not found: {run_id}")
            batch_rows = connection.execute("SELECT * FROM batches WHERE run_id=? ORDER BY position", (run_id,)).fetchall()
            result_rows = connection.execute(
                """SELECT c.batch_id,r.result_json,r.receipt_id FROM current_batch_results c
                   JOIN batch_results r ON r.result_id=c.result_id WHERE c.run_id=?""",
                (run_id,),
            ).fetchall()
            sessions = connection.execute("SELECT session_id,session_json FROM worker_sessions WHERE run_id=?", (run_id,)).fetchall()
            receipts = {
                row["receipt_id"]: json.loads(row["receipt_json"])
                for row in connection.execute(
                    "SELECT receipt_id,receipt_json FROM model_runs WHERE run_id=? ORDER BY created_at,receipt_id",
                    (run_id,),
                )
            }
        current_results = {row["batch_id"]: row for row in result_rows}
        batches = {}
        for row in batch_rows:
            current_result = current_results.get(row["batch_id"])
            receipt = receipts.get(current_result["receipt_id"]) if current_result else None
            batches[row["batch_id"]] = {
                "batch_id": row["batch_id"],
                "item_ids": json.loads(row["item_ids_json"]),
                "status": row["status"],
                "attempts": row["attempts"],
                "result": json.loads(current_result["result_json"]) if current_result else None,
                "error": row["error"],
                "receipt": receipt,
                "completed_at": row["completed_at"],
            }
        task = self.get_task_revision(str(run["task_revision_id"]))
        return {
            "format_version": "bulk_lanes_run_v1",
            "run_id": run["run_id"], "created_at": run["created_at"], "finished_at": run["finished_at"],
            "task": task.model_dump(mode="json", by_alias=True),
            "task_revision": run["task_revision_id"],
            "status": run["status"], "total_items": run["total_items"], "max_attempts": run["max_attempts"],
            "attempts_used": run["attempts_used"], "input_path": run["input_path"],
            "input_digest": run["input_digest"], "output_path": run["output_path"], "batches": batches,
            "sessions": {row["session_id"]: json.loads(row["session_json"]) for row in sessions},
            "model_runs": list(receipts.values()),
        }

    def run_exists(self, run_id: str) -> bool:
        with self.connect() as connection:
            return connection.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone() is not None

    def model_run_count(self, run_id: str) -> int:
        with self.connect() as connection:
            return int(connection.execute("SELECT count(*) FROM model_runs WHERE run_id=?", (run_id,)).fetchone()[0])
