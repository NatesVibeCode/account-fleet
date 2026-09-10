"""Item batching and prompt packaging."""
import hashlib
import json
from typing import Any, Dict, List
from .slicer import slice_document

def pack_items(
    raw_records: List[Dict[str, Any]],
    batch_size: int = 6,
    max_slice_chars: int = 6000
) -> List[Dict[str, Any]]:
    """Transforms raw records into sliced cards and packs them into bounded batches."""
    cards = []
    for r in raw_records:
        iid = str(r.get("item_id") or r.get("id") or r.get("cid") or hashlib.sha256(str(r).encode()).hexdigest()[:12])
        text = str(r.get("text") or r.get("content") or r.get("body") or r.get("description") or "")
        title = str(r.get("title") or r.get("name") or "")
        
        slices = slice_document(text, max_chars=max_slice_chars)
        cards.append({
            "item_id": iid,
            "title": title,
            "slices": slices,
            "full_char_length": len(text)
        })

    batches = []
    for i in range(0, len(cards), batch_size):
        chunk = cards[i:i + batch_size]
        batch_hash = hashlib.sha256(json.dumps([c["item_id"] for c in chunk], sort_keys=True).encode()).hexdigest()[:16]
        batches.append({
            "batch_id": f"batch_{batch_hash}",
            "items": chunk
        })

    return batches
