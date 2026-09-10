"""Air-gap boundary packet exporter."""
import json
import time
from pathlib import Path
from .models import CleanPacket, ExtractedItem, ProviderReceipt, TaskSpec

def export_clean_packet(
    run_data: dict,
    output_path: Path
) -> dict:
    """Validate and serialize verified records into a closed packet."""
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

    packet_model = CleanPacket.model_validate({
        "format_version": "bulk_lanes_v2",
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
    })
    packet = packet_model.model_dump(mode="json", by_alias=True)

    output_path.write_text(json.dumps(packet, indent=2))
    return packet
