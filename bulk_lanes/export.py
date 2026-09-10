"""Air-gap boundary packet exporter."""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

def export_clean_packet(
    manifest_data: dict,
    output_path: Path
) -> dict:
    """Consolidates verified records into an air-gapped clean packet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    verified_records = []
    receipts = []
    total_tokens = 0
    total_cost = 0.0

    for b in manifest_data.get("batches", {}).values():
        if b.get("status") == "verified" and b.get("result"):
            results = b["result"]
            if isinstance(results, list):
                verified_records.extend(results)
            elif isinstance(results, dict) and "items" in results:
                verified_records.extend(results["items"])
        
        receipt = b.get("receipt")
        if receipt:
            receipts.append(receipt)
            cost = receipt.get("cost")
            if isinstance(cost, (int, float)):
                total_cost += cost
            usage = receipt.get("usage")
            if isinstance(usage, dict):
                total_tokens += usage.get("total_tokens", 0)

    packet = {
        "format_version": "bulk_lanes_v1",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": manifest_data.get("run_id"),
        "total_verified_records": len(verified_records),
        "audit": {
            "total_batches_processed": len(manifest_data.get("batches", {})),
            "total_tokens_consumed": total_tokens,
            "total_cost_reported": total_cost,
            "batches_verified": sum(1 for b in manifest_data.get("batches", {}).values() if b.get("status") == "verified"),
            "batches_failed": sum(1 for b in manifest_data.get("batches", {}).values() if b.get("status") == "failed"),
        },
        "records": verified_records
    }

    output_path.write_text(json.dumps(packet, indent=2))
    return packet
