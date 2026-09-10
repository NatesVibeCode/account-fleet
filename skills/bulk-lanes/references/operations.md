# Operations

Read this for CLI or MCP operation.

## Fresh system

```bash
python3 -m pip install .
bulk-lanes setup --workspace-root "$PWD" --refresh-routes --json
```

Setup installs the standard skill at `<workspace>/.agents/skills/bulk-lanes`, initializes SQLite, and returns one stdio MCP definition. Use `--scope user` for `~/.agents/skills`. If a harness requires another discovery directory, pass that parent through `--skill-root`. Setup is idempotent and refuses to overwrite different content unless `--force` is explicit.

The CLI, JSON contracts, SQLite database, and stdio MCP server do not depend on skill discovery. The skill only supplies the exact operating procedure to compatible harnesses.

## Happy path

```bash
bulk-lanes doctor
bulk-lanes init my-task --preset classify
bulk-lanes validate my-task --input my-task.sample.jsonl
bulk-lanes test my-task --input my-task.sample.jsonl
bulk-lanes run my-task --input my-task.sample.jsonl --run-id my-run
```

For tabular data, pass CSV directly:
```bash
bulk-lanes run my-task --input data.csv --id-column id --text-column body --run-id my-run
```

`validate` is offline. `test` performs one real inference batch. `run` stores its exact task revision, input digest, typed batches, leases, attempts, sessions, receipts, and inference attempts in SQLite.

## Real-time status and benchmark eval

```bash
# Monitor live run progress, batch states, and per-route reliability
bulk-lanes status my-run --watch

# Benchmark routes on a test sample to update intelligent ranking priors
bulk-lanes eval my-task --input eval-sample.csv --id-column id --text-column body
```

## Inspect, resume, and export

```bash
bulk-lanes tasks --json
bulk-lanes routes --json
bulk-lanes routes add openai_compatible:llama3.2:latest --provider openai_compatible --free
bulk-lanes sessions my-run --json
bulk-lanes status my-run --json
bulk-lanes resume my-run --json
bulk-lanes export my-run --format csv --output results.csv
```

Resume needs only the run ID. SQLite already holds the batch payloads. Do not reconstruct a run from the original files.

Packaged routes are disabled hints, not current price evidence. `routes --refresh` contacts providers and appends observations. Use it only when that mutation is in scope.

## Data & Policy Flags

Runs can be restricted by policy:
- `--zdr`: Enforce zero data retention on provider models.
- `--no-data-collection`: Disallow models that train on inputs.
- `--provider <transport>`: Restrict candidate routes to specific transports (`openrouter`, `opencode`, `openai_compatible`).
- `--exclude-provider <transport>`: Exclude specific transports.
- `--openrouter-providers <names>`: Filter OpenRouter upstream routing (e.g. `Anthropic,Together`).
- `--openrouter-order <names>`: Custom ordering for upstream OpenRouter providers.

## Database

The default is `./bulk-lanes.db`. Select a different database with `--db PATH` or `BULK_LANES_DB`.

```bash
bulk-lanes schema database
```

The queue uses WAL, foreign keys, busy timeout, and atomic `BEGIN IMMEDIATE` leases. Attempt and model-run evidence is retained. Schema version is `"2"`.

## MCP

```json
{
  "mcpServers": {
    "bulk-lanes": {
      "command": "bulk-lanes",
      "args": ["serve", "--workspace-root", "/absolute/workspace"]
    }
  }
}
```

The MCP server exposes 12 structured tools:
1. `bulk_lanes_routes`: List admitted routes, optionally refresh.
2. `bulk_lanes_register_task`: Register an immutable task revision.
3. `bulk_lanes_tasks`: List registered task definitions.
4. `bulk_lanes_test`: Run one batch through candidate models (supports `id_column`, `text_column`).
5. `bulk_lanes_validate`: Offline task and input validation.
6. `bulk_lanes_run`: Launch bounded resumable campaign (supports `id_column`, `text_column`, `policy`).
7. `bulk_lanes_resume`: Resume pending batches from existing run.
8. `bulk_lanes_status`: Real-time batch progress and per-route reliability metrics.
9. `bulk_lanes_eval`: Benchmark routes against sample inputs and update ranking priors.
10. `bulk_lanes_export`: Export clean packet (`format="json"|"csv"`).
11. `bulk_lanes_schema`: View JSON Schemas or SQLite database schema.
12. `bulk_lanes_doctor`: Check workspace health and provider readiness.

The MCP database defaults to `<workspace>/bulk-lanes.db`. Task, input, database, and packet paths outside the root are refused.

## Stops

- No observed-zero route: inspect route states; do not fall back to billable routes.
- OpenCode missing: install/configure the normal CLI or use configured OpenRouter.
- Typed-input failure: fix the named field or malformed line; do not enable aliases or skipping.
- Typed-output failure: correct the task schema or model response; do not permit extra fields.
- Ambiguous quote: require explicit offsets instead of guessing which occurrence was cited.
- Attempt budget exhausted: report it; do not raise the ceiling without operator direction.
