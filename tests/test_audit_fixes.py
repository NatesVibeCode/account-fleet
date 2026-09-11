"""Regression tests for audit bug fixes."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from free_fleet.models import (
    CandidateExtractedItem,
    QuoteCandidate,
    InputItem,
    TaskSpec,
)
from free_fleet.providers.base import clean_llm_json
from free_fleet.providers.opencode import OpenCodeProvider
from free_fleet.input_data import load_input_items, _resolve_only_ids
from free_fleet.export import _filter_and_sort_records, _evaluate_filter
from free_fleet.grounding import normalize_grounding
from free_fleet.store import FreeFleetStore
from free_fleet.engine import Engine
from free_fleet.catalog import RouteCatalog, PriceState


def test_clean_llm_json_conversational_and_malformed():
    text1 = 'Certainly! Here is the JSON you requested:\n```json\n{"items": [{"id": 1}]}\n```\nHope this helps!'
    res1 = clean_llm_json(text1)
    assert res1 == {"items": [{"id": 1}]}

    text2 = '```json\n{"items": []}```'
    res2 = clean_llm_json(text2)
    assert res2 == {"items": []}

    text3 = '```\n{"items": ["a", "b"]} \n```'
    res3 = clean_llm_json(text3)
    assert res3 == {"items": ["a", "b"]}

    text4 = 'The result is: {"summary": "all clear"} - verified.'
    res4 = clean_llm_json(text4)
    assert res4 == {"summary": "all clear"}

    text5 = '```json\n{"items": [{"a": 1,},],}\n```'
    res5 = clean_llm_json(text5)
    assert res5 == {"items": [{"a": 1}]}

    assert clean_llm_json("") is None
    assert clean_llm_json("   ") is None
    assert clean_llm_json("Not a json at all") is None


def test_opencode_prefix_stripping():
    fake_runner = MagicMock()
    fake_runner.run.return_value = (
        0,
        json.dumps({"type": "text", "part": {"text": '{"items": []}'}}) + "\n" + json.dumps({"type": "step_finish", "part": {"cost": 0.0}}),
        "",
    )
    prov = OpenCodeProvider(runner=fake_runner)

    prov.run_prompt("opencode/anthropic/claude-3-5-sonnet", "test prompt")
    task_config = fake_runner.run.call_args[1]["task_config"]
    args = fake_runner.run.call_args[1]["args"]
    assert task_config["model"] == "anthropic/claude-3-5-sonnet"
    assert args[4] == "anthropic/claude-3-5-sonnet"

    prov.run_prompt("opencode:meta/llama-3", "test prompt")
    task_config = fake_runner.run.call_args[1]["task_config"]
    args = fake_runner.run.call_args[1]["args"]
    assert task_config["model"] == "meta/llama-3"
    assert args[4] == "meta/llama-3"


def test_csv_excel_bom_and_trailing_empty_rows(tmp_path: Path):
    bom_content = "\ufeffitem_id,text,title\nrow_1,Some text content,Title 1\nrow_2,More text content,Title 2\n\n   \n"
    csv_file = tmp_path / "excel_export.csv"
    csv_file.write_bytes(bom_content.encode("utf-8"))

    items = load_input_items(csv_file)
    assert len(items) == 2
    assert items[0].item_id == "row_1"
    assert items[0].text == "Some text content"
    assert items[1].item_id == "row_2"

    resolved = _resolve_only_ids(csv_file)
    assert resolved == {"row_1", "row_2"}


def test_export_sorting_mixed_types_and_quoted_filters():
    from free_fleet.models import ExtractedItem, QuoteRef

    digest = "a" * 64
    records = [
        ExtractedItem(
            item_id="rec_1",
            claims={"score": 85.0, "status": "passed"},
            quotes=[QuoteRef(slice_id="s1", start=0, end=10, text="verbatim12")],
            source_digest=digest,
            content_type="text/plain",
        ),
        ExtractedItem(
            item_id="rec_2",
            claims={"score": "N/A", "status": "failed"},
            quotes=[QuoteRef(slice_id="s1", start=0, end=10, text="verbatim12")],
            source_digest=digest,
            content_type="text/plain",
        ),
        ExtractedItem(
            item_id="rec_3",
            claims={"score": 95.0, "status": "passed"},
            quotes=[QuoteRef(slice_id="s1", start=0, end=10, text="verbatim12")],
            source_digest=digest,
            content_type="text/plain",
        ),
    ]

    sorted_recs = _filter_and_sort_records(records, sort_by="score", descending=True)
    assert [r.item_id for r in sorted_recs] == ["rec_3", "rec_1", "rec_2"]

    assert _evaluate_filter({"tier": "tier_1"}, "tier='tier_1'") is True
    assert _evaluate_filter({"tier": "tier_1"}, 'tier="tier_1"') is True
    assert _evaluate_filter({"score": 85}, "score>=80") is True


def test_resume_reclaims_abandoned_leased_batches(tmp_path: Path):
    db_path = tmp_path / "test.db"
    store = FreeFleetStore(db_path)
    catalog = RouteCatalog(db_path=db_path)
    catalog.add_route(
        route_id="demo/fake",
        provider="demo",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        enabled=True,
        price_state=PriceState.PRICE_OBSERVED_ZERO.value,
        verification_source="test",
    )

    spec = TaskSpec(
        name="test-task",
        instructions="Extract label",
        batch_size=1,
        claims_schema={"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"], "additionalProperties": False},
    )
    store.register_task(spec)

    items = [
        InputItem(item_id="item_1", text="This is sample text for item 1."),
        InputItem(item_id="item_2", text="This is sample text for item 2."),
    ]

    from free_fleet.packer import pack_items
    batches = pack_items(items, batch_size=1, max_slice_chars=1000)
    store.create_run(
        run_id="run_abandoned",
        task_revision_id=store.current_task_revision("test-task"),
        input_path="test",
        input_digest="a" * 64,
        total_items=2,
        max_attempts=10,
        batch_size=1,
        output_path=str(tmp_path / "packet.json"),
    )
    store.enqueue_batches("run_abandoned", batches, max_attempts_per_batch=3)

    lease1 = store.lease_batch("run_abandoned", worker_id="dead_worker")
    assert lease1 is not None
    with store.connect() as connection:
        connection.execute("UPDATE batches SET leased_at=datetime('now', '-10 minutes') WHERE run_id='run_abandoned' AND status='leased'")

    snapshot_before = store.run_snapshot("run_abandoned")
    assert snapshot_before["batches"][lease1["batch"]["batch_id"]]["status"] == "leased"

    from free_fleet.models import RoutePolicy
    engine = Engine(task=spec, store=store, catalog=catalog, policy=RoutePolicy(allowed_routes=["demo/fake"]))
    packet = engine.resume_campaign("run_abandoned", concurrency=1, output_packet_path=tmp_path / "packet.json")

    assert packet["total_verified_records"] == 2
    snapshot_after = store.run_snapshot("run_abandoned")
    assert snapshot_after["status"] == "completed"


def test_candidate_offsets_repaired_when_inaccurate():
    raw_cards = [{
        "item_id": "card_1",
        "source_digest": "a" * 64,
        "content_type": "text/plain",
        "slices": [{
            "slice_id": "card_1:s0",
            "start": 0,
            "end": 60,
            "text": "The company offers a free trial for 14 days without credit card.",
        }],
    }]

    extracted = [
        CandidateExtractedItem(
            item_id="card_1",
            claims={"label": "trial"},
            quotes=[QuoteCandidate(
                slice_id="card_1:s0",
                text="free trial for 14 days without",
                start=10,
                end=40,
            )],
        )
    ]

    normalized, err = normalize_grounding(extracted, raw_cards, min_quote_chars=15)
    assert err is None
    assert normalized is not None
    assert len(normalized) == 1
    quote = normalized[0].quotes[0]
    assert quote.start == 21
    assert quote.end == 51
    assert raw_cards[0]["slices"][0]["text"][quote.start:quote.end] == "free trial for 14 days without"


def test_mcp_server_evaluate_tool(tmp_path: Path):
    from free_fleet.mcp_server import create_mcp_server
    import anyio

    server = create_mcp_server(tmp_path)
    tool_names = [tool.name for tool in anyio.run(server.list_tools)]
    assert "free_fleet_eval" in tool_names
