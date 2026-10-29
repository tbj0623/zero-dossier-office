#!/usr/bin/env python3
"""Chromium vs Firefox numeric layout comparison on the LIVE site.

Both engines run identical code paths: same routes, same viewport, same settle
routine (fonts ready + all <img> decoded + scroll through then back + 2 rAF),
then capture:
  * element bounding boxes (x / y / width / height, device-pixel ratio 1)
  * computed font-size / line-height
  * document scrollWidth / clientWidth
  * a full-page screenshot

Elements measured (per assignment): header, hero h1, evidence column, board,
action buttons — plus supporting anchors (hero, hero lede, case grid/cards,
slot rows, recap blocks) so the report can explain any delta.

Usage: python run_layout_parity.py
Writes raw/layout-parity.json, shots/{chromium,firefox}-*.png
"""
from __future__ import annotations

import json
import sys

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, SETTLE, SHOTS, now_iso

SCENES = [
    ("home-1440", "#/", 1440, 900, True),
    ("cabinet-1440", "#/cabinet", 1440, 900, True),
    ("case-NA001-1440", "#/case/NA-001", 1440, 900, True),
    ("home-768", "#/", 768, 1024, True),
    ("case-NA004-768", "#/case/NA-004", 768, 1024, True),
    ("home-390", "#/", 390, 844, True),
    ("case-NA004-390", "#/case/NA-004", 390, 844, True),
    ("cabinet-390", "#/cabinet", 390, 844, True),
]

# element key -> CSS selector
ELEMENTS = {
    "header": ".site-header",
    "headerInner": ".site-header__inner",
    "brand": ".brand",
    "hero": ".hero",
    "heroH1": ".hero h1",
    "heroLede": ".hero__lede",
    "heroCta": "#cta-first",
    "caseGrid": ".case-grid",
    "caseCard1": ".case-card",
    "caseThumb1": ".case-card__thumb",
    "evidenceCol": ".evidence-col",
    "evidenceCard1": ".ev-card",
    "desk": ".desk",
    "board": ".board",
    "slots": "#slots",
    "slot1": "#slots .slot",
    "actions": ".actions",
    "btnSubmit": "#btn-submit",
    "btnUndo": "#btn-undo",
    "btnHint": "#btn-hint",
    "btnReset": "#btn-reset",
    "statusBar": ".status-bar",
}

MEASURE_JS = """(keys) => {
    const out = {};
    for (const [k, sel] of Object.entries(keys)) {
        const e = document.querySelector(sel);
        if (!e) { out[k] = null; continue; }
        const r = e.getBoundingClientRect();
        const cs = getComputedStyle(e);
        out[k] = {
            x: Math.round(r.x * 100) / 100,
            y: Math.round(r.y * 100) / 100,
            w: Math.round(r.width * 100) / 100,
            h: Math.round(r.height * 100) / 100,
            fontSize: cs.fontSize,
            lineHeight: cs.lineHeight,
            display: cs.display,
        };
    }
    out.__doc = {
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        scrollHeight: document.documentElement.scrollHeight,
        dpr: window.devicePixelRatio,
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
    };
    return out;
}"""


def launch(engine: str, p):
    if engine == "chromium":
        return p.chromium.launch(headless=True)
    if engine == "firefox":
        return p.firefox.launch(headless=True)
    raise ValueError(engine)


def capture(engine: str, p) -> dict:
    shots = {}
    browser = launch(engine, p)
    try:
        for name, route, w, h, full in SCENES:
            ctx = browser.new_context(viewport={"width": w, "height": h},
                                      locale="zh-CN", device_scale_factor=1)
            page = ctx.new_page()
            errs = []
            page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
            page.goto(LIVE_BASE + route, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(400)
            settle = page.evaluate(SETTLE)
            page.wait_for_timeout(400)
            metrics = page.evaluate(MEASURE_JS, ELEMENTS)
            path = SHOTS / f"{engine}-{name}.png"
            page.screenshot(path=str(path), full_page=full)
            shots[name] = {"metrics": metrics, "settle": settle, "console": errs,
                           "path": str(path), "viewport": [w, h],
                           "engine_version": browser.version}
            ctx.close()
            print(f"  {engine} {name}: {metrics['__doc']['clientWidth']}x{metrics['__doc']['scrollWidth']}")
    finally:
        browser.close()
    return shots


def px(v) -> float:
    if v is None:
        return 0.0
    return float(str(v).replace("px", "")) if str(v).endswith("px") else 0.0


def main() -> int:
    with sync_playwright() as p:
        print("capturing chromium ...")
        ch = capture("chromium", p)
        print("capturing firefox ...")
        fx = capture("firefox", p)

    scenes = {}
    for name, route, w, h, full in SCENES:
        a, b = ch[name], fx[name]
        rows = {}
        max_delta = 0.0
        worst = None
        for key in ELEMENTS:
            ma, mb = a["metrics"].get(key), b["metrics"].get(key)
            if ma is None and mb is None:
                rows[key] = {"present": False}
                continue
            if ma is None or mb is None:
                rows[key] = {"present": False, "only_in": "chromium" if mb is None else "firefox"}
                continue
            d = {k: round(mb[k] - ma[k], 2) for k in ("x", "y", "w", "h")}
            fs_d = round(px(mb["fontSize"]) - px(ma["fontSize"]), 2)
            lh_d = round(px(mb["lineHeight"]) - px(ma["lineHeight"]), 2)
            rows[key] = {
                "present": True,
                "chromium": ma, "firefox": mb,
                "delta": d, "fontSizeDelta": fs_d, "lineHeightDelta": lh_d,
                "maxAbsDelta": max(abs(v) for v in d.values()),
            }
            if rows[key]["maxAbsDelta"] > max_delta:
                max_delta = rows[key]["maxAbsDelta"]
                worst = key
        doc = {"chromium": a["metrics"]["__doc"], "firefox": b["metrics"]["__doc"]}
        diff_pct = None
        same_size = None
        diff_bbox = None
        try:
            ia = Image.open(a["path"]).convert("RGB")
            ib = Image.open(b["path"]).convert("RGB")
            same_size = ia.size == ib.size
            if same_size:
                diff = ImageChops.difference(ia, ib)
                hist = diff.convert("L").histogram()
                changed = sum(hist[3:])
                total = ia.size[0] * ia.size[1]
                diff_pct = round(100 * changed / total, 4)
                diff_bbox = diff.getbbox()
                diff.save(str(SHOTS / f"parity-diff-{name}.png"))
            else:
                diff_pct = None
        except Exception as exc:  # noqa: BLE001
            diff_pct = f"error: {exc}"
        scenes[name] = {
            "route": route, "viewport": [w, h], "elements": rows,
            "doc": doc, "maxAbsDelta": round(max_delta, 2), "worstElement": worst,
            "screenshot": {"chromium": a["path"], "firefox": b["path"]},
            "image": {"chromium_size": Image.open(a["path"]).size if diff_pct is not None else None,
                      "same_size": same_size, "pixels_diff_gt2_pct": diff_pct,
                      "diff_bbox": diff_bbox},
            "console": {"chromium": a["console"], "firefox": b["console"]},
        }
        print(f"{name}: maxAbsDelta={max_delta:.2f}px worst={worst} pixelDiff={diff_pct}%")

    payload = {
        "when": now_iso(), "base": LIVE_BASE,
        "engines": {"chromium": ch[SCENES[0][0]]["engine_version"],
                    "firefox": fx[SCENES[0][0]]["engine_version"]},
        "elements": ELEMENTS, "scenes": scenes,
    }
    (RAW / "layout-parity.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("-> raw/layout-parity.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
