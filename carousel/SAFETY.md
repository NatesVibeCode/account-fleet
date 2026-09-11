# Carousel Safety

This carousel PDF is **static images only** — no JavaScript, no embedded scripts, no external URLs.

- **Source:** Generated from `generate_carousel.py` (WeasyPrint + fitz, warm paper editorial, no AI gradients)
- **License:** MIT — local SQLite, no data leaves your machine (`free_fleet/store.py:66` WAL + `free_fleet/grounding.py:63` exact quote verification)
- **Verify before sharing:**

```bash
shasum -a 256 free-fleet-prospecting-carousel.pdf
# 50b3dc3e2ee049a5088f3c0df218f2c8e2dcec53a6fad293252bc085789cf6ca  free-fleet-prospecting-carousel.pdf

# VirusTotal (free, no account): https://www.virustotal.com/gui/home/upload → drag PDF → expect 0/90
```

- **Provenance:** `free-fleet doctor --json` + `github.com/NatesVibeCode/free-fleet` — source + MCP audit
- **Regenerate locally:** `python3 generate_carousel.py` (requires `weasyprint` + `pymupdf`)

If you want a pre-scanned link to share, upload the PDF once to VirusTotal and share the permalink (e.g., `https://www.virustotal.com/gui/file/<sha256>`).
