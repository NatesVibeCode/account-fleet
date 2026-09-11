"""Generate a 4-slide high-converting LinkedIn carousel PDF (1080x1350, 4:5).

Slide 1: Cover — The Hook: 2,500 -> 25 in 25 min | $0.00 + 4 Bars + Sniper Badge
Slide 2: Layers 1-2: 418 batches (15m) -> 100 batches (4m) + SCRAPE_1/GATE_1 & SCRAPE_2/GATE_2
Slide 3: Layers 3-4 + Proof: 25 batches (2m) -> 12 batches (1m) + DROP 100 -> DROP 25 -> 25 Tier-1 + Quickstart Proof
Slide 4: Output: Table Mock (item_id | priority | primary_quote_text) + ~550 Batches / $0 + GitHub CTA
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
    padding: 72px 70px 60px 70px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: #faf9f5;
    /* warm paper texture — paper grain + ruled lines + edge vignette */
    background-image:
      radial-gradient(circle at 1px 1px, rgba(20,20,19,0.075) 1.2px, transparent 0),
      repeating-linear-gradient(90deg, transparent 0 48px, rgba(20,20,19,0.015) 48px 49px),
      radial-gradient(ellipse at 50% 0%, rgba(232,228,215,0.9) 0%, transparent 58%);
    background-size: 20px 20px, 49px 49px, 100% 440px;
    background-repeat: repeat, repeat, no-repeat;
    box-shadow: inset 0 0 0 1px #e8e6dc, inset 0 0 110px rgba(232,228,215,0.65), inset 0 1px 0 rgba(255,255,255,0.9);
    overflow: hidden;
  }
  .slide::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image: repeating-linear-gradient(0deg, transparent 0 26px, rgba(20,20,19,0.032) 26px 27px);
    pointer-events: none;
  }
  .slide::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 5px;
    background: #141413;
    pointer-events: none;
  }

  /* Remove AI neon glows — keep flat editorial */
  .glow-top-right, .glow-bottom-left { display: none; }

  /* Header Pills — Anthropic editorial, flat warm */
  .pill-row {
    display: block;
    margin-bottom: 20px;
  }
  .tag-pill {
    display: inline-block;
    background: #faf9f5;
    border: 1px solid #e8e6dc;
    padding: 8px 18px;
    border-radius: 9999px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #57534e;
  }
  .tag-pill .dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    background: #d97757;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: middle;
  }

  .tag-pill.purple {
    background: #faf9f5;
    border-color: #e8e6dc;
    color: #57534e;
  }
  .tag-pill.purple .dot { background: #6a9bcc; }

  .tag-pill.green {
    background: #faf9f5;
    border-color: #e8e6dc;
    color: #57534e;
  }
  .tag-pill.green .dot { background: #788c5d; }

  /* Hero Typography — warm paper */
  .hero-numbers {
    font-size: 88px;
    font-weight: 900;
    line-height: 1.05;
    letter-spacing: -2px;
    color: #141413;
    margin-bottom: 8px;
  }
  .hero-numbers .accent-cyan { color: #6a9bcc; }
  .hero-numbers .accent-green { color: #788c5d; }

  .sub-headline {
    font-size: 32px;
    font-weight: 700;
    color: #57534e;
    margin-bottom: 12px;
  }

  .code-sub {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 17px;
    color: #44403c;
    background: #ffffff;
    border: 1px solid #e8e6dc;
    padding: 12px 20px;
    border-radius: 10px;
    display: inline-block;
    margin-top: 8px;
  }
  .code-sub span.cyan {
    color: #d97757;
    font-weight: 700;
  }
  .code-sub span.file {
    color: #6a9bcc;
    font-weight: 600;
  }

  /* Funnel Bars on Cover */
  .bars-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin: 28px 0;
  }

  .bar-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .bar-meta {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 19px;
    font-weight: 600;
    color: #78716c;
  }
  .bar-meta .count {
    font-size: 27px;
    font-weight: 900;
    color: #141413;
  }
  .bar-meta .count.cyan { color: #6a9bcc; }
  .bar-meta .count.purple { color: #788c5d; }
  .bar-meta .count.amber { color: #d97757; }

  .bar-track {
    width: 100%;
    height: 48px;
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(20,20,19,0.05);
  }
  .bar-fill {
    display: block;
    height: 48px;
    line-height: 48px;
    border-radius: 8px;
    padding-left: 18px;
    font-size: 19px;
    font-weight: 800;
    letter-spacing: 0.6px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.35), inset 0 -1px 0 rgba(20,20,19,0.08);
  }
  .bar-fill.bar-1 {
    width: 100%;
    background: #141413;
    color: #faf9f5;
  }
  .bar-fill.bar-2 {
    width: 60%;
    background: #6a9bcc;
    color: #faf9f5;
  }
  .bar-fill.bar-3 {
    width: 38%;
    background: #788c5d;
    color: #faf9f5;
  }
  .bar-fill.bar-4 {
    width: 24%;
    background: #d97757;
    color: #faf9f5;
  }

  .sniper-badge-container {
    margin-top: 8px;
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-left: 6px solid #788c5d;
    border-radius: 14px;
    padding: 22px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 10px rgba(20,20,19,0.05), inset 0 1px 0 rgba(255,255,255,0.9);
  }
  .sniper-badge-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .sniper-badge-left .label {
    font-size: 13px;
    font-weight: 700;
    color: #78716c;
    letter-spacing: 1.4px;
    text-transform: uppercase;
  }
  .sniper-badge-left .title {
    font-size: 26px;
    font-weight: 800;
    color: #141413;
  }
  .sniper-badge-right {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }
  .sniper-badge-right .arrow {
    font-size: 36px;
    font-weight: 900;
    color: #788c5d;
  }
  .sniper-badge-right .val {
    font-size: 60px;
    font-weight: 900;
    color: #141413;
    letter-spacing: -1.5px;
  }
  .sniper-badge-right .unit {
    font-size: 18px;
    font-weight: 700;
    color: #78716c;
    text-transform: uppercase;
  }

  /* Cards for slides 2 & 3 — paper on paper, layered with letterpress */
  .flow-card {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 16px;
    padding: 30px 32px;
    display: flex;
    flex-direction: column;
    gap: 18px;
    box-shadow: 0 1px 2px rgba(20,20,19,0.04), 0 8px 24px rgba(20,20,19,0.06), inset 0 1px 0 rgba(255,255,255,0.9);
  }
  .card-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .card-title-group {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .step-num {
    width: 36px;
    height: 36px;
    border-radius: 9px;
    background: #141413;
    border: 1px solid #141413;
    color: #faf9f5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 16px;
  }
  .step-num.purple {
    background: #6a9bcc;
    border-color: #6a9bcc;
    color: #faf9f5;
  }
  .step-num.amber {
    background: #d97757;
    border-color: #d97757;
    color: #faf9f5;
  }
  .step-num.green {
    background: #788c5d;
    border-color: #788c5d;
    color: #faf9f5;
  }
  .card-title {
    font-size: 24px;
    font-weight: 800;
    color: #141413;
  }
  .card-badge {
    font-size: 13px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 8px;
    background: #f5f5f0;
    color: #78716c;
    border: 1px solid #e8e6dc;
  }

  .pipe-flow {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #faf9f5;
    border: 1px solid #e8e6dc;
    padding: 15px 20px;
    border-radius: 10px;
    font-size: 17px;
    font-weight: 600;
  }
  .pipe-node {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .pipe-node .node-label {
    font-size: 11px;
    color: #a8a29e;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
  }
  .pipe-node .node-val {
    font-size: 16px;
    font-weight: 700;
    color: #141413;
    font-family: ui-monospace, "SF Mono", monospace;
  }
  .flow-arrow {
    color: #b0aea5;
    font-size: 18px;
    font-weight: 700;
    margin: 0 4px;
  }

  .outcomes-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
  }
  .outcome-box {
    border-radius: 14px;
    padding: 18px 22px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .outcome-box.drop {
    background: #fdf2f2;
    border: 1px solid #e8c4c4;
  }
  .outcome-box.drop .o-tag {
    color: #9f1239;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .outcome-box.drop .o-val {
    color: #b91c1c;
    font-size: 26px;
    font-weight: 800;
  }
  .outcome-box.drop .o-desc {
    color: #78716c;
    font-size: 13px;
    font-weight: 500;
  }

  .outcome-box.survive {
    background: #f0fdf4;
    border: 1px solid #a7c5a8;
  }
  .outcome-box.survive .o-tag {
    color: #365314;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .outcome-box.survive .o-val {
    color: #14532d;
    font-size: 26px;
    font-weight: 800;
  }
  .outcome-box.survive .o-desc {
    color: #57534e;
    font-size: 13px;
    font-weight: 500;
  }

  .connector-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin: -2px 0;
    color: #a8a29e;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .connector-arrow .line {
    height: 1px;
    background: #e8e6dc;
    flex: 1;
  }

  /* Code box — editorial ink */
  .terminal-box {
    background: #1a1a18;
    border: 1px solid #2a2a28;
    border-radius: 12px;
    overflow: hidden;
  }
  .terminal-header {
    background: #141413;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #2a2a28;
  }
  .t-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
  }
  .t-red { background: #d97757; }
  .t-yellow { background: #e8c4a0; }
  .t-green { background: #788c5d; }
  .t-title {
    margin-left: 10px;
    font-size: 12px;
    color: #b0aea5;
    font-family: ui-monospace, "SF Mono", monospace;
  }
  .terminal-body {
    padding: 20px 22px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 18px;
    color: #e8e6dc;
  }
  .terminal-body .prompt {
    color: #b0aea5;
    font-weight: 600;
    user-select: none;
  }
  .terminal-body .cmd {
    color: #faf9f5;
    font-weight: 700;
  }
  .terminal-note {
    font-size: 13px;
    color: #a8a29e;
    margin-top: 8px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  /* Slide 4 Table Mock — white on warm, letterpress */
  .table-card {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(20,20,19,0.05), inset 0 1px 0 rgba(255,255,255,0.9);
  }
  .table-top-bar {
    background: #141413;
    padding: 14px 20px;
    border-bottom: 1px solid #2a2a28;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: ui-monospace, "SF Mono", monospace;
    font-size: 14px;
    color: #faf9f5;
  }
  table.mock-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    text-align: left;
  }
  table.mock-table th {
    background: #f5f5f0;
    padding: 12px 18px;
    color: #78716c;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 11px;
    border-bottom: 1px solid #e8e6dc;
  }
  table.mock-table td {
    padding: 16px 18px;
    border-bottom: 1px solid #f5f5f0;
    vertical-align: top;
    background: #faf9f5;
  }
  table.mock-table tr:last-child td {
    border-bottom: none;
  }
  .badge-high {
    background: #141413;
    border: 1px solid #141413;
    color: #faf9f5;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    letter-spacing: 1px;
    display: inline-block;
  }
  .item-id-code {
    font-family: ui-monospace, monospace;
    font-weight: 700;
    color: #1a1a18;
    font-size: 15px;
  }
  .quote-verbatim {
    color: #44403c;
    font-style: italic;
    line-height: 1.4;
  }
  .quote-verbatim mark {
    background: #e8e6dc;
    color: #141413;
    padding: 1px 4px;
    border-radius: 4px;
    font-weight: 600;
    border: 1px solid #d6d3cd;
  }

  /* Summary Metrics Banner — white tiles on warm */
  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 14px;
    margin: 20px 0;
  }
  .metric-tile {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    border-radius: 12px;
    padding: 16px 12px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(20,20,19,0.04), inset 0 1px 0 rgba(255,255,255,0.9);
  }
  .metric-tile .m-val {
    font-size: 30px;
    font-weight: 900;
    color: #141413;
  }
  .metric-tile .m-val.green { color: #788c5d; }
  .metric-tile .m-val.cyan { color: #6a9bcc; }
  .metric-tile .m-lbl {
    font-size: 11px;
    font-weight: 700;
    color: #78716c;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
  }

  /* CTA Card — ink */
  .cta-card {
    background: #141413;
    border: 1px solid #2a2a28;
    border-radius: 14px;
    padding: 22px 26px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .cta-left .cta-title {
    font-size: 22px;
    font-weight: 800;
    color: #faf9f5;
    margin-bottom: 4px;
  }
  .cta-left .cta-repo {
    font-family: ui-monospace, monospace;
    font-size: 16px;
    color: #b0aea5;
    font-weight: 500;
  }
  .cta-btn {
    background: #faf9f5;
    color: #141413;
    font-size: 14px;
    font-weight: 800;
    padding: 12px 22px;
    border-radius: 9px;
    text-transform: uppercase;
    letter-spacing: 1px;
    white-space: nowrap;
  }

  /* Footer — warm hairline */
  .slide-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #e8e6dc;
    padding-top: 20px;
    font-size: 13px;
    font-weight: 500;
    color: #a8a29e;
  }
  .slide-footer .f-brand {
    color: #78716c;
    letter-spacing: 1px;
  }
  .slide-footer .f-brand span {
    color: #141413;
    font-weight: 700;
  }
  .slide-footer .f-page {
    background: #ffffff;
    border: 1px solid #e8e6dc;
    padding: 5px 12px;
    border-radius: 6px;
    color: #57534e;
    font-family: ui-monospace, monospace;
    font-weight: 600;
  }
</style>
</head>
<body>

<!-- ======================================================================= -->
<!-- SLIDE 1: THE HOOK                                                       -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="glow-top-right"></div>
  <div class="glow-bottom-left"></div>

  <!-- Header -->
  <div>
    <div class="pill-row">
        <div class="tag-pill">
          <span class="dot"></span>Automated Research Suite
        </div>
      </div>
    <div class="hero-numbers">
      2,500 <span class="accent-cyan">→</span> 25
    </div>
    <div class="sub-headline">
      in 25 min <span style="color:#475569; margin: 0 4px;">|</span> <span class="accent-green">$0.00 API Spend</span>
    </div>
    <div>
      <div class="code-sub">
        Open source research — <span class="cyan">every row includes the source quote</span>
      </div>
    </div>
  </div>

  <!-- 4 Funnel Bars — example account research, not a promise -->
  <div class="bars-container">
    <!-- Bar 1: Universe -->
    <div class="bar-row">
      <div class="bar-meta">
        <span>Starting set • example</span>
        <span class="count">2,500</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill bar-1">2,500 input</div>
      </div>
    </div>

    <!-- Bar 2: ICP -->
    <div class="bar-row">
      <div class="bar-meta">
        <span>Layer 1: Firmographic check</span>
        <span class="count cyan">600</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill bar-2">600 remaining</div>
      </div>
    </div>

    <!-- Bar 3: Tech -->
    <div class="bar-row">
      <div class="bar-meta">
        <span>Layer 2: Tech stack notes</span>
        <span class="count purple">150</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill bar-3">150 remaining</div>
      </div>
    </div>

    <!-- Bar 4: Intent -->
    <div class="bar-row">
      <div class="bar-meta">
        <span>Layer 3: Hiring signals</span>
        <span class="count amber">50</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill bar-4">50 remaining</div>
      </div>
    </div>

    <!-- Final set -->
    <div class="sniper-badge-container">
      <div class="sniper-badge-left">
        <span class="label">Layer 4 • Founder notes</span>
        <span class="title">25 selected for review</span>
      </div>
      <div class="sniper-badge-right">
        <span class="arrow">→</span>
        <span class="val">25</span>
        <span class="unit">selected</span>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div class="slide-footer">
    <div class="f-brand"><span>free-fleet</span> // research suite for account research</div>
    <div class="f-page">01 / 05 →</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 2: LAYERS 1 & 2                                                   -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="glow-top-right"></div>

  <!-- Top -->
  <div>
    <div class="pill-row">
      <div class="tag-pill">
        <span class="dot"></span>Account Research • Layers 1 &amp; 2
      </div>
    </div>
    <div class="hero-numbers" style="font-size: 60px;">
      418 batches <span style="font-size: 38px; color: #78716c;">(15m)</span> <span class="accent-cyan">→</span> 100 batches <span style="font-size: 38px; color: #78716c;">(4m)</span>
    </div>
    <p style="font-size: 19px; color: #78716c; margin-top: 6px;">
      Research suite filters 94% of raw noise before deep enrichment — via Claude/Cursor or CLI.
    </p>
  </div>

  <!-- Cards -->
  <div style="display: flex; flex-direction: column; gap: 20px;">
    <!-- Layer 1 Card -->
    <div class="flow-card">
      <div class="card-header-row">
        <div class="card-title-group">
          <div class="step-num">1</div>
          <div class="card-title">Layer 1: Firmographic Triage</div>
        </div>
        <div class="card-badge">418 Batches • 15 Mins</div>
      </div>

      <div class="pipe-flow">
        <div class="pipe-node">
          <span class="node-label">Input Action</span>
          <span class="node-val">SCRAPE_1 (Homepage &amp; Pricing)</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="pipe-node">
          <span class="node-label">Evidence Check</span>
          <span class="node-val">GATE_1 (Fit Score &ge; 70%)</span>
        </div>
      </div>

      <div class="outcomes-row">
        <div class="outcome-box drop">
          <span class="o-tag">Filtered at Gate 1</span>
          <span class="o-val">1,900 filtered</span>
          <span class="o-desc">Not matching firmographic check</span>
        </div>
        <div class="outcome-box survive">
          <span class="o-tag">Remaining</span>
          <span class="o-val">600 kept</span>
          <span class="o-desc">Quote found on homepage/pricing</span>
        </div>
      </div>
    </div>

    <!-- Connector -->
    <div class="connector-arrow">
      <div class="line"></div>
      <span>600 passed to next layer — example</span>
      <div class="line"></div>
    </div>

    <!-- Layer 2 Card -->
    <div class="flow-card">
      <div class="card-header-row">
        <div class="card-title-group">
          <div class="step-num purple">2</div>
          <div class="card-title">Layer 2: Tech stack</div>
        </div>
        <div class="card-badge">100 Batches • 4 Mins</div>
      </div>

      <div class="pipe-flow">
        <div class="pipe-node">
          <span class="node-label">Input Action</span>
          <span class="node-val">SCRAPE_2 (Docs, APIs, Changelogs)</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="pipe-node">
          <span class="node-label">Evidence Check</span>
          <span class="node-val">GATE_2 (Pain Score &ge; 75%)</span>
        </div>
      </div>

      <div class="outcomes-row">
        <div class="outcome-box drop">
          <span class="o-tag">Filtered at Gate 2</span>
          <span class="o-val">450 filtered</span>
          <span class="o-desc">No relevant tech signal in docs</span>
        </div>
        <div class="outcome-box survive">
          <span class="o-tag">Remaining</span>
          <span class="o-val">150 kept</span>
          <span class="o-desc">Quote found in docs/changelog</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div class="slide-footer">
    <div class="f-brand"><span>free-fleet</span> // research suite • 2 drops + 2 survivors</div>
    <div class="f-page">02 / 05 →</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 3: LAYERS 3 & 4 + PROOF                                           -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="glow-top-right"></div>

  <!-- Top -->
  <div>
    <div class="pill-row">
      <div class="tag-pill purple">
        <span class="dot"></span>Account Research • Layers 3 &amp; 4
      </div>
    </div>
    <div class="hero-numbers" style="font-size: 60px;">
      25 batches <span style="font-size: 38px; color: #78716c;">(2m)</span> <span class="accent-cyan">→</span> 12 batches <span style="font-size: 38px; color: #78716c;">(1m)</span>
    </div>
    <p style="font-size: 19px; color: #78716c; margin-top: 6px;">
      Research suite isolates hiring budget &amp; founder bottleneck language — verbatim.
    </p>
  </div>

  <!-- Flow Content: 2 Cards + Proof Terminal -->
  <div style="display: flex; flex-direction: column; gap: 18px;">
    <!-- Layer 3 Card -->
    <div class="flow-card" style="padding: 24px 28px; gap: 14px;">
      <div class="card-header-row">
        <div class="card-title-group">
          <div class="step-num amber">3</div>
          <div class="card-title" style="font-size: 22px;">Layer 3: Hiring signals</div>
        </div>
        <div class="card-badge">25 Batches • 2 Mins</div>
      </div>

      <div class="pipe-flow" style="padding: 12px 18px;">
        <div class="pipe-node">
          <span class="node-label">Input Action</span>
          <span class="node-val" style="font-size: 16px;">SCRAPE_3 (Careers, Greenhouse, Lever)</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="pipe-node">
          <span class="node-label">Evidence Check</span>
          <span class="node-val" style="font-size: 16px;">GATE_3 (Open Reqs Matching Problem)</span>
        </div>
      </div>

      <div class="outcomes-row">
        <div class="outcome-box drop" style="padding: 14px 18px;">
          <span class="o-tag">Filtered at Gate 3</span>
          <span class="o-val" style="font-size: 24px;">100 filtered</span>
          <span class="o-desc">No matching hiring signal</span>
        </div>
        <div class="outcome-box survive" style="padding: 14px 18px;">
          <span class="o-tag">Remaining</span>
          <span class="o-val" style="font-size: 24px;">50 kept</span>
          <span class="o-desc">Quote found in job post</span>
        </div>
      </div>
    </div>

    <!-- Layer 4 Card -->
    <div class="flow-card" style="padding: 24px 28px; gap: 14px;">
      <div class="card-header-row">
        <div class="card-title-group">
          <div class="step-num green">4</div>
          <div class="card-title" style="font-size: 22px;">Layer 4: Founder notes</div>
        </div>
        <div class="card-badge">12 Batches • 1 Min</div>
      </div>

      <div class="pipe-flow" style="padding: 12px 18px;">
        <div class="pipe-node">
          <span class="node-label">Check</span>
          <span class="node-val" style="font-size: 16px;">Founder posts / podcasts</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="pipe-node">
          <span class="node-label">Keep if</span>
          <span class="node-val" style="font-size: 16px;">Quote describes bottleneck</span>
        </div>
      </div>

      <div class="outcomes-row">
        <div class="outcome-box drop" style="padding: 14px 18px;">
          <span class="o-tag">Filtered at Gate 4</span>
          <span class="o-val" style="font-size: 24px;">25 filtered</span>
          <span class="o-desc">No relevant founder quote</span>
        </div>
        <div class="outcome-box survive" style="padding: 14px 18px; background:#f0fdf4; border-color:#a7c5a8;">
          <span class="o-tag" style="color:#365314;">Remaining</span>
          <span class="o-val" style="font-size: 24px; color:#14532d;">25 kept</span>
          <span class="o-desc" style="color:#57534e;">For review — with quotes</span>
        </div>
      </div>
    </div>

    <!-- Small Code Block Proof -->
    <div class="terminal-box">
      <div class="terminal-header">
        <span class="t-dot t-red"></span>
        <span class="t-dot t-yellow"></span>
        <span class="t-dot t-green"></span>
        <span class="t-title">bash ~ live offline proof</span>
      </div>
      <div class="terminal-body">
        <span class="prompt">$</span> <span class="cmd">free-fleet quickstart --demo --run-id demo</span>
        <div class="terminal-note">
          ✔ Deterministic demo pipeline • 0 API keys required • Validates quotes &amp; schemas in &lt;1s
        </div>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div class="slide-footer">
    <div class="f-brand"><span>free-fleet</span> // research suite • DROP 100 → DROP 25 → 25 Tier-1</div>
    <div class="f-page">03 / 05 →</div>
  </div>
</div>


<!-- ======================================================================= -->
<!-- SLIDE 4: THE VERIFIED OUTPUT & CTA                                      -->
<!-- ======================================================================= -->
<div class="slide">
  <div class="glow-bottom-left"></div>

  <!-- Top -->
  <div>
    <div class="pill-row">
      <div class="tag-pill green">
        <span class="dot"></span>Output &amp; Proof Payload
      </div>
    </div>
    <div class="hero-numbers" style="font-size: 52px; margin-bottom: 6px;">
      Auto-reviewed<br/><span style="color:#788c5d;">against the source</span>
    </div>
    <p style="font-size: 19px; color: #57534e; margin-top: 4px;">
      If the model can’t point to the exact quote, the row doesn’t ship — we try the next lane.
    </p>
  </div>

  <!-- Table Mock -->
  <div class="table-card">
    <div class="table-top-bar">
      <span>$ free-fleet export demo --format csv</span>
      <span style="color: #4ADE80; font-weight: 700;">3 of 25 verified records</span>
    </div>
    <table class="mock-table">
      <thead>
        <tr>
          <th style="width: 22%;">item_id</th>
          <th style="width: 15%;">priority</th>
          <th style="width: 63%;">primary_quote_text</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="item-id-code">acme_cloud</span></td>
          <td><span class="badge-high">HIGH</span></td>
          <td><span class="quote-verbatim">"<mark>scaling vector search across multi-tenant clusters</mark> is our #1 bottleneck this quarter"</span></td>
        </tr>
        <tr>
          <td><span class="item-id-code">stripe_billing</span></td>
          <td><span class="badge-high">HIGH</span></td>
          <td><span class="quote-verbatim">"seeking Staff Engineer to <mark>lead migration off legacy v1 billing pipeline</mark>"</span></td>
        </tr>
        <tr>
          <td><span class="item-id-code">hyper_ai</span></td>
          <td><span class="badge-high">HIGH</span></td>
          <td><span class="quote-verbatim">"currently using legacy self-hosted Postgres but <mark>hitting latency limits at 50k QPS</mark>"</span></td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Metrics Banner -->
  <div class="metrics-grid">
    <div class="metric-tile">
      <div class="m-val">~550</div>
      <div class="m-lbl">Total Batches</div>
    </div>
    <div class="metric-tile">
      <div class="m-val green">$0</div>
      <div class="m-lbl">Total API Cost</div>
    </div>
    <div class="metric-tile">
      <div class="m-val cyan">25 min</div>
      <div class="m-lbl">Run Time</div>
    </div>
    <div class="metric-tile">
      <div class="m-val green">25</div>
      <div class="m-lbl">Tier-1 Accounts</div>
    </div>
  </div>

  <!-- GitHub CTA Card -->
  <div class="cta-card">
    <div class="cta-left">
      <div class="cta-title">Run the Fleet on Your Machine</div>
      <div class="cta-repo">github.com/NatesVibeCode/free-fleet</div>
    </div>
    <div class="cta-btn">Star on GitHub ★</div>
  </div>

  <!-- Footer -->
  <div class="slide-footer">
    <div class="f-brand"><span>free-fleet</span> // MIT • Research Suite for account research</div>
    <div class="f-page">04 / 05 →</div>
  </div>
</div>

<!-- ======================================================================= -->
<!-- SLIDE 5: EASY INSTALL + SAFETY                                          -->
<!-- ======================================================================= -->
<div class="slide">
  <!-- Top -->
  <div>
    <div class="pill-row">
      <div class="tag-pill green">
        <span class="dot"></span>Easy Install • Claude / Cursor / Local
      </div>
    </div>
    <div class="hero-numbers" style="font-size: 54px; margin-bottom: 8px;">
      One command. <span style="color:#788c5d;">No keys.</span>
    </div>
    <p style="font-size: 19px; color: #57534e; margin-top: 6px;">
      Anyone with Claude Desktop or Cursor can run the Research Suite — no CLI expertise needed.
    </p>
  </div>

  <!-- Install cards -->
  <div style="display:flex; flex-direction:column; gap:16px;">
    <div class="terminal-box">
      <div class="terminal-header">
        <span class="t-dot t-red"></span><span class="t-dot t-yellow"></span><span class="t-dot t-green"></span>
        <span class="t-title">bash — install to Claude/Cursor</span>
      </div>
      <div class="terminal-body" style="font-size:17px;">
        <div><span class="prompt">$</span> <span class="cmd">pip install free-fleet</span></div>
        <div style="margin-top:8px;"><span class="prompt">$</span> <span class="cmd">free-fleet mcp install --workspace-root "$PWD"</span></div>
        <div class="terminal-note" style="color:#a8a29e;">Auto-writes <span style="color:#e8e6dc; font-family:ui-monospace;">claude_desktop_config.json</span> / <span style="color:#e8e6dc; font-family:ui-monospace;">mcp.json</span> → restart app</div>
        <div style="margin-top:10px;"><span class="prompt">$</span> <span style="cmd">free-fleet mcp install --dry-run --json</span> <span style="color:#78716c;"># preview</span></div>
        <div><span class="prompt">$</span> <span class="cmd">free-fleet quickstart --demo --run-id demo</span> <span style="color:#78716c;"># 0 keys, <1s proof</span></div>
      </div>
    </div>

    <div class="flow-card" style="padding:20px 22px; gap:12px;">
      <div style="display:flex; align-items:center; gap:12px;">
        <div class="step-num green" style="width:32px; height:32px; font-size:14px;">✓</div>
        <div style="font-size:18px; font-weight:800; color:#141413;">Or chat in Claude/Cursor — no terminal</div>
      </div>
      <div style="background:#faf9f5; border:1px solid #e8e6dc; border-radius:10px; padding:14px 18px; font-size:15px; color:#57534e; line-height:1.5;">
        <span style="color:#78716c; font-weight:700;">In Claude:</span> “Use free-fleet to triage <span style="font-family:ui-monospace; background:#ffffff; border:1px solid #e8e6dc; padding:2px 6px; border-radius:6px;">accounts.csv</span> for hiring intent — free-only”<br/>
        <span style="color:#a8a29e; font-size:13px;">→ Agent calls <span style="font-family:ui-monospace;">free_fleet_run</span> → SQLite leases → verifies quotes → <span style="font-family:ui-monospace;">free_fleet_export</span> → CSV</span>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <div class="slide-footer">
    <div class="f-brand"><span>free-fleet</span> // pip install free-fleet • Research Suite</div>
    <div class="f-page">05 / 05</div>
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

    # Render PNG images of each slide: exact 1080x1350
    carousel_dir = Path("carousel")
    carousel_dir.mkdir(exist_ok=True)
    doc = fitz.open(str(out_pdf))
    print(f"Converting {len(doc)} PDF pages to PNG (exact 1080x1350)...")
    for i, page in enumerate(doc, start=1):
        # In CSS px (96 dpi) to PDF pt (72 dpi): 1080px = 810pt, 1350px = 1012.5pt
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
