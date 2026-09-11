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

  /* Slide 3: Deliverable Table */
  .table-card {
    background: #ffffff;
    border: 1.5px solid #e8e6dc;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(20,20,19,0.04);
  }
  .table-top-bar {
    background: #141413;
    padding: 20px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 20px;
    font-weight: 800;
    color: #faf9f5;
  }
  table.mock-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 20px;
  }
  table.mock-table th {
    background: #f6f5ee;
    padding: 18px 24px;
    color: #78716c;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-size: 15px;
    border-bottom: 1.5px solid #e8e6dc;
    text-align: left;
  }
  table.mock-table td {
    padding: 20px 24px;
    border-bottom: 1px solid #f0eee6;
    vertical-align: middle;
    background: #ffffff;
    line-height: 1.45;
  }
  table.mock-table tr:last-child td {
    border-bottom: none;
  }
  .rank-num {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    font-weight: 900;
    font-size: 24px;
    color: #78716c;
  }
  .score-box {
    display: inline-block;
    background: #141413;
    color: #ffffff;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    font-weight: 900;
    font-size: 22px;
    padding: 7px 14px;
    border-radius: 10px;
  }
  .quote-callout {
    background: #faf9f5;
    border-left: 3.5px solid #788c5d;
    padding: 8px 14px;
    border-radius: 4px;
    color: #292524;
    font-size: 18px;
    font-style: italic;
    line-height: 1.4;
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
<!-- SLIDE 1: TITLE — BALANCED, COLORFUL COVER HOOK                          -->
<!-- ======================================================================= -->
<div class="slide" style="justify-content:space-between; padding: 80px 45px 60px 45px;">
  <div></div>

  <div style="display:flex; flex-direction:column; justify-content:center; align-items:center; margin: auto 0;">
    <div style="font-size:134px; font-weight:900; line-height:1.05; letter-spacing:-5.5px; color:#141413; text-align:center;">
      <div style="white-space:nowrap;">I built a tool to</div>
      <div style="color:#6a9bcc; white-space:nowrap;">research &amp; score</div>
      <div style="white-space:nowrap;">target accounts</div>
      <div style="color:#788c5d; white-space:nowrap;">for free, at scale.</div>
    </div>

    <div style="display:flex; align-items:center; gap:12px; font-size:32px; font-weight:800; color:#57534e; margin-top:54px; white-space:nowrap;">
      <span>Swipe to see how it works</span>
      <span style="font-size:38px; color:#d97757;">→</span>
    </div>
  </div>

  <div style="display:flex; justify-content:center; align-items:center; border-top:1px solid #e8e6dc; padding-top:28px;">
    <div style="font-family:ui-monospace; font-size:24px; font-weight:800; color:#141413;">
      github.com/NatesVibeCode/account-fleet
    </div>
  </div>
</div>

<!-- ======================================================================= -->
<!-- ======================================================================= -->
<!-- SLIDE 2: THE 100% FREE SETUP & HARNESS CONNECT                         -->
<!-- ======================================================================= -->
<div class="slide" style="justify-content:space-between; padding: 70px 65px 45px 65px;">
  <div class="slide-header">
    <div class="hero" style="font-size: 86px; line-height: 1.05; letter-spacing: -3px; margin-bottom: 14px;">
      All you need is<br/><span class="accent-green">2 free accounts.</span>
    </div>
    <div class="sub" style="font-size: 30px; font-weight: 600; color: #57534e; line-height: 1.4;">
      Then plug it into whatever harness or chat tool you already use.
    </div>
  </div>

  <div style="display:flex; flex-direction:column; gap: 24px;">
    <!-- Step 1: OpenCode -->
    <div class="card" style="padding: 32px 36px; gap: 14px; border-radius: 20px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size: 30px; font-weight: 900; color: #141413;">1. Free OpenCode Account</div>
        <div style="display:inline-block; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; background: rgba(120,140,93,0.12); color: #788c5d; border: 1px solid #c7d8be; padding: 6px 16px; border-radius: 12px;">Local Engine</div>
      </div>
      <div style="font-size: 22px; color: #57534e; line-height: 1.45;">
        Runs your open-source coding agent locally. Orchestrates extraction with <strong>zero seat licenses</strong>.
      </div>
    </div>

    <!-- Step 2: OpenRouter -->
    <div class="card" style="padding: 32px 36px; gap: 14px; border-radius: 20px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size: 30px; font-weight: 900; color: #141413;">2. Free OpenRouter Account</div>
        <div style="display:inline-block; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; background: rgba(106,155,204,0.12); color: #6a9bcc; border: 1px solid #b3cde0; padding: 6px 16px; border-radius: 12px;">$0 Model Routing</div>
      </div>
      <div style="font-size: 22px; color: #57534e; line-height: 1.45;">
        Routes prompts to free-tier cloud models. <strong>Zero token costs</strong>, zero spend, and zero credit card needed.
      </div>
    </div>

    <!-- Step 3: Any Harness -->
    <div class="card" style="padding: 32px 36px; gap: 14px; border-radius: 20px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size: 30px; font-weight: 900; color: #141413;">3. Use Whatever Harness You Want</div>
        <div style="display:inline-block; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; background: #f5f4ed; color: #57534e; border: 1px solid #e8e6dc; padding: 6px 16px; border-radius: 12px;">Your Workspace</div>
      </div>
      <div style="font-size: 22px; color: #57534e; line-height: 1.45;">
        Works out of the box in <strong>Claude Desktop, Cursor, Codex, Grokbot, Antigravity</strong>, or any MCP-compatible agent.
      </div>
      <div style="background: #faf9f5; border: 1px solid #e8e6dc; color: #141413; font-size: 20px; font-weight: 700; padding: 14px 20px; border-radius: 12px; display: flex; align-items: center; gap: 10px;">
        <span style="color: #788c5d; font-size: 24px;">✓</span> Add as a local MCP tool in 1 click — then just drag &amp; drop your CSV.
      </div>
    </div>

    <!-- Trust Bar -->
    <div style="background: #ffffff; border: 1.5px solid #e8e6dc; border-radius: 18px; padding: 22px 28px; display: flex; justify-content: space-around; align-items: center; text-align: center;">
      <div>
        <div style="font-size: 14px; font-weight: 800; text-transform: uppercase; color: #788c5d; letter-spacing: 1.2px;">$0 Cost</div>
        <div style="font-size: 20px; font-weight: 800; color: #141413; margin-top: 4px;">No Credit Card</div>
      </div>
      <div style="height: 36px; width: 1px; background: #e8e6dc;"></div>
      <div>
        <div style="font-size: 14px; font-weight: 800; text-transform: uppercase; color: #6a9bcc; letter-spacing: 1.2px;">No Lock-in</div>
        <div style="font-size: 20px; font-weight: 800; color: #141413; margin-top: 4px;">Any Agent / Chat</div>
      </div>
      <div style="height: 36px; width: 1px; background: #e8e6dc;"></div>
      <div>
        <div style="font-size: 14px; font-weight: 800; text-transform: uppercase; color: #d97757; letter-spacing: 1.2px;">Full Ownership</div>
        <div style="font-size: 20px; font-weight: 800; color: #141413; margin-top: 4px;">Local SQLite DB</div>
      </div>
    </div>
  </div>

  <div class="footer" style="padding-top: 18px; margin-top: 0;">
    <div class="brand"><span>free-fleet</span> // 100% free stack</div>
    <div class="page" style="font-size: 16px; padding: 8px 18px;">02 / 05</div>
  </div>
</div>

<!-- ======================================================================= -->
<!-- SLIDE 3: THE DELIVERABLE (COVER HOOK) — PRESERVED AS 03/05              -->
<!-- ======================================================================= -->
<div class="slide" style="justify-content:space-between; padding: 70px 65px 45px 65px;">
  <div class="slide-header">
    <div class="hero" style="font-size: 82px; line-height: 1.05; letter-spacing: -3px; margin-bottom: 14px;">
      Accounts scored, sorted,<br/>and <span class="accent">backed by proof.</span>
    </div>
    <div class="sub" style="font-size: 30px; font-weight: 600; color: #57534e; line-height: 1.4;">
      The top 25 accounts ranked by ICP fit — with exact evidence of technical gaps.
    </div>
  </div>

  <div style="display:flex; flex-direction:column; gap: 20px;">
    <!-- Table -->
    <div class="table-card">
      <div class="table-top-bar">
        <span style="font-family:ui-monospace, monospace;">ranked_target_accounts.csv</span>
        <span style="color:#a7c5a8; font-weight:800; font-size:17px;">Scored &amp; sorted by fit • Top 5 of 25 shown</span>
      </div>
      <table class="mock-table">
        <thead>
          <tr>
            <th style="width:9%;">Rank</th>
            <th style="width:21%;">Account</th>
            <th style="width:12%;">Score</th>
            <th style="width:58%;">Grounded Technical Evidence</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><span class="rank-num">#1</span></td>
            <td><span style="font-size:24px; font-weight:900; color:#141413;">stripe.com</span></td>
            <td><span class="score-box">98</span></td>
            <td>
              <div class="quote-callout">“lead migration off legacy v1 billing pipeline to Kafka”</div>
            </td>
          </tr>
          <tr>
            <td><span class="rank-num">#2</span></td>
            <td><span style="font-size:24px; font-weight:900; color:#141413;">hyper_ai</span></td>
            <td><span class="score-box">94</span></td>
            <td>
              <div class="quote-callout">“hitting latency limits at 50k QPS on Postgres cluster”</div>
            </td>
          </tr>
          <tr>
            <td><span class="rank-num">#3</span></td>
            <td><span style="font-size:24px; font-weight:900; color:#141413;">pinecone.io</span></td>
            <td><span class="score-box">91</span></td>
            <td>
              <div class="quote-callout">“scaling vector search across multi-tenant clusters”</div>
            </td>
          </tr>
          <tr>
            <td><span class="rank-num">#4</span></td>
            <td><span style="font-size:24px; font-weight:900; color:#141413;">posthog.com</span></td>
            <td><span class="score-box">87</span></td>
            <td>
              <div class="quote-callout">“optimizing ClickHouse to ingest 2B+ daily analytics events”</div>
            </td>
          </tr>
          <tr>
            <td><span class="rank-num">#5</span></td>
            <td><span style="font-size:24px; font-weight:900; color:#141413;">supabase.com</span></td>
            <td><span class="score-box">84</span></td>
            <td>
              <div class="quote-callout">“building globally distributed Edge Functions replication”</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Takeaway Banner -->
    <div style="background: #ffffff; border: 1.5px solid #e8e6dc; border-radius: 18px; padding: 22px 28px; display: flex; align-items: center; gap: 20px;">
      <div style="width: 52px; height: 52px; border-radius: 14px; background: rgba(120,140,93,0.15); border: 1px solid #c7d8be; display: flex; align-items: center; justify-content: center; font-size: 26px; color: #788c5d; font-weight: 900; flex-shrink: 0;">
        ✓
      </div>
      <div>
        <div style="font-size: 22px; font-weight: 900; color: #141413;">
          Every row carries a character-exact source quote
        </div>
        <div style="font-size: 19px; color: #57534e; margin-top: 4px; line-height: 1.4;">
          Reps never reach out cold with generic assumptions — they cite verified bottlenecks.
        </div>
      </div>
    </div>

    <!-- Deliverable Trust Bar (matching Slide 2) -->
    <div style="background: #ffffff; border: 1.5px solid #e8e6dc; border-radius: 18px; padding: 22px 28px; display: flex; justify-content: space-around; align-items: center; text-align: center;">
      <div>
        <div style="font-size: 14px; font-weight: 800; text-transform: uppercase; color: #788c5d; letter-spacing: 1.2px;">Ranked Pipeline</div>
        <div style="font-size: 20px; font-weight: 800; color: #141413; margin-top: 4px;">Top 25 Accounts</div>
      </div>
      <div style="height: 36px; width: 1px; background: #e8e6dc;"></div>
      <div>
        <div style="font-size: 14px; font-weight: 800; text-transform: uppercase; color: #6a9bcc; letter-spacing: 1.2px;">Zero Hallucinations</div>
        <div style="font-size: 20px; font-weight: 800; color: #141413; margin-top: 4px;">Exact Source Quotes</div>
      </div>
      <div style="height: 36px; width: 1px; background: #e8e6dc;"></div>
      <div>
        <div style="font-size: 14px; font-weight: 800; text-transform: uppercase; color: #d97757; letter-spacing: 1.2px;">Actionable CSV</div>
        <div style="font-size: 20px; font-weight: 800; color: #141413; margin-top: 4px;">Direct CRM Export</div>
      </div>
    </div>
  </div>

  <div class="footer" style="padding-top: 18px; margin-top: 0;">
    <div class="brand"><span>free-fleet</span> // ranked &amp; actionable spreadsheets</div>
    <div class="page" style="font-size: 16px; padding: 8px 18px;">03 / 05</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 4: THE 4-LAYER COMPOUNDING FILTER — PRESERVED AS 04/05            -->
<!-- ======================================================================= -->
<div class="slide" style="justify-content:space-between; padding: 70px 65px 45px 65px;">
  <div class="slide-header">
    <div class="hero" style="font-size: 86px; line-height: 1.05; letter-spacing: -3px;">
      The 4-Layer Filter.<br/>From 1,000 down<br/><span class="accent">to the top 25.</span>
    </div>
  </div>

  <div style="display:flex; flex-direction:column; gap: 20px;">
    <!-- Layer 1 -->
    <div class="card" style="padding: 28px 30px; display: flex; flex-direction: row; align-items: center; justify-content: space-between; border-radius: 18px;">
      <div style="display: flex; align-items: center; gap: 22px;">
        <div style="width: 52px; height: 52px; border-radius: 14px; background: #f5f4ed; border: 1.5px solid #e8e6dc; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 21px; color: #78716c; font-family: ui-monospace, monospace; flex-shrink: 0;">
          L1
        </div>
        <div>
          <div style="font-size: 25px; font-weight: 900; color: #141413;">Firmographic ICP Fit</div>
          <div style="font-size: 20px; color: #57534e; margin-top: 5px; line-height: 1.4;">Scans positioning &amp; homepages. Filters out wrong-fit companies instantly.</div>
        </div>
      </div>
      <div style="background: #faf9f5; border: 1.5px solid #e8e6dc; padding: 11px 0; width: 170px; text-align: center; border-radius: 12px; font-family: ui-monospace, monospace; font-weight: 800; font-size: 20px; color: #78716c; white-space: nowrap; margin-left: 20px; flex-shrink: 0;">
        1,000 → 600
      </div>
    </div>

    <!-- Layer 2 -->
    <div class="card" style="padding: 28px 30px; display: flex; flex-direction: row; align-items: center; justify-content: space-between; border-radius: 18px;">
      <div style="display: flex; align-items: center; gap: 22px;">
        <div style="width: 52px; height: 52px; border-radius: 14px; background: #f5f4ed; border: 1.5px solid #e8e6dc; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 21px; color: #78716c; font-family: ui-monospace, monospace; flex-shrink: 0;">
          L2
        </div>
        <div>
          <div style="font-size: 25px; font-weight: 900; color: #141413;">Tech Stack &amp; Architecture</div>
          <div style="font-size: 20px; color: #57534e; margin-top: 5px; line-height: 1.4;">Scans developer docs &amp; changelogs. Extracts exact infrastructure stack.</div>
        </div>
      </div>
      <div style="background: #faf9f5; border: 1.5px solid #e8e6dc; padding: 11px 0; width: 170px; text-align: center; border-radius: 12px; font-family: ui-monospace, monospace; font-weight: 800; font-size: 20px; color: #78716c; white-space: nowrap; margin-left: 20px; flex-shrink: 0;">
        600 → 150
      </div>
    </div>

    <!-- Layer 3 -->
    <div class="card" style="padding: 28px 30px; display: flex; flex-direction: row; align-items: center; justify-content: space-between; border-radius: 18px;">
      <div style="display: flex; align-items: center; gap: 22px;">
        <div style="width: 52px; height: 52px; border-radius: 14px; background: #f5f4ed; border: 1.5px solid #e8e6dc; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 21px; color: #78716c; font-family: ui-monospace, monospace; flex-shrink: 0;">
          L3
        </div>
        <div>
          <div style="font-size: 25px; font-weight: 900; color: #141413;">Hiring &amp; Budget Signals</div>
          <div style="font-size: 20px; color: #57534e; margin-top: 5px; line-height: 1.4;">Scans active engineering job posts for urgent initiatives and tooling gaps.</div>
        </div>
      </div>
      <div style="background: #faf9f5; border: 1.5px solid #e8e6dc; padding: 11px 0; width: 170px; text-align: center; border-radius: 12px; font-family: ui-monospace, monospace; font-weight: 800; font-size: 20px; color: #78716c; white-space: nowrap; margin-left: 20px; flex-shrink: 0;">
        150 → 50
      </div>
    </div>

    <!-- Layer 4 -->
    <div class="card" style="padding: 28px 30px; display: flex; flex-direction: row; align-items: center; justify-content: space-between; border-radius: 18px; border: 2px solid #6a9bcc; background: #f8fbff;">
      <div style="display: flex; align-items: center; gap: 22px;">
        <div style="width: 52px; height: 52px; border-radius: 14px; background: #6a9bcc; border: 1.5px solid #6a9bcc; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 21px; color: #ffffff; font-family: ui-monospace, monospace; flex-shrink: 0;">
          L4
        </div>
        <div>
          <div style="font-size: 25px; font-weight: 900; color: #141413;">Fit Scoring &amp; Verbatim Evidence</div>
          <div style="font-size: 20px; color: #57534e; margin-top: 5px; line-height: 1.4;">Scores survivors 0–100 and clips character-exact quotes of technical gaps.</div>
        </div>
      </div>
      <div style="background: #141413; border: 1.5px solid #141413; padding: 11px 0; width: 170px; text-align: center; border-radius: 12px; font-family: ui-monospace, monospace; font-weight: 900; font-size: 20px; color: #ffffff; white-space: nowrap; margin-left: 20px; flex-shrink: 0;">
        50 → 25
      </div>
    </div>

    <!-- Takeaway Banner -->
    <div style="background: #ffffff; border: 1.5px solid #e8e6dc; border-radius: 18px; padding: 24px 30px; display: flex; align-items: center; gap: 22px;">
      <div style="width: 54px; height: 54px; border-radius: 14px; background: rgba(106,155,204,0.15); border: 1px solid #b3cde0; display: flex; align-items: center; justify-content: center; font-size: 28px; color: #6a9bcc; font-weight: 900; flex-shrink: 0;">
        ✦
      </div>
      <div>
        <div style="font-size: 23px; font-weight: 900; color: #141413;">
          Why compounding works so well
        </div>
        <div style="font-size: 20px; color: #57534e; margin-top: 5px; line-height: 1.4;">
          You only spend model compute on accounts that proved fit. Zero wasted effort on dead leads.
        </div>
      </div>
    </div>
  </div>

  <div class="footer" style="padding-top: 18px; margin-top: 0;">
    <div class="brand"><span>free-fleet</span> // compounding evidence layers</div>
    <div class="page" style="font-size: 16px; padding: 8px 18px;">04 / 05</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 5: HOW VERIFICATION WORKS (EXACT SUBSTRING MATCH) — AS 05/05     -->
<!-- ======================================================================= -->
<div class="slide" style="justify-content:space-between; padding: 65px 65px 40px 65px;">
  <div class="slide-header">
    <div class="hero" style="font-size: 86px; line-height: 1.05; letter-spacing: -3px;">
      Don’t trust AI summaries.<br/><span class="accent-green">Require exact quotes.</span>
    </div>
  </div>

  <div style="display:flex; flex-direction:column; gap: 16px;">
    <!-- Step 1: Raw Public Source Ingestion -->
    <div class="card" style="padding: 24px 28px; gap: 14px; border-radius: 18px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size: 14px; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; color: #78716c;">
          1. Raw Source Ingestion
        </div>
        <div style="font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.8px; color: #57534e; background: #f5f4ed; border: 1.5px solid #e8e6dc; padding: 5px 12px; border-radius: 8px;">
          Public Web Page / Markdown
        </div>
      </div>
      <div style="font-size: 20px; line-height: 1.5; color: #141413; background: #faf9f5; border: 1.5px solid #e8e6dc; border-radius: 12px; padding: 16px 20px;">
        “We are looking for a Staff Engineer to join our Platform team. In this role, you will be responsible for <mark style="background: rgba(120,140,93,0.28); color: #141413; font-weight: 800; padding: 2px 6px; border-radius: 4px;">leading the migration of our legacy billing service to Apache Kafka</mark> and modernizing our distributed streaming architecture.”
      </div>
      <div style="font-size: 18px; color: #57534e; line-height: 1.4;">
        Free-fleet fetches raw unedited HTML/markdown from public URLs and indexes it in local SQLite before extraction.
      </div>
    </div>

    <!-- Step 2: Deterministic Python Verification Gate -->
    <div class="card" style="padding: 24px 28px; gap: 14px; border: 2px solid #788c5d; border-radius: 18px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size: 14px; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; color: #788c5d;">
          2. Exact Substring Verification Gate
        </div>
        <div style="font-family: ui-monospace, monospace; font-size: 13px; font-weight: 800; color: #4f6336; background: #eef5e8; border: 1.5px solid #b8d0a8; padding: 5px 12px; border-radius: 8px;">
          assert quote in raw_text
        </div>
      </div>

      <div style="display: flex; flex-direction: column; gap: 10px; background: #faf9f5; border: 1.5px solid #e8e6dc; border-radius: 12px; padding: 14px 18px;">
        <div style="display: grid; grid-template-columns: 140px 1fr; gap: 8px; align-items: baseline;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #78716c;">Claim</div>
          <div style="font-size: 21px; font-weight: 900; color: #141413;">Legacy billing migration to Kafka</div>
        </div>
        <div style="height: 1px; background: #e8e6dc;"></div>
        <div style="display: grid; grid-template-columns: 140px 1fr; gap: 8px; align-items: baseline;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #78716c;">Exact Quote</div>
          <div style="font-size: 19px; font-style: italic; font-weight: 700; color: #141413;">“leading the migration of our legacy billing service to Apache Kafka”</div>
        </div>
        <div style="height: 1px; background: #e8e6dc;"></div>
        <div style="display: grid; grid-template-columns: 140px 1fr; gap: 8px; align-items: baseline;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #78716c;">Byte Offsets</div>
          <div style="font-family: ui-monospace, monospace; font-size: 16px; font-weight: 700; color: #57534e;">chars 142 : 211 • verified match at line 1</div>
        </div>
      </div>

      <div style="font-size: 19px; color: #57534e; line-height: 1.4;">
        If the model hallucinates or paraphrases a single character, the substring match fails and the record is <strong>instantly discarded</strong>. Zero hallucinated claims enter your CSV.
      </div>
    </div>

    <!-- Takeaway Banner -->
    <div style="background: #ffffff; border: 1.5px solid #e8e6dc; border-radius: 16px; padding: 18px 24px; display: flex; align-items: center; gap: 18px;">
      <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(120,140,93,0.15); border: 1px solid #c7d8be; display: flex; align-items: center; justify-content: center; font-size: 24px; color: #788c5d; font-weight: 900; flex-shrink: 0;">
        ✓
      </div>
      <div>
        <div style="font-size: 21px; font-weight: 900; color: #141413;">
          Deterministic code replaces model trust
        </div>
        <div style="font-size: 18px; color: #57534e; margin-top: 3px; line-height: 1.35;">
          Python code verifies the quote against raw source text before writing any row to SQLite.
        </div>
      </div>
    </div>

    <!-- 3-Pillar Technical Mechanism Bar -->
    <div style="background: #ffffff; border: 1.5px solid #e8e6dc; border-radius: 16px; padding: 18px 24px; display: flex; justify-content: space-around; align-items: center; text-align: center;">
      <div>
        <div style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #788c5d; letter-spacing: 1.2px;">Exact Match</div>
        <div style="font-family: ui-monospace, monospace; font-size: 18px; font-weight: 800; color: #141413; margin-top: 3px;">quote in raw_text</div>
      </div>
      <div style="height: 32px; width: 1px; background: #e8e6dc;"></div>
      <div>
        <div style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #6a9bcc; letter-spacing: 1.2px;">Audit Trail</div>
        <div style="font-size: 19px; font-weight: 800; color: #141413; margin-top: 3px;">URL + Char Offset</div>
      </div>
      <div style="height: 32px; width: 1px; background: #e8e6dc;"></div>
      <div>
        <div style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #d97757; letter-spacing: 1.2px;">Failure Mode</div>
        <div style="font-size: 19px; font-weight: 800; color: #141413; margin-top: 3px;">Auto-Discarded</div>
      </div>
    </div>
  </div>

  <div class="footer" style="padding-top: 16px; margin-top: 0;">
    <div class="brand"><span>free-fleet</span> // character-exact verification</div>
    <div class="page" style="font-size: 16px; padding: 8px 18px;">05 / 05</div>
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
    print("Carousel export complete!")

if __name__ == "__main__":
    generate_carousel()
