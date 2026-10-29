#!/usr/bin/env python3
"""Does HEADED Playwright WebKit paint backdrop-filter? (headless may skip the compositor path)"""
from __future__ import annotations
import json
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from wk_common import SHOTS

GRID = ("background-image:repeating-linear-gradient(90deg,#000 0 12px,#fff 12px 24px),"
        "repeating-linear-gradient(0deg,transparent 0 12px,rgba(255,0,0,.95) 12px 24px)")

HTML = f"""<!doctype html><html><head><meta charset=utf-8><style>
html,body{{margin:0;background:#000}}
.stage{{position:relative;height:1200px;{GRID}}}
.hdr{{position:absolute;top:0;left:0;width:600px;height:64px;z-index:50;
  background:rgb(6 20 28 / 0.10);
  -webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px);}}
</style></head><body><div class="stage"><div class="hdr" id="hdr"></div></div></body></html>"""

def hf(x):
    g = x.astype(float).mean(axis=2)
    return float(np.abs(4*g[1:-1,1:-1]-g[:-2,1:-1]-g[2:,1:-1]-g[1:-1,:-2]-g[1:-1,2:]).mean())

out = {}
for headless in (True, False):
    with sync_playwright() as p:
        b = p.webkit.launch(headless=headless)
        pg = b.new_page(viewport={"width": 800, "height": 600}, device_scale_factor=1)
        pg.set_content(HTML)
        pg.wait_for_timeout(800)
        name = "headless" if headless else "headed"
        path = SHOTS / f"wk-blur-{name}.png"
        pg.screenshot(path=str(path))
        a = np.array(Image.open(path).convert("RGB"))
        band = a[0:64, 0:600]
        out[name] = {"hf": round(hf(band), 3), "std": round(float(band.std()), 3),
                     "mean": round(float(band.mean()), 2),
                     "computed": pg.evaluate("() => getComputedStyle(document.getElementById('hdr')).backdropFilter"),
                     "gpu": pg.evaluate("() => { const c=document.createElement('canvas'); const gl=c.getContext('webgl2')||c.getContext('webgl'); if(!gl) return 'no webgl'; const d=gl.getExtension('WEBGL_debug_renderer_info'); return d? gl.getParameter(d.UNMASKED_RENDERER_WEBGL): 'n/a'; }")}
        pg.close()
        b.close()
print(json.dumps(out, indent=1))
