"""User-friendly Command Line Interface for bulk-lanes."""
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
    ui.banner()
    cat = RouteCatalog()
    if getattr(args, "refresh", False):
        ui.info("Querying OpenCode CLI model registry for zero-cost routes...")
        try:
            count = cat.refresh_from_opencode()
            ui.success(f"Catalogue refreshed successfully ({count} models evaluated).")
        except Exception as e:
            ui.error(f"Failed to refresh catalogue: {e}")

    free_only = not args.all
    routes = cat.get_routes(free_only=free_only)
    if not routes:
        ui.warn("No routes found matching filter.")
        return
    ui.info(f"Showing {'all configured' if args.all else 'active free/zero-price'} routes:")
    ui.print_routes_table(routes)

def cmd_init(args):
    ui.banner()
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

    ui.success(f"Initialized new task in '{task_dir}/'")
    print(f"\nRun a dry-run test:\n  bulk-lanes test --task {task_file} --input {data_file}\n")
    print(f"Run a bulk execution:\n  bulk-lanes run --task {task_file} --input {data_file}\n")

def _load_input_data(input_path_str: str) -> List[dict]:
    p = Path(input_path_str)
    if not p.exists():
        ui.error(f"Input file not found: {input_path_str}")
        sys.exit(1)
    
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
        ui.error(f"Unsupported file format '{p.suffix}'. Use .json or .jsonl")
        sys.exit(1)
    return items

def cmd_test(args):
    ui.banner()
    task = load_task(args.task)
    items = _load_input_data(args.input)
    if not items:
        ui.error("No items found in input file.")
        return
    
    test_items = items[:task.batch_size]
    ui.info(f"Dry-run test: executing 1 batch of {len(test_items)} item(s) using task '{task.name}'...")

    engine = Engine(task=task)
    from .packer import pack_items
    batches = pack_items(test_items, batch_size=task.batch_size, max_slice_chars=task.max_slice_chars)
    if not batches:
        ui.error("Could not pack items into batch.")
        return

    b = batches[0]
    ui.info(f"Dispatching test batch '{b['batch_id']}' across available model ladder...")
    ok, results, receipt, err = engine.execute_batch(b)

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
    ui.banner()
    task = load_task(args.task)
    items = _load_input_data(args.input)
    if not items:
        ui.error("No input items to process.")
        return

    run_id = args.run_id or f"run_{task.name}_{int(time.time())}"
    run_dir = Path(args.output_dir or f"runs/{run_id}")
    
    ui.info(f"Starting bulk campaign '{run_id}'")
    ui.info(f"Items: {len(items)} | Concurrency: {args.concurrency} worker lanes")

    engine = Engine(task=task)
    out_packet = Path(args.output) if args.output else None
    engine.run_campaign(
        raw_items=items,
        run_dir=run_dir,
        concurrency=args.concurrency,
        max_attempts=args.max_attempts,
        output_packet_path=out_packet
    )

def cmd_resume(args):
    ui.banner()
    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        ui.error(f"No manifest found in {run_dir}")
        return
    
    manifest_data = json.loads(manifest_path.read_text())
    ui.info(f"Resuming run '{manifest_data.get('run_id')}' from {run_dir}")
    
    if not args.input or not args.task:
        ui.error("Resuming requires specifying --task and --input to reconstruct pending items.")
        return
        
    cmd_run(args)

def cmd_export(args):
    ui.banner()
    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        ui.error(f"No manifest found in {run_dir}")
        return
    manifest_data = json.loads(manifest_path.read_text())
    out_path = Path(args.output or (run_dir / "clean_packet.json"))
    packet = export_clean_packet(manifest_data, out_path)
    ui.success(f"Exported clean packet to: {out_path}")
    ui.info(f"Total records: {packet['total_verified_records']}")

def main():
    parser = argparse.ArgumentParser(
        prog="bulk-lanes",
        description="Air-Gapped Bulk Model Lane Orchestrator (OpenCode + OpenRouter)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # routes
    p_routes = subparsers.add_parser("routes", help="List available model lanes")
    p_routes.add_argument("--all", action="store_true", help="Show all routes including billable and disabled")
    p_routes.add_argument("--refresh", action="store_true", help="Refresh zero-cost catalogue from opencode CLI")

    # init
    p_init = subparsers.add_parser("init", help="Scaffold a new bulk triage task")
    p_init.add_argument("name", nargs="?", default="my_task", help="Name of the task directory to create")

    # test
    p_test = subparsers.add_parser("test", help="Dry run 1 batch to test prompt & grounding")
    p_test.add_argument("--task", required=True, help="Path to task.py definition")
    p_test.add_argument("--input", required=True, help="Path to sample input (.jsonl or .json)")

    # run
    p_run = subparsers.add_parser("run", help="Launch a bulk orchestration run")
    p_run.add_argument("--task", required=True, help="Path to task.py definition")
    p_run.add_argument("--input", required=True, help="Path to input data (.jsonl or .json)")
    p_run.add_argument("--concurrency", type=int, default=4, help="Worker concurrency limit (default: 4)")
    p_run.add_argument("--max-attempts", type=int, default=300, help="Attempt ceiling across campaign")
    p_run.add_argument("--output-dir", help="Directory for run manifest and artifacts")
    p_run.add_argument("--output", help="Output path for exported clean packet JSON")
    p_run.add_argument("--run-id", help="Optional run identifier")

    # resume
    p_resume = subparsers.add_parser("resume", help="Resume an interrupted run")
    p_resume.add_argument("run_dir", help="Directory of the run to resume")
    p_resume.add_argument("--task", required=True, help="Path to task.py")
    p_resume.add_argument("--input", required=True, help="Path to original input file")
    p_resume.add_argument("--concurrency", type=int, default=4)
    p_resume.add_argument("--max-attempts", type=int, default=300)
    p_resume.add_argument("--output-dir", default=None)
    p_resume.add_argument("--output", default=None)
    p_resume.add_argument("--run-id", default=None)

    # export
    p_export = subparsers.add_parser("export", help="Export clean packet from an existing run")
    p_export.add_argument("run_dir", help="Directory of the run")
    p_export.add_argument("--output", help="Output path for clean packet JSON")

    args = parser.parse_args()
    if not args.command:
        ui.banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "routes":
        cmd_routes(args)
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

if __name__ == "__main__":
    main()
