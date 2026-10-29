#!/usr/bin/env python3
"""Which condition kills backdrop-filter in WebKit? sticky vs absolute, overflow ancestors, isolation."""
from __future__ import annotations
import json
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from wk_common import RAW, SHOTS

GRID = ("background-image:repeating-linear-gradient(90deg,#000 0 12px,#fff 12px 24px),"
        "repeating-linear-gradient(0deg,transparent 0 12px,rgba(255,0,0,.95) 12px 24px)")

def page_html(case):
    body_style = "margin:0;background:#000;"
    if case.get("body_overflow"): body_style += "overflow-x:hidden;"
    sticky = "position:sticky;top:0;" if case["pos"] == "sticky" else "position:absolute;top:100px;left:0;"
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
html,body{{{body_style}}}
.spacer{{height:2000px;{GRID}}}
.hdr{{{sticky}width:600px;height:64px;z-index:50;
  background:rgb(6 20 28 / 0.15);
  -webkit-backdrop-filter:blur(20px) saturate(1.2);backdrop-filter:blur(20px) saturate(1.2);}}
.content{{height:2000px;{GRID}}}
</style></head><body>
<div class="hdr" id="hdr"></div>
<div class="content"></div>
</body></html>"""

def hf(x):
    g = x.astype(float).mean(axis=2)
    return float(np.abs(4*g[1:-1,1:-1]-g[:-2,1:-1]-g[2:,1:-1]-g[1:-1,:-2]-g[1:-1,2:]).mean())

cases = {
  "absolute_nooverflow": {"pos":"absolute","body_overflow":False},
  "sticky_nooverflow":   {"pos":"sticky","body_overflow":False},
  "absolute_overflowx":  {"pos":"absolute","body_overflow":True},
  "sticky_overflowx":    {"pos":"sticky","body_overflow":True},
}
out={}
with sync_playwright() as p:
    b = p.webkit.launch()
    for name,c in cases.items():
        pg = b.new_page(viewport={"width":800,"height":400}, device_scale_factor=1)
        pg.set_content(page_html(c)); pg.wait_for_timeout(300)
        # no scroll -> header at top for sticky
        pg.screenshot(path=str(SHOTS/f"wk-blurmatrix-{name}.png"))
        a=np.array(Image.open(SHOTS/f"wk-blurmatrix-{name}.png").convert("RGB"))
        top=int(pg.evaluate("() => document.getElementById('hdr').getBoundingClientRect().top"))
        band=a[top:top+64, 0:600]
        out[name]={"top":top,"hf":round(hf(band),3),"std":round(float(band.std()),3),
                   "computed": pg.evaluate("() => getComputedStyle(document.getElementById('hdr')).backdropFilter")}
        pg.close()
    b.close()
print(json.dumps(out, indent=1))
