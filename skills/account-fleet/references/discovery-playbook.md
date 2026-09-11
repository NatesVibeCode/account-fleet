# Discovery Playbook: Finding 500–1,000 Accounts for Free

This playbook guides an AI agent on how to discover high-intent target accounts from public sources without using paid data vendors.

---

## 1. ATS Search Operators

Applicant Tracking Systems are public goldmines. When a company posts a job opening on Ashby or Greenhouse, they state the exact tech stack they run and the exact architectural challenges they need to solve.

### Ashby (`jobs.ashbyhq.com`)
Dominant among modern AI, DevTools, and high-growth B2B SaaS startups (e.g. OpenAI, Linear, Ramp, Supabase, Perplexity).

```text
site:jobs.ashbyhq.com "[TechStack]" ("[PainPoint1]" OR "[PainPoint2]")
```

*Examples:*
- `site:jobs.ashbyhq.com "Kafka" ("billing" OR "streaming" OR "migration")`
- `site:jobs.ashbyhq.com "ClickHouse" "scaling"`
- `site:jobs.ashbyhq.com "Vector" ("Pinecone" OR "Qdrant" OR "latency")`

### Greenhouse (`boards.greenhouse.io`)
Used by established venture-backed scaleups and mid-market enterprise tech (e.g. Stripe, Figma, Databricks).

```text
site:boards.greenhouse.io "[TechStack]" ("Staff Engineer" OR "Infrastructure")
```

*Examples:*
- `site:boards.greenhouse.io "Postgres" ("50k QPS" OR "connection pool")`
- `site:boards.greenhouse.io "Kubernetes" ("multi-cluster" OR "cost optimization")`

### Lever (`jobs.lever.co`)
Used by global scaleups and remote engineering organizations.

```text
site:jobs.lever.co "[TechStack]" ("Senior Backend" OR "Platform")
```

---

## 2. Compiling the Discovered Raw Accounts into CSV

When the agent uses web search or web scraping tools, format each found job posting into an `accounts.csv` with these exact columns:

```csv
item_id,text,source_uri
stripe.com,"We are looking for a Staff Engineer to join our Platform team. In this role, you will be responsible for leading the migration of our legacy billing service to Apache Kafka and modernizing our distributed streaming architecture. Requirements: 8+ years experience with distributed event streaming...","https://jobs.ashbyhq.com/stripe/staff-infrastructure-engineer"
hyper_ai,"Looking for Senior Backend Engineer hitting latency limits at 50k QPS on Postgres cluster. You will optimize query plans, implement Read Replicas, and introduce caching layers...","https://boards.greenhouse.io/hyperai/backend-scale"
supabase.com,"Building globally distributed Edge Functions replication with low-latency state sync. Ideal candidates have deep expertise with WebAssembly and distributed consensus...","https://jobs.lever.co/supabase/edge-eng"
```

### Ingestion Requirements:
1. `item_id`: Use clean, canonical company domains (e.g. `stripe.com`, `hyper_ai`) so deduplication is automatic.
2. `text`: Preserve the raw paragraph or sentence where the bottleneck is discussed. Do not summarize or alter the text—the model must quote it verbatim during qualification.
3. `source_uri`: Always include the full URL of the post so that sales reps can click through to verify the opening.

---

## 3. Alternative Zero-Cost Discovery Sources

If ATS searches don't yield enough candidates, query these free registries:

### Hacker News "Who is Hiring" (Monthly Dump)
- Query: `site:news.ycombinator.com "Ask HN: Who is hiring?" "[Month Year]"`
- Contains 500–800 tech companies hiring every month. Each comment contains company name, URL, tech stack, and hiring manager email.

### Y Combinator Company Directory
- Endpoint: `https://api.ycombinator.com/v0.1/companies`
- Free public API containing ~5,000 top startups, filterable by batch (`W24`, `S23`), tags (`B2B`, `DevTools`, `Fintech`), and team size.
