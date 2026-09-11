"""Generate 5-slide LinkedIn carousel — Automated Research Suite (locked narrative).

Slide 1: What it is — free, local, every row carries its source quote (account research is one example)
Slide 2: How it's built — architecture DAG (Slice → Pack → SQLite leases → Scorer → Quote check → Packet)
Slide 3: What verified means — QuoteRef(start,end) check you can run yourself
Slide 4: What it looks like — real CSV example (saas_intelligence)
Slide 5: Try it — mcp install one command + Claude chat, no sales funnel math
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
  @page { size: 1080px 1350px; margin: 0; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #faf9f5; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #141413; -webkit-font-smoothing: antialiased; }
  .slide { width: 1080px; height: 1350px; page-break-after: always; break-after: page; position: relative; padding: 72px 70px 60px 70px; display: flex; flex-direction: column; justify-content: space-between; background: #faf9f5; background-image: radial-gradient(circle at 1px 1px, rgba(20,20,19,0.075) 1.2px, transparent 0), repeating-linear-gradient(90deg, transparent 0 48px, rgba(20,20,19,0.015) 48px 49px), radial-gradient(ellipse at 50% 0%, rgba(232,228,215,0.9) 0%, transparent 58%); background-size: 20px 20px, 49px 49px, 100% 440px; background-repeat: repeat, repeat, no-repeat; box-shadow: inset 0 0 0 1px #e8e6dc, inset 0 0 110px rgba(232,228,215,0.65), inset 0 1px 0 rgba(255,255,255,0.9); overflow: hidden; }
  .slide::before { content: ""; position: absolute; inset: 0; background-image: repeating-linear-gradient(0deg, transparent 0 26px, rgba(20,20,19,0.032) 26px 27px); pointer-events: none; }
  .slide::after { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 5px; background: #141413; pointer-events: none; }
  .pill-row { display: block; margin-bottom: 20px; }
  .tag-pill { display: inline-block; background: #ffffff; border: 1px solid #e8e6dc; padding: 8px 18px; border-radius: 9999px; font-size: 13px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #57534e; }
  .tag-pill .dot { display: inline-block; width: 7px; height: 7px; background: #d97757; border-radius: 50%; margin-right: 8px; vertical-align: middle; }
  .tag-pill.purple { background: #ffffff; border-color: #e8e6dc; color: #57534e; } .tag-pill.purple .dot { background: #6a9bcc; }
  .tag-pill.green { background: #ffffff; border-color: #e8e6dc; color: #57534e; } .tag-pill.green .dot { background: #788c5d; }
  .hero { font-size: 72px; font-weight: 900; line-height: 0.95; letter-spacing: -2px; color: #141413; margin-bottom: 10px; }
  .hero .accent { color: #6a9bcc; }
  .hero-small { font-size: 54px; font-weight: 900; line-height: 0.95; letter-spacing: -1.5px; color: #141413; margin-bottom: 10px; }
  .sub { font-size: 20px; font-weight: 600; color: #57534e; line-height: 1.4; margin-top: 6px; }
  .sub-light { font-size: 17px; color: #78716c; margin-top: 8px; line-height: 1.5; }
  .code-inline { font-family: ui-monospace, "SF Mono", monospace; background: #ffffff; border: 1px solid #e8e6dc; padding: 2px 8px; border-radius: 6px; font-size: 14px; }
  .card { background: #ffffff; border: 1px solid #e8e6dc; border-radius: 16px; padding: 28px 30px; display: flex; flex-direction: column; gap: 16px; box-shadow: 0 1px 2px rgba(20,20,19,0.04), 0 8px 24px rgba(20,20,19,0.06), inset 0 1px 0 rgba(255,255,255,0.9); }
  .terminal-box { background: #1a1a18; border: 1px solid #2a2a28; border-radius: 12px; overflow: hidden; }
  .terminal-header { background: #141413; padding: 10px 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #2a2a28; }
  .t-dot { width: 9px; height: 9px; border-radius: 50%; } .t-red { background: #d97757; } .t-yellow { background: #e8c4a0; } .t-green { background: #788c5d; }
  .t-title { margin-left: 10px; font-size: 12px; color: #b0aea5; font-family: ui-monospace, monospace; }
  .terminal-body { padding: 18px 20px; font-family: ui-monospace, monospace; font-size: 15px; color: #e8e6dc; line-height: 1.6; }
  .prompt { color: #b0aea5; } .cmd { color: #faf9f5; font-weight: 700; }
  .dag { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center; background: #faf9f5; border: 1px solid #e8e6dc; border-radius: 12px; padding: 18px 16px; }
  .dag-node { background: #ffffff; border: 1px solid #e8e6dc; border-radius: 10px; padding: 12px 14px; text-align: center; min-width: 110px; }
  .dag-node .n-label { font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #a8a29e; }
  .dag-node .n-val { font-size: 13px; font-weight: 700; color: #141413; margin-top: 3px; font-family: ui-monospace, monospace; }
  .dag-arrow { color: #b0aea5; font-weight: 800; }
  .quote-card { background: #faf9f5; border: 1px solid #e8e6dc; border-radius: 10px; padding: 16px 18px; font-family: ui-monospace, monospace; font-size: 13px; color: #44403c; line-height: 1.5; }
  .table-card { background: #ffffff; border: 1px solid #e8e6dc; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 12px rgba(20,20,19,0.05), inset 0 1px 0 rgba(255,255,255,0.9); }
  .table-top-bar { background: #141413; padding: 14px 20px; border-bottom: 1px solid #2a2a28; display: flex; justify-content: space-between; align-items: center; font-family: ui-monospace, monospace; font-size: 13px; color: #faf9f5; }
  table.mock-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
  table.mock-table th { background: #f5f5f0; padding: 10px 16px; color: #78716c; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; font-size: 10px; border-bottom: 1px solid #e8e6dc; }
  table.mock-table td { padding: 14px 16px; border-bottom: 1px solid #f5f5f0; vertical-align: top; background: #ffffff; }
  .badge { background: #141413; border: 1px solid #141413; color: #faf9f5; font-weight: 700; padding: 3px 8px; border-radius: 6px; font-size: 10px; letter-spacing: 1px; display: inline-block; }
  .mark { background: #e8e6dc; color: #141413; padding: 1px 4px; border-radius: 4px; font-weight: 600; border: 1px solid #d6d3cd; }
  .footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e8e6dc; padding-top: 18px; font-size: 12px; font-weight: 500; color: #a8a29e; }
  .footer .brand { color: #78716c; } .footer .brand span { color: #141413; font-weight: 700; }
  .footer .page { background: #ffffff; border: 1px solid #e8e6dc; padding: 4px 10px; border-radius: 6px; color: #57534e; font-family: ui-monospace, monospace; font-weight: 600; }
</style>
</head>
<body>

<!-- SLIDE 1: WHAT IT IS -->
<div class="slide">
  <div>
    <div class="pill-row"><div class="tag-pill"><span class="dot"></span>Automated Research Suite</div></div>
    <div class="hero">Every row<br/>carries its<br/><span class="accent">source.</span></div>
    <div class="sub">Free, local, open source. CSV/PDF/HTML in → table out where every row includes the exact quote it came from.</div>
    <div class="sub-light">Account research is one example. Bring any <span class="code-inline">TaskSpec</span> — SaaS notes, CVE triage, docs.</div>
  </div>
  <div class="card">
    <div style="font-size:13px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#6a9bcc;">Try the example in 30s — no keys</div>
    <div class="terminal-box" style="margin-top:4px;">
      <div class="terminal-header"><span class="t-dot t-red"></span><span class="t-dot t-yellow"></span><span class="t-dot t-green"></span><span class="t-title">bash</span></div>
      <div class="terminal-body"><span class="prompt">$</span> <span class="cmd">free-fleet quickstart --demo --run-id demo</span><br/><span style="color:#a8a29e;">→ writes runs/demo/clean_packet.{json,csv} via demo/fake</span></div>
    </div>
    <div style="font-size:13px; color:#78716c; margin-top:6px;">Local SQLite at <span class="code-inline">./free-fleet.db</span> • MIT • No data leaves your machine</div>
  </div>
  <div class="footer"><div class="brand"><span>free-fleet</span> // open source research suite</div><div class="page">01 / 05</div></div>
</div>

<!-- SLIDE 2: HOW IT'S BUILT -->
<div class="slide">
  <div>
    <div class="pill-row"><div class="tag-pill purple"><span class="dot"></span>How it’s built</div></div>
    <div class="hero-small">Slice → Pack<br/>→ Lease → Score<br/>→ Check → Packet</div>
    <div class="sub">Deterministic control plane — not an agent loop.</div>
  </div>
  <div class="dag">
    <div class="dag-node"><div class="n-label">Input</div><div class="n-val">Slice</div><div style="font-size:10px; color:#a8a29e;">slicer.py</div></div><div class="dag-arrow">→</div>
    <div class="dag-node"><div class="n-label">Pack</div><div class="n-val">Batch</div><div style="font-size:10px; color:#a8a29e;">packer.py</div></div><div class="dag-arrow">→</div>
    <div class="dag-node"><div class="n-label">Queue</div><div class="n-val">SQLite WAL</div><div style="font-size:10px; color:#a8a29e;">store.py:263</div></div><div class="dag-arrow">→</div>
    <div class="dag-node"><div class="n-label">Rank</div><div class="n-val">Bayesian</div><div style="font-size:10px; color:#a8a29e;">scoring.py</div></div><div class="dag-arrow">→</div>
    <div class="dag-node"><div class="n-label">Check</div><div class="n-val">Quote + Schema</div><div style="font-size:10px; color:#a8a29e;">grounding.py:63</div></div><div class="dag-arrow">→</div>
    <div class="dag-node" style="border-color:#788c5d;"><div class="n-label">Output</div><div class="n-val">Packet v2</div><div style="font-size:10px; color:#78716c;">models.py:294</div></div>
  </div>
  <div class="card" style="padding:18px 20px;">
    <div style="font-size:13px; font-weight:700; color:#141413;">Resumable • Auditable • Concurrent</div>
    <div style="font-size:13px; color:#57534e; line-height:1.5;"><span class="code-inline">BEGIN IMMEDIATE</span> leases • <span class="code-inline">inference_attempts</span> ledger • stale leases recovered • <span class="code-inline">free_fleet_v2</span> packet with digest</div>
  </div>
  <div class="footer"><div class="brand"><span>free-fleet</span> // architecture.mmd</div><div class="page">02 / 05</div></div>
</div>

<!-- SLIDE 3: WHAT VERIFIED MEANS -->
<div class="slide">
  <div>
    <div class="pill-row"><div class="tag-pill green"><span class="dot"></span>What “verified” means</div></div>
    <div class="hero-small">Quote must match<br/>the source <span style="color:#788c5d;">exactly.</span></div>
    <div class="sub">You can check it yourself — no trust required.</div>
  </div>
  <div class="card">
    <div style="font-size:12px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#6a9bcc;">QuoteRef — always stored with offsets</div>
    <div class="quote-card">{ slice_id: "full", start: 22, end: 75, text: "real-time latency monitoring for cloud microservices." }</div>
    <div style="background:#1a1a18; color:#e8e6dc; font-family:ui-monospace,monospace; font-size:12px; padding:14px 16px; border-radius:10px; line-height:1.6;">slice_text[start:end] == text<br/>// if not, <span style="color:#d97757;">grounding_failed</span> → rotate lane, no commit to SQLite<br/>// offsets optional if text occurs once, required if ambiguous</div>
    <div style="font-size:12px; color:#78716c; border-left:3px solid #e8e6dc; padding-left:12px; margin-top:4px;">Closed schema <span class="code-inline">additionalProperties: false</span> — model can’t add fields or markdown.</div>
  </div>
  <div class="footer"><div class="brand"><span>free-fleet</span> // grounding.py • models.py</div><div class="page">03 / 05</div></div>
</div>

<!-- SLIDE 4: WHAT IT LOOKS LIKE -->
<div class="slide">
  <div>
    <div class="pill-row"><div class="tag-pill green"><span class="dot"></span>What it looks like — example</div></div>
    <div class="hero-small">CSV in → CSV out<br/><span style="color:#6a9bcc;">with quotes.</span></div>
    <div class="sub">Real output from <span class="code-inline">examples/saas_intelligence</span> — account research example.</div>
  </div>
  <div class="table-card">
    <div class="table-top-bar"><span>$ free-fleet export demo --format csv</span><span style="color:#a7c5a8; font-weight:700;">3 rows, each with quote</span></div>
    <table class="mock-table">
      <thead><tr><th style="width:20%;">item_id</th><th style="width:18%;">pricing_type</th><th style="width:62%;">primary_quote_text</th></tr></thead>
      <tbody>
        <tr><td><span style="font-family:ui-monospace; font-weight:700;">stripe</span></td><td><span class="badge">usage_based</span></td><td style="font-style:italic; color:#44403c;">"<span class="mark">2.9% + 30¢ per successful card charge</span>"</td></tr>
        <tr><td><span style="font-family:ui-monospace; font-weight:700;">resend</span></td><td><span class="badge">free_tier</span></td><td style="font-style:italic; color:#44403c;">"<span class="mark">First 3,000 emails per month are completely free</span>"</td></tr>
        <tr><td><span style="font-family:ui-monospace; font-weight:700;">pinecone</span></td><td><span class="badge">free_tier</span></td><td style="font-style:italic; color:#44403c;">"<span class="mark">1 free index with 2GB storage</span>"</td></tr>
      </tbody>
    </table>
  </div>
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:14px;">
    <div style="background:#ffffff; border:1px solid #e8e6dc; border-radius:10px; padding:14px 16px; text-align:center;"><div style="font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#78716c;">Packet</div><div style="font-size:13px; font-family:ui-monospace; color:#141413; margin-top:4px;">free_fleet_v2 + digest</div></div>
    <div style="background:#ffffff; border:1px solid #e8e6dc; border-radius:10px; padding:14px 16px; text-align:center;"><div style="font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#78716c;">Audit</div><div style="font-size:13px; font-family:ui-monospace; color:#141413; margin-top:4px;">inference_attempts ledger</div></div>
  </div>
  <div class="footer"><div class="brand"><span>free-fleet</span> // every row auditable</div><div class="page">04 / 05</div></div>
</div>

<!-- SLIDE 5: TRY IT -->
<div class="slide">
  <div>
    <div class="pill-row"><div class="tag-pill"><span class="dot"></span>Try it — free, local</div></div>
    <div class="hero-small">One command<br/>in Claude.</div>
    <div class="sub">For technical builders and the GTM folks they support — no sales funnel, just a suite.</div>
  </div>
  <div style="display:flex; flex-direction:column; gap:14px;">
    <div class="terminal-box">
      <div class="terminal-header"><span class="t-dot t-red"></span><span class="t-dot t-yellow"></span><span class="t-dot t-green"></span><span class="t-title">bash — Claude & Cursor</span></div>
      <div class="terminal-body"><div><span class="prompt">$</span> <span class="cmd">pip install free-fleet</span></div><div style="margin-top:6px;"><span class="prompt">$</span> <span class="cmd">free-fleet mcp install --workspace-root "$PWD"</span></div><div style="color:#a8a29e; font-size:12px; margin-top:6px;">writes claude_desktop_config.json / mcp.json → restart app</div><div style="margin-top:8px;"><span class="prompt">$</span> <span class="cmd">free-fleet quickstart --demo</span> <span style="color:#78716c;"># no keys, <1s</span></div></div>
    </div>
    <div class="card" style="padding:16px 18px;">
      <div style="font-size:13px; font-weight:700; color:#141413;">In Claude/Cursor — chat, don’t configure</div>
      <div style="background:#faf9f5; border:1px solid #e8e6dc; border-radius:8px; padding:12px 14px; font-size:13px; color:#57534e; margin-top:8px;">“Use free-fleet to triage <span style="font-family:ui-monospace; background:#ffffff; border:1px solid #e8e6dc; padding:2px 6px; border-radius:6px;">accounts.csv</span> for pricing — free-only”</div>
      <div style="font-size:11px; color:#a8a29e; margin-top:6px;">→ calls free_fleet_run → SQLite leases → checks quote+schema → exports CSV</div>
    </div>
  </div>
  <div class="footer"><div class="brand"><span>free-fleet</span> // MIT • github.com/NatesVibeCode/free-fleet</div><div class="page">05 / 05</div></div>
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
