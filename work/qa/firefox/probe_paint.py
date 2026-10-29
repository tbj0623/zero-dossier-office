#!/usr/bin/env python3
"""Diagnose WHERE Chromium and Firefox paint differently.

For each engine, on a settled page, we:
  * list every <img>: src, complete, naturalWidth/Height, decoded size
  * read the ::before/::after background-image + opacity of .hero
  * report CSS.supports() for the risky features
  * screenshot the viewport and sample the RGB at fixed probe points
so the numbers can be compared directly instead of eyeballed.
"""
from __future__ import annotations

import json

from PIL import Image
from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, SETTLE, SHOTS, now_iso

PROBE_JS = """() => {
  const hero = document.querySelector('.hero');
  const hb = hero ? getComputedStyle(hero, '::before') : null;
  const ha = hero ? getComputedStyle(hero, '::after') : null;
  const hdr = document.querySelector('.site-header');
  const hcs = hdr ? getComputedStyle(hdr) : null;
  const imgState = [...document.images].map(i => ({
      src: i.currentSrc || i.src,
      complete: i.complete,
      nw: i.naturalWidth, nh: i.naturalHeight,
      cw: Math.round(i.getBoundingClientRect().width),
      ch: Math.round(i.getBoundingClientRect().height),
      loading: i.loading,
  }));
  return {
    ua: navigator.userAgent,
    heroBefore: hb ? {backgroundImage: hb.backgroundImage, backgroundSize: hb.backgroundSize,
                      backgroundPosition: hb.backgroundPosition, opacity: hb.opacity,
                      zIndex: hb.zIndex, inset: hb.inset} : null,
    heroAfter: ha ? {backgroundImage: ha.backgroundImage.slice(0, 160), opacity: ha.opacity} : null,
    header: hcs ? {background: hcs.backgroundColor, backdropFilter: hcs.backdropFilter,
                   webkitBackdropFilter: hcs.webkitBackdropFilter,
                   position: hcs.position, zIndex: hcs.zIndex} : null,
    bodyBg: getComputedStyle(document.body).backgroundColor,
    htmlBg: getComputedStyle(document.documentElement).backgroundColor,
    colorScheme: getComputedStyle(document.documentElement).colorScheme,
    images: imgState,
    supports: {
      backdropFilter: CSS.supports('backdrop-filter', 'blur(12px)'),
      webkitBackdropFilter: CSS.supports('-webkit-backdrop-filter', 'blur(12px)'),
      textWrapBalance: CSS.supports('text-wrap', 'balance'),
      textWrapPretty: CSS.supports('text-wrap', 'pretty'),
      aspectRatio: CSS.supports('aspect-ratio', '16 / 9'),
      clamp: CSS.supports('width', 'clamp(1rem, 2vw, 3rem)'),
      focusVisible: (() => { try { document.querySelector('a').matches(':focus-visible'); return true; } catch (e) { return false; } })(),
      scrollPaddingTop: CSS.supports('scroll-padding-top', '80px'),
      dialog: typeof HTMLDialogElement !== 'undefined' && typeof document.createElement('dialog').showModal === 'function',
      dvh: CSS.supports('height', '100dvh'),
      hoverMedia: CSS.supports('selector(:hover)'),
    },
    heroRect: hero ? (r => ({x: r.x, y: r.y, w: r.width, h: r.height}))(hero.getBoundingClientRect()) : null,
    heroBgDelay: performance.getEntriesByType('resource').filter(r => /harbor|archive-desk|webp/.test(r.name)).map(r => ({
        name: r.name.split('/').pop(), duration: Math.round(r.duration), size: r.transferSize, status: r.responseStatus
    })),
  };
}"""

SCENES = [
    ("home-1440", "#/", 1440, 900),
    ("home-390", "#/", 390, 844),
]


def run_engine(p, engine: str) -> dict:
    launcher = p.chromium if engine == "chromium" else p.firefox
    b = launcher.launch(headless=True)
    out = {"version": b.version, "scenes": {}}
    try:
        for name, route, w, h in SCENES:
            ctx = b.new_context(viewport={"width": w, "height": h}, locale="zh-CN", device_scale_factor=1)
            page = ctx.new_page()
            page.goto(LIVE_BASE + route, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(500)
            page.evaluate(SETTLE)
            page.wait_for_timeout(400)
            data = page.evaluate(PROBE_JS)
            shot = SHOTS / f"probe-{engine}-{name}.png"
            page.screenshot(path=str(shot))
            data["shot"] = str(shot)
            # sample probe points
            im = Image.open(shot).convert("RGB")
            pts = {
                "header_bg": (w // 2, 10),
                "header_right_empty": (w - 40, 32),
                "below_header": (w // 2, 75),
                "hero_mid_left": (30, 300) if h > 400 else (20, 300),
                "hero_center": (w // 2, 350),
                "page_bottom": (w // 2, h - 20),
            }
            data["probes"] = {k: {"xy": v, "rgb": im.getpixel(v)} for k, v in pts.items()}
            out["scenes"][name] = data
            ctx.close()
    finally:
        b.close()
    return out


with sync_playwright() as p:
    res = {"when": now_iso(), "base": LIVE_BASE,
           "chromium": run_engine(p, "chromium"),
           "firefox": run_engine(p, "firefox")}

(RAW / "paint-probe.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

for scene in ("home-1440", "home-390"):
    print("=" * 70)
    print(scene)
    for eng in ("chromium", "firefox"):
        d = res[eng]["scenes"][scene]
        print(f"  [{eng} {res[eng]['version']}]")
        print("    header:", d["header"])
        print("    bodyBg:", d["bodyBg"], "htmlBg:", d["htmlBg"], "colorScheme:", d["colorScheme"])
        print("    probes:", {k: v["rgb"] for k, v in d["probes"].items()})
        print("    images:", [(i["src"].split("/")[-1], i["complete"], i["nw"], i["nh"], i["cw"], i["ch"]) for i in d["images"]])
        print("    supports:", d["supports"])
        print("    heroRect:", d["heroRect"])
print("-> raw/paint-probe.json")
