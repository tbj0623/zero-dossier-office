#!/usr/bin/env python3
"""Red-team probe 3: measure real computed colour contrast of key text on the
live site (the project's own axe run reported 59-78 'incomplete' contrast nodes)."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://tbj0623.github.io/zero-dossier-office/"
OUT = Path(__file__).resolve().parent

JS = r"""
() => {
  function parse(c) {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(x => parseFloat(x.trim()));
    return {r:p[0], g:p[1], b:p[2], a: p.length > 3 ? p[3] : 1};
  }
  function lum({r,g,b}) {
    const f = v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); };
    return 0.2126*f(r) + 0.7152*f(g) + 0.0722*f(b);
  }
  function blend(fg, bg) {  // fg over bg
    return {r: fg.r*fg.a + bg.r*(1-fg.a), g: fg.g*fg.a + bg.g*(1-fg.a), b: fg.b*fg.a + bg.b*(1-fg.a), a:1};
  }
  function bgOf(el) {
    let n = el;
    while (n && n !== document.documentElement) {
      const cs = getComputedStyle(n);
      const c = parse(cs.backgroundColor);
      // A gradient/painting layer with a transparent background-color means we
      // cannot read the real backdrop from computed styles -> report unknown.
      if (cs.backgroundImage && cs.backgroundImage !== 'none' &&
          (!c || c.a < 0.9)) return {unknown: true};
      if (c && c.a > 0.9) return c;
      n = n.parentElement;
    }
    return parse(getComputedStyle(document.body).backgroundColor) || {r:8,g:24,b:33,a:1};
  }
  const sels = [
    ['body text', 'body'],
    ['.hero__lede', '.hero__lede'],
    ['.hero__note', '.hero__note'],
    ['.eyebrow', '.eyebrow'],
    ['.case-card__hook', '.case-card__hook'],
    ['.case-card__meta', '.case-card__meta'],
    ['.hint', '.hint'],
    ['.ev-card__body p', '.ev-card__body p'],
    ['.ev-card__rule', '.ev-card__rule'],
    ['.slot__label', '.slot__label'],
    ['.slot__index', '.slot__index'],
    ['.board__goal', '.board__goal'],
    ['.site-footer__legal', '.site-footer__legal'],
    ['.doc p', '.doc p'],
    ['.callout p', '.callout p'],
    ['code', 'code'],
    ['.pill', '.pill'],
    ['.status-bar', '.status-bar'],
    ['.message', '.message'],
    ['.act__desc', '.act__desc'],
    ['.verdict__lede', '.verdict__lede'],
  ];
  const out = [];
  for (const [label, sel] of sels) {
    const el = document.querySelector(sel);
    if (!el) { out.push({label, sel, missing: true}); continue; }
    const cs = getComputedStyle(el);
    const fg = parse(cs.color);
    const bg = bgOf(el);
    if (!fg) { out.push({label, sel, missing: true}); continue; }
    if (bg.unknown) { out.push({label, sel, unknown: true, color: cs.color,
                                 bg: cs.backgroundColor, fontPx: Math.round(parseFloat(cs.fontSize)*10)/10}); continue; }
    const composed = blend(fg, bg);
    const L1 = lum(composed), L2 = lum(bg);
    const ratio = (Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    const size = parseFloat(cs.fontSize);
    const bold = parseInt(cs.fontWeight, 10) >= 700;
    const large = size >= 24 || (size >= 18.66 && bold);
    out.push({
      label, sel,
      color: cs.color, bg: `rgb(${Math.round(bg.r)},${Math.round(bg.g)},${Math.round(bg.b)})`,
      fontPx: Math.round(size*10)/10, bold,
      ratio: Math.round(ratio*100)/100,
      required: large ? 3.0 : 4.5,
      pass: ratio >= (large ? 3.0 : 4.5),
    });
  }
  return out;
}
"""


def main() -> int:
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        for route, label in [("", "home"), ("#/cabinet", "cabinet"),
                             ("#/case/NA-001", "case"), ("#/manual", "manual")]:
            pg.goto(BASE + route, wait_until="networkidle")
            if "case" in route:
                pg.wait_for_selector("#slots .slot")
            res[label] = pg.evaluate(JS)
        b.close()
    (OUT / "contrast.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    for page, rows in res.items():
        print("==", page)
        for r in rows:
            if r.get("missing"):
                continue
            flag = "PASS" if r["pass"] else "**FAIL**"
            print(f'  {flag} {r["label"]:<22} {r["ratio"]:>5}:1 (need {r["required"]}) '
                  f'{r["fontPx"]}px {r["color"]} on {r["bg"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
