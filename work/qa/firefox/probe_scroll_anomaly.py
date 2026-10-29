#!/usr/bin/env python3
"""Why does #slots.scrollIntoView({block:'start'}) land 36px higher in Firefox
on the real site, when Firefox honours scroll-padding perfectly in isolation?

Controls:
  * fresh page (no prior scrolling) vs pre-scrolled-to-bottom
  * target #slots vs #board vs #case-title
  * list every ancestor's overflow / scrollTop / scroll-margin-top
  * repeat 3x to see whether the value is stable or noisy
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, now_iso

SETTLE = """async () => {
  let last=-1, stable=0, t0=performance.now();
  while (performance.now()-t0 < 3000) {
    await new Promise(r=>requestAnimationFrame(r));
    if (Math.abs(window.scrollY-last)<0.01) stable++; else { stable=0; last=window.scrollY; }
    if (stable>=5) break;
  }
  return {scrollY: Math.round(window.scrollY*100)/100, stableFrames: stable};
}"""

ANCESTORS = """(sel) => {
  const el = document.querySelector(sel);
  const out = [];
  let n = el;
  while (n && n !== document.documentElement) {
    const cs = getComputedStyle(n);
    if (cs.overflowY !== 'visible' || cs.overflowX !== 'visible' || cs.scrollMarginTop !== '0px') {
      out.push({tag: n.tagName.toLowerCase(), id: n.id || '', cls: (n.className||'').toString().slice(0,40),
                overflowY: cs.overflowY, overflowX: cs.overflowX,
                scrollMarginTop: cs.scrollMarginTop, scrollTop: Math.round(n.scrollTop)});
    }
    n = n.parentElement;
  }
  return out;
}"""

out = {"when": now_iso(), "results": {}}

with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        e = {"version": b.version, "runs": []}
        for trial in range(3):
            for pre in ("fresh", "prescrolled"):
                ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
                pg = ctx.new_page()
                pg.goto(LIVE_BASE + "#/case/NA-001", wait_until="networkidle", timeout=60000)
                pg.wait_for_selector("#slots .slot")
                pg.wait_for_timeout(500)
                if pre == "prescrolled":
                    pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                    pg.evaluate(SETTLE)
                for target in ("#slots", ".board", "#case-title"):
                    pg.evaluate("() => window.scrollTo(0,0)")
                    pg.evaluate(SETTLE)
                    if pre == "prescrolled":
                        pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                        pg.evaluate(SETTLE)
                    pg.evaluate(f"() => document.querySelector('{target}').scrollIntoView({{block:'start', behavior:'auto'}})")
                    st = pg.evaluate(SETTLE)
                    pg.wait_for_timeout(200)
                    m = pg.evaluate("""(sel) => {
                        const t = document.querySelector(sel).getBoundingClientRect();
                        const h = document.querySelector('.site-header').getBoundingClientRect();
                        return {top: Math.round(t.top*100)/100, headerBottom: Math.round(h.bottom*100)/100,
                                gap: Math.round((t.top - h.bottom)*100)/100};
                    }""", target)
                    e["runs"].append({"trial": trial, "pre": pre, "target": target, **st, **m})
                if target == "#slots" and trial == 0 and pre == "fresh":
                    e["ancestors_slots"] = pg.evaluate(ANCESTORS, "#slots")
                ctx.close()
        b.close()
        out["results"][eng] = e
        print(eng, "done")

(RAW / "scroll-anomaly.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

for eng, e in out["results"].items():
    print("=" * 66)
    print(eng, e["version"])
    for r in e["runs"]:
        print(f"  trial{r['trial']} {r['pre']:11s} {r['target']:12s} scrollY={r['scrollY']:7.2f} top={r['top']:7.2f} gap={r['gap']:7.2f}")
    print("  ancestors:", e.get("ancestors_slots"))
print("-> raw/scroll-anomaly.json")

