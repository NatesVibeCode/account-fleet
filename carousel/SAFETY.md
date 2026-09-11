# Carousel Safety

PDF is static images only — no JS.

```bash
shasum -a 256 free-fleet-prospecting-carousel.pdf
# c7a0a43bc88b7b4b5319616a40408fd7a6a5ad621530660b62b30c67ef5016f5
# VirusTotal: https://www.virustotal.com/gui/home/upload → 0/90
```

Source: `generate_carousel.py` (warm paper, WeasyPrint+fitz). MIT, local SQLite, no data leaves machine.
