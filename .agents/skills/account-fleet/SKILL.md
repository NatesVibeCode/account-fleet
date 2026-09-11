---
name: account-fleet
description: Turn conversational ICPs into scored, verified target account deliverables using free models, public job posts (Ashby, Greenhouse), and character-exact quote verification. Use when discovering, researching, scoring, and ranking target accounts with zero hallucinations.
---

# Account Fleet: Target Account Research & Scoring Skill

Turn a founder or seller's conversational Ideal Customer Profile (ICP) into a ranked pipeline of qualified target accounts, where every single qualification is backed by a verbatim quote from an active job post or engineering document.

---

## The Outbound Account Execution Pipeline

```
0. Calibration Interview ──> 1. ICP Deconstruction ──> 2. Discovery Queries ──> 3. Task Spec & Rubric
                                                                                      │
                                                                                      ▼
5. Ranked CSV Export     <── 4. Python Substring Gate <── Free Model Fleet
```

---

## Phase 0: Calibrate the ICP & Profile (The 3-Question Protocol)

Founders and operators frequently describe their ICP in broad firmographics (e.g. *"I sell database optimization to SaaS companies"*, *"Find me fintech targets"*). 

**Do not jump directly into web searches or rubric generation with vague descriptions.**

Run the 3-question calibration interview to reverse-engineer their dream accounts into verifiable technical keywords and architecture:

1. **The Breaking Point Catalyst**: *"What is the exact technical breaking point where someone has to buy your product? (e.g., hitting 50k QPS latency limits on Postgres, Redis bills exceeding $10k/mo, or migrating off legacy billing?)"*
2. **The 2–3 Anchor Logos**: *"Who are 2 or 3 of your happiest existing customers or dream accounts? (e.g., Stripe, PostHog, Supabase)"*
3. **Non-Negotiable Architecture**: *"What infrastructure or tech stack must they run for your product to work? (e.g., must run Kubernetes, must use Kafka, must be on AWS?)"*

Synthesize the answers into an explicit ICP profile with positive tech triggers, negative stack exclusions, and present a 10-second operator confirmation before running queries.

See [references/icp-interview.md](references/icp-interview.md) for the complete interview playbook and profile synthesis templates.

---

## Phase 1: Deconstruct the ICP into 3 Technical Signals

Never evaluate an account on vague firmographics alone. When a user describes their product or target customer, deconstruct it into three mandatory technical signals:

1. **Target Architecture / Tech Stack**:
   - What infrastructure or frameworks must the prospect run? (e.g. `Kafka`, `ClickHouse`, `Postgres`, `Kubernetes`, `Snowflake`, `PyTorch`).
2. **Active Bottleneck / Technical Pain**:
   - What exact problem proves they have urgent need?
   - *Migration*: Moving off legacy v1 systems or migrating between databases.
   - *Scale / Latency*: Hitting QPS ceilings, memory limits, or query timeouts.
   - *Cost / Overhead*: Spiking cloud bills, cluster maintenance overhead.
   - *Security / Compliance*: SOC2, HIPAA, data residency, GDPR requirements.
3. **Hiring / Budget Urgency**:
   - What roles indicate they are spending budget to solve this *right now*? (e.g. `Staff Infrastructure Engineer`, `Data Platform Lead`, `Senior DevOps`).

See [references/icp-decomposition.md](references/icp-decomposition.md) for full breakdown templates.

---

## Phase 2: Formulate Discovery Queries

The highest-intent public signal comes from Applicant Tracking Systems (ATS) where companies state their actual architecture and pain points in unedited job posts.

Search these domains directly:

