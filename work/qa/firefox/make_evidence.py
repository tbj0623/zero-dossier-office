#!/usr/bin/env python3
"""Assemble the evidence images referenced by FIREFOX_REPORT.md."""
from __future__ import annotations

from PIL import Image, ImageDraw

from fx_common import SHOTS

# ---- 1. backdrop-filter evidence (Chromium blurs, Firefox does not) ----
ch = Image.open(SHOTS / "bfpref-chromium.png").convert("RGB").crop((20, 20, 220, 140))
fx = Image.open(SHOTS / "bfpref-firefox-default.png").convert("RGB").crop((20, 20, 220, 140))
canvas = Image.new("RGB", (200, 120 * 2 + 34), (18, 18, 18))
canvas.paste(ch, (0, 18))
canvas.paste(fx, (0, 120 + 34 - 18))
d = ImageDraw.Draw(canvas)
d.text((4, 3), "CHROMIUM: backdrop-filter blurs the checkerboard", fill=(255, 220, 120))
d.text((4, 120 + 20), "FIREFOX 153.0: pane is a flat tint, NO blur", fill=(255, 140, 120))
canvas.resize((canvas.width * 2, canvas.height * 2), Image.NEAREST).save(SHOTS / "evidence-backdrop-filter.png")
print("evidence-backdrop-filter.png")

# ---- 2. dialog open (Firefox) ----
im = Image.open(SHOTS / "fx-08-dialog-open.png").convert("RGB")
im.thumbnail((900, 900))
im.save(SHOTS / "evidence-dialog-firefox.png")
print("evidence-dialog-firefox.png", im.size)

# ---- 3. header comparison, real page ----
a = Image.open(SHOTS / "bfreal-chromium-on.png").convert("RGB")
b = Image.open(SHOTS / "bfreal-firefox-on.png").convert("RGB")
c = Image.new("RGB", (1440, 64 * 2 + 34), (18, 18, 18))
c.paste(a, (0, 18))
c.paste(b, (0, 64 + 34 - 18))
d = ImageDraw.Draw(c)
d.text((4, 3), "CHROMIUM header (real page, content under sticky bar)", fill=(255, 220, 120))
d.text((4, 64 + 20), "FIREFOX header (same scroll position)", fill=(255, 140, 120))
c.save(SHOTS / "evidence-header-realmode.png")
print("evidence-header-realmode.png", c.size)
