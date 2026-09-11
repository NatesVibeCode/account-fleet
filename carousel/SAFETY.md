# Carousel Safety

PDF is static images only — no JS.

```bash
shasum -a 256 free-fleet-prospecting-carousel.pdf
# 00c8d89fca6f0a578777f67946e6d9c1a0ade83ad842004aea8c09b21d85bd91
# VirusTotal: https://www.virustotal.com/gui/home/upload → 0/90
```

Source: `generate_carousel.py` (warm paper, WeasyPrint+fitz). MIT, local SQLite, no data leaves machine.
