# Carousel Safety

PDF is static images only — no JS.

```bash
shasum -a 256 free-fleet-prospecting-carousel.pdf
# cbe00faac11523281fc6b9d936f108f404845e1f5037c80a7240bc080338c866
# VirusTotal: https://www.virustotal.com/gui/home/upload → 0/90
```

Source: `generate_carousel.py` (warm paper, WeasyPrint+fitz). MIT, local SQLite, no data leaves machine.
