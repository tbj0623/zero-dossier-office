#!/usr/bin/env python3
"""Corrected, isolated probes for the three findings that the first pass left
ambiguous. Nothing here reuses a measurement from run_css_risks.py.

1. backdrop-filter — a SYNTHETIC, isolation test (checkerboard behind a fixed
   pane) proves whether Firefox paints backdrop-filter at all, independent of
   whatever happens to be behind the real header. Then the real sticky header is
   re-tested with high-contrast content (text) behind it and a settled scroll.
2. scroll-padding-top + scrollIntoView — scroll is allowed to STOP COMPLETELY
   (poll scrollY until stable for 5 frames) before measuring, because
   html{scroll-behavior:smooth} otherwise reports a mid-animation position.
3. text-wrap: balance on the hero h1 — measured on the HOME view (the h1 is
   display:none on the cabinet view, which is why the first pass read height 0).
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, SHOTS, now_iso

SETTLE_SCROLL = """async () => {
    // wait until scrollY has not changed for 5 consecutive frames (max 4 s)
    let last = -1, stable = 0, t0 = performance.now();
    while (performance.now() - t0 < 4000) {
        await new Promise(r => requestAnimationFrame(r));
        if (Math.abs(window.scrollY - last) < 0.01) stable++;
        else { stable = 0; last = window.scrollY; }
        if (stable >= 5) break;
    }
    return {scrollY: window.scrollY, stableFrames: stable};
}"""

SYNTH = """
<html><body style="margin:0">
<div style="position:fixed;inset:0;background:
   repeating-conic-gradient(#fff 0% 25%, #000 0% 50%) 50% / 24px 24px"></div>
<div id="pane" style="position:fixed;left:40px;top:40px;width:200px;height:120px;
   background:rgba(6,20,28,0.84);backdrop-filter:blur(12px) saturate(1.2);"></div>
<div id="paneNoBlur" style="position:fixed;left:40px;top:200px;width:200px;height:120px;
   background:rgba(6,20,28,0.84);"></div>
</body></html>
"""


def energy(path):
    g = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    out = np.zeros((g.shape[0] - 2, g.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            out += k[i, j] * g[i:g.shape[0] - 2 + i, j:g.shape[1] - 2 + j]
    return float(out.var())


out = {"when": now_iso(), "base": LIVE_BASE, "engines": {}}

with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        e = {"version": b.version}

        # ---------- 1a. synthetic backdrop-filter ----------
        ctx = b.new_context(viewport={"width": 400, "height": 400}, device_scale_factor=1)
        pg = ctx.new_page()
        pg.set_content(SYNTH)
        pg.wait_for_timeout(400)
        shot = SHOTS / f"bfsynth-{eng}.png"
        pg.screenshot(path=str(shot))
        im = Image.open(shot)
        crop_blur = im.crop((40, 40, 240, 160))
        crop_plain = im.crop((40, 200, 240, 320))
        pb = SHOTS / f"bfsynth-{eng}-blur-crop.png"
        pp = SHOTS / f"bfsynth-{eng}-plain-crop.png"
        crop_blur.save(pb)
        crop_plain.save(pp)
        e["backdrop_synthetic"] = {
            "energy_with_backdrop_filter": round(energy(pb), 3),
            "energy_without": round(energy(pp), 3),
            "ratio_with_over_without": round(energy(pb) / max(1e-9, energy(pp)), 4),
            "blur_actually_painted": energy(pb) < energy(pp) * 0.5,
            "computed": pg.evaluate("""() => {
                const a = getComputedStyle(document.querySelector('#pane'));
                return {backdropFilter: a.backdropFilter, webkit: a.webkitBackdropFilter,
                        supports: CSS.supports('backdrop-filter','blur(12px)')};
            }"""),
        }
        ctx.close()

        # ---------- 1b. real sticky header, high-contrast content behind ----------
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/cabinet", wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(600)
        # put the heading row directly under the sticky header
        pg.evaluate("""() => {
            const target = document.querySelector('#cabinet .case-card');
            const y = target.getBoundingClientRect().top + window.scrollY - 30;
            window.scrollTo(0, y);
        }""")
        pg.evaluate(SETTLE_SCROLL)
        pg.wait_for_timeout(300)
        on = SHOTS / f"bfreal-{eng}-on.png"
        pg.screenshot(path=str(on), clip={"x": 0, "y": 0, "width": 1440, "height": 64})
        pg.add_style_tag(content=".site-header{backdrop-filter:none !important;-webkit-backdrop-filter:none !important}")
        pg.wait_for_timeout(500)
        off = SHOTS / f"bfreal-{eng}-off.png"
        pg.screenshot(path=str(off), clip={"x": 0, "y": 0, "width": 1440, "height": 64})
        a = np.asarray(Image.open(on).convert("RGB"), dtype=np.int16)
        bb = np.asarray(Image.open(off).convert("RGB"), dtype=np.int16)
        d = np.abs(a - bb)
        e["backdrop_real_header"] = {
            "energy_on": round(energy(on), 3),
            "energy_off": round(energy(off), 3),
            "pct_pixels_differ_gt2": round(float((d.max(axis=2) > 2).mean() * 100), 3),
            "mean_abs_delta": round(float(d.mean()), 4),
            "max_abs_delta": int(d.max()),
            "scrollY": pg.evaluate("() => window.scrollY"),
        }
        ctx.close()

        # ---------- 2. scroll-padding + scrollIntoView (fully settled) ----------
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/case/NA-001", wait_until="networkidle", timeout=60000)
        pg.wait_for_selector("#slots .slot")
        pg.wait_for_timeout(400)
        res = {}
        for label, js_arg in (("auto", "{block:'start', behavior:'auto'}"),
                              ("instant", "{block:'start', behavior:'instant'}")):
            pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            pg.evaluate(SETTLE_SCROLL)
            pg.wait_for_timeout(200)
            try:
                pg.evaluate(f"() => document.querySelector('#slots').scrollIntoView({js_arg})")
            except Exception as exc:  # noqa: BLE001  (behavior:'instant' may be unsupported)
                res[label] = {"error": f"{type(exc).__name__}: {str(exc)[:120]}"}
                continue
            st = pg.evaluate(SETTLE_SCROLL)
            pg.wait_for_timeout(300)
            m = pg.evaluate("""() => {
                const s = document.querySelector('#slots').getBoundingClientRect();
                const h = document.querySelector('.site-header').getBoundingClientRect();
                const main = document.querySelector('main');
                const mr = main ? main.getBoundingClientRect() : null;
                return {slotsTop: Math.round(s.top * 100) / 100,
                        headerBottom: Math.round(h.bottom * 100) / 100,
                        mainTop: mr ? Math.round(mr.top * 100) / 100 : null,
                        gapBelowHeader: Math.round((s.top - h.bottom) * 100) / 100,
                        clearOfHeader: s.top >= h.bottom - 1,
                        scrollY: Math.round(window.scrollY)};
            }""")
            res[label] = {**st, **m}
        e["scroll_into_view"] = res

        e["scroll_padding_css"] = pg.evaluate("""() => ({
            html: getComputedStyle(document.documentElement).scrollPaddingTop,
            mainMargin: getComputedStyle(document.querySelector('main')).scrollMarginTop,
            viewMargin: document.querySelector('.view[data-active="true"]')
                ? getComputedStyle(document.querySelector('.view[data-active="true"]')).scrollMarginTop : null,
            scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
        })""")

        # also: a plain anchor jump to #main (skip link) — sticky-header clearance
        pg.goto(LIVE_BASE + "#/manual", wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(900)
        pg.evaluate(SETTLE_SCROLL)
        jump = pg.evaluate("""async () => {
            // #main may be re-rendered by the router after a hash change, so
            // re-query it after every await instead of holding a stale reference
            const waitFor = async (sel, ms = 2000) => {
                const t0 = performance.now();
                while (performance.now() - t0 < ms) {
                    const el = document.querySelector(sel);
                    if (el) return el;
                    await new Promise(r => requestAnimationFrame(r));
                }
                return null;
            };
            location.hash = '#main';
            await new Promise(r => setTimeout(r, 250));
            const target = await waitFor('#main');
            if (!target) return {error: '#main not present after hash change'};
            target.scrollIntoView();
            let last = -1, stable = 0, t0 = performance.now();
            while (performance.now() - t0 < 3000) {
              await new Promise(r => requestAnimationFrame(r));
              if (Math.abs(window.scrollY - last) < 0.01) stable++; else { stable = 0; last = window.scrollY; }
              if (stable >= 5) break;
            }
            const cur = document.querySelector('#main');
            if (!cur) return {error: '#main vanished during scroll'};
            const m = cur.getBoundingClientRect();
            const h = document.querySelector('.site-header').getBoundingClientRect();
            return {mainTop: Math.round(m.top), headerBottom: Math.round(h.bottom),
                    clear: m.top >= h.bottom - 1, gap: Math.round(m.top - h.bottom)};
        }""")
        e["skip_link_scroll"] = jump
        ctx.close()

        # ---------- 3. text-wrap: balance on the HOME hero h1 ----------
        e["hero_text"] = {}
        for name, w, h_ in (("w390", 390, 844), ("w768", 768, 1024), ("w1440", 1440, 900)):
            ctx = b.new_context(viewport={"width": w, "height": h_}, locale="zh-CN")
            pg = ctx.new_page()
            pg.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(600)
            e["hero_text"][name] = pg.evaluate("""() => {
                const h1 = document.querySelector('.hero h1');
                const cs = getComputedStyle(h1);
                const r = h1.getBoundingClientRect();
                const lh = parseFloat(cs.lineHeight);
                // count visual lines with a Range over the text nodes
                const range = document.createRange();
                range.selectNodeContents(h1);
                const rects = [...range.getClientRects()].filter(q => q.width > 1 && q.height > 1);
                const lines = [];
                for (const q of rects) {
                    const hit = lines.find(l => Math.abs(l.top - q.top) < 2);
                    if (hit) { hit.left = Math.min(hit.left, q.left); hit.right = Math.max(hit.right, q.right); }
                    else lines.push({top: Math.round(q.top), left: Math.round(q.left), right: Math.round(q.right)});
                }
                const widths = lines.map(l => Math.round((l.right - l.left) * 10) / 10);
                return {
                    textWrap: cs.textWrap, textWrapMode: cs.textWrapMode || null,
                    fontSize: cs.fontSize, lineHeight: cs.lineHeight,
                    height: Math.round(r.height * 100) / 100,
                    linesByGeometry: lh ? Math.round(r.height / lh * 100) / 100 : null,
                    lineRectCount: lines.length, lineWidths: widths,
                    widestLine: widths.length ? Math.max(...widths) : null,
                    narrowestLine: widths.length ? Math.min(...widths) : null,
                    balanceSpread: widths.length > 1 ? Math.round((Math.max(...widths) - Math.min(...widths)) * 10) / 10 : null,
                    overflowsHorizontally: h1.scrollWidth > h1.clientWidth + 1,
                    scrollWidth: h1.scrollWidth, clientWidth: h1.clientWidth,
                };
            }""")
            ctx.close()

        b.close()
        out["engines"][eng] = e
        print(eng, "done")

(RAW / "css-risks-confirm.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

for eng in ("chromium", "firefox"):
    d = out["engines"][eng]
    print("=" * 66)
    print(eng, d["version"])
    print(" 1a synthetic backdrop:", d["backdrop_synthetic"])
    print(" 1b real header       :", d["backdrop_real_header"])
    print(" 2  scrollIntoView    :", json.dumps(d["scroll_into_view"], ensure_ascii=False))
    print("    scroll-padding css:", d["scroll_padding_css"])
    print("    skip link        :", d["skip_link_scroll"])
    for n, v in d["hero_text"].items():
        print(f" 3  {n}: wrap={v['textWrap']} lines={v['lineRectCount']} widths={v['lineWidths']} spread={v['balanceSpread']} overflow={v['overflowsHorizontally']}")
print("-> raw/css-risks-confirm.json")