| Source | Target Domain | Example Query |
|---|---|---|
| **Ashby** (Modern Tech/AI) | `jobs.ashbyhq.com` | `site:jobs.ashbyhq.com "Kafka" ("migration" OR "billing")` |
| **Greenhouse** (High-Growth) | `boards.greenhouse.io` | `site:boards.greenhouse.io "Postgres" ("latency" OR "50k QPS")` |
| **Lever** (Tech / Scaleups) | `jobs.lever.co` | `site:jobs.lever.co "ClickHouse" "scaling"` |
| **Engineering Docs** | `docs.*` / `blog.*` | `site:company.com/blog "architecture" "migration"` |

Compile discovered items into `accounts.csv` with columns:
- `item_id`: Company domain or identifier (e.g. `stripe.com`)
- `text`: Raw unedited job posting description or engineering blog excerpt
- `source_uri`: Direct URL of the live posting (e.g. `https://jobs.ashbyhq.com/stripe/...`)

See [references/discovery-playbook.md](references/discovery-playbook.md) for discovery scripts and search operators.

---

## Phase 3: Build the Task Spec & 0–100 Scoring Rubric

Register a typed task with an explicit 0–100 rubric. Every high score must cite an exact quote.

### Standard Claims Schema:
```json
{
  "type": "object",
  "properties": {
    "score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "description": "ICP qualification fit score from 0 to 100"
    },
    "identified_gap": {
      "type": "string",
      "description": "Concise summary of the verified technical bottleneck or initiative"
    },
    "fit_tier": {
      "enum": ["tier_1", "tier_2", "tier_3", "unfit"],
      "description": "tier_1 (85-100), tier_2 (70-84), tier_3 (50-69), unfit (<50)"
    }
  },
  "required": ["score", "identified_gap", "fit_tier"],
  "additionalProperties": false
}
```

### Standard Rubric:
- **Tier 1 (85–100)**: Active, explicit initiative cited directly in source text (e.g. "migrating legacy billing to Kafka"). Must cite exact bottleneck quote.
- **Tier 2 (70–84)**: Relevant tech stack present and senior hiring underway, but specific migration is implied rather than explicitly stated.
- **Tier 3 (50–69)**: Right industry/firmographic fit, but tech stack is standard or unverified.
- **Unfit (<50)**: Uses incompatible architecture or outside the target domain.

See [references/scoring-rubric-guide.md](references/scoring-rubric-guide.md) for task templates and instructions.

---

## Phase 4: Execute with Free Models & Exact Substring Verification

Run the batch campaign through free model routes (OpenRouter / OpenCode / Local Ollama):

```bash
# Initialize task
account-fleet init target-research --preset score

# Run campaign across accounts.csv
account-fleet run target-research \
  --input accounts.csv \
  --id-column item_id \
  --text-column text \
  --run-id campaign-01 \
  --free-only \
  --sessions 4
```

### The Invariant: Substring Verification Gate
Every model claim must include an exact quote. Under the hood:
```python
assert quote in raw_text
```
- If the model hallucinated, paraphrased, or changed one character, the check fails and the attempt rotates.
- If verified, the exact character range `[start, end]` and source URI are committed to SQLite.

---

## Phase 5: Export & Present the Ranked Deliverable

Export the top-scoring accounts sorted descending, ready for sales reps or CRM import:

```bash
account-fleet export campaign-01 \
  --format csv \
  --sort-by score \
  --desc \
  --top 25 \
  --rank \
  --output ranked_target_accounts.csv
```

### Format of the Final Deliverable:
| Rank | Account | Score | Identified Gap | Verbatim Quote Proof | Source URL |
|---|---|---|---|---|---|
| #1 | `stripe.com` | 98 | Legacy billing Kafka migration | “leading the migration of our legacy billing service to Apache Kafka” | `jobs.ashbyhq.com/stripe/...` |
| #2 | `hyper_ai` | 94 | Postgres QPS latency limits | “hitting latency limits at 50k QPS on Postgres cluster” | `boards.greenhouse.io/...` |

See [references/mcp-recipes.md](references/mcp-recipes.md) for prompt recipes in Claude Desktop, Codex, and Cursor.
