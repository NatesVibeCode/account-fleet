# bulk-lanes

[![CI](https://github.com/NatesVibeCode/bulk-lanes/actions/workflows/ci.yml/badge.svg)](https://github.com/NatesVibeCode/bulk-lanes/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Run evidence-bound bulk classification, extraction, summarization, and triage through an installed model provider.

SQLite is the control plane. JSON and JSONL are typed import/export formats.

One task shape covers many jobs: `instructions` states the outcome, while a closed `claims_schema` defines the exact returned fields. Presets handle common work; a TaskSpec JSON handles domain-specific fields without adding code or accepting arbitrary output.

## Fresh system

```bash
git clone https://github.com/NatesVibeCode/bulk-lanes.git
python3 -m pip install ./bulk-lanes

mkdir my-bulk-workspace && cd my-bulk-workspace
bulk-lanes setup --workspace-root "$PWD" --refresh-routes
bulk-lanes init product-triage --preset classify
bulk-lanes validate product-triage --input product-triage.sample.jsonl
bulk-lanes test product-triage --input product-triage.sample.jsonl
bulk-lanes run product-triage --input product-triage.sample.jsonl --run-id first-run
```

The default project skill location is `.agents/skills/bulk-lanes`. Use `--scope user` for `~/.agents/skills`, or `--skill-root PATH` only when a harness documents a different discovery root.

`setup` is idempotent. It installs the standard skill bundled in the Python package, initializes the workspace database, and returns typed stdio MCP configuration plus exact next commands. It never overwrites different content unless `--force` is explicit. The CLI and MCP server work even when a harness does not support skills.

Resume without rebuilding the task or input:

```bash
bulk-lanes resume first-run
bulk-lanes export first-run
```

The default database is `./bulk-lanes.db`. Select another with `--db` or `BULK_LANES_DB`. During setup, the database must remain below the selected workspace root so the same path is valid through MCP.

## What SQLite owns

- immutable task revisions and the selected current revision;
- current routes plus append-only price observations;
- runs, typed batch payloads, atomic worker leases, and attempt ceilings;
- append-only batch attempts, verified results, and model receipts with explicit current-result selection;
- worker-session summaries and export state.

The queue uses WAL mode, foreign keys, a busy timeout, and `BEGIN IMMEDIATE` leasing. Two workers cannot claim the same batch.

Inspect the exact schema:

```bash
bulk-lanes schema database
```

## Standard input

Every JSON or JSONL record uses one closed shape:

```json
{
  "$schema": "https://raw.githubusercontent.com/NatesVibeCode/bulk-lanes/master/schemas/input-item-v1.schema.json",
  "item_id": "item_1",
  "text": "Source text to process",
  "title": "Optional title",
  "source_uri": "https://example.com/source",
  "content_type": "text/plain",
  "metadata": {}
}
```

Only `item_id` and `text` are required. Unknown fields, duplicate IDs, blank text, and malformed JSONL fail validation.

## Typed task fields

`init` includes four focused presets:

```bash
bulk-lanes init labels --preset classify
bulk-lanes init facts --preset extract
bulk-lanes init queue --preset triage
bulk-lanes init summaries --preset summarize
```

Task-specific fields live inside a closed JSON Schema. The stable record envelope is always:

```json
{
  "item_id": "item_1",
  "source_uri": "https://example.com/source",
  "source_digest": "sha256...",
  "content_type": "text/plain",
  "claims": {},
  "quotes": [{"slice_id": "full", "start": 0, "end": 11, "text": "exact quote"}]
}
```

Models only need to return `slice_id` and exact quote `text`. The verifier computes offsets when the quote occurs once. Repeated text requires explicit offsets. Stored and exported records always contain canonical offsets.

Print the admitted schemas:

```bash
bulk-lanes schema task
bulk-lanes schema input
bulk-lanes schema candidate-output
bulk-lanes schema output
bulk-lanes schema packet
```

## Commands

| Command | Purpose |
|---|---|
| `setup` | Install the bundled skill and initialize a fresh harness workspace |
| `doctor` | Check SQLite, installed CLIs, optional OpenRouter auth, and usable routes |
| `routes` | List routes; `--refresh` contacts providers and records observations |
| `tasks` | List current registered tasks |
| `init` | Register a task from a preset and create one sample input |
| `validate` | Check task and input without inference |
| `test` | Exercise one real model batch |
| `run` | Create and execute a bounded SQLite-backed run |
| `resume` | Continue the stored queue by run ID |
| `sessions` | Inspect recorded worker summaries |
| `export` | Produce a validated `bulk_lanes_v2` packet |
| `schema` | Print a JSON or SQLite contract |
| `serve` | Start the typed MCP server |

Add `--json` for stable machine output.

Each packet embeds the exact closed `TaskSpec` and binds it to `task_revision`. Loading or exporting the packet revalidates every record's `claims` against that task, along with the run ID, input SHA-256 digest, canonical evidence, admitted receipts, and audit counts.

## Normal CLI execution

OpenCode runs through the installed `opencode` command and uses its normal authentication. A temporary task-local config denies model tool permissions, defines no task MCP servers, and disables sharing.

OpenRouter is optional. Costs are taken only from provider data or receipts; a route name containing `free` is only a candidate. Packaged route data is imported disabled as discovery hints. A fresh provider observation is required before any route enters the zero-price ladder.

## Data and provider boundary

`test`, `run`, and `resume` send the selected source slices and task instructions to the chosen model provider. Do not process private, regulated, licensed, or customer data unless that provider and account are approved for it.

The software is MIT-licensed and free to use. Model providers are separate services with their own accounts, terms, rate limits, availability, and pricing. An observed-zero route is evidence about the reported price at one time; it is not a promise that a provider will remain free.

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

The MCP database defaults to `<workspace>/bulk-lanes.db`. All MCP-controlled task, input, database, and packet paths must stay below the workspace root.

## Verify

```bash
pytest -q
```

The wheel contains the SQLite migration, five public JSON Schemas, and the complete companion skill. A source checkout is needed only to develop or run the tests.

## License

MIT. See [LICENSE](LICENSE). Report security issues through the repository's [private vulnerability reporting](https://github.com/NatesVibeCode/bulk-lanes/security/advisories/new), not a public issue.
