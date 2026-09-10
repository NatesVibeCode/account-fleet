"""bulk-lanes: Air-Gapped Bulk Model Lane Orchestrator."""
import json
from pathlib import Path
from .task import Task, load_task
from .engine import Engine
from .catalog import RouteCatalog
from .grounding import verify_grounding
from .slicer import slice_document
from .packer import pack_items
from .export import export_clean_packet

def read_packet(packet_path: str) -> dict:
    """Convenience helper for downstream trusted applications to safely load a clean packet."""
    p = Path(packet_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Packet file not found: {packet_path}")
    data = json.loads(p.read_text())
    if data.get("format_version") != "bulk_lanes_v1":
        raise ValueError(f"Unknown or unsupported packet format: {data.get('format_version')}")
    return data

__all__ = [
    "Task",
    "load_task",
    "Engine",
    "RouteCatalog",
    "verify_grounding",
    "slice_document",
    "pack_items",
    "export_clean_packet",
    "read_packet",
]
