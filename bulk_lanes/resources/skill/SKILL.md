---
name: bulk-lanes
description: Run repeatable bulk classification, extraction, summarization, and triage over source text with closed fields, exact quote offsets, SQLite checkpoints, bounded attempts, and explicit route-price evidence. Use when every returned claim must be typed and traceable to its source; do not use for open-ended agent delegation.
---

# Bulk Lanes

Deliver a validated `bulk_lanes_v2` packet from typed input while SQLite retains the exact task revision, queue state, attempts, verified results, routes, and receipts.

Start with `command -v bulk-lanes`. On a fresh system, run `bulk-lanes setup --workspace-root "$PWD" --refresh-routes --json`, then execute its typed `next_commands` in order.

## Choose the operation

- To define or change extraction fields, read [references/task-contracts.md](references/task-contracts.md).
- To test, run, resume, monitor status, evaluate routes, export, inspect routes, or configure MCP, read [references/operations.md](references/operations.md).
- For tabular data, use CSV input (`--id-column`, `--text-column`) and export (`--format csv`).
- For status queries, run `bulk-lanes status <run_id>` or use MCP `bulk_lanes_status`; do not resume or start runs for monitoring.
- To benchmark routes against task samples before large runs, use `bulk-lanes eval` or MCP `bulk_lanes_eval`.

## Invariants

1. SQLite is the system of record. JSON, JSONL, and CSV are typed import/export formats.
2. Use registered task names. Import declarative `TaskSpec` JSON only when a file is explicitly supplied; never load Python task plugins.
3. Require `claims_schema.type: object` and `additionalProperties: false`.
4. Treat model output as untrusted until candidate-output, claims-schema, deterministic quote normalization, and canonical `ModelOutput` checks pass.
5. The model may omit quote offsets only when its exact quote text occurs once in the named slice. Repeated text requires explicit offsets.
6. A route name containing `free` proves nothing. Zero-price runs use only `price_observed_zero` routes. Local endpoints (`localhost`/`127.0.0.1`) default to zero cost; external OpenAI-compatible endpoints require explicit pricing or are treated as unknown cost.
7. OpenCode runs through the normally installed CLI. Its task-local configuration denies model tool permissions, defines no task MCP servers, and disables sharing. Keep that single transport boundary.
8. For MCP, set one absolute `--workspace-root`. Keep its SQLite database and every file path below that root.
9. Read exported packets through `read_packet`; it checks the embedded TaskSpec digest and revalidates every record's claims. Do not bypass `bulk_lanes_v2` validation.
10. Model selection uses Bayesian-smoothed historical scoring. Every intermediate attempt failure, schema error, ungrounded quote, rate limit, and latency is recorded immutably in `inference_attempts`.

## Workflow

1. Run `bulk-lanes doctor --json`, then inspect `bulk-lanes routes --json`. Refresh only when requested or needed; refresh contacts providers and appends route evidence.
2. For local or private models (Ollama, vLLM, LM Studio), add the route with `bulk-lanes routes add <id> --provider <provider> --free`.
3. Create or select a task, then run `bulk-lanes validate TASK --input FILE --json` before inference.
4. Run one batch with `bulk-lanes test TASK --input FILE --json`.
5. Optionally benchmark candidate routes with `bulk-lanes eval TASK --input FILE --json` to update intelligent ranking priors.
6. Start the bounded campaign with an explicit run ID, session count, attempt ceiling, and optional policy (`--zdr`, `--provider`, `--exclude-provider`).
7. Monitor progress in real time with `bulk-lanes status RUN_ID --watch`.
8. On interruption, inspect the stored run and call `bulk-lanes resume RUN_ID`; do not reconstruct or restart its batches from input files.
9. Export and validate the packet with `bulk-lanes export RUN_ID [--format csv|json]`. Report database path, run ID, packet path, verified/failed counts, attempts, and route/cost evidence.

Never call a worker session an independent coding-agent session. `--sessions` is bounded batch concurrency inside one bulk-lanes campaign.
