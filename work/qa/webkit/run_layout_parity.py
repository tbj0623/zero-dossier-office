#!/usr/bin/env python3
"""Layout parity: WebKit vs Chromium, identical measurement code.

Same viewports (1440x900, 768x1024, 390x844), same scenes (home, cabinet, NA-001
desk), same settle routine, same element selectors. Reports numeric deltas
(WebKit - Chromium) and flags anything > 2 px.

Writes raw/layout-parity.json and shots/{webkit,chromium}-<scene>.png.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from wk_common import BASE, CROPS, RAW, SHOTS, now_iso

SCENES = [
    ("home-1440", "#/", 1440, 900),
    ("cabinet-1440", "#/cabinet", 1440, 900),
    ("case-NA001-1440", "#/case/NA-001", 1440, 900),
    ("home-768", "#/", 768, 1024),
    ("cabinet-768", "#/cabinet", 768, 1024),
    ("case-NA001-768", "#/case/NA-001", 768, 1024),
    ("home-390", "#/", 390, 844),
    ("cabinet-390", "#/cabinet", 390, 844),
    ("case-NA001-390", "#/case/NA-001", 390, 844),
]

# The five mandated elements first, then supporting anchors.
ELEMENTS = {
    "header": ".site-header",
    "heroH1": ".hero h1",
    "evidenceCol": "#view-case .evidence-col",
    "board": "#view-case .board",
    "actionButtons": "#view-case .actions",
    # supporting anchors
    "headerInner": ".site-header__inner",
    "brand": ".brand",
    "hero": ".hero",
    "heroLede": ".hero__lede",
    "heroCta": "#cta-first",
    "caseGrid": "#view-cabinet .case-grid",
    "caseCard1": "#view-cabinet .case-card",
    "caseThumb1": "#view-cabinet .case-card__thumb",
    "desk": "#view-case .desk",
    "evidenceCard1": "#view-case .ev-card",
    "slots": "#view-case #slots",
    "slot1": "#view-case #slots .slot",
    "btnSubmit": "#view-case #btn-submit",
    "btnUndo": "#view-case #btn-undo",
    "btnHint": "#view-case #btn-hint",
    "btnReset": "#view-case #btn-reset",
    "statusBar": "#view-case .status-bar",
    "doc": "__doc__",
}

MEASURE_JS = """(keys) => {
    const out = {};
    for (const [k, sel] of Object.entries(keys)) {
        if (sel === '__doc__') continue;
        const e = document.querySelector(sel);
        if (!e) { out[k] = null; continue; }
        const r = e.getBoundingClientRect();
        const cs = getComputedStyle(e);
        const visible = cs.display !== 'none' && cs.visibility !== 'hidden' && (r.width > 0 || r.height > 0);
        out[k] = {
            x: Math.round(r.x * 100) / 100, y: Math.round(r.y * 100) / 100,
            w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100,
            right: Math.round(r.right * 100) / 100, bottom: Math.round(r.bottom * 100) / 100,
            fontSize: cs.fontSize, lineHeight: cs.lineHeight,
            display: cs.display, position: cs.position, visible,
        };
    }
    out.__doc = {
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        scrollHeight: document.documentElement.scrollHeight,
        dpr: window.devicePixelRatio, innerWidth: window.innerWidth, innerHeight: window.innerHeight,
    };
    return out;
}"""

SETTLE = """async () => {
    if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (e) {} }
    const imgs = [...document.images];
    await Promise.all(imgs.map(i => (i.complete && i.naturalWidth > 0) ? Promise.resolve()
        : new Promise(r => { i.addEventListener('load', r, {once:true}); i.addEventListener('error', r, {once:true}); setTimeout(r, 4000); })));
    window.scrollTo(0, 0);
    const h = document.body.scrollHeight;
    for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 20)); }
    window.scrollTo(0, 0);
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    return {images: imgs.length, decoded: imgs.filter(i => i.complete && i.naturalWidth > 0).length};
}"""


def launch(engine, p):
    if engine == "webkit":
        return p.webkit.launch(headless=True)
    if engine == "chromium":
        return p.chromium.launch(headless=True)
    raise ValueError(engine)


def capture(engine: str, p) -> dict:
    shots = {}
    browser = launch(engine, p)
    try:
        for name, route, w, h in SCENES:
            ctx = browser.new_context(viewport={"width": w, "height": h},
                                      locale="zh-CN", device_scale_factor=1)
            page = ctx.new_page()
            errs: list[str] = []
            page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
            page.goto(f"{BASE}/{route}", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(500)
            # wait for the desk to actually exist
            if "case" in route:
                page.wait_for_selector("#slots .slot", timeout=15000)
            settle = page.evaluate(SETTLE)
            page.wait_for_timeout(450)
            metrics = page.evaluate(MEASURE_JS, ELEMENTS)
            path = SHOTS / f"{engine}-{name}.png"
            page.screenshot(path=str(path), full_page=True)
            shots[name] = {"metrics": metrics, "settle": settle, "console": errs,
                           "path": str(path), "viewport": [w, h]}
            print(f"  {engine} {name}: {metrics['__doc']['clientWidth']}x{metrics['__doc']['scrollWidth']}")
            ctx.close()
        shots["__version__"] = browser.version
    finally:
        browser.close()
    return shots


def main() -> int:
    with sync_playwright() as p:
        print("capturing webkit ...")
        wk = capture("webkit", p)
        print("capturing chromium ...")
        ch = capture("chromium", p)

    report = {"when": now_iso(), "base": BASE,
              "webkit_version": wk.get("__version__"), "chromium_version": ch.get("__version__"),
              "scenes": {}, "threshold_px": 2.0}

    all_deltas: list[dict] = []
    for name, route, w, h in SCENES:
        a, b = wk[name], ch[name]   # a = webkit, b = chromium
        rows = {}
        for key in ELEMENTS:
            if key == "doc":
                continue
            ma, mb = a["metrics"].get(key), b["metrics"].get(key)
            if ma is None or mb is None:
                rows[key] = {"present": False, "webkit": ma, "chromium": mb}
                continue
            d = {k: round(ma[k] - mb[k], 3) for k in ("x", "y", "w", "h")}
            worst = max(abs(d["x"]), abs(d["y"]), abs(d["w"]), abs(d["h"]))
            rows[key] = {"present": True, "webkit": ma, "chromium": mb, "delta": d,
                         "worst_abs_px": worst, "over_threshold": worst > 2.0}
            all_deltas.append({"scene": name, "key": key, **d, "worst": worst})
        doc_a, doc_b = a["metrics"]["__doc"], b["metrics"]["__doc"]
        rows["__doc"] = {
            "webkit": doc_a, "chromium": doc_b,
            "scrollWidth_delta": doc_a["scrollWidth"] - doc_b["scrollWidth"],
            "scrollHeight_delta": doc_a["scrollHeight"] - doc_b["scrollHeight"],
            "overflow_webkit": doc_a["scrollWidth"] > doc_a["clientWidth"] + 1,
            "overflow_chromium": doc_b["scrollWidth"] > doc_b["clientWidth"] + 1,
        }
        over = [k for k, v in rows.items()
                if isinstance(v, dict) and v.get("over_threshold")]
        report["scenes"][name] = {
            "route": route, "viewport": [w, h], "rows": rows, "over_threshold": over,
            "console_webkit": a["console"], "console_chromium": b["console"],
            "screenshot_webkit": a["path"], "screenshot_chromium": b["path"],
        }
        print(f"{name}: over-threshold {over if over else 'none'}")

    # top offenders across all scenes
    worst = sorted(all_deltas, key=lambda d: d["worst"], reverse=True)[:25]
    report["worst_deltas"] = worst
    report["max_delta_all"] = round(max((d["worst"] for d in all_deltas), default=0), 3)
    report["count_over_threshold"] = sum(1 for d in all_deltas if d["worst"] > 2.0)

    (RAW / "layout-parity.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== worst deltas (WebKit - Chromium) ===")
    for d in worst[:15]:
        print(f"  {d['scene']:22s} {d['key']:16s} dx={d['x']:7.2f} dy={d['y']:7.2f} "
              f"dw={d['w']:7.2f} dh={d['h']:7.2f}")
    print(f"\nmax |delta| = {report['max_delta_all']} px; "
          f"{report['count_over_threshold']} measurements over 2 px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
