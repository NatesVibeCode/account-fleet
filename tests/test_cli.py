import json
from argparse import Namespace

from bulk_lanes import cli
from bulk_lanes.store import BulkLanesStore


def test_init_registers_task_and_writes_typed_sample(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "state.db"
    cli.cmd_init(Namespace(
        name="demo",
        preset="triage",
        batch_size=4,
        sample=None,
        db=str(db),
        json=True,
    ))

    task = BulkLanesStore(db).get_task("demo")
    assert set(task.claims_schema["properties"]) == {"priority", "reason"}
    assert (tmp_path / "demo.sample.jsonl").is_file()


def test_validate_is_offline_and_strict(tmp_path, capsys):
    db = tmp_path / "state.db"
    input_path = tmp_path / "input.jsonl"
    cli.cmd_init(Namespace(
        name="demo", preset="classify", batch_size=4,
        sample=str(input_path), db=str(db), json=True,
    ))
    capsys.readouterr()

    cli.cmd_validate(Namespace(task="demo", input=str(input_path), db=str(db), json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["input_items"] == 1


def test_json_flag_works_before_command():
    args = cli.build_parser().parse_args(["--json", "tasks"])
    if args.global_json:
        args.json = True
    assert args.json is True


def test_presets_cover_each_named_bulk_job():
    assert set(cli.PRESETS) == {"classify", "extract", "summarize", "triage"}


def test_routes_add_and_list_cli(tmp_path, capsys):
    db = tmp_path / "routes_test.db"
    cli.cmd_routes(Namespace(
        action="add",
        route_id="local/test-model",
        add=None,
        provider="openai_compatible",
        free=True,
        input_cost=0.0,
        output_cost=0.0,
        disable=False,
        all=False,
        refresh=False,
        db=str(db),
        json=True,
    ))
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "added"
    assert payload["route"]["id"] == "local/test-model"

    cli.cmd_routes(Namespace(
        action="list",
        route_id=None,
        add=None,
        provider=None,
        free=False,
        disable=False,
        all=False,
        refresh=False,
        db=str(db),
        json=True,
    ))
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload["count"] == 1
    assert list_payload["routes"][0]["id"] == "local/test-model"


def test_export_and_status_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import csv
    from bulk_lanes.models import ExtractedItem, PackedBatch, SourceSlice
    from bulk_lanes.store import BulkLanesStore

    db = tmp_path / "run_test.db"
    store = BulkLanesStore(db)

    # Register task
    cli.cmd_init(Namespace(
        name="test-triage",
        preset="triage",
        batch_size=2,
        sample=None,
        db=str(db),
        json=True,
    ))
    capsys.readouterr()

    # Create run in store
    task = store.get_task("test-triage")
    rev_id = store.register_task(task)
    run_id = "test-run-1"
    store.create_run(
        run_id=run_id,
        task_revision_id=rev_id,
        input_path="input.csv",
        input_digest="d" * 64,
        total_items=1,
        max_attempts=10,
        batch_size=2,
        output_path="out.json",
    )
    from bulk_lanes.packer import pack_items
    from bulk_lanes.models import ProviderReceipt
    batch = pack_items([{"item_id": "item-1", "text": "broken button error"}], batch_size=2)[0]
    store.enqueue_batches(run_id, [batch], max_attempts_per_batch=5)
    lease = store.lease_batch(run_id, "worker-1")
    assert lease is not None
    receipt = ProviderReceipt(
        id="rec-1",
        provider="openai_compatible",
        requested_route="local/test-model",
        status="complete",
        cost=0.0,
        cost_status="reported_zero",
        usage={"total_tokens": 10},
        duration_seconds=0.2,
    )
    store.complete_batch(
        run_id=run_id,
        attempt_id=lease["attempt_id"],
        worker_id="worker-1",
        results=[{
            "item_id": "item-1",
            "source_digest": batch["items"][0]["source_digest"],
            "content_type": "text/plain",
            "claims": {"priority": "high", "reason": "broken button"},
            "quotes": [{"slice_id": "full", "start": 0, "end": 6, "text": "broken"}],
        }],
        receipt=receipt,
    )

    # Test status CLI
    cli.cmd_status(Namespace(run_id=run_id, watch=False, interval=1.0, db=str(db), json=True))
    status_out = json.loads(capsys.readouterr().out)
    assert status_out["run_id"] == run_id
    assert status_out["verified_items"] == 1

    # Test export CSV CLI
    csv_file = tmp_path / "exported.csv"
    cli.cmd_export(Namespace(run_id=run_id, format="csv", output=str(csv_file), db=str(db), json=True))
    export_out = json.loads(capsys.readouterr().out)
    assert export_out["format"] == "csv"
    assert csv_file.is_file()

    with open(csv_file, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["item_id"] == "item-1"
        assert reader[0]["priority"] == "high"
        assert reader[0]["reason"] == "broken button"
        assert reader[0]["primary_quote_text"] == "broken"

