#!/usr/bin/env python3
"""Controlled visual-parity comparison: Chromium vs Edge on identical, settled states.

Both engines navigate to the same routes, wait for network idle + all images
decoded + fonts ready, force scroll to 0, then screenshot. Any pixel diff then
reflects engine/layout differences rather than load-timing noise.

Usage: python run_visual_parity.py
"""
from __future__ import annotations

import json
import sys

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from qa_common import LIVE_BASE, RAW, SHOTS, ConsoleCollector, now_iso

SETTLE = """async () => {
    if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (e) {} }
    const imgs = [...document.images];
    await Promise.all(imgs.map(i => (i.complete && i.naturalWidth > 0)
        ? Promise.resolve()
        : new Promise(r => { i.addEventListener('load', r, {once:true}); i.addEventListener('error', r, {once:true}); setTimeout(r, 4000); })));
    window.scrollTo(0, 0);
    // force lazy images in view by scrolling through then back
    const h = document.body.scrollHeight;
    for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 30)); }
    window.scrollTo(0, 0);
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    return {images: imgs.length, decoded: imgs.filter(i => i.complete && i.naturalWidth > 0).length};
}"""

SCENES = [
    ("home-1440", "#/", {"width": 1440, "height": 900}, False),
    ("cabinet-1440", "#/cabinet", {"width": 1440, "height": 900}, True),
    ("case-NA001-1440", "#/case/NA-001", {"width": 1440, "height": 900}, True),
    ("case-NA004-mobile390", "#/case/NA-004", {"width": 390, "height": 844}, True),
    ("cabinet-mobile390", "#/cabinet", {"width": 390, "height": 844}, False),
    ("manual-1024", "#/manual", {"width": 1024, "height": 768}, False),
]


def capture(engine: str, out_dir) -> dict:
    shots = {}
    with sync_playwright() as p:
        browser = (p.chromium.launch(headless=True, channel="msedge") if engine == "msedge"
                   else p.chromium.launch(headless=True))
        for name, route, vp, full in SCENES:
            ctx = browser.new_context(viewport=vp, locale="zh-CN",
                                      is_mobile=vp["width"] < 500, has_touch=vp["width"] < 500,
                                      device_scale_factor=1)
            page = ctx.new_page()
            cc = ConsoleCollector(page)
            page.goto(LIVE_BASE + route, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(500)
            settle = page.evaluate(SETTLE)
            page.wait_for_timeout(350)
            path = out_dir / f"{engine}-{name}.png"
            page.screenshot(path=str(path), full_page=full)
            shots[name] = {"path": str(path), "settle": settle,
                           "console": cc.all,
                           "scrollWidth": page.evaluate("() => document.documentElement.scrollWidth"),
                           "clientWidth": page.evaluate("() => document.documentElement.clientWidth")}
            ctx.close()
        browser.close()
    return shots


def main() -> int:
    shots = {}
    for eng in ("chromium", "msedge"):
        shots[eng] = capture(eng, SHOTS)
        print(f"{eng}: captured {len(shots[eng])} scenes")

    diffs = {}
    for name, _route, vp, _full in SCENES:
        a, b = shots["chromium"][name], shots["msedge"][name]
        ia, ib = Image.open(a["path"]).convert("RGB"), Image.open(b["path"]).convert("RGB")
        rec = {
            "chromium": {"size": ia.size, "scrollWidth": a["scrollWidth"], "clientWidth": a["clientWidth"],
                         "images": a["settle"]},
            "msedge": {"size": ib.size, "scrollWidth": b["scrollWidth"], "clientWidth": b["clientWidth"],
                       "images": b["settle"]},
        }
        if ia.size != ib.size:
            rec.update({"same_size": False})
        else:
            diff = ImageChops.difference(ia, ib)
            hist = diff.convert("L").histogram()
            changed = sum(hist[3:])            # ignore <=2/255 channel noise
            total = ia.size[0] * ia.size[1]
            rec.update({
                "same_size": True,
                "diff_bbox": diff.getbbox(),
                "pixels_differing_gt2": changed,
                "pct": round(100 * changed / total, 4),
                "layout_scrollwidth_equal": a["scrollWidth"] == b["scrollWidth"],
            })
            if changed:
                diff.save(str(SHOTS / f"parity-diff-{name}.png"))
        diffs[name] = rec
        print(f"{name}: size={ia.size} vs {ib.size} pct_diff={rec.get('pct')} "
              f"scrollW={a['scrollWidth']}/{b['scrollWidth']}")

    payload = {"when": now_iso(), "base": LIVE_BASE, "scenes": diffs, "shots": shots}
    (RAW / "visual-parity.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("-> raw/visual-parity.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
