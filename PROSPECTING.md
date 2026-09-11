# Compounding B2B Prospecting with free-fleet

> **How to turn 50,000 raw domain names into 150 hyper-targeted, zero-hallucination outbound accounts for $0.00 in API spend.**

---

## The LinkedIn Post

*(Copy, paste, and attach the diagram generated from `prospecting-funnel.mmd`)*

```markdown
I don't think people realize the superpower they were just handed for free.

Most B2B outbound teams spend $500–$2,000/month on tools like Clay, Apollo, and OpenAI API credits just to scrape websites and send hallucinated "I noticed your company does X" cold emails.

Here is the exact compounding pipeline you can run right now on your laptop using free-fleet for $0.00:

1. Top of Funnel (50,000 Accounts)
Dump 50,000 raw domains into a free-fleet triage lane. Scrape homepages and run them through free 70B models (Llama 3.3, Qwen 2.5) with strict JSON schemas. Extract B2B/B2C, pricing model, and ICP fit.
→ 40,000 unqualified accounts dropped.
→ 10,000 qualified survivors pass to Layer 2.

2. Tech Stack & Architecture Pain (10,000 Accounts)
Scrape developer documentation, changelogs, and integration pages. free-fleet extracts competitor tech in use, legacy APIs, and migration hurdles.
Every single claim is character-grounded: if the model doesn't cite an exact verbatim substring from the docs, the check fails and routes failover.
→ 7,500 stable accounts dropped.
→ 2,500 tech-vulnerable accounts pass to Layer 3.

3. Hiring Velocity & Active Budget (2,500 Accounts)
Scrape open roles from Greenhouse/Lever. free-fleet extracts open positions matching your trigger keywords (e.g. "Staff Data Engineer", "Migration lead") and extracts verbatim quotes from the job description proving active budget allocation.
→ 2,000 passive accounts dropped.
→ 500 high-intent accounts pass to Layer 4.

4. Founder Voice & Executive Signals (500 Accounts)
Scrape recent founder posts, podcast transcripts, and executive interviews. free-fleet extracts direct quotes highlighting current quarterly priorities or strategic bottlenecks.
→ 350 deprioritized.
→ 150 Tier-1 "Sniper" accounts survive.

5. The Cold Email (Zero Hallucinations)
You synthesize the 4 layers into a cold email that looks like you spent 4 hours researching them:

"Saw your CEO mentioned on the Latent Space podcast that 'scaling vector search across multi-tenant clusters is our #1 bottleneck this quarter.'

Noticed your careers page is hiring a Staff Data Engineer specifically to 'lead the migration off legacy Pinecone', while your docs note you're still on API v1.

We built a drop-in adapter that eliminates that migration hurdle..."

Every single quote is verified at character-level precision.
Zero hallucinations.
Zero Clay credit burn.
$0.00 total API cost.

All orchestrated with SQLite checkpointing and Bayesian-ranked model routing.

Open source on GitHub: https://github.com/NatesVibeCode/free-fleet
```

---

## The Step-by-Step CLI Playbook

Here is how you execute this compounding funnel in practice:

### Layer 1: Firmographic & Business Model Triage

```bash
# 1. Initialize triage task
free-fleet init firmographic-triage --preset triage

# 2. Run fleet on raw accounts CSV
free-fleet run firmographic-triage \
  --input raw_accounts.csv \
  --id-column domain \
  --text-column homepage_text \
  --run-id layer-1 \
  --sessions 8 \
  --free-only

# 3. Export verified records
free-fleet export layer-1 --format csv --output layer1_verified.csv
```

Filter `layer1_verified.csv` for `priority == 'high'` or fit score threshold.

---

### Layer 2: Tech Stack & Architecture Vulnerability

```bash
# 1. Create tech extraction task
free-fleet init tech-vulnerability --preset extract

# 2. Run fleet on docs/integration text
free-fleet run tech-vulnerability \
  --input layer1_survivors_docs.csv \
  --id-column domain \
  --text-column docs_text \
  --run-id layer-2 \
  --sessions 8 \
  --free-only

# 3. Export verified records
free-fleet export layer-2 --format csv --output layer2_verified.csv
```

---

### Layer 3: Job Openings & Hiring Intent Signals

```bash
# 1. Create hiring signal extraction task
free-fleet init hiring-signals --preset extract

# 2. Run fleet on scraped job descriptions
free-fleet run hiring-signals \
  --input layer2_survivors_jobs.csv \
  --id-column domain \
  --text-column job_description \
  --run-id layer-3 \
  --sessions 8 \
  --free-only

# 3. Export verified records
free-fleet export layer-3 --format csv --output layer3_verified.csv
```

---

### Layer 4: Founder Voice & Executive Signals

```bash
# 1. Create executive signal task
free-fleet init exec-signals --preset summarize

# 2. Run fleet on interviews and social transcripts
free-fleet run exec-signals \
  --input layer3_survivors_interviews.csv \
  --id-column domain \
  --text-column interview_transcript \
  --run-id layer-4 \
  --sessions 8 \
  --free-only

# 3. Export verified records
free-fleet export layer-4 --format csv --output layer4_sniper_accounts.csv
```

---

### Layer 5: Synthesize and Outbound

Each row in `layer4_sniper_accounts.csv` contains:
- `primary_quote_text` (CEO quote from interview)
- `claims` (specific strategic bet)
- Linked with Layer 2 and Layer 3 quotes and claims.

Because `free-fleet` guarantees that all quotes exist verbatim in source text via character offset proofs, **your sales reps or automated outreach agents can never hallucinate a customer fact.**
