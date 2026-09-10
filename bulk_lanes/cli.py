"""Universal Command Line Interface for bulk-lanes.
Supports interactive human TUI, pure machine-readable JSON mode (--json),
and standard MCP server mode (bulk-lanes serve) for any agent harness.
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import List

from . import ui
from .catalog import RouteCatalog
from .engine import Engine
from .export import export_clean_packet
from .manifest import ManifestManager
from .task import Task, load_task

def cmd_routes(args):
    cat = RouteCatalog()
    refresh_stats = {}
    if getattr(args, "refresh", False):
        if not args.json:
            ui.banner()
            ui.info("Scanning provider catalogues (OpenCode + OpenRouter) for free models in schema...")
        refresh_stats = cat.refresh_all()
        if not args.json:
            for prov, val in refresh_stats.items():
                if prov.endswith("_error"):
                    ui.warn(f"Provider {prov.replace('_error', '')} notice: {val}")
                else:
                    ui.success(f"Provider '{prov}': {val} free models discovered from schema.")

    free_only = not args.all
    routes = cat.get_routes(free_only=free_only)

    if args.json:
        out = {
            "status": "ok",
            "free_only": free_only,
            "total_routes": len(routes),
            "refresh": refresh_stats if args.refresh else None,
            "routes": routes
        }
        print(json.dumps(out, indent=2))
        return

    if not getattr(args, "refresh", False):
        ui.banner()
    if not routes:
        ui.warn("No routes found matching filter.")
        return
    ui.info(f"Showing {'all configured' if args.all else 'active free/zero-price'} routes:")
    ui.print_routes_table(routes)

def cmd_sessions(args):
    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        if args.json:
            print(json.dumps({"error": f"Manifest not found in {run_dir}"}))
        else:
            ui.error(f"No run manifest found in {run_dir}")
        return

    data = json.loads(manifest_path.read_text())
    sessions = data.get("sessions", {})
    
    if args.json:
        print(json.dumps({"run_id": data.get("run_id"), "sessions": sessions}, indent=2))
        return

    ui.banner()
    if not sessions:
        ui.info(f"No active or recorded worker sessions found in run '{data.get('run_id')}'.")
        return

    ui.info(f"Worker sessions recorded for run '{data.get('run_id')}':")
    ui.print_sessions_table(sessions)

def cmd_init(args):
    task_name = args.name or "my_task"
    task_dir = Path(task_name)
    task_dir.mkdir(parents=True, exist_ok=True)

    task_file = task_dir / "task.py"
    data_file = task_dir / "sample_input.jsonl"

    task_code = '''from bulk_lanes import Task

class CustomTriageTask(Task):
    name = "''' + task_name + '''"
    batch_size = 4
    min_quote_chars = 15
    quote_field = "quotes"

    system_prompt = (
        "You are an air-gapped triage worker. "
        "Analyze the items and extract structured facts. "
        "Every claim MUST provide an exact verbatim quote from the source text as evidence."
    )

    user_prompt_template = """
Analyze the following items and return JSON matching this schema:
{
  "items": [
    {
      "item_id": "<id>",
      "summary": "<one sentence description>",
      "category": "<category or classification>",
      "quotes": ["<exact quote from text>"]
    }
  ]
}

