#!/usr/bin/env python3
"""Corrected final checks (previous attempt cropped the wrong region and reused
a stale measurement — this file re-measures everything from scratch).

1. backdrop-filter: compare, in headless AND headed, the energy of
   (a) a pane WITH backdrop-filter, (b) an identical pane WITHOUT it,
   both over the same checkerboard, cropped to the pane rectangle only.
2. dialog Tab: press Tab six times, measuring document.activeElement and
   document.hasFocus() after EVERY press, in both engines.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from fx_common import RAW, SHOTS, now_iso

SYNTH = """
<html><body style="margin:0">
<div style="position:fixed;inset:0;background:
   repeating-conic-gradient(#fff 0% 25%, #000 0% 50%) 50% / 24px 24px"></div>
<div id="blur" style="position:fixed;left:20px;top:20px;width:200px;height:120px;
   background:rgba(6,20,28,0.5);backdrop-filter:blur(12px) saturate(1.2)"></div>
<div id="plain" style="position:fixed;left:20px;top:200px;width:200px;height:120px;
   background:rgba(6,20,28,0.5)"></div>
</body></html>
"""

DIALOG = """
<html><body>
<button id="opener">open</button>
<dialog id="d"><h2>T</h2><button id="cancel">cancel</button><button id="ok">ok</button></dialog>
<script>
document.getElementById('opener').addEventListener('click', () => {
  document.getElementById('d').showModal(); document.getElementById('cancel').focus();
});
</script>
</body></html>
"""


def energy(im: Image.Image) -> float:
    g = np.asarray(im.convert("L"), dtype=np.float64)
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    o = np.zeros((g.shape[0] - 2, g.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            o += k[i, j] * g[i:g.shape[0] - 2 + i, j:g.shape[1] - 2 + j]
    return float(o.var())


def backdrop(b, tag):
    ctx = b.new_context(viewport={"width": 400, "height": 360}, device_scale_factor=1)
    pg = ctx.new_page()
    pg.set_content(SYNTH)
    pg.wait_for_timeout(500)
    shot = SHOTS / f"bf2-{tag}.png"
    pg.screenshot(path=str(shot))
    im = Image.open(shot)
    e_blur = energy(im.crop((20, 20, 220, 140)))
    e_plain = energy(im.crop((20, 200, 220, 320)))
    ctx.close()
    return {
        "energy_pane_with_backdrop_filter": round(e_blur, 3),
        "energy_pane_without": round(e_plain, 3),
        "ratio": round(e_blur / max(1e-9, e_plain), 4),
        "blur_painted": e_blur < e_plain * 0.5,
    }


out = {"when": now_iso(), "backdrop_by_mode": {}, "dialog_tab": {}}

with sync_playwright() as p:
    for mode in ("headless", "headed"):
        for eng in ("firefox", "chromium"):
            key = f"{eng}-{mode}"
            try:
                launcher = p.firefox if eng == "firefox" else p.chromium
                b = launcher.launch(headless=(mode == "headless"))
                rec = {"version": b.version, **backdrop(b, key)}
                b.close()
                out["backdrop_by_mode"][key] = rec
                print(key, rec)
            except Exception as exc:  # noqa: BLE001
                out["backdrop_by_mode"][key] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
                print(key, "ERROR", exc)

    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        ctx = b.new_context(viewport={"width": 800, "height": 600})
        pg = ctx.new_page()
        pg.set_content(DIALOG)
        pg.click("#opener")
        pg.wait_for_timeout(400)
        steps = [{"step": "open", **pg.evaluate("""() => {
            const a = document.activeElement;
            return {id: a.id || a.tagName.toLowerCase(), hasFocus: document.hasFocus(),
                    inDialog: !!(a.closest && a.closest('#d'))}; }""")}]
        for i in range(6):
            pg.keyboard.press("Tab")
            pg.wait_for_timeout(120)
            steps.append({"step": f"Tab{i+1}", **pg.evaluate("""() => {
                const a = document.activeElement;
                return {id: a.id || a.tagName.toLowerCase(), hasFocus: document.hasFocus(),
                        inDialog: !!(a.closest && a.closest('#d'))}; }""")})
        out["dialog_tab"][eng] = {"version": b.version, "steps": steps}
        ctx.close()
        b.close()

(RAW / "backdrop-and-dialog-final.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n=== dialog Tab sequence (cancel focused at open) ===")
for eng, d in out["dialog_tab"].items():
    print(f"{eng} {d['version']}:")
    for s in d["steps"]:
        print(f"   {s['step']:6s} -> {s['id']:8s} inDialog={s['inDialog']} document.hasFocus={s['hasFocus']}")
print("-> raw/backdrop-and-dialog-final.json")
