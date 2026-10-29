#!/usr/bin/env python3
"""Probe: does WebKit actually PAINT backdrop-filter on the sticky header?

The header's authored background is a 0.97 -> 0.94 alpha gradient, so *any*
blur behind it is attenuated to 3–6% — a naive "with vs without backdrop-filter"
comparison would read 0.00 px difference even if the blur worked perfectly.
So this probe uses a 4-cell design that isolates the two variables:

  A  authored                      (gradient 0.97/0.94 + blur 12px)
  B  authored, backdrop-filter:none (gradient 0.97/0.94, no blur)
  C  low-alpha bg (0.18), no blur   (control: translucent, no blur)
  D  low-alpha bg (0.18) + blur 20px

Evidence that WebKit paints the blur = C vs D differ, with D's high-frequency
energy *lower* than C's. Evidence about the shipped header = A vs B.
Writes raw/backdrop-probe.json + shots/wk-backdrop-*.png.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from wk_common import BASE, RAW, SHOTS, now_iso


def shot(page, name: str) -> np.ndarray:
    p = SHOTS / name
    page.screenshot(path=str(p), full_page=False)
    return np.array(Image.open(p).convert("RGB"))


def hf_energy(arr: np.ndarray) -> float:
    g = arr.astype(np.float64).mean(axis=2)
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    return float(lap.mean())


def metrics(arr: np.ndarray) -> dict:
    return {"w": int(arr.shape[1]), "h": int(arr.shape[0]),
            "mean_rgb": [round(float(x), 2) for x in arr.reshape(-1, 3).mean(axis=0)],
            "hf_energy": round(hf_energy(arr), 4),
            "std": round(float(arr.astype(np.float64).std()), 3)}


def main() -> int:
    out: dict = {"when": now_iso(), "base": BASE, "method": "4-cell A/B/C/D pixel isolation"}
    with sync_playwright() as p:
        b = p.webkit.launch(headless=True)
        out["version"] = b.version
        page = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle", timeout=45000)
        page.wait_for_selector("#slots .slot", timeout=15000)
        page.wait_for_timeout(900)
        page.evaluate("() => window.scrollTo(0, 380)")
        page.wait_for_timeout(700)

        info = page.evaluate("""() => {
            const h = document.querySelector('.site-header');
            const cs = getComputedStyle(h);
            const r = h.getBoundingClientRect();
            return {backdropFilter: cs.backdropFilter, webkitBackdropFilter: cs.webkitBackdropFilter,
                    backgroundImage: cs.backgroundImage, backgroundColor: cs.backgroundColor,
                    top: r.top, height: r.height, width: r.width, scrollY: window.scrollY};
        }""")
        out["computed"] = info
        h = int(round(info["height"]))

        def band(img):
            return img[0:h, :, :]

        # A — authored
        A = band(shot(page, "wk-backdrop-A-authored.png"))

        # B — same background, no backdrop-filter
        page.add_style_tag(content=".site-header{backdrop-filter:none !important;-webkit-backdrop-filter:none !important}")
        page.wait_for_timeout(450)
        B = band(shot(page, "wk-backdrop-B-noblur.png"))

        # C — translucent bg, no blur
        page.add_style_tag(content=""".site-header{backdrop-filter:none !important;-webkit-backdrop-filter:none !important;
            background:rgb(6 20 28 / 0.18) !important;}""")
        page.wait_for_timeout(450)
        C = band(shot(page, "wk-backdrop-C-translucent-noblur.png"))

        # D — translucent bg + strong blur
        page.add_style_tag(content=""".site-header{backdrop-filter:blur(20px) !important;-webkit-backdrop-filter:blur(20px) !important;
            background:rgb(6 20 28 / 0.18) !important;}""")
        page.wait_for_timeout(450)
        D = band(shot(page, "wk-backdrop-D-translucent-blur20.png"))

        diff = lambda x, y: float(np.abs(x.astype(np.int16) - y.astype(np.int16)).mean())
        out["cells"] = {"A_authored": metrics(A), "B_same_bg_no_blur": metrics(B),
                        "C_translucent_no_blur": metrics(C), "D_translucent_blur20": metrics(D)}
        out["deltas"] = {
            "A_vs_B_mean_abs_px": round(diff(A, B), 4),
            "A_vs_B_max_abs_px": int(np.abs(A.astype(np.int16) - B.astype(np.int16)).max()),
            "C_vs_D_mean_abs_px": round(diff(C, D), 4),
            "C_vs_D_max_abs_px": int(np.abs(C.astype(np.int16) - D.astype(np.int16)).max()),
        }
        out["deltas"]["C_hf_to_D_hf_ratio"] = round(
            out["cells"]["D_translucent_blur20"]["hf_energy"] / max(out["cells"]["C_translucent_no_blur"]["hf_energy"], 1e-9), 4)
        out["verdict_inputs"] = {
            "blur_is_painted_when_visible": out["deltas"]["C_vs_D_mean_abs_px"] > 1.0
            and out["deltas"]["C_hf_to_D_hf_ratio"] < 0.8,
            "authored_blur_is_visually_inert": out["deltas"]["A_vs_B_max_abs_px"] <= 1,
            "opaque_fallback_carries_header": out["deltas"]["A_vs_B_max_abs_px"] <= 1,
        }

        # readability of header text against its own painted band
        contrast = page.evaluate("""() => {
            const parse = (s) => { const m = s.match(/rgba?\\(([^)]+)\\)/); if(!m) return null;
                const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number);
                return {r:p[0], g:p[1], b:p[2], a:p.length>3?p[3]:1}; };
            const lum = (c) => { const f=(v)=>{v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};
                return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
            const res = {};
            const els = {brandName: document.querySelector('.brand__name'),
                         brandSub: document.querySelector('.brand__sub'),
                         navLink: document.querySelector('.site-nav a'),
                         langBtn: document.querySelector('.nav-lang')};
            for (const [k, el] of Object.entries(els)) {
                if (!el) { res[k] = null; continue; }
                const cs = getComputedStyle(el);
                const fg = parse(cs.color);
                // darkest authored background of the header gradient
                const bg = {r:5, g:17, b:24, a:1};
                const b2 = {r: fg.r*fg.a+bg.r*(1-fg.a), g: fg.g*fg.a+bg.g*(1-fg.a), b: fg.b*fg.a+bg.b*(1-fg.a)};
                const L1 = lum(b2)+0.05, L2 = lum(bg)+0.05;
                res[k] = {color: cs.color, fontSize: cs.fontSize,
                          ratioOnDarkestHeader: Math.round((Math.max(L1,L2)/Math.min(L1,L2))*100)/100};
            }
            return res;
        }""")
        out["text_contrast"] = contrast

        page.close()
        b.close()

    (RAW / "backdrop-probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
