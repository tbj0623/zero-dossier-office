#!/usr/bin/env python3
"""Build side-by-side crop strips (Chromium | Firefox | amplified diff) so the
difference can be inspected visually rather than inferred."""
from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw

from fx_common import SHOTS

CROPS = [
    ("home-1440", "header", (0, 0, 1440, 70)),
    ("home-1440", "hero", (0, 64, 1440, 420)),
    ("home-1440", "herotext", (60, 200, 780, 420)),
    ("case-NA001-1440", "deskhead", (60, 80, 900, 240)),
    ("case-NA001-1440", "board", (700, 200, 1400, 640)),
    ("home-390", "mobile-top", (0, 0, 390, 420)),
]


def strip(name: str, label: str, box):
    a = Image.open(SHOTS / f"chromium-{name}.png").convert("RGB").crop(box)
    b = Image.open(SHOTS / f"firefox-{name}.png").convert("RGB").crop(box)
    d = ImageChops.difference(a, b).point(lambda v: min(255, v * 6))
    w, h = a.size
    pad = 22
    canvas = Image.new("RGB", (w, h * 3 + pad * 3), (20, 20, 20))
    canvas.paste(a, (0, pad))
    canvas.paste(b, (0, h + pad * 2))
    canvas.paste(d, (0, h * 2 + pad * 3))
    dr = ImageDraw.Draw(canvas)
    dr.text((4, 4), f"{label}  CHROMIUM (top) / FIREFOX (mid) / DIFF x6 (bottom)  {w}x{h}", fill=(255, 220, 120))
    out = SHOTS / f"cmp-{name}-{label}.png"
    canvas.save(out)
    print(out, canvas.size)


for name, label, box in CROPS:
    strip(name, label, box)
