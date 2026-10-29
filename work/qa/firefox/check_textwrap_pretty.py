#!/usr/bin/env python3
"""Does the missing `text-wrap: pretty` in Firefox change the rendered paragraphs?

Chromium supports `pretty` (last-line widow avoidance); Firefox computes `wrap`.
We compare, for every <p> on the home + cabinet + desk views:
  * computed textWrap
  * box height, line count
  * the last line's width as a share of the box width (a widow is a very short
    last line; `pretty` exists to avoid exactly that)
If heights and last-line shares match across engines, the unsupported keyword is
cosmetic in practice for this site.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, now_iso

JS = """() => {
  const out = [];
  const ps = [...document.querySelectorAll('main p, .site-header p, .message')];
  ps.forEach((p, i) => {
    if (!p.offsetParent && getComputedStyle(p).position !== 'fixed') return;
    const cs = getComputedStyle(p);
    if (cs.display === 'none') return;
    const r = p.getBoundingClientRect();
    if (r.width < 10 || r.height < 5) return;
    const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.6;
    const lines = Math.max(1, Math.round(r.height / lh));
    // last line width via a Range over the last text node
    let lastLineWidth = null;
    const nodes = [...p.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
    const el = p.querySelector('*');
    const target = nodes.length ? nodes[nodes.length - 1] : el;
    if (target) {
      const rg = document.createRange();
      rg.selectNodeContents(target);
      const rects = [...rg.getClientRects()].filter(q => q.width > 1 && q.height > 1);
      if (rects.length) {
        const last = rects[rects.length - 1];
        lastLineWidth = Math.round(last.width);
      }
    }
    out.push({
      i, tag: p.tagName.toLowerCase(), cls: p.className || '',
      text: (p.textContent || '').trim().slice(0, 34),
      textWrap: cs.textWrap, width: Math.round(r.width * 100) / 100,
      height: Math.round(r.height * 100) / 100, lines,
      lastLineWidth,
      lastLineShare: lastLineWidth ? Math.round(lastLineWidth / r.width * 1000) / 1000 : null,
    });
  });
  return out;
}"""

ROUTES = ["#/", "#/cabinet", "#/case/NA-001", "#/manual"]
out = {"when": now_iso(), "base": LIVE_BASE, "engines": {}}

with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        e = {"version": b.version, "routes": {}}
        for route in ROUTES:
            ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
            pg = ctx.new_page()
            pg.goto(LIVE_BASE + route, wait_until="networkidle", timeout=60000)
            if route.startswith("#/case"):
                pg.wait_for_selector("#slots .slot")
            pg.wait_for_timeout(700)
            e["routes"][route] = pg.evaluate(JS)
            ctx.close()
        b.close()
        out["engines"][eng] = e
        print(eng, "done")

(RAW / "textwrap-pretty.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print("\nParagraph-level comparison (same DOM order, same viewport):")
for route in ROUTES:
    ca = out["engines"]["chromium"]["routes"][route]
    fb = out["engines"]["firefox"]["routes"][route]
    print(f"\n== {route}  ({len(ca)} vs {len(fb)} paragraphs)")
    n = min(len(ca), len(fb))
    mism = 0
    for i in range(n):
        a, b2 = ca[i], fb[i]
        same_h = abs(a["height"] - b2["height"]) < 1.0
        same_lines = a["lines"] == b2["lines"]
        if not (same_h and same_lines):
            mism += 1
            print(f"  DIFF #{i} {a['text']!r}: cr h={a['height']} lines={a['lines']} "
                  f"| fx h={b2['height']} lines={b2['lines']}")
    print(f"  height/line mismatches: {mism}/{n}; "
          f"wrap kinds cr={set(x['textWrap'] for x in ca)} fx={set(x['textWrap'] for x in fb)}")
    shares = [(a["lastLineShare"], b2["lastLineShare"]) for a, b2 in zip(ca, fb)
              if a["lastLineShare"] is not None and b2["lastLineShare"] is not None]
    if shares:
        worst = max(shares, key=lambda s: abs(s[0] - s[1]))
        print(f"  last-line share: max |delta| = {abs(worst[0]-worst[1]):.3f} "
              f"(cr {worst[0]:.3f} vs fx {worst[1]:.3f})")
print("-> raw/textwrap-pretty.json")
