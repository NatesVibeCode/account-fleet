"""Human and machine CLI for the SQLite-backed bulk-lanes control plane."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shlex
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from . import ui
from .catalog import RouteCatalog
from .engine import Engine
from .export import export_clean_packet
from .input_data import load_input_items
from .models import (
    CandidateModelOutput,
    CleanPacket,
    DoctorCheck,
    DoctorReport,
    InputItem,
    ModelOutput,
    RoutePolicy,
    TaskSpec,
    ValidationReport,
)
from .packer import pack_items
from .store import BulkLanesStore, SCHEMA_SQL, SCHEMA_VERSION, default_db_path
from .setup import installed_skill_matches, setup_workspace, skill_destination
from .task import load_task_spec


def _extract_policy(args: argparse.Namespace) -> RoutePolicy | None:
    providers = getattr(args, "provider", None)
    exclude_providers = getattr(args, "exclude_provider", None) or []
    routes = getattr(args, "route", None)
    exclude_routes = getattr(args, "exclude_route", None) or []
    zdr = bool(getattr(args, "zdr", False))
    no_data_coll = bool(getattr(args, "no_data_collection", False))
    max_cost_in = float(getattr(args, "max_cost_in", 0.0) or 0.0)
    max_cost_out = float(getattr(args, "max_cost_out", 0.0) or 0.0)

    if not any([providers, exclude_providers, routes, exclude_routes, zdr, no_data_coll, max_cost_in > 0, max_cost_out > 0]):
        return None

    return RoutePolicy(
        allowed_providers=providers if providers else None,
        excluded_providers=exclude_providers,
        allowed_routes=routes if routes else None,
        excluded_routes=exclude_routes,
        zdr=zdr,
        allow_data_collection=not no_data_coll,
        max_cost_per_1k_input=max_cost_in,
        max_cost_per_1k_output=max_cost_out,
    )


def _load_input(args: argparse.Namespace) -> list[InputItem]:
    return load_input_items(
        args.input,
        id_column=getattr(args, "id_column", None),
        text_column=getattr(args, "text_column", None),
        title_column=getattr(args, "title_column", None),
        uri_column=getattr(args, "uri_column", None),
    )


PRESETS: dict[str, dict[str, Any]] = {
    "summarize": {
        "instructions": "Summarize each item using only supported source facts.",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    },
    "classify": {
        "instructions": "Classify each item and give a short supported summary.",
        "properties": {"label": {"type": "string"}, "summary": {"type": "string"}},
        "required": ["label", "summary"],
    },
    "extract": {
        "instructions": "Extract a short supported summary and the named entities present in the source.",
        "properties": {
            "summary": {"type": "string"},
            "entities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "entities"],
    },
    "triage": {
        "instructions": "Assign a supported triage priority and explain why.",
        "properties": {
            "priority": {"enum": ["high", "medium", "low", "unknown"]},
            "reason": {"type": "string"},
        },
        "required": ["priority", "reason"],
    },
}


def _package_version() -> str:
    try:
        return importlib.metadata.version("bulk-lanes")
    except importlib.metadata.PackageNotFoundError:
        return "0.2.0"


def _emit(value: Any, json_mode: bool, human: str | None = None) -> None:
    payload = value.model_dump(mode="json", by_alias=True) if hasattr(value, "model_dump") else value
    if json_mode or human is None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(human)


def _store(args: argparse.Namespace) -> BulkLanesStore:
    return BulkLanesStore(Path(args.db) if getattr(args, "db", None) else default_db_path())


def _resolve_task(reference: str, store: BulkLanesStore) -> TaskSpec:
    path = Path(reference)
    if path.is_file():
        spec = load_task_spec(path)
        store.register_task(spec)
        return spec
    return store.get_task(reference)


def cmd_routes(args: argparse.Namespace) -> None:
    catalog = RouteCatalog(db_path=_store(args).path)
    refresh = catalog.refresh_all() if args.refresh else None
    routes = catalog.get_routes(free_only=not args.all, include_disabled=args.all)
    if args.json:
        _emit({"routes": routes, "count": len(routes), "refresh": refresh}, True)
    else:
        ui.banner()
        ui.print_routes_table(routes)


def cmd_tasks(args: argparse.Namespace) -> None:
    tasks = _store(args).list_tasks()
    human = "No tasks registered." if not tasks else "\n".join(
        f"{task['task_name']}  {task['revision_id'][:12]}" for task in tasks
    )
    _emit({"tasks": tasks, "count": len(tasks)}, args.json, human)


def cmd_init(args: argparse.Namespace) -> None:
    preset = PRESETS[args.preset]
    spec = TaskSpec(
        name=args.name,
        instructions=preset["instructions"],
        batch_size=args.batch_size,
        claims_schema={
            "type": "object",
            "properties": preset["properties"],
            "required": preset["required"],
            "additionalProperties": False,
        },
    )
    store = _store(args)
    revision = store.register_task(spec)
    sample_path = Path(args.sample or f"{args.name}.sample.jsonl")
    if not sample_path.exists():
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        sample = InputItem(item_id="item_1", title="Example", text="Replace this text with the source you want to process.")
        sample_path.write_text(json.dumps(sample.model_dump(mode="json", by_alias=True), ensure_ascii=False) + "\n")
    _emit(
        {
            "created": True,
            "task": spec.name,
            "preset": args.preset,
            "revision": revision,
            "database": str(store.path.resolve()),
            "sample_input": str(sample_path),
            "next": f"bulk-lanes validate {spec.name} --input {sample_path}",
        },
        args.json,
        f"Created task '{spec.name}' from preset '{args.preset}'.\n"
        f"Sample: {sample_path}\nNext: bulk-lanes validate {spec.name} --input {sample_path}",
    )


def cmd_validate(args: argparse.Namespace) -> None:
    store = _store(args)
    task = _resolve_task(args.task, store)
    items = _load_input(args)
    batches = pack_items(items, task.batch_size, task.max_slice_chars)
    _emit(
        ValidationReport(valid=True, task=task.name, input_items=len(items), batches=len(batches)),
        args.json,
        f"Valid. Task '{task.name}' will process {len(items)} items in {len(batches)} batches.",
    )


def cmd_test(args: argparse.Namespace) -> None:
    store = _store(args)
    task = _resolve_task(args.task, store)
    items = _load_input(args)
    policy = _extract_policy(args)
    batch = pack_items(items[: task.batch_size], task.batch_size, task.max_slice_chars)[0]
    engine = Engine(task=task, store=store, policy=policy)
    ok, results, receipt, error = engine.execute_batch(batch)
    _emit(
        {"ok": ok, "results": results, "receipt": receipt or None, "error": error},
        args.json,
        f"{'Passed' if ok else 'Failed'} one batch.\n{json.dumps(results if ok else {'error': error}, indent=2)}",
    )
    if not ok:
        raise SystemExit(1)


def cmd_run(args: argparse.Namespace) -> None:
    store = _store(args)
    task = _resolve_task(args.task, store)
    items = _load_input(args)
    policy = _extract_policy(args)
    run_id = args.run_id or f"{task.name}-{int(time.time())}"
    output = Path(args.output or f"runs/{run_id}/clean_packet.json")
    packet = Engine(task=task, store=store, policy=policy).run_campaign(
        raw_items=items,
        run_id=run_id,
        input_path=str(Path(args.input).resolve()),
        concurrency=args.sessions,
        max_attempts=args.max_attempts,
        output_packet_path=output,
        policy=policy,
    )
    _emit(
        {"run_id": run_id, "packet": str(output), "result": packet},
        args.json,
        f"Run '{run_id}' {store.run_snapshot(run_id)['status']}.\nPacket: {output}\nVerified records: {packet['total_verified_records']}",
    )


def cmd_resume(args: argparse.Namespace) -> None:
    store = _store(args)
    task = store.get_run_task(args.run_id)
    snapshot = store.run_snapshot(args.run_id)
    output = Path(args.output or snapshot["output_path"])
    packet = Engine(task=task, store=store).resume_campaign(
        args.run_id,
        concurrency=args.sessions,
        output_packet_path=output,
    )
    _emit(
        {"run_id": args.run_id, "packet": str(output), "result": packet},
        args.json,
        f"Run '{args.run_id}' {store.run_snapshot(args.run_id)['status']}.\nPacket: {output}\nVerified records: {packet['total_verified_records']}",
    )


def cmd_sessions(args: argparse.Namespace) -> None:
    snapshot = _store(args).run_snapshot(args.run_id)
    _emit(
        {"run_id": args.run_id, "status": snapshot["status"], "sessions": snapshot["sessions"]},
        args.json,
        f"Run '{args.run_id}' is {snapshot['status']}. Recorded worker sessions: {len(snapshot['sessions'])}.",
    )


def cmd_status(args: argparse.Namespace) -> None:
    store = _store(args)
    if not getattr(args, "watch", False):
        report = store.get_run_status(args.run_id)
        if args.json:
            _emit(report, True)
        else:
            ui.print_status_dashboard(report)
        return

    try:
        while True:
            report = store.get_run_status(args.run_id)
            if args.json:
                _emit(report, True)
            else:
                print("\033[H\033[J", end="")
                ui.print_status_dashboard(report)
            if report.status in ("completed", "completed_with_failures", "budget_exhausted"):
                break
            time.sleep(getattr(args, "interval", 2.0))
    except KeyboardInterrupt:
        pass


def cmd_eval(args: argparse.Namespace) -> None:
    from .eval import RouteEvaluator

    store = _store(args)
    task = _resolve_task(args.task, store)
    items = _load_input(args)
    target_routes = [r.strip() for r in args.routes.split(",") if r.strip()] if getattr(args, "routes", None) else None

    evaluator = RouteEvaluator(task=task, store=store)
    report = evaluator.evaluate_all(
        samples=items,
        routes=target_routes,
        expected_claims_key=getattr(args, "expected_claims_col", None),
    )
    if args.json:
        _emit(report, True)
    else:
        ui.print_eval_table(report)


def cmd_export(args: argparse.Namespace) -> None:
    store = _store(args)
    snapshot = store.run_snapshot(args.run_id)
    fmt = getattr(args, "format", "json") or "json"
    default_name = f"runs/{args.run_id}/clean_packet.{fmt}"
    output = Path(args.output or default_name)
    packet = export_clean_packet(snapshot, output, export_format=fmt)
    _emit(
        {"run_id": args.run_id, "output": str(output), "format": fmt, "result": packet},
        args.json,
        f"Exported {packet['total_verified_records']} verified records to {output} (format: {fmt}).",
    )


def cmd_schema(args: argparse.Namespace) -> None:
    models = {
        "task": TaskSpec,
        "input": InputItem,
        "candidate-output": CandidateModelOutput,
        "output": ModelOutput,
        "packet": CleanPacket,
    }
    schema = (
        {"schema_version": SCHEMA_VERSION, "sql": SCHEMA_SQL}
        if args.kind == "database"
        else models[args.kind].model_json_schema(by_alias=True)
    )
    _emit(schema, True)


def cmd_setup(args: argparse.Namespace) -> None:
    report = setup_workspace(
        scope=args.scope,
        workspace_root=args.workspace_root,
        db_path=args.db,
        skill_root=args.skill_root,
        dry_run=args.dry_run,
        force=args.force,
        refresh_routes=args.refresh_routes,
    )
    next_lines = "\n".join(shlex.join(command) for command in report.next_commands)
    _emit(
        report,
        args.json,
        f"Configured bulk-lanes at {report.skill_path}.\n"
        f"Database: {report.database}\nNext:\n{next_lines}",
    )


def cmd_doctor(args: argparse.Namespace) -> None:
    store = _store(args)
    catalog = RouteCatalog(db_path=store.path)
    observed_routes = catalog.get_routes(free_only=True)
    opencode = shutil.which("opencode")
    openrouter_key = bool(os.environ.get("OPENROUTER_API_KEY"))
    checks = [
        DoctorCheck(name="database", ok=store.schema_version() == "1", detail=f"SQLite schema {store.schema_version()} at {store.path.resolve()}"),
        DoctorCheck(name="opencode", ok=bool(opencode), detail=opencode or "opencode not found in PATH"),
        DoctorCheck(name="openrouter", ok=openrouter_key, detail="OPENROUTER_API_KEY configured" if openrouter_key else "optional key not configured"),
        DoctorCheck(name="routes", ok=bool(observed_routes), detail=f"{len(observed_routes)} enabled observed-zero routes"),
    ]
    workspace = Path(args.workspace_root).expanduser().resolve()
    destination = skill_destination(args.scope, Path.home().resolve(), workspace, args.skill_root)
    skill_ok = installed_skill_matches(destination)
    checks.append(DoctorCheck(
        name="skill",
        ok=skill_ok,
        detail=str(destination) if skill_ok else f"missing or outdated at {destination}",
    ))
    ready = checks[0].ok and checks[3].ok and (checks[1].ok or checks[2].ok)
    report = DoctorReport(ready=ready, database=str(store.path.resolve()), checks=checks)
    human = "\n".join(f"{'OK' if check.ok else '--'}  {check.name}: {check.detail}" for check in checks)
    _emit(report, args.json, f"{'Ready' if ready else 'Not ready'}\n{human}")
    if not ready:
        raise SystemExit(1)


def cmd_serve(args: argparse.Namespace) -> None:
    from .mcp_server import run_mcp_server

    run_mcp_server(args.workspace_root, args.db)


def _input_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id-column", help="CSV column to use for item ID")
    parser.add_argument("--text-column", help="CSV column to use for source text")
    parser.add_argument("--title-column", help="Optional CSV column for item title")
    parser.add_argument("--uri-column", help="Optional CSV column for source URI")


def _policy_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", action="append", help="Allow specific provider (can repeat)")
    parser.add_argument("--exclude-provider", action="append", help="Exclude specific provider (can repeat)")
    parser.add_argument("--route", action="append", help="Allow specific route ID (can repeat)")
    parser.add_argument("--exclude-route", action="append", help="Exclude specific route ID (can repeat)")
    parser.add_argument("--zdr", action="store_true", help="Require Zero Data Retention upstream")
    parser.add_argument("--no-data-collection", action="store_true", help="Deny provider data collection")
    parser.add_argument("--max-cost-in", type=float, default=0.0, help="Max cost per 1k input tokens (default: 0.0)")
    parser.add_argument("--max-cost-out", type=float, default=0.0, help="Max cost per 1k output tokens (default: 0.0)")


def _common(parser: argparse.ArgumentParser, *, json_output: bool = True, database: bool = True) -> None:
    if database:
        parser.add_argument("--db", help="SQLite control-plane path (default: ./bulk-lanes.db)")
    if json_output:
        parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bulk-lanes",
        description="Typed bulk classification, extraction, summarization, and triage",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    parser.add_argument("--json", dest="global_json", action="store_true", help="Emit machine-readable JSON")
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="Bootstrap a portable harness workspace")
    setup.add_argument("--scope", choices=["user", "project"], default="project")
    setup.add_argument("--workspace-root", default=".")
    setup.add_argument("--skill-root", help="Advanced: nonstandard parent directory for installed skills")
    setup.add_argument("--db", help="SQLite path below the workspace root")
    setup.add_argument("--refresh-routes", action="store_true", help="Contact providers and record current pricing")
    setup.add_argument("--dry-run", action="store_true", help="Return the setup plan without writing")
    setup.add_argument("--force", action="store_true", help="Update managed skill files when the destination differs")
    setup.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    routes = commands.add_parser("routes", help="List or refresh model routes")
    routes.add_argument("--all", action="store_true", help="Include non-zero, candidate, and disabled routes")
    routes.add_argument("--refresh", action="store_true", help="Contact providers and update route observations")
    _common(routes)

    tasks = commands.add_parser("tasks", help="List registered task definitions")
    _common(tasks)

    init = commands.add_parser("init", help="Create a typed task from a preset")
    init.add_argument("name")
    init.add_argument("--preset", choices=sorted(PRESETS), default="classify")
    init.add_argument("--batch-size", type=int, default=4)
    init.add_argument("--sample", help="Sample input path")
    _common(init)

    validate = commands.add_parser("validate", help="Validate a task and input without inference")
    validate.add_argument("task", help="Registered task name or TaskSpec JSON path")
    validate.add_argument("--input", required=True)
    _input_options(validate)
    _common(validate)

    test = commands.add_parser("test", help="Run one real inference batch")
    test.add_argument("task", help="Registered task name or TaskSpec JSON path")
    test.add_argument("--input", required=True)
    _input_options(test)
    _policy_options(test)
    _common(test)

    run = commands.add_parser("run", help="Create and execute a resumable run")
    run.add_argument("task", help="Registered task name or TaskSpec JSON path")
    run.add_argument("--input", required=True)
    run.add_argument("--sessions", type=int, default=4)
    run.add_argument("--max-attempts", type=int, default=300)
    run.add_argument("--run-id")
    run.add_argument("--output")
    _input_options(run)
    _policy_options(run)
    _common(run)

    resume = commands.add_parser("resume", help="Resume a run from its SQLite queue")
    resume.add_argument("run_id")
    resume.add_argument("--sessions", type=int, default=4)
    resume.add_argument("--output")
    _common(resume)

    status = commands.add_parser("status", help="Show real-time progress, attempts, and route stats for a run")
    status.add_argument("run_id")
    status.add_argument("--watch", action="store_true", help="Live monitor run progress until completion")
    status.add_argument("--interval", type=float, default=2.0, help="Watch refresh interval in seconds")
    _common(status)

    eval_cmd = commands.add_parser("eval", help="Benchmark routes against test samples and update intelligent route scores")
    eval_cmd.add_argument("task", help="Registered task name or TaskSpec JSON path")
    eval_cmd.add_argument("--input", required=True, help="Evaluation dataset (CSV, JSONL, or JSON)")
    eval_cmd.add_argument("--routes", help="Optional comma-separated route IDs to test")
    eval_cmd.add_argument("--expected-claims-col", help="Column/metadata key containing ground-truth claims")
    _input_options(eval_cmd)
    _common(eval_cmd)

    sessions = commands.add_parser("sessions", help="Inspect recorded run sessions")
    sessions.add_argument("run_id")
    _common(sessions)

    export = commands.add_parser("export", help="Export a validated packet from a run")
    export.add_argument("run_id")
    export.add_argument("--output")
    export.add_argument("--format", choices=["json", "csv"], default="json", help="Output format: json or csv")
    _common(export)

    schema = commands.add_parser("schema", help="Print an admitted JSON Schema")
    schema.add_argument("kind", choices=["task", "input", "candidate-output", "output", "packet", "database"])

    doctor = commands.add_parser("doctor", help="Check the local CLI, database, auth, and routes")
    doctor.add_argument("--scope", choices=["user", "project"], default="project")
    doctor.add_argument("--workspace-root", default=".")
    doctor.add_argument("--skill-root", help="Advanced: nonstandard parent directory for installed skills")
    _common(doctor)

    serve = commands.add_parser("serve", help="Run the MCP server over stdio")
    serve.add_argument("--workspace-root", default=".")
    serve.add_argument("--db", help="SQLite path below workspace root")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "global_json", False):
        args.json = True
    handlers = {
        "setup": cmd_setup,
        "routes": cmd_routes,
        "tasks": cmd_tasks,
        "init": cmd_init,
        "validate": cmd_validate,
        "test": cmd_test,
        "run": cmd_run,
        "resume": cmd_resume,
        "status": cmd_status,
        "eval": cmd_eval,
        "sessions": cmd_sessions,
        "export": cmd_export,
        "schema": cmd_schema,
        "doctor": cmd_doctor,
        "serve": cmd_serve,
    }
    try:
        handlers[args.command](args)
    except SystemExit:
        raise
    except Exception as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            ui.error(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
