import csv
from bulk_lanes.export import export_clean_csv, export_clean_packet
from bulk_lanes.input_data import load_input_items
from bulk_lanes.models import TaskSpec


def test_csv_import_with_custom_columns(tmp_path):
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text(
        "domain,research,employee_count,industry\n"
        "google.com,Search engine and cloud provider,180000,Technology\n"
        "stripe.com,Online payment infrastructure platform,8000,Financial Services\n"
    )

    items = load_input_items(
        csv_file,
        id_column="domain",
        text_column="research",
    )

    assert len(items) == 2
    assert items[0].item_id == "google.com"
    assert items[0].text == "Search engine and cloud provider"
    assert items[0].metadata == {"employee_count": "180000", "industry": "Technology"}

    assert items[1].item_id == "stripe.com"
    assert items[1].text == "Online payment infrastructure platform"
    assert items[1].metadata == {"employee_count": "8000", "industry": "Financial Services"}


def test_csv_export_projection(tmp_path):
    task = TaskSpec(
        name="classify",
        claims_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "sentiment": {"type": "string"},
            },
            "required": ["category", "sentiment"],
            "additionalProperties": False,
        },
    )

    import hashlib
    import json

    task_payload = task.model_dump(mode="json", by_alias=True)
    task_revision = hashlib.sha256(
        json.dumps(task_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()

    run_data = {
        "run_id": "test-run",
        "task": task_payload,
        "task_revision": task_revision,
        "input_digest": "1" * 64,
        "batches": {
            "b1": {
                "status": "verified",
                "result": [{
                    "item_id": "item-1",
                    "source_uri": "https://example.com/1",
                    "source_digest": "a" * 64,
                    "content_type": "text/plain",
                    "claims": {"category": "cloud", "sentiment": "positive"},
                    "quotes": [{
                        "slice_id": "full",
                        "start": 0,
                        "end": 20,
                        "text": "great cloud provider",
                    }],
                }],
            }
        },
        "model_runs": [{
            "id": "rec-1",
            "provider": "openrouter",
            "requested_route": "openrouter/free",
            "status": "complete",
            "cost": 0.0,
            "cost_status": "reported_zero",
            "usage": {"total_tokens": 15},
            "duration_seconds": 0.5,
        }],
    }

    csv_output = tmp_path / "results.csv"
    export_clean_packet(run_data, csv_output, export_format="csv")

    assert csv_output.is_file()
    with open(csv_output, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        row = reader[0]
        assert row["item_id"] == "item-1"
        assert row["source_uri"] == "https://example.com/1"
        assert row["category"] == "cloud"
        assert row["sentiment"] == "positive"
        assert row["primary_quote_text"] == "great cloud provider"
        assert row["quote_count"] == "1"
