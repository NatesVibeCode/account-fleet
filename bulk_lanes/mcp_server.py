"""Model Context Protocol (MCP) server for bulk-lanes.
Allows any MCP-compatible agent harness (Cursor, Claude, OpenCode, Codex, Antigravity)
to orchestrate bulk free-tier lanes directly as native tools.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .catalog import RouteCatalog
from .engine import Engine
from .export import export_clean_packet
from .manifest import ManifestManager
from .task import load_task

def run_mcp_server():
    """Lightweight stdio JSON-RPC MCP server implementation."""
    cat = RouteCatalog()

    tools = [
        {
            "name": "bulk_lanes_routes",
            "description": "List and optionally refresh available free-tier model routes across OpenCode and OpenRouter.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "refresh": {"type": "boolean", "description": "Scan provider schemas to discover new free models"},
                    "free_only": {"type": "boolean", "default": True, "description": "Filter strictly for zero-cost routes"}
                }
            }
        },
        {
            "name": "bulk_lanes_test",
            "description": "Dry run a single batch of items against a task definition to verify prompt, schema, and mathematical quote grounding.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_path": {"type": "string", "description": "Path to task.py definition file"},
                    "input_path": {"type": "string", "description": "Path to input sample file (.json or .jsonl)"}
                },
                "required": ["task_path", "input_path"]
            }
        },
        {
            "name": "bulk_lanes_run",
            "description": "Launch a parallel bulk triage run across free model lanes and export a verified clean packet.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_path": {"type": "string", "description": "Path to task.py definition file"},
                    "input_path": {"type": "string", "description": "Path to input data file (.json or .jsonl)"},
                    "sessions": {"type": "integer", "default": 4, "description": "Number of concurrent worker sessions"},
                    "output_dir": {"type": "string", "description": "Directory for run manifest and outputs"},
                    "output_packet": {"type": "string", "description": "Output path for clean packet JSON"}
                },
                "required": ["task_path", "input_path"]
            }
        },
        {
            "name": "bulk_lanes_export",
            "description": "Export verified records from a completed or in-progress run directory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "run_dir": {"type": "string", "description": "Path to run directory containing manifest.json"},
                    "output_path": {"type": "string", "description": "Output path for exported packet JSON"}
                },
                "required": ["run_dir"]
            }
        }
    ]

    def handle_call_tool(name: str, arguments: dict) -> dict:
        if name == "bulk_lanes_routes":
            if arguments.get("refresh"):
                cat.refresh_all()
            routes = cat.get_routes(free_only=arguments.get("free_only", True))
            return {"content": [{"type": "text", "text": json.dumps(routes, indent=2)}]}

        elif name == "bulk_lanes_test":
            task = load_task(arguments["task_path"])
            items = []
            p = Path(arguments["input_path"])
            if p.suffix == ".jsonl":
                items = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            else:
                data = json.loads(p.read_text())
                items = data if isinstance(data, list) else data.get("items", [])
            
            engine = Engine(task=task)
            from .packer import pack_items
            batches = pack_items(items[:task.batch_size], batch_size=task.batch_size, max_slice_chars=task.max_slice_chars)
            if not batches:
                return {"isError": True, "content": [{"type": "text", "text": "No batches could be packed from input."}]}
            
            ok, results, receipt, err = engine.execute_batch(batches[0])
            res_payload = {"ok": ok, "results": results, "receipt": receipt, "error": err}
            return {"isError": not ok, "content": [{"type": "text", "text": json.dumps(res_payload, indent=2)}]}

        elif name == "bulk_lanes_run":
            task = load_task(arguments["task_path"])
            p = Path(arguments["input_path"])
            items = [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.suffix == ".jsonl" else json.loads(p.read_text())
            if isinstance(items, dict) and "items" in items:
                items = items["items"]
            
            run_dir = Path(arguments.get("output_dir") or f"runs/run_{task.name}")
            out_packet = Path(arguments["output_packet"]) if arguments.get("output_packet") else None
            engine = Engine(task=task)
            packet = engine.run_campaign(
                raw_items=items,
                run_dir=run_dir,
                concurrency=arguments.get("sessions", 4),
                output_packet_path=out_packet
            )
            return {"content": [{"type": "text", "text": json.dumps(packet, indent=2)}]}

        elif name == "bulk_lanes_export":
            run_dir = Path(arguments["run_dir"])
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                return {"isError": True, "content": [{"type": "text", "text": f"Manifest not found in {run_dir}"}]}
            manifest_data = json.loads(manifest_path.read_text())
            out_path = Path(arguments.get("output_path") or (run_dir / "clean_packet.json"))
            packet = export_clean_packet(manifest_data, out_path)
            return {"content": [{"type": "text", "text": json.dumps(packet, indent=2)}]}

        return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

    # Standard JSON-RPC 2.0 loop over stdin/stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "bulk-lanes", "version": "0.1.0"}
                }
            }
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools}
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            call_res = handle_call_tool(tool_name, tool_args)
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": call_res
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
