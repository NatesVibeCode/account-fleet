# free-fleet

[![CI](https://github.com/NatesVibeCode/free-fleet/actions/workflows/ci.yml/badge.svg)](https://github.com/NatesVibeCode/free-fleet/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Coordinated free LLM worker fleet for high-throughput, evidence-grounded batch processing across free, paid, and local models.

Run structured classification, entity extraction, summarization, and triage across thousands of records with SQLite checkpointing, character-exact quote grounding, and deterministic verification against source text.

---

## 30-Second Example: CSV In, Verified CSV Out

Suppose you have customer feedback in `feedback.csv`:

```csv
id,comment
fb_1,"The onboarding was smooth, but the checkout button gave a 500 error."
fb_2,"Fast shipping and the packaging was completely recyclable."
fb_3,"Customer support never answered my email about the missing invoice."
```

### 1. Initialize a task and run

```bash
# Initialize a typed triage task preset (priority, reason, grounded quotes)
free-fleet init customer-triage --preset triage

# Process the CSV using intelligent model routing
free-fleet run customer-triage --input feedback.csv --id-column id --text-column comment --run-id triage-01
```

### 2. Export verified results

```bash
free-fleet export triage-01 --format csv --output results.csv
```

### 3. Output (`results.csv`)

```csv
item_id,priority,reason,primary_quote_text,quote_count,source_uri,source_digest
fb_1,high,"Checkout button failure blocks user purchase","checkout button gave a 500 error",1,"",a8f110...
fb_2,low,"Positive customer feedback on eco packaging","packaging was completely recyclable",1,"",4c2b81...
fb_3,medium,"Support request regarding invoice remains unanswered","never answered my email about the missing invoice",1,"",9e11fd...
```

Outputs contain structured claims paired with verbatim quotes deterministically verified against the raw source text.

---

## Why You Can Trust the Output

1. **Deterministic Quote Verification**: Cited quotes are verified against the raw source text at character-level precision and resolved to canonical `[start, end]` character offsets. If a model fabricates or alters a cited quote, validation fails and triggers immediate route rotation. *(Note: This deterministically proves that all cited quotes are verbatim source substrings; semantic entailment of claims from quotes is model-generated).*
2. **Closed JSON Schemas**: Outputs adhere strictly to closed JSON Schemas defined in the `TaskSpec`. Models cannot add unexpected fields, produce unformatted markdown, or drift out of schema.
3. **Intelligent Route Scoring**: Instead of blind round-robin rotation, `free-fleet` uses Bayesian-smoothed historical scoring based on verification rates, malformed JSON rates, grounding accuracy, and latency. Models that consistently produce verified results are prioritized.
4. **Non-Destructive Rate-Limit Handling**: When an API returns a `429 Too Many Requests` or `5xx Server Error`, `free-fleet` puts the route in cooldown and retries the batch immediately on an alternative route without burning the batch attempt limit.
5. **Zero-Price Circuit Breaker & Spend Ceilings**: For zero-price campaigns, route pricing is observed directly from provider receipts; if an unexpected charge occurs, the circuit breaker trips immediately. For paid campaigns, catalog rates and `--max-request-cost` spend ceilings enforce budget boundaries.

---

## Quickstart

### Installation

```bash
git clone https://github.com/NatesVibeCode/free-fleet.git
python3 -m pip install ./free-fleet
```

### Initialize Workspace

```bash
mkdir my-workspace && cd my-workspace
free-fleet setup --workspace-root "$PWD" --refresh-routes
```

### Presets

Create typed tasks instantly with built-in presets:

```bash
free-fleet init classify-demo --preset classify
free-fleet init extract-demo --preset extract
free-fleet init triage-demo --preset triage
free-fleet init summarize-demo --preset summarize
```

Validate and test before launching large runs:

```bash
# Validate task spec and input without making any API calls
free-fleet validate classify-demo --input input.jsonl

# Test a single real batch
free-fleet test classify-demo --input input.jsonl
```

---

## Core Capabilities

### 1. CSV In / CSV Out
Directly process tabular data without custom transformation scripts:

```bash
# Run on CSV specifying ID and text columns
free-fleet run my-task --input records.csv --id-column id --text-column body

# Export directly to CSV
free-fleet export <run_id> --format csv --output results.csv
```

### 2. Live Run Monitoring
Track queue progress, worker concurrency, and route-level metrics in real time:

```bash
free-fleet status <run_id> --watch
```

Output:
```
============================================================
Run: triage-01  |  Task: customer-triage  |  Status: RUNNING
Progress: [=========================>              ] 62.5% (650/1040)
============================================================
Batches:
  Pending:    15
  Leased:      4
  Done:       65
  Failed:      0

Route Performance:
  openrouter:qwen/qwen-2.5-72b-instruct:free
    Attempts: 45 | Verified: 44 | Rate limits: 1 | Latency: 1.2s
  openrouter:meta-llama/llama-3.3-70b-instruct:free
    Attempts: 24 | Verified: 23 | Rate limits: 0 | Latency: 1.8s
```

### 3. Continuous Route Evaluation
Benchmark available routes against test datasets to determine which models excel at your specific task:

```bash
free-fleet eval customer-triage --input test-samples.csv --id-column id --text-column comment
```

Output:
```
========================================================================================
Route Evaluation Benchmark
Task: customer-triage  |  Samples: 20
========================================================================================
Route                                      Success   Grounding   Score    Avg Latency
----------------------------------------------------------------------------------------
openrouter:qwen/qwen-2.5-72b-instruct:free   100.0%     100.0%    0.982          1.15s
openrouter:meta-llama/llama-3.3-70b-free      95.0%      90.0%    0.871          1.82s
opencode:llama3                               80.0%      85.0%    0.742          2.40s
```
Evaluation benchmarks automatically update route selection priors for subsequent runs.

### 4. Local Models & Generic OpenAI-Compatible Providers
Run bulk workloads completely locally with **Ollama**, **LM Studio**, **vLLM**, or fast cloud inference providers like **Groq** and **Cerebras**:

```bash
# Register your local or custom route in the catalog
free-fleet routes add ollama/llama3.2:latest --provider ollama --free

# Or configure environment variables
export OPENAI_COMPATIBLE_BASE_URL="http://localhost:11434/v1"
export OPENAI_COMPATIBLE_API_KEY="ollama"
export OPENAI_COMPATIBLE_MODEL="llama3.2:latest"

# Run with local provider selection
free-fleet run my-task --input data.csv --id-column id --text-column text --provider ollama
```

Endpoints on `localhost` or `127.0.0.1` are automatically marked free (`cost = 0.0`). For third-party cloud OpenAI-compatible endpoints, specify costs explicitly (`--input-cost` / `--output-cost`) or leave them as unknown-cost to prevent accidental misclassification.

### 5. Explicit Data & Privacy Policy
Enforce zero data retention (ZDR), prohibit provider data collection, limit request spend, and control upstream routing on a per-run basis:

```bash
free-fleet run my-task \
  --input sensitive-data.jsonl \
  --zdr \
  --no-data-collection \
  --provider openrouter \
  --exclude-provider opencode \
  --openrouter-providers Anthropic,Together \
  --max-request-cost 0.05
```

You can pass `--openrouter-providers` as a comma-separated list or as repeatable `--openrouter-provider` flags.

---

## SQLite Control Plane

`free-fleet` uses SQLite in WAL mode with `BEGIN IMMEDIATE` atomic leases. If a worker crashes or a laptop closes, the run can be resumed seamlessly:

```bash
free-fleet resume <run_id>
```

- **Resumable**: Batches are committed upon verification. Completed work is never repeated.
- **Fault-Tolerant**: Stale worker leases are automatically recovered after timeout.
- **Concurrent**: Multiple worker processes can safely lease batches simultaneously without collisions.
- **Auditable**: Every attempt, model receipt, cost observation, and verification failure is recorded immutably in `inference_attempts`.

---

## Commands

| Command | Purpose |
|---|---|
| `setup` | Bootstrap a portable workspace with bundled skills and SQLite database |
| `doctor` | Check SQLite, installed CLIs, provider authentication, and available routes |
| `routes` | List or refresh discovered model routes (`--refresh`) |
| `routes add` | Register an explicit custom or local model route (`--free`, `--input-cost`) |
| `tasks` | List registered task definitions |
| `init` | Create a typed task from a preset (`classify`, `extract`, `triage`, `summarize`) |
| `validate` | Check task schema and input formatting without inference |
| `test` | Run one real batch through candidate models |
| `run` | Create and execute a SQLite-backed resumable run |
| `resume` | Resume an unfinished run from its SQLite queue |
| `status` | Show real-time progress, attempts, and route stats (`--watch`) |
| `eval` | Benchmark routes on sample inputs and update route ranking priors |
| `sessions` | Inspect recorded worker sessions and audit logs |
| `export` | Export a validated packet or CSV (`--format csv\|json`) |
| `schema` | Print admitted JSON Schemas or database contracts |
| `serve` | Run the Model Context Protocol (MCP) server over stdio |

Pass `--json` to any command for machine-readable JSON output.

---

## MCP Server

`free-fleet` includes a Model Context Protocol (MCP) server for integration into Cursor, Claude Desktop, Antigravity, and other agent environments:

```json
{
  "mcpServers": {
    "free-fleet": {
      "command": "free-fleet",
      "args": ["serve", "--workspace-root", "/absolute/path/to/workspace"]
    }
  }
}
```

---

## Verification & Testing

Run the test suite:

```bash
pytest -q
```

All core components (Bayesian route scoring, SQLite control plane, rate limit cooldowns, OpenAI-compatible provider, CSV IO, real-time status monitoring, and route evals) are covered by automated unit and integration tests.

---

## License

MIT. See [LICENSE](LICENSE).
