---
name: bulk-lanes
description: Orchestrate parallel bulk worker sessions across free OpenCode and OpenRouter model lanes with zero-trust sandboxing and mathematical quote-grounding.
---

# Bulk Lanes Orchestration Skill

Use this skill when you have high-volume untrusted documents (scraped web pages, vulnerability advisories, research papers, tickets, code diffs) and need to triage or extract facts in parallel using free model lanes without risking frontier API costs, tool execution on the host, or hallucinated outputs.

## Core Capabilities

1. **Auto-Discovery of Free Models**: Automatically scans provider schemas (OpenCode CLI, OpenRouter API) for any model with `"free"` in its schema/ID or zero-cost pricing.
2. **Parallel Worker Sessions**: Dispatches work across multiple concurrent worker sessions (`--sessions N`).
3. **Air-Gapped Sandboxing**: In OpenCode, all agent tools and MCPs are denied (`permission: {'*': 'deny'}`), mounts are read-only, and execution is isolated.
4. **Mathematical Quote Grounding**: Every extracted claim must cite an exact verbatim substring from the source document.
5. **Clean Packet Export**: Emits validated JSON packets for safe ingestion into internal databases and private agents.

---

## Quick CLI Reference

```bash
# 1. Automatically refresh and discover all free models across providers
bulk-lanes routes --refresh

# 2. Scaffold a new task template
bulk-lanes init my_task

# 3. Dry-run test 1 batch to verify schema and quote-grounding
bulk-lanes test --task my_task/task.py --input my_task/sample_input.jsonl

# 4. Launch a bulk campaign with 8 parallel worker sessions
bulk-lanes run \
  --task my_task/task.py \
  --input my_task/sample_input.jsonl \
  --sessions 8 \
  --output-dir ./runs/sweep_01 \
  --output clean_packet.json

# 5. Inspect active/completed worker sessions in a run
bulk-lanes sessions ./runs/sweep_01

# 6. Resume an interrupted run without duplicate spend
bulk-lanes resume ./runs/sweep_01 --task my_task/task.py --input my_task/sample_input.jsonl
```

---

## Consuming in Downstream Trusted Code

```python
from bulk_lanes import read_packet

packet = read_packet("clean_packet.json")
for record in packet["records"]:
    # Mathematical grounding verified: quote exists verbatim in source
    internal_db.upsert(
        id=record["item_id"],
        data=record
    )
```
