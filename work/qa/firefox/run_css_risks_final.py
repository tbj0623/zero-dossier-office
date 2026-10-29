#!/usr/bin/env python3
"""Final disambiguation of the three candidate Firefox divergences.

1. backdrop-filter: is it a *build/pref* default in this Playwright Firefox, or
   does Gecko never paint it? Launch a second Firefox with
   `layout.css.backdrop-filter.enabled=true` and re-run the identical synthetic
   and real-header test. (Chromium has no equivalent switch.)
2. scroll-padding-top vs scrollIntoView: test in the MIDDLE of a long document,
   away from the scroll clamp, so "ignored" cannot be confused with "clamped".
3. text-wrap: balance on the hero h1: count lines by box height / line-height
   and by per-text-node rects only (Range over a block also yields the block's
   own full-width rect, which inflated the first attempt).
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from fx_common import LIVE_BASE, RAW, SHOTS, now_iso

SYNTH = """
<html><body style="margin:0">
<div style="position:fixed;inset:0;background:
   repeating-conic-gradient(#fff 0% 25%, #000 0% 50%) 50% / 24px 24px"></div>
<div id="pane" style="position:fixed;left:40px;top:40px;width:200px;height:120px;
   background:rgba(6,20,28,0.84);backdrop-filter:blur(12px) saturate(1.2);"></div>
</body></html>
"""

SETTLE_SCROLL = """async () => {
    let last = -1, stable = 0, t0 = performance.now();
    while (performance.now() - t0 < 4000) {
        await new Promise(r => requestAnimationFrame(r));
        if (Math.abs(window.scrollY - last) < 0.01) stable++;
        else { stable = 0; last = window.scrollY; }
        if (stable >= 5) break;
    }
    return {scrollY: window.scrollY, stableFrames: stable};
}"""


def energy(path):
    g = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    out = np.zeros((g.shape[0] - 2, g.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            out += k[i, j] * g[i:g.shape[0] - 2 + i, j:g.shape[1] - 2 + j]
    return float(out.var())


def backdrop_test(b, tag):
    ctx = b.new_context(viewport={"width": 400, "height": 400}, device_scale_factor=1)
    pg = ctx.new_page()
    pg.set_content(SYNTH)
    pg.wait_for_timeout(400)
    shot = SHOTS / f"bfpref-{tag}.png"
    pg.screenshot(path=str(shot))
    crop = Image.open(shot).crop((40, 40, 240, 160))
    cp = SHOTS / f"bfpref-{tag}-crop.png"
    crop.save(cp)
    e = energy(cp)
    sup = pg.evaluate("() => CSS.supports('backdrop-filter','blur(12px)')")
    ctx.close()
    return {"energy": round(e, 3), "supports": sup, "painted": e < 50}


out = {"when": now_iso(), "base": LIVE_BASE}

with sync_playwright() as p:
    res = {}

    # ---- 1. backdrop-filter, default vs pref-enabled ----
    fx_default = p.firefox.launch(headless=True)
    res["firefox_default"] = {"version": fx_default.version,
                              "backdrop": backdrop_test(fx_default, "firefox-default")}
    fx_default.close()

    try:
        fx_pref = p.firefox.launch(headless=True, firefox_user_prefs={
            "layout.css.backdrop-filter.enabled": True,
            "layout.css.backdrop-filter.force-enabled": True,
        })
        res["firefox_pref_enabled"] = {"version": fx_pref.version,
                                       "backdrop": backdrop_test(fx_pref, "firefox-pref")}
        fx_pref.close()
    except Exception as exc:  # noqa: BLE001
        res["firefox_pref_enabled"] = {"error": f"{type(exc).__name__}: {exc}"}

    ch = p.chromium.launch(headless=True)
    res["chromium"] = {"version": ch.version, "backdrop": backdrop_test(ch, "chromium")}

    # ---- 2. scroll-padding in the middle of a long document ----
    res["scroll_padding_midpage"] = {}
    for eng, br in (("chromium", ch), ("firefox", p.firefox.launch(headless=True))):
        ctx = br.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + "#/cabinet", wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(700)
        # pick a card in the middle of the page, way above the end
        r = pg.evaluate("""async () => {
            const cards = [...document.querySelectorAll('#cabinet .case-card')];
            const t = cards[2] || cards[0];
            window.scrollTo(0, 0);
            let last=-1, stable=0, t0=performance.now();
            while (performance.now()-t0 < 3000) {
              await new Promise(r=>requestAnimationFrame(r));
              if (Math.abs(window.scrollY-last)<0.01) stable++; else { stable=0; last=window.scrollY; }
              if (stable>=5) break;
            }
            return {top: t.getBoundingClientRect().top + window.scrollY,
                    docH: document.documentElement.scrollHeight,
                    maxScroll: document.documentElement.scrollHeight - window.innerHeight};
        }""")
        pg.evaluate("""() => {
            const cards = [...document.querySelectorAll('#cabinet .case-card')];
            (cards[2] || cards[0]).scrollIntoView({block: 'start', behavior: 'auto'});
        }""")
        st = pg.evaluate(SETTLE_SCROLL)
        m = pg.evaluate("""() => {
            const cards = [...document.querySelectorAll('#cabinet .case-card')];
            const t = (cards[2] || cards[0]).getBoundingClientRect();
            const h = document.querySelector('.site-header').getBoundingClientRect();
            return {cardTop: Math.round(t.top * 100) / 100, headerBottom: Math.round(h.bottom * 100) / 100,
                    gap: Math.round((t.top - h.bottom) * 100) / 100,
                    clear: t.top >= h.bottom - 1,
                    expectedGapIfPaddingApplied: 80 - Math.round(h.bottom)};
        }""")
        res["scroll_padding_midpage"][eng] = {**r, **st, **m,
                                              "docScrollPaddingTop": pg.evaluate(
                                                  "() => getComputedStyle(document.documentElement).scrollPaddingTop")}
        ctx.close()
        if eng == "firefox":
            br.close()

    # ---- 3. hero h1 text-wrap, honest line counting ----
    res["hero_h1"] = {}
    for eng, br in (("chromium", ch), ("firefox", p.firefox.launch(headless=True))):
        res["hero_h1"][eng] = {}
        for name, w, h_ in (("w390", 390, 844), ("w768", 768, 1024), ("w1440", 1440, 900)):
            ctx = br.new_context(viewport={"width": w, "height": h_}, locale="zh-CN")
            pg = ctx.new_page()
            pg.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(600)
            res["hero_h1"][eng][name] = pg.evaluate("""() => {
                const h1 = document.querySelector('.hero h1');
                const cs = getComputedStyle(h1);
                const r = h1.getBoundingClientRect();
                const lh = parseFloat(cs.lineHeight);
                // per-text-node rects only (no block box)
                const rects = [];
                (function walk(n) {
                    if (n.nodeType === 3 && n.textContent.trim()) {
                        const rg = document.createRange();
                        rg.selectNodeContents(n);
                        for (const q of rg.getClientRects()) if (q.width > 1 && q.height > 1) rects.push(q);
                    } else if (n.nodeType === 1) { for (const c of n.childNodes) walk(c); }
                })(h1);
                const tops = [...new Set(rects.map(q => Math.round(q.top)))].sort((a,b)=>a-b);
                // merge tops that are within 2px (same visual line)
                const lines = [];
                for (const t of tops) {
                    const hit = lines.find(l => Math.abs(l.top - t) < 2);
                    if (hit) hit.top = Math.min(hit.top, t); else lines.push({top: t});
                }
                const accent = h1.querySelector('.accent');
                return {
                    textWrap: cs.textWrap, fontSize: cs.fontSize, lineHeight: cs.lineHeight,
                    height: Math.round(r.height * 100) / 100,
                    linesByHeight: lh ? Math.round(r.height / lh * 100) / 100 : null,
                    textNodeRects: rects.length,
                    linesByTextNodes: lines.length,
                    accentDisplay: accent ? getComputedStyle(accent).display : null,
                    overflows: h1.scrollWidth > h1.clientWidth + 1,
                    scrollWidth: h1.scrollWidth, clientWidth: h1.clientWidth,
                    heroHeight: Math.round(document.querySelector('.hero').getBoundingClientRect().height * 100) / 100,
                };
            }""")
            ctx.close()
        br.close()

    ch.close()

out["results"] = res
(RAW / "css-risks-final.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps({k: v for k, v in res.items() if k in ("firefox_default", "firefox_pref_enabled", "chromium")},
                 ensure_ascii=False, indent=2))
print("\n--- scroll-padding midpage ---")
print(json.dumps(res["scroll_padding_midpage"], ensure_ascii=False, indent=2))
print("\n--- hero h1 ---")
print(json.dumps(res["hero_h1"], ensure_ascii=False, indent=2))
print("-> raw/css-risks-final.json")
