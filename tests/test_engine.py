import json

from bulk_lanes.catalog import RouteCatalog
from bulk_lanes.engine import Engine
from bulk_lanes.models import TaskSpec
from bulk_lanes.packer import pack_items


class ProviderStub:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def run_prompt(self, route_id, prompt, system_prompt=None, timeout_sec=120, session_id=None):
        self.calls += 1
        receipt = {
            "id": "receipt-1",
            "session_id": session_id,
            "provider": "stub",
            "requested_route": route_id,
            "status": "complete",
            "cost": 0.0,
            "cost_status": "reported_zero",
            "usage": {"total_tokens": 1},
            "error": None,
            "duration_seconds": 0.01,
        }
        return True, json.dumps(self.payload), receipt


def _engine(tmp_path, payload):
    catalog = RouteCatalog(config_path=tmp_path / "routes.json")
    catalog.data = {
        "revision": 2,
        "routes": [{"id": "stub/zero", "provider": "stub", "enabled": True, "price_state": "price_observed_zero"}],
    }
    task = TaskSpec(
        name="typed",
        claims_schema={
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
            "additionalProperties": False,
        },
    )
    engine = Engine(task, catalog=catalog)
    engine.opencode_prov = ProviderStub(payload)
    return engine


def test_engine_rejects_extra_model_fields(tmp_path):
    payload = {
        "items": [{
            "item_id": "i1",
            "claims": {"summary": "supported"},
            "quotes": [{"slice_id": "full", "start": 0, "end": 21, "text": "supported source text"}],
            "untrusted": "leak",
        }]
    }
    ok, _, _, error = _engine(tmp_path, payload).execute_batch(pack_items([{"item_id": "i1", "text": "supported source text"}])[0])
    assert ok is False
    assert "Typed output validation failed" in error


def test_engine_exports_only_validated_shape(tmp_path):
    payload = {
        "items": [{
            "item_id": "i1",
            "claims": {"summary": "supported"},
            "quotes": [{"slice_id": "full", "start": 0, "end": 21, "text": "supported source text"}],
        }]
    }
    ok, results, _, error = _engine(tmp_path, payload).execute_batch(pack_items([{"item_id": "i1", "text": "supported source text"}])[0])
    assert ok is True
    assert error is None
    assert results[0]["item_id"] == "i1"
    assert results[0]["claims"] == payload["items"][0]["claims"]
    assert results[0]["quotes"] == payload["items"][0]["quotes"]
    assert results[0]["content_type"] == "text/plain"
    assert len(results[0]["source_digest"]) == 64


def test_campaign_state_and_receipts_live_in_sqlite(tmp_path):
    payload = {
        "items": [{
            "item_id": "i1",
            "claims": {"summary": "supported"},
            "quotes": [{"slice_id": "full", "text": "supported source text"}],
        }]
    }
    engine = _engine(tmp_path, payload)
    output = tmp_path / "packet.json"
    packet = engine.run_campaign(
        raw_items=[{"item_id": "i1", "text": "supported source text"}],
        run_id="run-1",
        input_path="input.jsonl",
        concurrency=2,
        max_attempts=3,
        output_packet_path=output,
    )

    assert packet["total_verified_records"] == 1
    assert packet["$schema"].endswith("/packet-v2.schema.json")
    assert packet["task"]["name"] == "typed"
    assert packet["audit"]["model_attempts"] == 1
    assert len(packet["receipts"]) == 1
    assert engine.store.run_snapshot("run-1")["status"] == "completed"
    assert engine.store.model_run_count("run-1") == 1

    calls = engine.opencode_prov.calls
    engine.resume_campaign("run-1", concurrency=2, output_packet_path=output)
    assert engine.opencode_prov.calls == calls
