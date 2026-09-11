# Carousel Safety

PDF is static images only — no JS.

```bash
shasum -a 256 free-fleet-prospecting-carousel.pdf
# 0bfc3c60caf43ed07219562e32372a873730a690b7b062cbace6d24655f33196
# VirusTotal: https://www.virustotal.com/gui/home/upload → 0/90
```

Source: `generate_carousel.py` (warm paper, WeasyPrint+fitz). MIT, local SQLite, no data leaves machine.
