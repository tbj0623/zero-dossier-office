#!/usr/bin/env python3
"""Minimal, site-independent test: can Playwright WebKit paint backdrop-filter at all?"""
from __future__ import annotations
import json
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from wk_common import BASE, RAW, SHOTS

HTML = """
<!doctype html><html><head><meta charset=utf-8><style>
html,body{margin:0;background:#000}
.wrap{position:relative;height:400px;background:#fff}
.grid{position:absolute;inset:0;background-image:
  repeating-linear-gradient(90deg,#000 0 20px,#fff 20px 40px),
  repeating-linear-gradient(0deg,transparent 0 20px,rgba(255,0,0,.9) 20px 40px);}
.panel{position:absolute;left:0;top:100px;width:400px;height:100px;background:rgb(10 20 30 / 0.15)}
.blur{-webkit-backdrop-filter:blur(20px) saturate(1.2);backdrop-filter:blur(20px) saturate(1.2)}
.sticky{position:sticky;top:0;height:64px;background:rgb(6 20 28 / .94)}
</style></head><body>
<div class="wrap">
  <div class="grid"></div>
  <div class="panel blur" id="p1"></div>
  <div class="panel" id="p2"></div>
</div>
<script>
window.__probe = () => ({
  p1bf: getComputedStyle(document.getElementById('p1')).backdropFilter,
  p1wbf: getComputedStyle(document.getElementById('p1')).webkitBackdropFilter,
  supports: CSS.supports('backdrop-filter','blur(20px)'),
});
</script>
</body></html>
"""

with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(viewport={"width": 800, "height": 500}, device_scale_factor=1)
    pg.set_content(HTML)
    pg.wait_for_timeout(600)
    print(json.dumps(pg.evaluate("() => window.__probe()"), indent=1))
    pg.screenshot(path=str(SHOTS / "wk-blur-minimal.png"))
    a = np.array(Image.open(SHOTS / "wk-blur-minimal.png").convert("RGB"))
    # p1 at y 100..200 x 0..400 ; p2 same region offset x 400..800  -> compare pattern
    p1 = a[110:190, 20:380]
    p2 = a[110:190, 420:780]
    print("p1 std", float(p1.std()), "p2 std", float(p2.std()))
    print("mean abs diff", float(np.abs(p1.astype(int)-p2.astype(int)).mean()))
    # hf
    def hf(x):
        g = x.astype(float).mean(axis=2)
        return float(np.abs(4*g[1:-1,1:-1]-g[:-2,1:-1]-g[2:,1:-1]-g[1:-1,:-2]-g[1:-1,2:]).mean())
    print("p1 hf", hf(p1), "p2 hf", hf(p2))
    b.close()
