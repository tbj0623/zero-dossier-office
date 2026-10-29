#!/usr/bin/env python3
"""Do the app's OWN scrollIntoView calls land correctly in Firefox?

  1. verdict: renderVerdict() -> #case-root.scrollIntoView({block:'start'})
     Is #verdict-title visible below the 64px sticky header?
  2. hint: revealHint() -> last hint card .scrollIntoView({block:'nearest'})
     Is the new hint card inside the viewport and not under the header?
Run in both engines for a direct comparison.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import (LIVE_BASE, RAW, SHOTS, current_order, expected_solution,
                       fill_order, now_iso)

SETTLE = """async () => {
  let last=-1, stable=0, t0=performance.now();
  while (performance.now()-t0 < 3000) {
    await new Promise(r=>requestAnimationFrame(r));
    if (Math.abs(window.scrollY-last)<0.01) stable++; else { stable=0; last=window.scrollY; }
    if (stable>=5) break;
  }
  return {scrollY: Math.round(window.scrollY*100)/100};
}"""

out = {"when": now_iso(), "base": LIVE_BASE, "engines": {}}

with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        e = {"version": b.version}

        # ---- 1. verdict ----
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/case/NA-001", wait_until="networkidle", timeout=60000)
        pg.wait_for_selector("#slots .slot")
        # scroll down first so the verdict scroll has somewhere to go
        pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        pg.evaluate(SETTLE)
        fill_order(pg, expected_solution("NA-001"))
        pg.click("#btn-submit")
        pg.wait_for_selector(".verdict", timeout=15000)
        pg.wait_for_timeout(1400)   # smooth scroll + 420ms render delay
        st = pg.evaluate(SETTLE)
        e["verdict"] = {**st, **pg.evaluate("""() => {
            const t = document.querySelector('#verdict-title');
            const h = document.querySelector('.site-header').getBoundingClientRect();
            const r = t.getBoundingClientRect();
            return {titleTop: Math.round(r.top*100)/100,
                    headerBottom: Math.round(h.bottom*100)/100,
                    titleVisibleBelowHeader: r.top >= h.bottom - 1,
                    hiddenPx: Math.round((h.bottom - r.top)*100)/100,
                    activeElement: document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null,
                    viewportH: window.innerHeight};
        }""")}
        pg.screenshot(path=str(SHOTS / f"verdictscroll-{eng}.png"))
        ctx.close()

        # ---- 2. hint card ----
        ctx = b.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN",
                            is_mobile=True, has_touch=True, device_scale_factor=2)
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/case/NA-003", wait_until="networkidle", timeout=60000)
        pg.wait_for_selector("#slots .slot")
        pg.evaluate("() => window.scrollTo(0,0)")
        pg.evaluate(SETTLE)
        pg.click("#btn-hint")
        pg.wait_for_timeout(1200)
        st2 = pg.evaluate(SETTLE)
        e["hint"] = {**st2, **pg.evaluate("""() => {
            const cards = [...document.querySelectorAll('.hint-card')];
            const c = cards[cards.length-1];
            const h = document.querySelector('.site-header').getBoundingClientRect();
            if (!c) return {found: false};
            const r = c.getBoundingClientRect();
            return {found: true, hintTop: Math.round(r.top*100)/100,
                    hintBottom: Math.round(r.bottom*100)/100,
                    headerBottom: Math.round(h.bottom*100)/100,
                    fullyInViewport: r.top >= h.bottom - 1 && r.bottom <= window.innerHeight + 1,
                    viewportH: window.innerHeight};
        }""")}
        pg.screenshot(path=str(SHOTS / f"hintscroll-{eng}.png"))
        ctx.close()
        b.close()
        out["engines"][eng] = e
        print(eng, "done")

(RAW / "app-scroll-calls.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
for eng, e in out["engines"].items():
    print("=" * 60)
    print(eng, e["version"])
    print("  verdict:", json.dumps(e["verdict"], ensure_ascii=False))
    print("  hint   :", json.dumps(e["hint"], ensure_ascii=False))
print("-> raw/app-scroll-calls.json")
