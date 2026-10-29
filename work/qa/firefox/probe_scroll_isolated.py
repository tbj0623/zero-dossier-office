#!/usr/bin/env python3
"""Isolate Firefox's scroll-padding-top + scrollIntoView behaviour.

A. SYNTHETIC (no site code): a 3000px page, html{scroll-padding-top:80px}, a
   target div at y=1500. Call scrollIntoView({block:'start'}) and measure the
   resulting target top. If Firefox ignores scroll-padding here too, the cause
   is the engine; if it honours it, the site is doing something else.
B. REAL SITE: quantify how much of the board is actually hidden behind the
   sticky header after the app's own scrollIntoView, and whether the first
   interactive control is covered.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, SHOTS, now_iso

SYNTH = """
<html><head><style>
  html { scroll-behavior: auto; scroll-padding-top: 80px; }
  body { margin: 0; }
  .spacer { height: 1500px; background: #eee; }
  #target { height: 400px; background: #39f; }
  .tail { height: 2000px; background: #ddd; }
  .fixed { position: fixed; top: 0; left: 0; right: 0; height: 64px; background: #000; z-index: 9; }
</style></head><body>
<div class="fixed"></div>
<div class="spacer"></div>
<div id="target">target</div>
<div class="tail"></div>
</body></html>
"""

SETTLE = """async () => {
  let last=-1, stable=0, t0=performance.now();
  while (performance.now()-t0 < 3000) {
    await new Promise(r=>requestAnimationFrame(r));
    if (Math.abs(window.scrollY-last)<0.01) stable++; else { stable=0; last=window.scrollY; }
    if (stable>=5) break;
  }
  return {scrollY: Math.round(window.scrollY), stableFrames: stable};
}"""

out = {"when": now_iso(), "synthetic": {}, "real_site": {}}

with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)

        # ---------- A. synthetic ----------
        ctx = b.new_context(viewport={"width": 1000, "height": 700})
        pg = ctx.new_page()
        pg.set_content(SYNTH)
        pg.wait_for_timeout(300)
        variants = {}
        for label, css in [("scroll-padding 80px", None),
                           ("scroll-padding 0", "html{scroll-padding-top:0 !important}")]:
            if css:
                pg.add_style_tag(content=css)
            pg.evaluate("() => window.scrollTo(0,0)")
            pg.evaluate(SETTLE)
            pg.evaluate("() => document.querySelector('#target').scrollIntoView({block:'start', behavior:'auto'})")
            st = pg.evaluate(SETTLE)
            m = pg.evaluate("""() => ({
                targetTop: Math.round(document.querySelector('#target').getBoundingClientRect().top),
                scrollPadding: getComputedStyle(document.documentElement).scrollPaddingTop,
            })""")
            variants[label] = {**st, **m}
        out["synthetic"][eng] = {"version": b.version, "variants": variants}
        ctx.close()

        # ---------- B. real site ----------
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/case/NA-001", wait_until="networkidle", timeout=60000)
        pg.wait_for_selector("#slots .slot")
        pg.wait_for_timeout(400)
        pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        pg.evaluate(SETTLE)
        pg.evaluate("() => document.querySelector('#slots').scrollIntoView({block:'start', behavior:'auto'})")
        st = pg.evaluate(SETTLE)
        pg.wait_for_timeout(300)
        m = pg.evaluate("""() => {
            const slots = document.querySelector('#slots').getBoundingClientRect();
            const hdr = document.querySelector('.site-header').getBoundingClientRect();
            const firstBtn = document.querySelector('#slots .slot[data-index="0"] [data-act="pick"]');
            const fb = firstBtn ? firstBtn.getBoundingClientRect() : null;
            const h2 = document.querySelector('#board-heading');
            const h2r = h2 ? h2.getBoundingClientRect() : null;
            // which element is actually painted at the first button's centre?
            const hit = fb ? document.elementFromPoint(fb.left + fb.width/2, fb.top + fb.height/2) : null;
            return {
                slotsTop: Math.round(slots.top * 100)/100,
                headerBottom: Math.round(hdr.bottom * 100)/100,
                hiddenPx: Math.round((hdr.bottom - slots.top) * 100)/100,
                hiddenShareOfBoardHeading: h2r ? Math.round((hdr.bottom - h2r.top) * 100)/100 : null,
                boardHeadingTop: h2r ? Math.round(h2r.top * 100)/100 : null,
                firstButtonTop: fb ? Math.round(fb.top * 100)/100 : null,
                firstButtonCoveredByHeader: fb ? fb.top < hdr.bottom - 1 : null,
                hitAtFirstButtonCentre: hit ? (hit.id || hit.className || hit.tagName) : null,
                scrollPadding: getComputedStyle(document.documentElement).scrollPaddingTop,
                mainScrollMargin: getComputedStyle(document.querySelector('main')).scrollMarginTop,
            };
        }""")
        out["real_site"][eng] = {"version": b.version, **st, **m}
        pg.screenshot(path=str(SHOTS / f"scrollintoview-{eng}.png"))
        ctx.close()
        b.close()

(RAW / "scroll-into-view-isolated.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print("=== synthetic scrollIntoView(block:start) ===")
for eng, d in out["synthetic"].items():
    print(f"  {eng} {d['version']}:")
    for k, v in d["variants"].items():
        print(f"     {k:22s} -> targetTop={v['targetTop']} scrollY={v['scrollY']} scrollPadding={v['scrollPadding']}")
print("\n=== real site #slots.scrollIntoView(block:start) ===")
for eng, d in out["real_site"].items():
    print(f"  {eng} {d['version']}: {json.dumps({k: v for k, v in d.items() if k != 'version'}, ensure_ascii=False)}")
print("-> raw/scroll-into-view-isolated.json")
