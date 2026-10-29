#!/usr/bin/env python3
"""Measure EVERY interactive target at 390px (the project's own e2e only checked
'#slots button, .actions button, .site-header button, .site-header a')."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://tbj0623.github.io/zero-dossier-office/"
OUT = Path(__file__).resolve().parent

JS = r"""
() => {
  const sel = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"]), [draggable="true"]';
  const els = [...document.querySelectorAll(sel)];
  const bad = [], all = [];
  for (const e of els) {
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;      // hidden
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const w = Math.round(r.width), h = Math.round(r.height);
    const rec = {tag: e.tagName, cls: (e.className && e.className.baseVal !== undefined ?
                 e.className.baseVal : e.className) || '', id: e.id || '',
                 text: (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0,28),
                 w, h};
    all.push(rec);
    if (w < 44 || h < 44) bad.push(rec);
  }
  return {total: all.length, undersized: bad};
}
"""


def main() -> int:
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for w in (390, 768, 1440):
            ctx = b.new_context(viewport={"width": w, "height": 900}, locale="zh-CN",
                                is_mobile=w < 500, has_touch=w < 500)
            pg = ctx.new_page()
            for route, label in [("", "home"), ("#/case/NA-001", "case"), ("#/manual", "manual")]:
                pg.goto(BASE + route, wait_until="networkidle")
                if "case" in route:
                    pg.wait_for_selector("#slots .slot")
                # expand evidence + reveal a hint so those controls are live
                if "case" in route:
                    for btn in pg.query_selector_all(".ev-card__summary"):
                        if btn.get_attribute("aria-expanded") == "false":
                            btn.click()
                    pg.click("#btn-hint")
                res = pg.evaluate(JS)
                out[f"{w}px/{label}"] = res
            ctx.close()
        b.close()
    (OUT / "targets.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    for k, v in out.items():
        print(f"{k}: {v['total']} targets, {len(v['undersized'])} under 44px")
        for u in v["undersized"][:8]:
            print(f"    {u['tag']}.{u['cls'][:34]:<34} {u['w']}x{u['h']}  '{u['text']}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