Items to triage:
{items_json}
"""
'''
    sample_records = [
        {"item_id": "item_01", "title": "Acme Metrics", "text": "Acme Metrics provides real-time latency monitoring for distributed cloud microservices with sub-millisecond alerting."},
        {"item_id": "item_02", "title": "Beta Auth", "text": "Beta Auth is a passkey-first identity provider offering developer SDKs in Python, Rust, and TypeScript with zero monthly minimums."},
        {"item_id": "item_03", "title": "Gamma DB", "text": "Gamma DB is an embedded vector search engine written in C++ that supports disk-backed HNSW indexing for billion-scale datasets."},
        {"item_id": "item_04", "title": "Delta Shield", "text": "Delta Shield monitors internal Kubernetes clusters for anomalous egress traffic and automatically isolates compromised pods in seconds."}
    ]

    task_file.write_text(task_code)
    with data_file.open("w") as f:
        for r in sample_records:
            f.write(json.dumps(r) + "\n")

    if args.json:
        print(json.dumps({"status": "created", "task_file": str(task_file), "sample_data": str(data_file)}, indent=2))
        return

    ui.banner()
    ui.success(f"Initialized new task in '{task_dir}/'")
    print(f"\nRun a dry-run test:\n  bulk-lanes test --task {task_file} --input {data_file}\n")
    print(f"Run a bulk execution:\n  bulk-lanes run --task {task_file} --input {data_file}\n")

def _load_input_data(input_path_str: str) -> List[dict]:
    p = Path(input_path_str)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path_str}")
    
    items = []
    if p.suffix == ".jsonl":
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    elif p.suffix == ".json":
        data = json.loads(p.read_text())
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "items" in data:
            items = data["items"]
    else:
        raise ValueError(f"Unsupported file format '{p.suffix}'. Use .json or .jsonl")
    return items

def cmd_test(args):
    task = load_task(args.task)
    try:
        items = _load_input_data(args.input)
    except Exception as e:
        if args.json:
            print(json.dumps({"ok": False, "error": str(e)}))
            sys.exit(1)
        ui.error(str(e))
        sys.exit(1)

    if not items:
        if args.json:
            print(json.dumps({"ok": False, "error": "No items found in input file."}))
            sys.exit(1)
        ui.error("No items found in input file.")
        return
    
    test_items = items[:task.batch_size]
    if not args.json:
        ui.banner()
        ui.info(f"Dry-run test: executing 1 batch of {len(test_items)} item(s) using task '{task.name}'...")

    engine = Engine(task=task)
    from .packer import pack_items
    batches = pack_items(test_items, batch_size=task.batch_size, max_slice_chars=task.max_slice_chars)
    if not batches:
        if args.json:
            print(json.dumps({"ok": False, "error": "Could not pack items into batch."}))
            sys.exit(1)
        ui.error("Could not pack items into batch.")
        return

    b = batches[0]
    if not args.json:
        ui.info(f"Dispatching test batch '{b['batch_id']}' across available free model ladder...")
    ok, results, receipt, err = engine.execute_batch(b)

    if args.json:
        res_payload = {
            "ok": ok,
            "route_used": receipt.get("requested_route") if receipt else None,
            "cost": receipt.get("cost") if receipt else None,
            "duration_seconds": receipt.get("duration_seconds") if receipt else None,
            "results": results,
            "error": err
        }
        print(json.dumps(res_payload, indent=2))
        sys.exit(0 if ok else 1)

    print("\n" + "=" * 80)
    if ok:
        ui.success("Batch successfully executed and passed mathematical grounding!")
        ui.info(f"Route used: {receipt.get('requested_route')}")
        ui.info(f"Reported cost: {receipt.get('cost')} ({receipt.get('cost_status')})")
        ui.info(f"Duration: {receipt.get('duration_seconds', 0):.2f}s")
        print("\nExtracted Items:")
        print(json.dumps(results, indent=2))
    else:
        ui.error(f"Execution or grounding failed: {err}")
        if receipt:
            ui.warn(f"Last receipt: {json.dumps(receipt, indent=2)}")
    print("=" * 80 + "\n")

def cmd_run(args):
    task = load_task(args.task)
    try:
        items = _load_input_data(args.input)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "error": str(e)}))
            sys.exit(1)
        ui.error(str(e))
        sys.exit(1)

    if not items:
        if args.json:
            print(json.dumps({"status": "error", "error": "No input items to process."}))
            sys.exit(1)
        ui.error("No input items to process.")
        return

    concurrency = args.sessions or args.concurrency or 4
    run_id = args.run_id or f"run_{task.name}_{int(time.time())}"
    run_dir = Path(args.output_dir or f"runs/{run_id}")
    out_packet = Path(args.output) if args.output else (run_dir / "clean_packet.json")

    if not args.json:
        ui.banner()
        ui.info(f"Starting bulk campaign '{run_id}'")
        ui.info(f"Items: {len(items)} | Parallel Worker Sessions: {concurrency}")

    engine = Engine(task=task)
    packet = engine.run_campaign(
        raw_items=items,
        run_dir=run_dir,
        concurrency=concurrency,
        max_attempts=args.max_attempts,
        output_packet_path=out_packet
    )

    if args.json:
        print(json.dumps(packet, indent=2))

def cmd_resume(args):
    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        if args.json:
            print(json.dumps({"status": "error", "error": f"No manifest found in {run_dir}"}))
            sys.exit(1)
        ui.error(f"No manifest found in {run_dir}")
        return
    
    manifest_data = json.loads(manifest_path.read_text())
    if not args.json:
        ui.banner()
        ui.info(f"Resuming run '{manifest_data.get('run_id')}' from {run_dir}")
    
    if not args.input or not args.task:
        err = "Resuming requires specifying --task and --input to reconstruct pending items."
        if args.json:
            print(json.dumps({"status": "error", "error": err}))
            sys.exit(1)
        ui.error(err)
        return
        
    cmd_run(args)

def cmd_export(args):
    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        if args.json:
            print(json.dumps({"status": "error", "error": f"No manifest found in {run_dir}"}))
            sys.exit(1)
        ui.error(f"No manifest found in {run_dir}")
        return
    manifest_data = json.loads(manifest_path.read_text())
    out_path = Path(args.output or (run_dir / "clean_packet.json"))
    packet = export_clean_packet(manifest_data, out_path)
    
    if args.json:
        print(json.dumps(packet, indent=2))
        return

    ui.banner()
    ui.success(f"Exported clean packet to: {out_path}")
    ui.info(f"Total records: {packet['total_verified_records']}")

def cmd_serve(args):
    from .mcp_server import run_mcp_server
    run_mcp_server()

def main():
    parser = argparse.ArgumentParser(
        prog="bulk-lanes",
        description="Air-Gapped Bulk Model Lane Orchestrator for any harness (OpenCode + OpenRouter)"
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output for agent harnesses")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # routes
    p_routes = subparsers.add_parser("routes", help="List available model lanes")
    p_routes.add_argument("--all", action="store_true", help="Show all routes including billable and disabled")
    p_routes.add_argument("--refresh", action="store_true", help="Scan providers for models with 'free' in schema")
    p_routes.add_argument("--json", action="store_true", help="Output as JSON")

    # sessions
    p_sessions = subparsers.add_parser("sessions", help="Inspect worker sessions for a run")
    p_sessions.add_argument("run_dir", help="Directory of the run to inspect")
    p_sessions.add_argument("--json", action="store_true", help="Output as JSON")

    # init
    p_init = subparsers.add_parser("init", help="Scaffold a new bulk triage task")
    p_init.add_argument("name", nargs="?", default="my_task", help="Name of the task directory to create")
    p_init.add_argument("--json", action="store_true", help="Output as JSON")

    # test
    p_test = subparsers.add_parser("test", help="Dry run 1 batch to test prompt & grounding")
    p_test.add_argument("--task", required=True, help="Path to task.py definition")
    p_test.add_argument("--input", required=True, help="Path to sample input (.jsonl or .json)")
    p_test.add_argument("--json", action="store_true", help="Output as JSON")

    # run
    p_run = subparsers.add_parser("run", help="Launch a bulk orchestration run")
    p_run.add_argument("--task", required=True, help="Path to task.py definition")
    p_run.add_argument("--input", required=True, help="Path to input data (.jsonl or .json)")
    p_run.add_argument("--sessions", "--concurrency", dest="sessions", type=int, default=4, help="Number of parallel worker sessions (default: 4)")
    p_run.add_argument("--max-attempts", type=int, default=300, help="Attempt ceiling across campaign")
    p_run.add_argument("--output-dir", help="Directory for run manifest and artifacts")
    p_run.add_argument("--output", help="Output path for exported clean packet JSON")
    p_run.add_argument("--run-id", help="Optional run identifier")
    p_run.add_argument("--json", action="store_true", help="Output as JSON")

    # resume
    p_resume = subparsers.add_parser("resume", help="Resume an interrupted run")
    p_resume.add_argument("run_dir", help="Directory of the run to resume")
    p_resume.add_argument("--task", required=True, help="Path to task.py")
    p_resume.add_argument("--input", required=True, help="Path to original input file")
    p_resume.add_argument("--sessions", "--concurrency", dest="sessions", type=int, default=4)
    p_resume.add_argument("--max-attempts", type=int, default=300)
    p_resume.add_argument("--output-dir", default=None)
    p_resume.add_argument("--output", default=None)
    p_resume.add_argument("--run-id", default=None)
    p_resume.add_argument("--json", action="store_true", help="Output as JSON")

    # export
    p_export = subparsers.add_parser("export", help="Export clean packet from an existing run")
    p_export.add_argument("run_dir", help="Directory of the run")
    p_export.add_argument("--output", help="Output path for clean packet JSON")
    p_export.add_argument("--json", action="store_true", help="Output as JSON")

    # serve (MCP Server)
    p_serve = subparsers.add_parser("serve", help="Run MCP (Model Context Protocol) server over stdio")

    args = parser.parse_args()
    if not args.command:
        if args.json:
            print(json.dumps({"error": "No command specified"}))
        else:
            ui.banner()
            parser.print_help()
        sys.exit(0)

    if args.command == "routes":
        cmd_routes(args)
    elif args.command == "sessions":
        cmd_sessions(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "resume":
        cmd_resume(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "serve":
        cmd_serve(args)

if __name__ == "__main__":
    main()
