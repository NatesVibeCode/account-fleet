"""Typed MCP tools with a workspace-confined file boundary."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .catalog import RouteCatalog
from .engine import Engine
from .export import export_clean_packet
from .input_data import load_input_items
from .models import (
    BatchTestResult,
    CandidateModelOutput,
    CleanPacket,
    DoctorCheck,
    DoctorReport,
    InputItem,
    ID_PATTERN,
    ModelOutput,
    RouteEvalReport,
    RoutePolicy,
    RoutesResult,
    RunStatusReport,
    SchemaResult,
    TaskSpec,
    TaskRegistrationResult,
    TasksResult,
    ValidationReport,
)
from .packer import pack_items
from .store import BulkLanesStore, SCHEMA_SQL, SCHEMA_VERSION
from .task import load_task_spec


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("workspace root must be a directory")

    def path(self, value: str, *, exists: bool = False) -> Path:
        candidate = Path(value).expanduser()
        resolved = (self.root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"path escapes workspace root: {value}")
        if exists and not resolved.exists():
            raise FileNotFoundError(f"path not found: {value}")
        return resolved


def create_mcp_server(workspace_root: str | Path, db_path: str | Path | None = None) -> FastMCP:
    workspace = Workspace(workspace_root)
    resolved_db = workspace.path(str(db_path)) if db_path else workspace.path("bulk-lanes.db")
    store = BulkLanesStore(resolved_db)

    def resolve_task(reference: str) -> TaskSpec:
        candidate = workspace.path(reference)
        if candidate.is_file():
            task = load_task_spec(candidate)
            store.register_task(task)
            return task
        return store.get_task(reference)

    server = FastMCP(
        "bulk-lanes",
        instructions="Execute typed, evidence-bound bulk tasks inside the configured workspace.",
    )

    @server.tool(structured_output=True)
    def bulk_lanes_routes(
        refresh: Annotated[bool, Field(description="Refresh provider catalogues")] = False,
        observed_zero_only: Annotated[bool, Field(description="Return only routes with observed zero pricing")] = True,
    ) -> RoutesResult:
        """List admitted routes; optionally append fresh provider price observations."""
        catalog = RouteCatalog(db_path=store.path)
        refresh_result = catalog.refresh_all() if refresh else None
        routes = catalog.get_routes(free_only=observed_zero_only, include_disabled=not observed_zero_only)
        return RoutesResult.model_validate({"routes": routes, "refresh": refresh_result})

    @server.tool(structured_output=True)
    def bulk_lanes_register_task(task: TaskSpec) -> TaskRegistrationResult:
        """Validate and register one immutable, declarative task revision."""
        revision = store.register_task(task)
        return TaskRegistrationResult(task=task.name, revision=revision)

    @server.tool(structured_output=True)
    def bulk_lanes_tasks() -> TasksResult:
        """List the current registered task names and their exact revision IDs."""
        tasks = store.list_tasks()
        return TasksResult(tasks=tasks, count=len(tasks))

    @server.tool(structured_output=True)
    def bulk_lanes_test(
        task: Annotated[str, Field(description="Registered task name or workspace-relative TaskSpec JSON")],
        input_path: Annotated[str, Field(description="Workspace-relative JSON, JSONL, or CSV input")],
        id_column: Annotated[str | None, Field(description="Optional CSV ID column")] = None,
        text_column: Annotated[str | None, Field(description="Optional CSV text column")] = None,
    ) -> BatchTestResult:
        """Run one real inference batch and return only typed, source-grounded results."""
        task_spec = resolve_task(task)
        items = load_input_items(workspace.path(input_path, exists=True), id_column=id_column, text_column=text_column)
        batches = pack_items(items[:task_spec.batch_size], task_spec.batch_size, task_spec.max_slice_chars)
        if not batches:
            raise ValueError("input contains no packable items")
        ok, results, receipt, error = Engine(task=task_spec, store=store).execute_batch(batches[0])
        return BatchTestResult.model_validate({
            "ok": ok,
            "results": results,
            "receipt": receipt or None,
            "error": error,
        })

    @server.tool(structured_output=True)
    def bulk_lanes_validate(
        task: Annotated[str, Field(description="Registered task name or workspace-relative TaskSpec JSON")],
        input_path: Annotated[str, Field(description="Workspace-relative JSON, JSONL, or CSV input")],
        id_column: Annotated[str | None, Field(description="Optional CSV ID column")] = None,
        text_column: Annotated[str | None, Field(description="Optional CSV text column")] = None,
    ) -> ValidationReport:
        """Validate a task and all input records offline without invoking a model."""
        task_spec = resolve_task(task)
        items = load_input_items(workspace.path(input_path, exists=True), id_column=id_column, text_column=text_column)
        batches = pack_items(items, task_spec.batch_size, task_spec.max_slice_chars)
        return ValidationReport(valid=True, task=task_spec.name, input_items=len(items), batches=len(batches))

    @server.tool(structured_output=True)
    def bulk_lanes_run(
        task: Annotated[str, Field(description="Registered task name or workspace-relative TaskSpec JSON")],
        input_path: Annotated[str, Field(description="Workspace-relative JSON, JSONL, or CSV input")],
        run_id: Annotated[str, Field(description="Stable run identifier", pattern=ID_PATTERN, max_length=128)],
        sessions: Annotated[int, Field(ge=1, le=64)] = 4,
        max_attempts: Annotated[int, Field(ge=1, le=100_000)] = 300,
        output_packet: Annotated[str | None, Field(description="Optional workspace-relative packet path")] = None,
        id_column: Annotated[str | None, Field(description="Optional CSV ID column")] = None,
        text_column: Annotated[str | None, Field(description="Optional CSV text column")] = None,
        policy: Annotated[RoutePolicy | None, Field(description="Optional RoutePolicy with privacy, transport, or cost bounds")] = None,
    ) -> CleanPacket:
        """Create and execute a bounded, resumable SQLite-backed bulk campaign."""
        task_spec = resolve_task(task)
        input_file = workspace.path(input_path, exists=True)
        items = load_input_items(input_file, id_column=id_column, text_column=text_column)
        packet_path = workspace.path(output_packet) if output_packet else workspace.path(f"runs/{run_id}/clean_packet.json")
        packet = Engine(task=task_spec, store=store, policy=policy).run_campaign(
            raw_items=items,
            run_id=run_id,
            input_path=str(input_file),
            concurrency=sessions,
            max_attempts=max_attempts,
            output_packet_path=packet_path,
            policy=policy,
        )
        return CleanPacket.model_validate(packet)

    @server.tool(structured_output=True)
    def bulk_lanes_resume(
        run_id: Annotated[str, Field(description="Existing SQLite run identifier")],
        sessions: Annotated[int, Field(ge=1, le=64)] = 4,
        output_packet: Annotated[str | None, Field(description="Optional workspace-relative packet path")] = None,
    ) -> CleanPacket:
        """Resume pending batches from an existing run without rereading source files."""
        task_spec = store.get_run_task(run_id)
        snapshot = store.run_snapshot(run_id)
        packet_path = workspace.path(output_packet) if output_packet else workspace.path(snapshot["output_path"])
        packet = Engine(task=task_spec, store=store).resume_campaign(run_id, sessions, packet_path)
        return CleanPacket.model_validate(packet)

    @server.tool(structured_output=True)
    def bulk_lanes_status(
        run_id: Annotated[str, Field(description="Existing SQLite run identifier")],
    ) -> RunStatusReport:
        """Show real-time progress, batch status counts, and per-route reliability metrics for a run."""
        return store.get_run_status(run_id)

    @server.tool(structured_output=True)
    def bulk_lanes_eval(
        task: Annotated[str, Field(description="Registered task name or workspace-relative TaskSpec JSON")],
        input_path: Annotated[str, Field(description="Evaluation dataset (CSV, JSONL, or JSON)")],
        routes: Annotated[list[str] | None, Field(description="Optional list of route IDs to benchmark")] = None,
        id_column: Annotated[str | None, Field(description="Optional CSV ID column")] = None,
        text_column: Annotated[str | None, Field(description="Optional CSV text column")] = None,
    ) -> RouteEvalReport:
        """Benchmark candidate routes against test samples and update intelligent ranking priors."""
        from .eval import RouteEvaluator
        task_spec = resolve_task(task)
        items = load_input_items(workspace.path(input_path, exists=True), id_column=id_column, text_column=text_column)
        evaluator = RouteEvaluator(task=task_spec, store=store)
        return evaluator.evaluate_routes(samples=items, candidate_routes=routes)

    @server.tool(structured_output=True)
    def bulk_lanes_export(
        run_id: Annotated[str, Field(description="Existing SQLite run identifier")],
        output_path: Annotated[str | None, Field(description="Optional workspace-relative export path")] = None,
        export_format: Annotated[str, Field(description="Export format: json or csv")] = "json",
    ) -> CleanPacket:
        """Export verified records as a self-validating typed packet (JSON) or flat CSV."""
        snapshot = store.run_snapshot(run_id)
        default_ext = "csv" if export_format == "csv" else "json"
        destination = workspace.path(output_path) if output_path else workspace.path(f"runs/{run_id}/clean_packet.{default_ext}")
        packet = export_clean_packet(snapshot, destination, export_format=export_format)
        return CleanPacket.model_validate(packet)

    @server.tool(structured_output=True)
    def bulk_lanes_schema(
        kind: Annotated[str, Field(pattern="^(task|input|candidate-output|output|packet|database)$")],
    ) -> SchemaResult:
        """Return an admitted JSON Schema or the authoritative SQLite schema."""
        models = {
            "task": TaskSpec,
            "input": InputItem,
            "candidate-output": CandidateModelOutput,
            "output": ModelOutput,
            "packet": CleanPacket,
        }
        from .store import get_database_schema_sql
        document = (
            {"schema_version": SCHEMA_VERSION, "sql": get_database_schema_sql()}
            if kind == "database"
            else models[kind].model_json_schema(by_alias=True)
        )
        return SchemaResult(kind=kind, schema_document=document)

    @server.tool(structured_output=True)
    def bulk_lanes_doctor() -> DoctorReport:
        """Check workspace SQLite state, provider availability, and usable routes."""
        catalog = RouteCatalog(db_path=store.path)
        routes = catalog.get_routes(free_only=True)
        opencode = shutil.which("opencode")
        openrouter = bool(os.environ.get("OPENROUTER_API_KEY"))
        checks = [
            DoctorCheck(name="database", ok=store.schema_version() in ("1", "2"), detail=f"SQLite schema {store.schema_version()}"),
            DoctorCheck(name="opencode", ok=bool(opencode), detail=opencode or "opencode not found in PATH"),
            DoctorCheck(name="openrouter", ok=openrouter, detail="configured" if openrouter else "optional key not configured"),
            DoctorCheck(name="routes", ok=bool(routes), detail=f"{len(routes)} enabled observed-zero routes"),
        ]
        ready = checks[0].ok and checks[3].ok and (checks[1].ok or checks[2].ok)
        return DoctorReport(ready=ready, database=str(store.path), checks=checks)

    return server


def run_mcp_server(workspace_root: str | Path = ".", db_path: str | Path | None = None) -> None:
    create_mcp_server(workspace_root, db_path).run(transport="stdio")
