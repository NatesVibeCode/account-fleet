"""Generate 4-slide LinkedIn carousel — Automated Research Suite.

Universal typography, styling, and sizing system across all 4 slides:
- Slide 1: Accounts scored, sorted, and backed by proof (every row carries its source quote)
- Slide 2: The 4-Layer Filter — how 1,000 accounts become 25 with evidence (account research example)
- Slide 3: Quote must match the source exactly (QuoteRef verification you can run yourself)
- Slide 4: Run it where you already chat — Claude, Codex, Cursor, Grokbot, Antigravity
"""

from pathlib import Path
import fitz
import weasyprint

def generate_carousel():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: 1080px 1350px;
    margin: 0;
  }
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  body {
    background: #faf9f5;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #141413;
    -webkit-font-smoothing: antialiased;
  }

  .slide {
    width: 1080px;
    height: 1350px;
    page-break-after: always;
    break-after: page;
    position: relative;
    padding: 52px 60px 32px 60px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    gap: 28px;
    background: #faf9f5;
    background-image: radial-gradient(circle at 1px 1px, rgba(20,20,19,0.075) 1.2px, transparent 0), repeating-linear-gradient(90deg, transparent 0 48px, rgba(20,20,19,0.015) 48px 49px), radial-gradient(ellipse at 50% 0%, rgba(232,228,215,0.9) 0%, transparent 58%);
    background-size: 20px 20px, 49px 49px, 100% 440px;
    background-repeat: repeat, repeat, no-repeat;
    box-shadow: inset 0 0 0 1px #ece9e0, inset 0 0 80px rgba(232,228,215,0.5), inset 0 1px 0 rgba(255,255,255,0.9);
    overflow: hidden;
  }
  .slide::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image: repeating-linear-gradient(0deg, transparent 0 26px, rgba(20,20,19,0.032) 26px 27px);
    pointer-events: none;
  }
  .slide::after { display: none; }

  .slide-header {
    display: flex;
    flex-direction: column;
  }

  .slide-body {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  /* Universal Pills */
  .pill-row {
    display: block;
    margin-bottom: 18px;
  }
  .tag-pill {
    display: inline-block;
    background: #ffffff;
    border: 1px solid #e8e6dc;
    padding: 10px 22px;
    border-radius: 9999px;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #57534e;
    box-shadow: 0 1px 3px rgba(20,20,19,0.04);
  }
  .tag-pill .dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    background: #d97757;
    border-radius: 50%;
    margin-right: 10px;
    vertical-align: middle;
  }
  .tag-pill.purple { background: #ffffff; border-color: #e8e6dc; color: #57534e; }
  .tag-pill.purple .dot { background: #6a9bcc; }
  .tag-pill.green { background: #ffffff; border-color: #e8e6dc; color: #57534e; }
  .tag-pill.green .dot { background: #788c5d; }

  /* Universal Typography Across ALL Slides */
  .hero {
    font-size: 78px;
    font-weight: 900;
    line-height: 1.02;
    letter-spacing: -2px;
    color: #141413;
    margin-bottom: 14px;
  }
  .hero .accent { color: #6a9bcc; }
  .hero .accent-green { color: #788c5d; }

  .sub {
    font-size: 26px;
    font-weight: 600;
    color: #57534e;
    line-height: 1.45;
    margin-top: 8px;
  }

  /* Universal Cards */
  .card {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 20px;
    padding: 28px 32px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: 0 2px 4px rgba(20,20,19,0.03), 0 12px 32px rgba(20,20,19,0.06), inset 0 1px 0 rgba(255,255,255,0.9);
  }

  /* Universal Two Column Sub-Cards */
  .two-col-cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
  }
  .sub-stat-card {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 16px;
    padding: 24px 28px;
    box-shadow: 0 1px 3px rgba(20,20,19,0.03);
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-sizing: border-box;
  }
  .sub-stat-card .s-tag {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #78716c;
    margin-bottom: 6px;
  }
  .sub-stat-card .s-val {
    font-size: 24px;
    font-weight: 800;
    color: #141413;
    line-height: 1.25;
  }
  .sub-stat-card .s-desc {
    font-size: 16px;
    color: #57534e;
    margin-top: 8px;
    line-height: 1.5;
    hyphens: none;
    -webkit-hyphens: none;
    text-align: left;
  }

  /* Slide 1: Deliverable Table */
  .table-card {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 2px 16px rgba(20,20,19,0.06), inset 0 1px 0 rgba(255,255,255,0.9);
  }
  .table-top-bar {
    background: #141413;
    padding: 18px 26px;
    border-bottom: 1px solid #2a2a28;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    font-weight: 700;
    color: #faf9f5;
  }
  table.mock-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 15px;
    text-align: left;
  }
  table.mock-table th {
    background: #f5f5f0;
    padding: 13px 18px;
    color: #78716c;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-size: 12px;
    border-bottom: 1px solid #e8e6dc;
  }
  table.mock-table td {
    padding: 14px 18px;
    border-bottom: 1px solid #f5f5f0;
    vertical-align: middle;
    background: #ffffff;
    line-height: 1.45;
  }
  table.mock-table tr:last-child td {
    border-bottom: none;
  }
  .rank-num {
    font-size: 14px;
    font-weight: 800;
    color: #78716c;
  }
  .score-box {
    background: #141413;
    color: #faf9f5;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 13px;
    letter-spacing: 0.5px;
    display: inline-block;
    text-align: center;
  }
  .mark {
    background: #e8e6dc;
    color: #141413;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 700;
    border: 1px solid #d6d3cd;
  }

  /* Slide 2: 4-Layer Compounding Filter */
  .layer-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .layer-card {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 16px;
    padding: 24px 26px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 2px 6px rgba(20,20,19,0.03);
  }
  .layer-card.highlight {
    border-color: #788c5d;
    background: #fbfcf9;
    box-shadow: 0 4px 14px rgba(120, 140, 93, 0.12);
  }
  .layer-badge-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .layer-tag {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #78716c;
  }
  .layer-card.highlight .layer-tag { color: #788c5d; }
  .layer-scope {
    font-size: 13px;
    font-weight: 800;
    background: #faf9f5;
    border: 1px solid #e8e6dc;
    padding: 3px 10px;
    border-radius: 6px;
    color: #78716c;
  }
  .layer-card.highlight .layer-scope {
    background: rgba(120, 140, 93, 0.15);
    border-color: #a7c5a8;
    color: #2d4a22;
  }
  .layer-title {
    font-size: 22px;
    font-weight: 800;
    color: #141413;
  }
  .layer-desc {
    font-size: 16px;
    color: #57534e;
    line-height: 1.5;
  }

  /* Slide 4: Desktop App Chat Preview */
  .chat-box {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(20,20,19,0.04);
  }
  .chat-box-header {
    background: #f5f4ed;
    border-bottom: 1px solid #e8e6dc;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    font-weight: 700;
    color: #78716c;
  }
  .chat-dot { width: 11px; height: 11px; border-radius: 50%; }
  .c-red { background: #d97757; }
  .c-yellow { background: #e8c4a0; }
  .c-green { background: #788c5d; }
  .chat-box-body {
    padding: 22px 26px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .c-msg {
    border-radius: 14px;
    padding: 16px 20px;
    font-size: 18px;
    line-height: 1.55;
  }
  .c-user {
    background: #faf9f5;
    border: 1px solid #e8e6dc;
    color: #141413;
  }
  .c-user .c-label {
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #6a9bcc;
    margin-bottom: 6px;
  }
  .c-agent {
    background: rgba(120, 140, 93, 0.08);
    border: 1px solid #c7d8be;
    color: #141413;
  }
  .c-agent .c-label {
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #788c5d;
    margin-bottom: 6px;
  }

  /* Universal Footer */
  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #e8e6dc;
    padding-top: 16px;
    font-size: 12px;
    font-weight: 500;
    color: #a8a29e;
    margin-top: auto;
  }
  .footer .brand { color: #78716c; }
  .footer .brand span { color: #141413; font-weight: 800; }
  .footer .page {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    padding: 6px 14px;
    border-radius: 8px;
    color: #57534e;
    font-weight: 700;
    font-size: 14px;
  }
</style>
</head>
<body>

<!-- ======================================================================= -->
<!-- SLIDE 1: TITLE — CENTERED, 2 LINES, NO PILLS, NO FOOTER                   -->
<!-- ======================================================================= -->
<div class="slide" style="justify-content:center; align-items:center; text-align:center; padding: 96px 60px;">
  <div style="display:flex; flex-direction:column; align-items:center; gap:22px; width:100%; max-width:920px;">
    <div class="hero" style="font-size:92px; line-height:0.88; letter-spacing:-3px; text-align:center;">
      Research and score<br/><span class="accent">anything</span> at scale, for free.
    </div>
    <div style="font-size:20px; font-weight:500; color:#57534e; text-align:center; margin-top:8px;">
      Your target accounts • Your docs • Your criteria — every row backed by proof.
    </div>
    <div style="margin-top:14px; background:#1a1a18; border:1px solid #2a2a28; border-radius:10px; padding:14px 20px; display:inline-flex; align-items:center; gap:18px;">
      <span style="font-family:ui-monospace; font-size:14px; color:#e8e6dc;"><span style="color:#a8a29e;">$</span> free-fleet quickstart --demo</span>
      <span style="font-size:11px; font-weight:800; letter-spacing:1px; text-transform:uppercase; color:#a7c5a8; border-left:1px solid #2a2a28; padding-left:18px;">Try in 30s →</span>
    </div>
  </div>
</div>

<!-- ======================================================================= -->
<!-- SLIDE 2: THE DELIVERABLE (COVER HOOK) — GOOD SLIDE PRESERVED AS 02/05  -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="slide-header">
    <div class="hero">
      Accounts scored, sorted,<br/>and <span class="accent">backed by proof.</span>
    </div>
    <div class="sub">
      The top 25 accounts ranked by fit score — with grounded evidence of their exact technical gaps.
    </div>
  </div>

  <div class="slide-body">
    <div class="table-card">
      <div class="table-top-bar">
        <span>ranked_target_accounts.csv</span>
        <span style="color:#a7c5a8; font-weight:800;">Scored &amp; sorted by fit • Top 5 shown</span>
      </div>
      <table class="mock-table">
        <thead>
          <tr>
            <th style="width:8%;">Rank</th>
            <th style="width:18%;">Account</th>
            <th style="width:10%;">Score</th>
            <th style="width:26%;">Identified Gap</th>
            <th style="width:38%;">Grounded Evidence of Gap</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><span class="rank-num">#1</span></td>
            <td style="font-weight:800; color:#141413;">stripe.com</td>
            <td><span class="score-box">98</span></td>
            <td style="font-weight:700; color:#141413;">Legacy billing migration to Kafka</td>
            <td style="font-style:italic; color:#44403c;">"<span class="mark">lead migration off legacy v1 billing pipeline</span>"</td>
          </tr>
          <tr>
            <td><span class="rank-num">#2</span></td>
            <td style="font-weight:800; color:#141413;">hyper_ai</td>
            <td><span class="score-box">94</span></td>
            <td style="font-weight:700; color:#141413;">50k QPS database latency wall</td>
            <td style="font-style:italic; color:#44403c;">"<span class="mark">hitting latency limits at 50k QPS on self-hosted Postgres</span>"</td>
          </tr>
          <tr>
            <td><span class="rank-num">#3</span></td>
            <td style="font-weight:800; color:#141413;">pinecone.io</td>
            <td><span class="score-box">91</span></td>
            <td style="font-weight:700; color:#141413;">Multi-tenant cluster search scaling</td>
            <td style="font-style:italic; color:#44403c;">"<span class="mark">scaling vector search across multi-tenant clusters</span>"</td>
          </tr>
          <tr>
            <td><span class="rank-num">#4</span></td>
            <td style="font-weight:800; color:#141413;">posthog.com</td>
            <td><span class="score-box">87</span></td>
            <td style="font-weight:700; color:#141413;">ClickHouse 2B+ event ingestion</td>
            <td style="font-style:italic; color:#44403c;">"<span class="mark">optimizing ClickHouse to ingest 2B+ daily analytics events</span>"</td>
          </tr>
          <tr>
            <td><span class="rank-num">#5</span></td>
            <td style="font-weight:800; color:#141413;">supabase.com</td>
            <td><span class="score-box">84</span></td>
            <td style="font-weight:700; color:#141413;">Distributed edge replication lag</td>
            <td style="font-style:italic; color:#44403c;">"<span class="mark">building globally distributed real-time Edge Functions</span>"</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="two-col-cards">
      <div class="sub-stat-card">
        <div class="s-tag">Prioritized Pipeline</div>
        <div class="s-val">Scored &amp; Sorted Accounts</div>
        <div class="s-desc">Reps focus on top-scoring accounts first instead of guessing which cold accounts have active needs.</div>
      </div>
      <div class="sub-stat-card">
        <div class="s-tag">Grounded Evidence</div>
        <div class="s-val">Documented Technical Gaps</div>
        <div class="s-desc">Every qualification is backed by verbatim text proving the company’s real bottleneck.</div>
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="brand"><span>free-fleet</span> // ranked &amp; actionable spreadsheets</div>
    <div class="page">02 / 05</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 2: THE 4-LAYER COMPOUNDING FILTER                                 -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="slide-header">
    <div class="hero">
      The 4-Layer Filter.<br/>From 1,000 down<br/><span class="accent">to the top 25.</span>
    </div>
    <div class="sub">
      Don’t run one broad prompt. Compound layers of evidence, enriching only the survivors at each stage.
    </div>
  </div>

  <div class="slide-body">
    <div class="layer-grid">
      <!-- Layer 1 -->
      <div class="layer-card">
        <div class="layer-badge-row">
          <span class="layer-tag">Layer 1</span>
          <span class="layer-scope">1,000 → 600</span>
        </div>
        <div class="layer-title">Firmographic ICP Fit</div>
        <div class="layer-desc">
          Scans homepage &amp; positioning. Immediately filters out wrong audience, B2C, and out-of-scope company types.
        </div>
      </div>

      <!-- Layer 2 -->
      <div class="layer-card">
        <div class="layer-badge-row">
          <span class="layer-tag">Layer 2</span>
          <span class="layer-scope">600 → 150</span>
        </div>
        <div class="layer-title">Tech Stack &amp; Architecture</div>
        <div class="layer-desc">
          Scans developer docs, API changelogs, and integrations. Validates tech compatibility with verbatim quotes.
        </div>
      </div>

      <!-- Layer 3 -->
      <div class="layer-card">
        <div class="layer-badge-row">
          <span class="layer-tag">Layer 3</span>
          <span class="layer-scope">150 → 50</span>
        </div>
        <div class="layer-title">Hiring &amp; Budget Signals</div>
        <div class="layer-desc">
          Scans active job descriptions and career pages. Pinpoints open roles citing target technologies or bottlenecks.
        </div>
      </div>

      <!-- Layer 4 -->
      <div class="layer-card">
        <div class="layer-badge-row">
          <span class="layer-tag">Layer 4 • Final 25</span>
          <span class="layer-scope">50 → 25</span>
        </div>
        <div class="layer-title">Scoring &amp; Gap Analysis</div>
        <div class="layer-desc">
          Ranks surviving accounts by ICP fit score (0–100) and extracts verbatim evidence of their core technical gaps.
        </div>
      </div>
    </div>

    <div class="card" style="padding:24px 28px; gap:8px;">
      <div style="font-size:20px; font-weight:800; color:#141413;">Why this compounds so powerfully</div>
      <div style="font-size:16px; color:#57534e; line-height:1.55;">
        By Layer 4, you don’t just have account names. You have 25 top-scoring accounts with verbatim evidence proving their exact technical gaps and active bottlenecks.
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="brand"><span>free-fleet</span> // compounding evidence layers</div>
    <div class="page">03 / 05</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 3: HOW VERIFICATION WORKS (EXACT SUBSTRING MATCH)                -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="slide-header">
    <div class="hero">
      Don’t trust AI summaries.<br/><span class="accent-green">Require exact quotes.</span>
    </div>
    <div class="sub">
      Every account qualification is grounded in verbatim evidence of their real technical gaps.
    </div>
  </div>

  <div class="slide-body">
    <!-- Step 1: Raw Public Source -->
    <div class="card" style="padding:24px 28px; gap:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:13px; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; color:#78716c;">Step 1 • Public Job Post / Career Page</span>
        <span style="font-size:13px; font-weight:700; color:#57534e; background:#f5f4ed; border:1px solid #e8e6dc; padding:4px 10px; border-radius:6px;">Role: Staff Infrastructure Engineer</span>
      </div>
      <div style="font-size:18px; line-height:1.55; color:#141413; background:#faf9f5; border:1px solid #e8e6dc; border-radius:12px; padding:18px 20px;">
        “We are looking for a Staff Engineer to join our Platform team. In this role, you will be responsible for <span style="background:rgba(120,140,93,0.25); padding:2px 6px; border-radius:4px; font-weight:700;">leading the migration of our legacy billing service to Apache Kafka</span> and modernizing our distributed streaming architecture.”
      </div>
    </div>

    <!-- Step 2: Verification Gate -->
    <div class="card" style="padding:24px 28px; gap:12px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:13px; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; color:#788c5d;">Step 2 • Verbatim Verification Gate</span>
        <span style="font-size:13px; font-weight:700; color:#788c5d; background:rgba(120,140,93,0.12); border:1px solid #c7d8be; padding:4px 10px; border-radius:6px;">✓ Substring Matched</span>
      </div>
      <div style="display:grid; grid-template-columns:140px 1fr; gap:10px; align-items:center; background:#faf9f5; border:1px solid #e8e6dc; border-radius:12px; padding:14px 18px;">
        <div style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#78716c;">Identified Gap</div>
        <div style="font-size:16px; font-weight:800; color:#141413;">Legacy Billing Migration to Kafka</div>
        <div style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#78716c;">ICP Fit Score</div>
        <div style="font-size:15px; font-weight:800; color:#141413;"><span class="score-box" style="padding:2px 8px; font-size:12px;">98</span> • Tier-1 Target Account</div>
        <div style="font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#78716c;">Grounded Evidence</div>
        <div style="font-size:15px; font-style:italic; color:#141413;">“leading the migration of our legacy billing service to Apache Kafka”</div>
      </div>
      <div style="font-size:15px; color:#57534e; line-height:1.5;">
        If the model hallucinates a gap or assumes an unverified bottleneck, the substring match fails and the account is discarded. Every qualified account is backed by documented proof.
      </div>
    </div>

    <div class="two-col-cards">
      <div class="sub-stat-card">
        <div class="s-tag">Proof Over Predictions</div>
        <div class="s-val">Documented Gaps</div>
        <div class="s-desc">Account qualification is anchored in an explicit bottleneck cited directly by the company.</div>
      </div>
      <div class="sub-stat-card">
        <div class="s-tag">Zero Hallucinations</div>
        <div class="s-val">1-Click Verifiable Audit</div>
        <div class="s-desc">Anyone on your team can verify the exact sentence on the live page proving why this account qualified.</div>
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="brand"><span>free-fleet</span> // character-exact verification</div>
    <div class="page">04 / 05</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 4: HOW TO RUN IT IN CLAUDE DESKTOP                                -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="slide-header">
    <div class="hero">
      Run it where<br/>you already chat.
    </div>
    <div class="sub">
      Connect once, then score accounts and extract verified gaps in plain English.
    </div>
  </div>

  <div class="slide-body">
    <!-- 3 Simple Steps -->
    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">
      <div class="sub-stat-card" style="padding:18px 20px;">
        <div style="font-size:13px; font-weight:800; color:#6a9bcc; margin-bottom:4px; text-transform:uppercase; letter-spacing:1px;">1. Connect</div>
        <div class="s-val" style="font-size:18px;">Enable Tool</div>
        <div class="s-desc" style="font-size:14px; margin-top:6px; line-height:1.45;">Add free-fleet to Claude, Codex, Cursor, Grokbot, or any MCP host.</div>
      </div>
      <div class="sub-stat-card" style="padding:18px 20px;">
        <div style="font-size:13px; font-weight:800; color:#788c5d; margin-bottom:4px; text-transform:uppercase; letter-spacing:1px;">2. Drop CSV</div>
        <div class="s-val" style="font-size:18px;">Upload Accounts</div>
        <div class="s-desc" style="font-size:14px; margin-top:6px; line-height:1.45;">Drag &amp; drop your list of companies or website URLs into chat.</div>
      </div>
      <div class="sub-stat-card" style="padding:18px 20px;">
        <div style="font-size:13px; font-weight:800; color:#d97757; margin-bottom:4px; text-transform:uppercase; letter-spacing:1px;">3. Chat</div>
        <div class="s-val" style="font-size:18px;">Ask in Plain English</div>
        <div class="s-desc" style="font-size:14px; margin-top:6px; line-height:1.45;">Ask Claude to score accounts, sort them, and extract grounded evidence of technical gaps.</div>
      </div>
    </div>

    <!-- Chat Box Preview -->
    <div class="chat-box">
      <div class="chat-box-header">
        <span class="chat-dot c-red"></span>
        <span class="chat-dot c-yellow"></span>
        <span class="chat-dot c-green"></span>
        <span style="margin-left:8px; font-weight:700;">Claude / Codex / Cursor / Grokbot</span>
      </div>
      <div class="chat-box-body" style="padding:18px 22px; gap:12px;">
        <div class="c-msg c-user" style="padding:14px 18px; font-size:16px;">
          <div class="c-label">You</div>
          “Triage <strong>accounts.csv</strong> to score the top accounts and extract grounded evidence of infrastructure bottlenecks and data pipeline migrations.”
        </div>
        <div class="c-msg c-agent" style="padding:14px 18px; font-size:16px;">
          <div class="c-label">Claude</div>
          ✓ Processed 100 accounts in 2 minutes • Scored and ranked top 25 accounts with grounded evidence of technical gaps • Exported <strong>ranked_accounts.csv</strong>
        </div>
      </div>
    </div>

    <div class="two-col-cards">
      <div class="sub-stat-card">
        <div class="s-tag">Local &amp; Private</div>
        <div class="s-val">Permissive MIT License</div>
        <div class="s-desc">Open source and private. Account data and qualification criteria never leave your machine.</div>
      </div>
      <div class="sub-stat-card">
        <div class="s-tag">Open Source</div>
        <div class="s-val">Star on GitHub ★</div>
        <div class="s-desc">Quickstart guide and templates available at github.com/NatesVibeCode/free-fleet.</div>
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="brand"><span>free-fleet</span> // free &amp; open source on github</div>
    <div class="page">05 / 05</div>
  </div>
</div>

</body>
</html>
"""

    out_pdf = Path("free-fleet-prospecting-carousel.pdf")
    print(f"Rendering PDF with WeasyPrint: {out_pdf}...")
    html = weasyprint.HTML(string=html_content)
    html.write_pdf(target=str(out_pdf))
    print(f"PDF successfully created ({out_pdf.stat().st_size} bytes)")

    carousel_dir = Path("carousel")
    carousel_dir.mkdir(exist_ok=True)
    doc = fitz.open(str(out_pdf))
    print(f"Converting {len(doc)} PDF pages to PNG (exact 1080x1350)...")
    for i, page in enumerate(doc, start=1):
        scale_x = 1080.0 / page.rect.width
        scale_y = 1350.0 / page.rect.height
        matrix = fitz.Matrix(scale_x, scale_y)
        pix = page.get_pixmap(matrix=matrix)
        png_path = carousel_dir / f"slide-{i}.png"
        pix.save(str(png_path))
        print(f"  Slide {i} saved: {png_path} ({pix.width}x{pix.height})")
    doc.close()
    
    # Remove any extra stale slide PNGs if switching from 5 to 4 slides
    stale_slide = carousel_dir / "slide-5.png"
    if stale_slide.exists():
        stale_slide.unlink()
        print("  Removed stale slide-5.png")

    print("Carousel export complete!")

if __name__ == "__main__":
    generate_carousel()
