# bulk-lanes

[![CI](https://github.com/bulk-lanes/bulk-lanes/actions/workflows/ci.yml/badge.svg)](https://github.com/bulk-lanes/bulk-lanes/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Universal, air-gapped bulk model lane orchestrator (OpenCode + OpenRouter) with mathematical quote-grounding and automatic free-tier schema discovery.**

`bulk-lanes` solves a common problem in agentic and LLM architectures:
> **"You have thousands of untrusted documents (scraped web pages, vulnerability notices, papers, customer logs, code diffs). You want to process them in parallel without burning expensive frontier model credits or granting untrusted public text tool access near your private host, and you want mathematical proof that facts aren't hallucinated before ingesting them into your trusted systems."**

---

## Key Features

- **Dynamic Free-in-Schema Auto-Discovery**: Automatically inspects provider model schemas (OpenCode CLI, OpenRouter API) and admits any model where `"free"` appears in its schema/ID or where pricing is zero.
- **Universal Harness Compatibility**:
  - **Human CLI**: Polished terminal UI with live progress indicators and ANSI tables.
  - **Machine-Readable JSON Mode (`--json`)**: Pure JSON output on stdout for AI coding harnesses (Claude Code, Codex, Aider, script pipelines).
  - **Model Context Protocol (MCP) Server (`bulk-lanes serve`)**: Drop-in native tools for Cursor, Claude Desktop, Windsurf, OpenCode, and Antigravity.
  - **Universal Agent Skill (`SKILL.md`)**: Conforms to the standard Agent Skill spec in `.agents/skills/bulk-lanes/SKILL.md`.
  - **Python SDK (`import bulk_lanes`)**: Native Python library for downstream applications.
- **Parallel Multi-Session Orchestration**: Dispatches work across $N$ dedicated concurrent worker sessions (`--sessions N`).
- **Mathematical Quote Grounding**: Every extracted claim must cite an exact verbatim substring ($\ge 15$ chars) from the source document. Hallucinations or prompt injections that fabricate quotes are rejected.
- **Zero-Trust Sandboxing**: OpenCode tasks execute with all agent tools denied (`permission: {'*': 'deny'}`), read-only task mounts, and isolated tmpfs environments.
- **Resumable State & Budget Reservation**: Atomic manifests (`manifest.json`) pre-allocate attempt budgets so interrupted runs never loop or double-spend on restart.
- **Air-Gapped Clean Packets**: Exports typed, validated JSON packets with complete audit receipts (tokens, cost status, verification proofs) for safe ingestion into your private databases or internal agents.

---

## Architecture Overview

```
                          [ UNTRUSTED FLEET ZONE ]
                (Public Data & Auto-Discovered Free Models)
┌──────────────────────┐
│ Raw Inputs (.jsonl)  │
└──────────┬───────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ bulk-lanes Engine                                      │
│  ├── Document Slicer     (Offset & slice tracking)     │
│  ├── Batch Packer        (Multi-item prompt packing)   │
│  └── Multi-Session Pool  (Parallel concurrent workers) │
└──────────┬─────────────────────────────────────────────┘
           │
           ├───► [Lane 1: OpenCode Container Pool]  (Nemotron, Mimo, Big-Pickle, Muse Spark)
           └───► [Lane 2: OpenRouter Pool]          (Free tier & budget routes - throttled)
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ Grounded Verification Gate                             │
│  ├── Schema Validation (Type / structure checks)       │
│  ├── Verbatim Quote Matcher (Exact substring in slice) │
│  └── Circuit Breaker (Disables broken/paid routes)     │
└──────────┬─────────────────────────────────────────────┘
           │
═══════════╪══════════════════════════════════════════════ [ AIR GAP BOUNDARY ]
           ▼
┌──────────────────────┐
│ Clean Packet JSON    │ (Sanitized, Verified Artifact)
└──────────┬───────────┘
           │
           ▼               [ TRUSTED CORE ZONE ]
┌────────────────────────────────────────────────────────┐
│ Your Private Systems                                   │
│ (Internal DB, Private Agent, Vector RAG, CRM, Analytics│
└────────────────────────────────────────────────────────┘
```

---

## Installation

```bash
git clone https://github.com/your-org/bulk-lanes.git
cd bulk-lanes
pip install -e .
```

---

## Universal Harness Usage

### 1. Interactive CLI (Human / Terminal)
```bash
# Discover all free models across providers
bulk-lanes routes --refresh

# Scaffold a new task template
bulk-lanes init my_task
cd my_task

# Dry run 1 batch to test schema and quote-grounding
bulk-lanes test --task task.py --input sample_input.jsonl

# Run parallel worker sessions in bulk
bulk-lanes run \
  --task task.py \
  --input sample_input.jsonl \
  --sessions 8 \
  --output-dir ./runs/sweep_01 \
  --output clean_packet.json

# Inspect worker sessions
bulk-lanes sessions ./runs/sweep_01

# Resume if interrupted
bulk-lanes resume ./runs/sweep_01 --task task.py --input sample_input.jsonl
```

### 2. Machine-Readable JSON Mode (For Agent Harnesses & Scripts)
Pass `--json` to any command to receive raw JSON on stdout without ANSI formatting:
```bash
bulk-lanes routes --json
bulk-lanes test --task task.py --input sample.jsonl --json
bulk-lanes run --task task.py --input data.jsonl --sessions 4 --json
```

### 3. Model Context Protocol (MCP) Server
Launch `bulk-lanes serve` to expose standard JSON-RPC tools (`bulk_lanes_routes`, `bulk_lanes_test`, `bulk_lanes_run`, `bulk_lanes_export`) over stdio.

Add to your `cursor.json`, `claude_desktop_config.json`, or MCP configuration:
```json
{
  "mcpServers": {
    "bulk-lanes": {
      "command": "bulk-lanes",
      "args": ["serve"]
    }
  }
}
```

### 4. Universal Agent Skill
The repository includes a ready-to-use Agent Skill specification:
- `.agents/skills/bulk-lanes/SKILL.md` (universal agent standard)
- `skills/bulk-lanes/SKILL.md`

Any modern agent harness will automatically discover this skill when the repository is cloned into a project or workspace.

### 5. Python SDK (Downstream Ingestion)
```python
from bulk_lanes import read_packet

# Read verified, air-gapped packet
packet = read_packet("clean_packet.json")

print(f"Verified records: {packet['total_verified_records']}")
print(f"Total tokens used: {packet['audit']['total_tokens_consumed']}")
print(f"Reported cost: ${packet['audit']['total_cost_reported']}")

for record in packet["records"]:
    # Safe to ingest: verified by schema and mathematically grounded by exact source quotes
    internal_db.upsert(
        id=record["item_id"],
        facts=record,
        citations=record["quotes"]
    )
```

---

## Defining Custom Tasks

Tasks are defined as clean Python classes:

```python
from bulk_lanes import Task

class MyExtractionTask(Task):
    name = "saas_triage"
    batch_size = 6                  # Pack 6 items per model call
    min_quote_chars = 15            # Minimum character length for valid quote
    quote_field = "evidence_quotes" # Key model must populate

    system_prompt = (
        "You are an air-gapped triage worker. "
        "Extract structured capabilities from the provided text. "
        "Every claim MUST be backed by a verbatim quote from the text."
    )

    user_prompt_template = """
Extract information for each item:
{
  "items": [
    {
      "item_id": "<id>",
      "summary": "<one sentence>",
      "has_api": true | false,
      "evidence_quotes": ["<verbatim quote from text>"]
    }
  ]
}

Items:
{items_json}
"""
```

---

## Running Tests

```bash
pytest -v
```

---

## License

MIT © [bulk-lanes contributors](LICENSE)
