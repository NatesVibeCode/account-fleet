from concurrent.futures import ThreadPoolExecutor

import pytest

from free_fleet.models import ProviderReceipt, RouteInfo, TaskSpec
from free_fleet.packer import pack_items
from free_fleet.store import BulkLanesStore, digest_json


def _task():
    return TaskSpec(name="demo")


def _run(store, run_id="run-1", count=1):
    revision = store.register_task(_task())
    records = [{"item_id": f"i{i}", "text": f"source text number {i}"} for i in range(count)]
    batches = pack_items(records, batch_size=1)
    store.create_run(run_id, revision, "input.jsonl", digest_json(records), count, 20, 1, "packet.json")
    store.enqueue_batches(run_id, batches, 3)
    return batches


def test_schema_has_recovered_control_plane_tables(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    with store.connect() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "task_revisions", "current_tasks", "route_observations", "current_routes",
        "runs", "batches", "batch_attempts", "model_runs", "batch_results", "current_batch_results", "worker_sessions",
        "route_cooldowns", "route_evaluations", "inference_attempts",
    } <= tables
    assert store.schema_version() == "4"
    assert {"profile_revisions", "active_profiles"} <= tables
    with store.connect() as connection:
        task_columns = {row[1] for row in connection.execute("PRAGMA table_info(task_revisions)")}
    assert "spec_json" not in task_columns
    assert {"format_version", "instructions", "batch_size", "max_slice_chars", "min_quote_chars", "claims_schema_json"} <= task_columns


def test_concurrent_lease_claims_batch_once(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    _run(store)
    with ThreadPoolExecutor(max_workers=8) as pool:
        leases = list(pool.map(lambda i: store.lease_batch("run-1", f"worker-{i}"), range(8)))
    assert sum(lease is not None for lease in leases) == 1
    assert store.run_snapshot("run-1")["attempts_used"] == 1


def test_twenty_concurrent_leases_are_unique(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    _run(store, count=20)
    with ThreadPoolExecutor(max_workers=20) as pool:
        leases = list(pool.map(lambda i: store.lease_batch("run-1", f"worker-{i}"), range(20)))
    assert all(lease is not None for lease in leases)
    assert len({lease["batch"]["batch_id"] for lease in leases}) == 20
    assert store.run_snapshot("run-1")["attempts_used"] == 20


def test_task_revisions_and_model_receipts_are_append_only(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    batches = _run(store)
    lease = store.lease_batch("run-1", "worker")
    receipt = ProviderReceipt(
        id="receipt-1", provider="fixture", requested_route="fixture/zero", status="complete",
        cost=0.0, cost_status="reported_zero", usage={"total_tokens": 1}, duration_seconds=0.01,
    )
    packed_item = batches[0]["items"][0]
    result = [{
        "item_id": "i0", "source_uri": None, "source_digest": packed_item["source_digest"],
        "content_type": "text/plain", "claims": {"summary": "ok", "category": "test"},
        "quotes": [{"slice_id": "full", "start": 0, "end": 20, "text": "source text number 0"}],
    }]
    store.complete_batch("run-1", lease["attempt_id"], "worker", result, receipt)
    with store.connect() as connection:
        with pytest.raises(Exception, match="append-only"):
            connection.execute("DELETE FROM model_runs")
        with pytest.raises(Exception, match="append-only"):
            connection.execute("UPDATE task_revisions SET task_name='changed'")
        with pytest.raises(Exception, match="append-only"):
            connection.execute("DELETE FROM batch_results")


def test_failed_attempt_requeues_until_batch_limit(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    _run(store)
    for number in range(1, 4):
        lease = store.lease_batch("run-1", f"worker-{number}")
        assert lease["attempt_number"] == number
        store.fail_batch("run-1", lease["attempt_id"], f"worker-{number}", "bad output", None)
    assert store.lease_batch("run-1", "last") is None
    assert store.run_snapshot("run-1")["batches"][next(iter(store.run_snapshot("run-1")["batches"]))]["status"] == "failed"


def test_route_observations_are_versioned_and_current_is_explicit(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    store.upsert_route(RouteInfo(id="provider/model", provider="provider", enabled=False, price_state="candidate"))
    store.upsert_route(RouteInfo(
        id="provider/model", provider="provider", enabled=True, price_state="price_observed_zero",
        cost_per_1k_input=0.0, cost_per_1k_output=0.0,
    ))
    with store.connect() as connection:
        assert connection.execute("SELECT count(*) FROM route_observations").fetchone()[0] == 2
        current = connection.execute(
            "SELECT o.route_json FROM current_routes c JOIN route_observations o ON o.observation_id=c.observation_id"
        ).fetchone()[0]
        assert __import__("json").loads(current)["price_state"] == "price_observed_zero"
        with pytest.raises(Exception, match="append-only"):
            connection.execute("DELETE FROM route_observations")


def test_identical_route_observations_retain_each_event(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    route = RouteInfo(id="provider/model", provider="provider", enabled=False, price_state="candidate")
    store.upsert_route(route)
    store.upsert_route(route)
    with store.connect() as connection:
        assert connection.execute("SELECT count(*) FROM route_observations").fetchone()[0] == 2


def test_run_identifier_cannot_escape_output_shape(tmp_path):
    store = BulkLanesStore(tmp_path / "state.db")
    revision = store.register_task(_task())
    with pytest.raises(ValueError, match="run_id"):
        store.create_run("../escape", revision, "input", "digest", 1, 1, 1, "output")
