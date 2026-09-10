"""Typed bulk evidence processing with exact source-offset verification."""
import json
from pathlib import Path
from .task import load_task_spec
from .engine import Engine
from .catalog import RouteCatalog
from .grounding import verify_grounding
from .models import CleanPacket, ExtractedItem, InputItem, ModelOutput, QuoteRef, TaskSpec
from .input_data import load_input_items
from .store import BulkLanesStore
from .slicer import slice_document
from .packer import pack_items
from .export import export_clean_packet

def read_packet(packet_path: str) -> dict:
    """Convenience helper for downstream trusted applications to safely load a clean packet."""
    p = Path(packet_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Packet file not found: {packet_path}")
    return CleanPacket.model_validate_json(p.read_text()).model_dump(mode="json", by_alias=True)

__all__ = [
    "load_task_spec",
    "Engine",
    "RouteCatalog",
    "verify_grounding",
    "CleanPacket",
    "ExtractedItem",
    "InputItem",
    "ModelOutput",
    "QuoteRef",
    "TaskSpec",
    "BulkLanesStore",
    "load_input_items",
    "slice_document",
    "pack_items",
    "export_clean_packet",
    "read_packet",
]
