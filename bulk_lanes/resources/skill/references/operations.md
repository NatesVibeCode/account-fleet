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

`validate` is offline. `test` performs one real inference batch. `run` stores its exact task revision, input digest, typed batches, leases, attempts, sessions, and receipts in SQLite.

## Inspect and resume

```bash
bulk-lanes tasks --json
bulk-lanes routes --json
bulk-lanes sessions my-run --json
bulk-lanes resume my-run --json
bulk-lanes export my-run --output clean_packet.json --json
```

Resume needs only the run ID. SQLite already holds the batch payloads. Do not reconstruct a run from the original files.

Packaged routes are disabled hints, not current price evidence. `routes --refresh` contacts providers and appends observations. Use it only when that mutation is in scope.

## Database

The default is `./bulk-lanes.db`. Select a different database with `--db PATH` or `BULK_LANES_DB`.

```bash
bulk-lanes schema database
```

The queue uses WAL, foreign keys, busy timeout, and atomic `BEGIN IMMEDIATE` leases. Attempt and model-run evidence is retained.

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

The MCP database defaults to `<workspace>/bulk-lanes.db`. Task, input, database, and packet paths outside the root are refused.

## Stops

- No observed-zero route: inspect route states; do not fall back to billable routes.
- OpenCode missing: install/configure the normal CLI or use configured OpenRouter.
- Typed-input failure: fix the named field or malformed line; do not enable aliases or skipping.
- Typed-output failure: correct the task schema or model response; do not permit extra fields.
- Ambiguous quote: require explicit offsets instead of guessing which occurrence was cited.
- Attempt budget exhausted: report it; do not raise the ceiling without operator direction.
