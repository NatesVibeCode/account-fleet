# Carousel Safety

PDF is static images only — no JS.

```bash
shasum -a 256 free-fleet-prospecting-carousel.pdf
# 643a2996628a2115659fc2c3c2e89a059649eb3ad94658d531e66f9b0e410832
# VirusTotal: https://www.virustotal.com/gui/home/upload → 0/90
```

Source: `generate_carousel.py` (warm paper, WeasyPrint+fitz). MIT, local SQLite, no data leaves machine.
