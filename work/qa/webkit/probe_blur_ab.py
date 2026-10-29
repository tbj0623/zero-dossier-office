#!/usr/bin/env python3
"""Clean A/B: identical element, identical position, only backdrop-filter toggled."""
from __future__ import annotations
import json
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from wk_common import SHOTS

GRID = ("background-image:repeating-linear-gradient(90deg,#000 0 12px,#fff 12px 24px),"
        "repeating-linear-gradient(0deg,transparent 0 12px,rgba(255,0,0,.95) 12px 24px)")

def html(pos, blur):
    if pos == "sticky":
        style = "position:sticky;top:0;"
    elif pos == "absolute":
        style = "position:absolute;top:0;left:0;"
    elif pos == "fixed":
        style = "position:fixed;top:0;left:0;"
    else:
        style = "position:relative;"
    bf = ("-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px);" if blur else "")
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
html,body{{margin:0;background:#000;overflow-x:hidden}}
.stage{{position:relative;height:1200px;{GRID}}}
.hdr{{{style}width:600px;height:64px;z-index:50;background:rgb(6 20 28 / 0.10);{bf}}}
</style></head><body><div class="stage"><div class="hdr" id="hdr"></div></div></body></html>"""

def hf(x):
    g = x.astype(float).mean(axis=2)
    return float(np.abs(4*g[1:-1,1:-1]-g[:-2,1:-1]-g[2:,1:-1]-g[1:-1,:-2]-g[1:-1,2:]).mean())

out = {}
with sync_playwright() as p:
    b = p.webkit.launch()
    for pos in ("absolute", "sticky", "fixed"):
        for blur in (True, False):
            name = f"{pos}_{'blur' if blur else 'noblur'}"
            pg = b.new_page(viewport={"width": 800, "height": 600}, device_scale_factor=1)
            pg.set_content(html(pos, blur))
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(SHOTS / f"wk-ab-{name}.png"))
            a = np.array(Image.open(SHOTS / f"wk-ab-{name}.png").convert("RGB"))
            r = pg.evaluate("() => { const x = document.getElementById('hdr').getBoundingClientRect(); return [Math.round(x.left), Math.round(x.top), Math.round(x.width), Math.round(x.height)]; }")
            band = a[r[1]:r[1]+r[3], r[0]:r[0]+r[2]]
            out[name] = {"rect": r, "hf": round(hf(band), 3), "std": round(float(band.std()), 3)}
            pg.close()
    b.close()

print(json.dumps(out, indent=1))
for pos in ("absolute", "sticky", "fixed"):
    fr = out[f"{pos}_blur"]["hf"] / max(out[f"{pos}_noblur"]["hf"], 1e-9)
    print(f"{pos:9s} blur_hf={out[f'{pos}_blur']['hf']:8.3f}  noblur_hf={out[f'{pos}_noblur']['hf']:8.3f}  ratio={fr:.3f}")
