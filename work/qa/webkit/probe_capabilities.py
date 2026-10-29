#!/usr/bin/env python3
"""Probe WebKit capabilities that matter for this site, before writing the full suite.

Answers, with measured evidence:
  - WebKit engine version + UA + Playwright build
  - CSS.supports() matrix for the features named in the assignment
  - 100dvh computed value
  - backdrop-filter paint (does a blur actually render?)
  - <dialog>.showModal() support
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright
from wk_common import BASE, RAW, now_iso

PROBE = r"""() => {
  const s = (p) => { try { return CSS.supports(p); } catch (e) { return 'ERR:' + e.message; } };
  const cs = (sel, prop) => {
    const e = document.querySelector(sel);
    return e ? getComputedStyle(e)[prop] : null;
  };
  const hero = document.querySelector('.hero');
  const heroRect = hero ? hero.getBoundingClientRect() : null;
  const dlg = document.querySelector('#confirm-dialog');
  return {
    ua: navigator.userAgent,
    platform: navigator.platform,
    vendor: navigator.vendor,
    devicePixelRatio: window.devicePixelRatio,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    supports: {
      'backdrop-filter': s('backdrop-filter: blur(1px)'),
      '-webkit-backdrop-filter': s('-webkit-backdrop-filter: blur(1px)'),
      'text-wrap: balance': s('text-wrap: balance'),
      'text-wrap: pretty': s('text-wrap: pretty'),
      'aspect-ratio': s('aspect-ratio: 16 / 9'),
      'clamp()': s('width: clamp(1rem, 2vw, 3rem)'),
      'min()': s('width: min(1rem, 2vw)'),
      'gap (flex)': s('display:flex; gap: 1px'),
      'gap (grid)': s('display:grid; gap: 1px'),
      'inset': s('inset: 0'),
      'place-items': s('place-items: center'),
      'overscroll-behavior': s('overscroll-behavior: contain'),
      'scroll-padding-top': s('scroll-padding-top: 1px'),
      '100dvh': s('height: 100dvh'),
      '100svh': s('height: 100svh'),
      '100lvh': s('height: 100lvh'),
      'dialog': typeof HTMLDialogElement !== 'undefined',
      'showModal': !!(dlg && typeof dlg.showModal === 'function'),
      ':focus-visible': s('selector(:focus-visible)'),
      'scrollbar-gutter': s('scrollbar-gutter: stable'),
      'color-mix': s('color: color-mix(in srgb, red, blue)'),
      'container-queries': s('container-type: inline-size'),
      'subgrid': s('grid-template-columns: subgrid'),
      'oklch': s('color: oklch(0.5 0.1 200)'),
      'text-underline-offset': s('text-underline-offset: 3px'),
      'overflow: clip': s('overflow: clip'),
      'inset-inline': s('inset-inline: 0'),
      'rgba-space-syntax': s('color: rgb(1 2 3 / 0.5)'),
      'env(safe-area-inset)': s('padding: env(safe-area-inset-bottom)'),
      '-webkit-tap-highlight-color': s('-webkit-tap-highlight-color: transparent'),
    },
    computed: {
      heroMinHeight: hero ? getComputedStyle(hero).minHeight : null,
      heroHeight: heroRect ? Math.round(heroRect.height * 100) / 100 : null,
      heroWidth: heroRect ? Math.round(heroRect.width * 100) / 100 : null,
      bodyMinHeight: getComputedStyle(document.body).minHeight,
      docClientHeight: document.documentElement.clientHeight,
      headerBackdrop: cs('.site-header', 'backdropFilter') || cs('.site-header', 'webkitBackdropFilter'),
      headerBg: cs('.site-header', 'backgroundImage'),
      headerPos: cs('.site-header', 'position'),
      headerTop: document.querySelector('.site-header')?.getBoundingClientRect().top,
      mockDvhSupported: getComputedStyle(document.documentElement).getPropertyValue('--x') !== undefined,
      h1FontSize: cs('.hero h1', 'fontSize'),
      bodyFontSize: getComputedStyle(document.body).fontSize,
      h1TextWrap: cs('.hero h1', 'textWrap'),
      thumbAspect: cs('.case-card__thumb', 'aspectRatio'),
      htmlScrollPaddingTop: cs('html', 'scrollPaddingTop'),
      overscroll: cs('body', 'overscrollBehavior'),
      tapHighlight: cs('.btn', 'webkitTapHighlightColor'),
    },
  };
}"""


def main() -> int:
    out = {"when": now_iso(), "base": BASE}
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        out["version"] = browser.version
        out["playwright_browser_type"] = "webkit"
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(700)
        out["home"] = page.evaluate(PROBE)
        page.goto(f"{BASE}/#/cabinet", wait_until="networkidle", timeout=45000)
        page.wait_for_selector("#view-cabinet .case-card", timeout=15000)
        page.wait_for_timeout(600)
        out["cabinet"] = page.evaluate(PROBE)
        ctx.close()
        browser.close()

    (RAW / "capabilities-probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("WebKit version:", out["version"])
    print("UA:", out["home"]["ua"])
    print("\nCSS.supports:")
    for k, v in out["home"]["supports"].items():
        print(f"  {k:34s} {v}")
    print("\ncomputed (home 1440x900):")
    for k, v in out["home"]["computed"].items():
        print(f"  {k:26s} {v}")
    print("\ncomputed (cabinet 1440x900):")
    for k, v in out["cabinet"]["computed"].items():
        print(f"  {k:26s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
