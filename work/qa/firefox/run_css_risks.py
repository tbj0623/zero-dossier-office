#!/usr/bin/env python3
"""STEP 4 — the six named CSS risks, measured (not assumed).

1. backdrop-filter on the sticky header: prove it PAINTS a blur, by comparing the
   same header strip with the property forced off via injected CSS.
2. text-wrap: balance: support, and whether the h1 actually balances / does not
   explode (height, line count via height/line-height, overflow).
3. aspect-ratio on .case-card__thumb: computed ratio vs 16/9 at three widths.
4. clamp() font sizes: computed px at 390/768/1440, monotonic, inside bounds.
5. :focus-visible: keyboard focus shows a ring; a mouse click must NOT.
6. scroll-padding-top + scrollIntoView: after the app scrolls an element to the
   top, is it actually clear of the 64 px sticky header?
"""
from __future__ import annotations

import json

from PIL import Image
from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, SHOTS, now_iso


def laplacian_energy(im: Image.Image) -> float:
    """High-frequency energy; blurred content scores lower."""
    import numpy as np
    g = np.asarray(im.convert("L"), dtype=np.float64)
    if g.size < 9:
        return 0.0
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    out = np.zeros((g.shape[0] - 2, g.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            out += k[i, j] * g[i:g.shape[0] - 2 + i, j:g.shape[1] - 2 + j]
    return float(out.var())


def header_blur_test(page, tag: str) -> dict:
    """Scroll so real content sits under the sticky header, then compare the
    header strip with backdrop-filter on vs off."""
    page.evaluate("() => window.scrollTo(0, 900)")
    page.wait_for_timeout(700)
    on_path = SHOTS / f"bf-{tag}-on.png"
    page.screenshot(path=str(on_path), clip={"x": 0, "y": 0, "width": 1440, "height": 64})
    on_energy = laplacian_energy(Image.open(on_path))

    page.add_style_tag(content="""
        .site-header { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; }
    """)
    page.wait_for_timeout(700)
    off_path = SHOTS / f"bf-{tag}-off.png"
    page.screenshot(path=str(off_path), clip={"x": 0, "y": 0, "width": 1440, "height": 64})
    off_energy = laplacian_energy(Image.open(off_path))

    import numpy as np
    a = np.asarray(Image.open(on_path).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(off_path).convert("RGB"), dtype=np.int16)
    delta = np.abs(a - b)
    return {
        "energy_on": round(on_energy, 3),
        "energy_off": round(off_energy, 3),
        "energy_delta_pct": round(100 * (on_energy - off_energy) / max(1e-9, off_energy), 2),
        "mean_abs_rgb_delta_on_vs_off": round(float(delta.mean()), 4),
        "pct_pixels_differ_gt2": round(float((delta.max(axis=2) > 2).mean() * 100), 3),
        "shots": {"on": str(on_path), "off": str(off_path)},
    }


SCENES = [("w390", 390, 844), ("w768", 768, 1024), ("w1440", 1440, 900)]

out = {"when": now_iso(), "base": LIVE_BASE, "engines": {}}

with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        eng_out = {"version": b.version}

        # ---- 1. backdrop-filter (1440 only) ----
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN", device_scale_factor=1)
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/cabinet", wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(800)
        eng_out["backdrop_filter"] = header_blur_test(pg, f"{eng}-header")
        # also confirm the sticky header really is sticky
        eng_out["header_sticky"] = pg.evaluate("""() => {
            const h = document.querySelector('.site-header');
            const r = h.getBoundingClientRect();
            return {position: getComputedStyle(h).position, top: Math.round(r.top),
                    scrollY: Math.round(window.scrollY), height: Math.round(r.height)};
        }""")
        ctx.close()

        # ---- 2/3/4. text-wrap, aspect-ratio, clamp ----
        eng_out["scenes"] = {}
        for name, w, h in SCENES:
            ctx = b.new_context(viewport={"width": w, "height": h}, locale="zh-CN", device_scale_factor=1)
            pg = ctx.new_page()
            pg.goto(LIVE_BASE + "#/cabinet", wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(600)
            data = pg.evaluate("""() => {
                const h1 = document.querySelector('.hero h1');
                const h1cs = h1 ? getComputedStyle(h1) : null;
                const h1r = h1 ? h1.getBoundingClientRect() : null;
                const lh = h1cs ? parseFloat(h1cs.lineHeight) : 0;
                const thumb = document.querySelector('.case-card__thumb');
                const tr = thumb ? thumb.getBoundingClientRect() : null;
                const fs = (sel) => { const e = document.querySelector(sel); return e ? getComputedStyle(e).fontSize : null; };
                return {
                    h1: h1 ? {
                        textWrap: h1cs.textWrap, fontSize: h1cs.fontSize, lineHeight: h1cs.lineHeight,
                        width: Math.round(h1r.width * 100) / 100,
                        height: Math.round(h1r.height * 100) / 100,
                        approxLines: lh ? Math.round(h1r.height / lh * 100) / 100 : null,
                        scrollWidth: h1.scrollWidth, clientWidth: h1.clientWidth,
                        overflows: h1.scrollWidth > h1.clientWidth + 1,
                    } : null,
                    thumb: thumb ? {
                        width: Math.round(tr.width * 100) / 100, height: Math.round(tr.height * 100) / 100,
                        ratio: Math.round(tr.width / tr.height * 10000) / 10000,
                        target1666: Math.round(16 / 9 * 10000) / 10000,
                        computedAspectRatio: getComputedStyle(thumb).aspectRatio,
                    } : null,
                    fonts: {
                        body: fs('body'), h1: fs('.hero h1'), lede: fs('.hero__lede'),
                        cardTitle: fs('.case-card__title'), navLink: fs('.site-nav a'),
                    },
                    docScrollWidth: document.documentElement.scrollWidth,
                    docClientWidth: document.documentElement.clientWidth,
                };
            }""")
            eng_out["scenes"][name] = data
            ctx.close()

        # ---- 5. :focus-visible keyboard vs mouse ----
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/case/NA-001", wait_until="networkidle", timeout=60000)
        pg.wait_for_selector("#btn-submit")
        pg.mouse.click(5, 5)  # neutral click so nothing is focused by keyboard
        pg.wait_for_timeout(150)
        pg.keyboard.press("Tab")
        kb = pg.evaluate("""() => { const a = document.activeElement; const cs = getComputedStyle(a);
            return {matchesFocusVisible: a.matches(':focus-visible'), outlineStyle: cs.outlineStyle,
                    outlineWidth: cs.outlineWidth, outlineColor: cs.outlineColor, id: a.id || a.className}; }""")
        pg.click("#btn-submit")
        pg.wait_for_timeout(200)
        mouse = pg.evaluate("""() => { const a = document.activeElement; const cs = getComputedStyle(a);
            return {matchesFocusVisible: a.matches(':focus-visible'), outlineStyle: cs.outlineStyle,
                    outlineWidth: cs.outlineWidth, id: a.id || a.className}; }""")
        eng_out["focus_visible"] = {"keyboard": kb, "mouse": mouse}
        ctx.close()

        # ---- 6. scroll-padding-top + scrollIntoView ----
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/case/NA-001", wait_until="networkidle", timeout=60000)
        pg.wait_for_selector("#slots .slot")
        sp = pg.evaluate("""() => ({
            htmlScrollPaddingTop: getComputedStyle(document.documentElement).scrollPaddingTop,
            supports: CSS.supports('scroll-padding-top', '80px'),
            mainScrollMargin: getComputedStyle(document.querySelector('main') || document.body).scrollMarginTop,
        })""")
        # scroll far down, then ask the app's own target (the board) to scrollIntoView
        pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.querySelector('#slots').scrollIntoView({block: 'start', behavior: 'auto'})")
        pg.wait_for_timeout(600)
        si = pg.evaluate("""() => {
            const slots = document.querySelector('#slots').getBoundingClientRect();
            const hdr = document.querySelector('.site-header').getBoundingClientRect();
            return {slotsTop: Math.round(slots.top * 100) / 100,
                    headerBottom: Math.round(hdr.bottom * 100) / 100,
                    scrollY: Math.round(window.scrollY),
                    clearOfHeader: slots.top >= hdr.bottom - 1,
                    gap: Math.round((slots.top - hdr.bottom) * 100) / 100};
        }""")
        eng_out["scroll_padding"] = {**sp, "scrollIntoView": si}
        ctx.close()

        # ---- 6b. anchor navigation to a section (#main skip link style) ----
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/cabinet", wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(700)
        pg.click("#cabinet .case-card a.btn")
        pg.wait_for_timeout(900)
        eng_out["anchor_nav"] = pg.evaluate("""() => {
            const t = document.querySelector('#case-title');
            const hdr = document.querySelector('.site-header').getBoundingClientRect();
            const r = t ? t.getBoundingClientRect() : null;
            return r ? {titleTop: Math.round(r.top), headerBottom: Math.round(hdr.bottom),
                        hiddenUnderHeader: r.top < hdr.bottom - 2, scrollY: Math.round(window.scrollY)} : null;
        }""")
        ctx.close()

        b.close()
        out["engines"][eng] = eng_out
        print(eng, "done")

(RAW / "css-risks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

for eng in ("chromium", "firefox"):
    d = out["engines"][eng]
    print("=" * 60)
    print(eng, d["version"])
    print(" backdrop:", d["backdrop_filter"])
    print(" sticky:", d["header_sticky"])
    for n, s in d["scenes"].items():
        print(f"  {n}: h1 wrap={s['h1']['textWrap']} {s['h1']['fontSize']} h={s['h1']['height']} lines~{s['h1']['approxLines']} overflows={s['h1']['overflows']}"
              f" | thumb {s['thumb']['width']}x{s['thumb']['height']} ratio={s['thumb']['ratio']} (16/9={s['thumb']['target1666']})")
        print(f"      fonts: {s['fonts']}")
    print(" focus-visible kb:", d["focus_visible"]["keyboard"])
    print(" focus-visible mouse:", d["focus_visible"]["mouse"])
    print(" scroll-padding:", d["scroll_padding"])
    print(" anchor nav:", d["anchor_nav"])
print("-> raw/css-risks.json")
