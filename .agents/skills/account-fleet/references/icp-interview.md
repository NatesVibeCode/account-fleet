# ICP Calibration & Reverse-Engineering Guide

When an operator, founder, or sales leader gives a vague or broad target description (e.g. *"I sell database optimization to SaaS companies"*, *"Find me fintech targets"*), **do not immediately jump into searching**. 

Non-technical sellers think in company size and industry. Account-Fleet requires **technical trigger words** and **verifiable architectural bottlenecks**.

Follow this 3-step calibration protocol to reverse-engineer their exact ICP and calibrated scoring rubric in 60 seconds.

---

## Step 1: The 3-Question Calibration Interview

Ask the operator these exact three questions:

### Question 1: The Breaking Point Catalyst
> *"What is the exact technical breaking point where someone has to buy your tool? (e.g., when their Redis memory bill spikes over $10k/mo, when they hit 50k QPS query timeouts on Postgres, or when they start migrating off legacy billing?)"*

### Question 2: The 2–3 Anchor Customers / Dream Logos
> *"Who are 2 or 3 of your happiest existing customers or dream accounts? (e.g., Stripe, PostHog, Supabase)"*

### Question 3: Non-Negotiable Architecture
> *"What infrastructure or tech stack must they run for your product to work? (e.g., must run Kubernetes, must use Kafka, must be on AWS?)"*

---

## Step 2: Reverse-Engineer Anchor Logos

Use the 2–3 anchor logos provided in Question 2 to extract the hidden technical baseline:
1. Search their engineering blogs or public job posts on Ashby/Greenhouse.
2. Identify their common architecture (e.g. they all use Kafka for streaming and Postgres for billing).
3. Identify the seniority and titles of the engineers they hire to manage this stack.

---

## Step 3: Synthesize the Calibrated Profile & Rubric

Synthesize their answers into an explicit, structured profile:

```json
{
  "icp_profile": {
    "product_category": "Database Performance & Query Optimization",
    "required_stack": ["PostgreSQL", "Kafka", "Kubernetes"],
    "negative_stack_exclusions": ["MongoDB", "DynamoDB", "Firebase"],
    "trigger_pain_phrases": [
      "query latency limits",
      "50k QPS",
      "connection pool exhaustion",
      "read replica lag",
      "legacy billing migration"
    ],
    "target_roles": [
      "Staff Infrastructure Engineer",
      "Senior Database Reliability Engineer",
      "Lead Platform Architect"
    ]
  },
  "calibrated_scoring_rubric": {
    "tier_1_score_85_100": {
      "definition": "Explicit technical bottleneck cited verbatim in an active job post or changelog (e.g. 'hitting latency limits at 50k QPS on Postgres').",
      "evidence_rule": "Must cite verbatim sentence containing stack + active pain."
    },
    "tier_2_score_70_84": {
      "definition": "Confirmed target stack (Postgres + Kafka) and actively hiring Staff/Senior infrastructure roles, but specific bottleneck is implied rather than explicitly named.",
      "evidence_rule": "Must cite verbatim sentence proving stack presence and senior hiring."
    },
    "tier_3_score_50_69": {
      "definition": "Company matches firmographic criteria (B2B SaaS / Tech) but no evidence of high-scale database pain.",
      "evidence_rule": "General company overview quote."
    },
    "unfit_score_0_49": {
      "definition": "Uses competing or incompatible tech stack (e.g. purely managed NoSQL) or outside target domain.",
      "evidence_rule": "None (auto-discarded from final deliverable)."
    }
  }
}
```

---

## Step 4: The 10-Second User Confirmation

Present the synthesized profile to the operator in clean, non-jargon formatting:

> **Target Profile Summary:**
> - **Must-Have Stack**: PostgreSQL, Kafka, Kubernetes
> - **Pain Triggers**: 50k QPS limits, query latency, connection pool exhaustion, legacy billing migration
> - **Negative Exclusions**: Purely NoSQL / Firebase architectures
> - **Target Hiring**: Staff Infrastructure / DBRE roles
>
> **Scoring Scale:**
> - **85–100 (Tier 1)**: Actively citing latency/scaling bottlenecks on Ashby/Greenhouse
> - **70–84 (Tier 2)**: Heavy Postgres stack + hiring Staff Infra
> - **<50**: Discarded
>
> *Does this match your dream accounts, or should I adjust any keywords before running discovery?*

Once approved, proceed immediately to Discovery and Qualification.
