#!/usr/bin/env python3
"""Targeted probe: `text-wrap: pretty` line-breaking divergence between engines.

This is the single cause of every non-zero pixel difference found in the
side-by-side crops. It is not a layout bug: the boxes are identical to <0.1 px,
only the break point inside a paragraph differs.

Measured three ways, in each engine:
  * computed text-wrap on .hero__lede
  * the actual line widths with the page's own CSS
  * the same line widths with text-wrap forced to `wrap` and to `balance`
    (controls that prove the difference comes from `pretty`, not from fonts)

Writes raw/textwrap-pretty.json.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright
from wk_common import BASE, RAW, now_iso

JS = """() => {
  const out = {};
  const probe = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const w = () => { const r = document.createRange(); r.selectNodeContents(el);
      return [...r.getClientRects()].map(x => Math.round(x.width * 100) / 100); };
    const h = () => Math.round(el.getBoundingClientRect().height * 100) / 100;
    const rec = {asIs: {wrap: getComputedStyle(el).textWrap, widths: w(), h: h()}};
    const st = document.createElement('style'); st.id = '__tw';
    document.head.appendChild(st);
    for (const mode of ['wrap', 'balance', 'normal']) {
      st.textContent = `${sel}{text-wrap:${mode} !important}`;
      void el.offsetHeight;
      rec[mode] = {widths: w(), h: h()};
    }
    st.remove();
    return rec;
  };
  return {lede: probe('.hero__lede'), h1: probe('.hero h1'),
          pitchBody: probe('.pitch__card p'),
          supports: {balance: CSS.supports('text-wrap', 'balance'),
                     pretty: CSS.supports('text-wrap', 'pretty')}};
}"""


def main() -> int:
    out: dict = {"when": now_iso(), "base": BASE, "engines": {}}
    with sync_playwright() as p:
        for eng, launcher in (("webkit", p.webkit), ("chromium", p.chromium), ("firefox", p.firefox)):
            b = launcher.launch(headless=True)
            pg = b.new_page(viewport={"width": 1440, "height": 900}, locale="zh-CN")
            pg.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
            pg.wait_for_timeout(900)
            out["engines"][eng] = {"version": b.version, **pg.evaluate(JS)}
            b.close()

    (RAW / "textwrap-pretty.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    for eng, v in out["engines"].items():
        lede = v["lede"]
        print(f"== {eng} v{v['version']}")
        print(f"   supports: {v['supports']}")
        print(f"   lede asIs ({lede['asIs']['wrap']}): {lede['asIs']['widths']} h={lede['asIs']['h']}")
        print(f"   lede wrap   : {lede['wrap']['widths']}")
        print(f"   lede balance: {lede['balance']['widths']}")
        print(f"   h1   asIs ({v['h1']['asIs']['wrap']}): {v['h1']['asIs']['widths']}")

    wk = out["engines"]["webkit"]["lede"]
    ch = out["engines"]["chromium"]["lede"]
    print("\n--- conclusion ---")
    print(f"default break  : webkit {wk['asIs']['widths']}  vs chromium {ch['asIs']['widths']}")
    print(f"forced 'wrap'  : webkit {wk['wrap']['widths']}  vs chromium {ch['wrap']['widths']}")
    print(f"forced 'balance': webkit {wk['balance']['widths']}  vs chromium {ch['balance']['widths']}")
    same_wrap = wk["wrap"]["widths"] == ch["wrap"]["widths"]
    same_bal = wk["balance"]["widths"] == ch["balance"]["widths"]
    print(f"identical under 'wrap'={same_wrap}; identical under 'balance'={same_bal}; "
          f"divergent only under 'pretty'={wk['asIs']['widths'] != ch['asIs']['widths']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
