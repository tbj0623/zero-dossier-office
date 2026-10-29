#!/usr/bin/env python3
"""Text-layout deep probe: does Firefox break lines the same way, and with the
same physical font, as Chromium?

  * computed font-family for body / h1 / lede
  * which families the UA actually has (document.fonts.check)
  * canvas advance width of a fixed CJK string under the computed stack
  * number of line boxes for h1 / lede / first paragraph, via Range.getClientRects()
  * per-line rects, so a wrap difference is visible as data, not opinion
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, now_iso

JS = """() => {
  const cs = (sel, prop) => { const e = document.querySelector(sel); return e ? getComputedStyle(e)[prop] : null; };
  const lineBoxes = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const range = document.createRange();
    range.selectNodeContents(el);
    const rects = [...range.getClientRects()].filter(r => r.width > 0.5 && r.height > 0.5);
    // merge rects that share a top (same visual line)
    const lines = [];
    for (const r of rects) {
      const hit = lines.find(l => Math.abs(l.top - r.top) < 2);
      if (hit) { hit.left = Math.min(hit.left, r.left); hit.right = Math.max(hit.right, r.right); }
      else lines.push({top: Math.round(r.top), left: Math.round(r.left), right: Math.round(r.right)});
    }
    return {count: lines.length, lines};
  };
  const measure = (font) => {
    const c = document.createElement('canvas').getContext('2d');
    c.font = font;
    return {
      cjk: Math.round(c.measureText('这些记录，不应该同时成立。').width * 100) / 100,
      latin: Math.round(c.measureText('The Zero Dossier Office').width * 100) / 100,
    };
  };
  const families = ['Noto Sans SC', 'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei',
                    'Songti SC', 'SimSun', 'Noto Serif SC', 'Georgia', 'system-ui', 'sans-serif', 'serif'];
  return {
    bodyFamily: cs('body', 'fontFamily'),
    h1Family: cs('.hero h1', 'fontFamily'),
    h1Size: cs('.hero h1', 'fontSize'),
    bodySize: cs('body', 'fontSize'),
    available: Object.fromEntries(families.map(f => [f, document.fonts.check(`16px "${f}"`)])),
    canvasMeasured: {
      bodyStack: measure(`16px ${cs('body', 'fontFamily')}`),
      h1Stack: measure(`${cs('.hero h1', 'fontSize')} ${cs('.hero h1', 'fontFamily')}`),
      genericSerif: measure('48px serif'),
      genericSans: measure('16px sans-serif'),
      simsun: measure('48px "SimSun"'),
      songti: measure('48px "Songti SC"'),
      yahei: measure('16px "Microsoft YaHei"'),
    },
    h1Lines: lineBoxes('.hero h1'),
    ledeLines: lineBoxes('.hero__lede'),
    eyebrowLines: lineBoxes('.eyebrow'),
    ledeWidth: cs('.hero__lede', 'width'),
    ledeTextWrap: cs('.hero__lede', 'textWrap'),
    h1TextWrap: cs('.hero h1', 'textWrap'),
    pTextWrap: (() => { const p = document.querySelector('.hero__lede'); return p ? getComputedStyle(p).textWrap : null; })(),
  };
}"""

out = {"when": now_iso(), "base": LIVE_BASE}
with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN", device_scale_factor=1)
        pg = ctx.new_page()
        pg.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(600)
        out[eng] = {"version": b.version, **pg.evaluate(JS)}
        ctx.close()
        b.close()

(RAW / "text-probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

for eng in ("chromium", "firefox"):
    d = out[eng]
    print("=" * 60)
    print(eng, d["version"])
    print("  body font:", d["bodyFamily"])
    print("  h1   font:", d["h1Family"], d["h1Size"])
    print("  canvas body:", d["canvasMeasured"]["bodyStack"], " h1:", d["canvasMeasured"]["h1Stack"])
    print("  generic serif:", d["canvasMeasured"]["genericSerif"], " sans:", d["canvasMeasured"]["genericSans"])
    print("  SimSun:", d["canvasMeasured"]["simsun"], " Songti SC:", d["canvasMeasured"]["songti"])
    print("  h1 lines:", d["h1Lines"]["count"], [ (l['left'], l['right']) for l in d["h1Lines"]["lines"]])
    print("  lede lines:", d["ledeLines"]["count"], [ (l['left'], l['right']) for l in d["ledeLines"]["lines"]])
    print("  textWrap h1/p:", d["h1TextWrap"], "/", d["pTextWrap"])
    print("  available:", {k: v for k, v in d["available"].items() if v})
print("-> raw/text-probe.json")
