# Carousel Safety

This carousel PDF is **static images only** — no JavaScript, no embedded scripts, no external URLs.

- **Source:** Generated from `generate_carousel.py` (WeasyPrint + fitz, warm paper editorial, no AI gradients)
- **License:** MIT — local SQLite, no data leaves your machine (`free_fleet/store.py:66` WAL + `free_fleet/grounding.py:63` exact quote verification)
- **Verify before sharing:**

```bash
shasum -a 256 free-fleet-prospecting-carousel.pdf
# 59bbc0977b60b8c7c549895c9ee66b4cecf77ad729e8d3f2442e6acf281b5899  free-fleet-prospecting-carousel.pdf

# VirusTotal (free, no account): https://www.virustotal.com/gui/home/upload → drag PDF → expect 0/90
```

- **Provenance:** `free-fleet doctor --json` + `github.com/NatesVibeCode/free-fleet` — source + MCP audit
- **Regenerate locally:** `python3 generate_carousel.py` (requires `weasyprint` + `pymupdf`)

If you want a pre-scanned link to share, upload the PDF once to VirusTotal and share the permalink (e.g., `https://www.virustotal.com/gui/file/<sha256>`).
