#!/usr/bin/env python3
"""Sticky backdrop-filter: does it survive position:sticky at all, and does page scrolling matter?"""
from __future__ import annotations
import json
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from wk_common import SHOTS

GRID = ("background-image:repeating-linear-gradient(90deg,#000 0 12px,#fff 12px 24px),"
        "repeating-linear-gradient(0deg,transparent 0 12px,rgba(255,0,0,.95) 12px 24px)")

def html(pos, blur, extra=""):
    style = "position:sticky;top:0;" if pos=="sticky" else "position:fixed;top:0;left:0;"
    bf = ("-webkit-backdrop-filter:blur(20px) saturate(1.2);backdrop-filter:blur(20px) saturate(1.2);" if blur else "")
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
html{{margin:0;background:#000}}{extra}
body{{margin:0;background:#000}}
.hdr{{{style}width:600px;height:64px;z-index:50;background:rgb(6 20 28 / 0.15);{bf}}}
.content{{height:3000px;{GRID}}}
</style></head><body>
<div class="hdr" id="hdr"></div>
<div class="content"></div>
</body></html>"""

def hf(x):
    g = x.astype(float).mean(axis=2)
    return float(np.abs(4*g[1:-1,1:-1]-g[:-2,1:-1]-g[2:,1:-1]-g[1:-1,:-2]-g[1:-1,2:]).mean())

out={}
with sync_playwright() as p:
    b=p.webkit.launch()
    variants=[("sticky",True,""),("sticky",False,""),("fixed",True,""),("fixed",False,""),
              ("sticky",True,"body{overflow-x:hidden}"),("absolute",True,"")]
    for pos,blur,extra in variants:
        if pos=="absolute":
            continue
        name=f"{pos}_{'blur' if blur else 'noblur'}{'_ovx' if 'overflow' in extra else ''}"
        pg=b.new_page(viewport={"width":800,"height":400}, device_scale_factor=1)
        pg.set_content(html(pos,blur,extra)); pg.wait_for_timeout(250)
        pg.evaluate("() => window.scrollTo(0, 500)")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(SHOTS/f"wk-bm3-{name}.png"))
        a=np.array(Image.open(SHOTS/f"wk-bm3-{name}.png").convert("RGB"))
        top=int(pg.evaluate("() => Math.round(document.getElementById('hdr').getBoundingClientRect().top)"))
        band=a[max(top,0):max(top,0)+64, 0:600]
        out[name]={"top":top,"hf":round(hf(band),3),"std":round(float(band.std()),3),"mean":round(float(band.mean()),2)}
        pg.close()
    b.close()
print(json.dumps(out, indent=1))
for pos in ("sticky","fixed"):
    print(pos, "blur hf", out[f"{pos}_blur"]["hf"], "noblur hf", out[f"{pos}_noblur"]["hf"])
