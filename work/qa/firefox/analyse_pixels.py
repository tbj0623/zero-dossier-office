#!/usr/bin/env python3
"""Characterise the Chromium-vs-Firefox pixel difference instead of just counting it.

For every scene we report, over the overlapping area:
  * mean / p95 / max per-channel absolute delta
  * share of pixels differing by >2, >16, >64
  * a 4x6 tile grid of "percent pixels differing" so the report can say WHERE
  * the same statistics restricted to a text-free strip (header bar) vs a
    text-dense strip (body copy) when those can be located
"""
from __future__ import annotations

import json

from PIL import Image, ImageChops

from fx_common import RAW, SHOTS

SCENES = ["home-1440", "cabinet-1440", "case-NA001-1440", "home-768",
          "case-NA004-768", "home-390", "case-NA004-390", "cabinet-390"]


def stats(a, b):
    diff = ImageChops.difference(a, b)
    g = diff.convert("L")
    hist = g.histogram()
    total = a.size[0] * a.size[1]
    cum = 0
    gt = {}
    for th in (2, 16, 64):
        gt[th] = round(100 * sum(hist[th + 1:]) / total, 4)
    # mean delta
    s = sum(i * h for i, h in enumerate(hist))
    return {
        "mean_delta": round(s / total, 4),
        "max_delta": max(i for i, h in enumerate(hist) if h),
        "pct_gt2": gt[2], "pct_gt16": gt[16], "pct_gt64": gt[64],
        "diff_bbox": diff.getbbox(),
    }


def tiles(a, b, rows=6, cols=4):
    w, h = a.size
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            box = (int(c * w / cols), int(r * h / rows), int((c + 1) * w / cols), int((r + 1) * h / rows))
            sub_a, sub_b = a.crop(box), b.crop(box)
            d = ImageChops.difference(sub_a, sub_b).convert("L").histogram()
            tot = (box[2] - box[0]) * (box[3] - box[1])
            row.append(round(100 * sum(d[3:]) / tot, 2))
        out.append(row)
    return out


def band(a, b, y0, y1):
    w, h = a.size
    box = (0, max(0, y0), w, min(h, y1))
    sub_a, sub_b = a.crop(box), b.crop(box)
    return stats(sub_a, sub_b)


result = {}
for name in SCENES:
    pa = SHOTS / f"chromium-{name}.png"
    pb = SHOTS / f"firefox-{name}.png"
    a = Image.open(pa).convert("RGB")
    b = Image.open(pb).convert("RGB")
    same = a.size == b.size
    entry = {"chromium_size": list(a.size), "firefox_size": list(b.size), "same_size": same}
    if same:
        entry.update(stats(a, b))
        entry["tiles_pct_gt2"] = tiles(a, b)
        # header strip 0..64 is the sticky bar (backdrop-filter), 64..140 hero eyebrow area
        entry["band_header_0_64"] = band(a, b, 0, 64)
        entry["band_64_300"] = band(a, b, 64, 300)
        entry["band_mid"] = band(a, b, a.size[1] // 3, 2 * a.size[1] // 3)
        # save an amplified diff for visual inspection
        d = ImageChops.difference(a, b)
        d.point(lambda v: min(255, v * 6)).save(str(SHOTS / f"diff-amplified-{name}.png"))
    else:
        h = min(a.size[1], b.size[1])
        entry.update(stats(a.crop((0, 0, a.size[0], h)), b.crop((0, 0, b.size[0], h))))
        entry["note"] = "heights differ; compared over the overlapping area"
    result[name] = entry
    print(name, json.dumps({k: v for k, v in entry.items() if k != "tiles_pct_gt2"}, ensure_ascii=False))

(RAW / "pixel-analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("-> raw/pixel-analysis.json")
