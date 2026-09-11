"""Air-gap boundary packet and CSV exporter."""
import csv
import json
import time
from pathlib import Path
from .models import CleanPacket, ExtractedItem, ProviderReceipt, RoutePolicy, TaskSpec


def export_clean_csv(
    run_data: dict,
    output_path: Path,
) -> Path:
    """Project verified records into a frictionless tabular CSV format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    verified_records: list[ExtractedItem] = []
    task = TaskSpec.model_validate(run_data["task"])

    for b in run_data.get("batches", {}).values():
        if b.get("status") == "verified" and b.get("result"):
            results = b["result"]
            if isinstance(results, list):
                validated = [ExtractedItem.model_validate(item) for item in results]
            elif isinstance(results, dict) and "items" in results:
                validated = [ExtractedItem.model_validate(item) for item in results["items"]]
            else:
                continue
            for item in validated:
                task.validate_claims(item.claims)
            verified_records.extend(validated)

    # Determine all unique claim keys
    claim_keys: list[str] = []
    if task.claims_schema and "properties" in task.claims_schema:
        claim_keys = list(task.claims_schema["properties"].keys())
    for rec in verified_records:
        for k in rec.claims.keys():
            if k not in claim_keys:
                claim_keys.append(k)

    fieldnames = ["item_id"]
    fieldnames.extend(claim_keys)
    fieldnames.extend(["primary_quote_text", "quote_count", "source_uri", "source_digest"])

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in verified_records:
            row = {
                "item_id": rec.item_id,
                "primary_quote_text": rec.quotes[0].text if rec.quotes else "",
                "quote_count": len(rec.quotes),
                "source_uri": rec.source_uri or "",
                "source_digest": rec.source_digest,
            }
            for k in claim_keys:
                val = rec.claims.get(k)
                if isinstance(val, (dict, list)):
                    row[k] = json.dumps(val, ensure_ascii=False)
                elif val is not None:
                    row[k] = str(val)
                else:
                    row[k] = ""
            writer.writerow(row)

    return output_path


def export_clean_packet(
    run_data: dict,
    output_path: Path,
    export_format: str = "json",
) -> dict:
    """Validate and serialize verified records into a closed packet or CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    verified_records: list[ExtractedItem] = []
    receipts: list[ProviderReceipt] = []
    task = TaskSpec.model_validate(run_data["task"])

    for b in run_data.get("batches", {}).values():
        if b.get("status") == "verified" and b.get("result"):
            results = b["result"]
            if isinstance(results, list):
                validated = [ExtractedItem.model_validate(item) for item in results]
            elif isinstance(results, dict) and "items" in results:
                validated = [ExtractedItem.model_validate(item) for item in results["items"]]
            else:
                raise ValueError("verified batch result has an invalid shape")
            for item in validated:
                task.validate_claims(item.claims)
            verified_records.extend(validated)
        
    raw_receipts = run_data.get("model_runs")
    if isinstance(raw_receipts, list):
        receipts = [ProviderReceipt.model_validate(receipt) for receipt in raw_receipts]
    else:
        receipts = [
            ProviderReceipt.model_validate(batch["receipt"])
            for batch in run_data.get("batches", {}).values()
            if batch.get("receipt")
        ]
    total_tokens = sum(
        int(receipt.usage.get("total_tokens", 0))
        for receipt in receipts
        if isinstance(receipt.usage, dict)
    )
    total_cost = sum(receipt.cost for receipt in receipts if receipt.cost is not None)

    policy = RoutePolicy.model_validate(run_data["policy"]) if run_data.get("policy") else None

    packet_model = CleanPacket.model_validate({
        "format_version": "free_fleet_v2",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": run_data.get("run_id"),
        "task": task,
        "task_revision": run_data["task_revision"],
        "input_digest": run_data["input_digest"],
        "total_verified_records": len(verified_records),
        "audit": {
            "total_batches_processed": len(run_data.get("batches", {})),
            "total_tokens_consumed": total_tokens,
            "total_cost_reported": total_cost,
            "batches_verified": sum(1 for b in run_data.get("batches", {}).values() if b.get("status") == "verified"),
            "batches_failed": sum(1 for b in run_data.get("batches", {}).values() if b.get("status") == "failed"),
            "model_attempts": int(run_data.get("attempts_used", len(receipts))),
            "receipts_recorded": len(receipts),
            "unknown_cost_attempts": sum(1 for receipt in receipts if receipt.cost is None),
        },
        "records": verified_records,
        "receipts": receipts,
        "policy": policy,
    })
    packet = packet_model.model_dump(mode="json", by_alias=True)

    if export_format == "csv" or output_path.suffix.lower() == ".csv":
        export_clean_csv(run_data, output_path)
    elif export_format == "jsonl" or output_path.suffix.lower() == ".jsonl":
        # One JSON record per line, with flattened claims + quote
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in verified_records:
                flat = {
                    "item_id": rec.item_id,
                    "source_uri": rec.source_uri,
                    "source_digest": rec.source_digest,
                    **rec.claims,
                    "primary_quote_text": rec.quotes[0].text if rec.quotes else "",
                    "quote_count": len(rec.quotes),
                    "quotes": [q.model_dump(mode="json") for q in rec.quotes],
                }
                f.write(json.dumps(flat, ensure_ascii=False) + "\n")
    else:
        output_path.write_text(json.dumps(packet, indent=2))

    return packet
