#!/usr/bin/env python3
"""Does `text-wrap: balance` change the hero heading's actual line breaking?

The h1 is `<span>这些记录，</span><span class=accent>不应该同时成立。</span>` and
`.accent{display:block}` — i.e. the "balance" would have to re-break inside each
block-level span. Element rects are inconclusive (Chromium reports 3 rects,
Firefox 2 for the same element height), so instead we measure the INK: the
horizontal extent of non-background pixels on each text row of both the h1 and
its accent line. Same ink extent + same height = same rendering.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, SHOTS, now_iso

out = {"when": now_iso(), "base": LIVE_BASE, "engines": {}}

with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        e = {"version": b.version, "views": {}}
        for name, w, h in (("w390", 390, 844), ("w768", 768, 1024), ("w1440", 1440, 900)):
            ctx = b.new_context(viewport={"width": w, "height": h}, locale="zh-CN", device_scale_factor=1)
            pg = ctx.new_page()
            pg.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(700)
            box = pg.evaluate("""() => {
                const h1 = document.querySelector('.hero h1');
                const r = h1.getBoundingClientRect();
                return {x: Math.round(r.x), y: Math.round(r.y),
                        w: Math.round(r.width), h: Math.round(r.height),
                        textWrap: getComputedStyle(h1).textWrap,
                        fontSize: getComputedStyle(h1).fontSize};
            }""")
            path = SHOTS / f"h1-{eng}-{name}.png"
            pg.screenshot(path=str(path), clip={"x": box["x"], "y": box["y"],
                                                "width": max(1, box["w"]), "height": max(1, box["h"])})
            # ink extent per text row
            im = Image.open(path).convert("L")
            a = np.asarray(im, dtype=np.float64)
            bg = np.median(a)
            ink = np.abs(a - bg) > 40
            rows = ink.sum(axis=1)
            text_rows = np.where(rows > 2)[0]
            lines = []
            if len(text_rows):
                start = text_rows[0]
                prev = text_rows[0]
                for r in text_rows[1:]:
                    if r - prev > 3:
                        lines.append((int(start), int(prev)))
                        start = r
                    prev = r
                lines.append((int(start), int(prev)))
            line_extents = []
            for (y0, y1) in lines:
                cols = np.where(ink[y0:y1 + 1].any(axis=0))[0]
                line_extents.append({"y": [int(y0), int(y1)],
                                     "x0": int(cols[0]) if len(cols) else None,
                                     "x1": int(cols[-1]) if len(cols) else None,
                                     "ink_width": int(cols[-1] - cols[0] + 1) if len(cols) else 0})
            e["views"][name] = {"box": box, "ink_lines": line_extents,
                                "ink_line_count": len(line_extents),
                                "shot": str(path)}
            ctx.close()
        b.close()
        out["engines"][eng] = e
        print(eng, "done")

(RAW / "h1-ink.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

for view in ("w390", "w768", "w1440"):
    print("=" * 60)
    print(view)
    for eng in ("chromium", "firefox"):
        v = out["engines"][eng]["views"][view]
        print(f"  {eng:9s} box={v['box']['w']}x{v['box']['h']} wrap={v['box']['textWrap']} "
              f"ink_lines={v['ink_line_count']} widths={[l['ink_width'] for l in v['ink_lines']]}")
print("-> raw/h1-ink.json")
