# bulk-lanes

**Air-gapped bulk model lane orchestrator (OpenCode + OpenRouter) with mathematical quote-grounding.**

`bulk-lanes` is an open-source framework designed for **Zero-Trust Compute for Trusted Systems**.

When you have thousands of raw documents (scraped web pages, CVE reports, papers, tickets) and want to run bulk extraction without spending hundreds of dollars on frontier APIs or exposing your private host to untrusted web content and hallucinated outputs:
1. **Compute is Untrusted**: Tasks are packed into batches and dispatched over free/cheap model lanes (OpenCode container models and OpenRouter `:free` routes).
2. **Execution is Sandboxed**: Tasks run with all agent tools denied (`permission: {'*': 'deny'}`), read-only task mounts, and isolated environments.
3. **Outputs are Mathematically Grounded**: Every claim must cite an exact verbatim substring from the input document. Hallucinations or prompt injections that fabricate quotes are rejected.
4. **Air-Gapped Clean Packets**: Output is exported as a validated, typed JSON artifact with audit receipts that your trusted systems can safely ingest.

---

## Quickstart

### 1. Check Active Model Lanes
View active zero-price routes and health status:
```bash
bulk-lanes routes
```

### 2. Scaffold a New Task
Create a new task template and sample data:
```bash
bulk-lanes init saas_triage
cd saas_triage
```

### 3. Dry-Run a Single Batch
Verify your prompt, schema, and grounding checks with a single test batch:
```bash
bulk-lanes test --task task.py --input sample_input.jsonl
```

### 4. Run Bulk Campaign
Launch parallel worker lanes across thousands of items:
```bash
bulk-lanes run \
  --task task.py \
  --input sample_input.jsonl \
  --concurrency 4 \
  --output-dir ./runs/batch_01 \
  --output clean_packet.json
```

### 5. Resume Interrupted Runs
If a run stops or hits an API rate limit, resume right where it left off without duplicate spend:
```bash
bulk-lanes resume ./runs/batch_01 --task task.py --input sample_input.jsonl
```

---

## Downstream Ingestion (Into Your Trusted Stuff)

In your private agent, internal database, or RAG application:
```python
from bulk_lanes import read_packet

# Read verified, air-gapped packet
packet = read_packet("clean_packet.json")

print(f"Verified records: {packet['total_verified_records']}")
print(f"Total tokens used: {packet['audit']['total_tokens_consumed']}")
print(f"Reported cost: ${packet['audit']['total_cost_reported']}")

for record in packet["records"]:
    # Ingest safely into internal DB / vector store
    my_trusted_db.upsert(
        id=record["item_id"],
        summary=record["summary"],
        category=record["category"],
        citations=record["quotes"]
    )
```

---

## Task Authoring

Tasks are defined as lightweight Python classes:

```python
from bulk_lanes import Task

class PricingAuditTask(Task):
    name = "pricing_audit"
    batch_size = 6                  # Packs 6 items per model call
    min_quote_chars = 15            # Minimum character length for valid quote
    quote_field = "evidence_quotes" # Key model must populate

    system_prompt = (
        "Extract pricing models from the provided web landing pages. "
        "Every claim MUST be backed by a verbatim quote from the text."
    )

    user_prompt_template = """
Extract pricing info for each item:
{
  "items": [
    {
      "item_id": "<id>",
      "has_free_tier": true | false,
      "starting_price": "<string or null>",
      "evidence_quotes": ["<verbatim quote from text>"]
    }
  ]
}

Items:
{items_json}
"""
```

---

## Architecture & Security

- **Container Isolation**: When Docker or OrbStack is available, tasks execute in read-only containers (`--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--tmpfs`, no host filesystem mount).
- **Subprocess Fallback**: When Docker is offline, execution runs in an isolated ephemeral directory with sanitized environment variables and custom XDG configuration paths.
- **Circuit Breaker**: Any route reporting unexpected non-zero billing on a zero-price route is automatically disabled.
