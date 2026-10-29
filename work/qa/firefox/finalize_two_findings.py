#!/usr/bin/env python3
"""Final refinements that decide how these two findings must be reported.

1. backdrop-filter: headless vs HEADED Firefox. If the blur paints in a headed
   window but not in headless, the gap is a headless-capture limitation of the
   test harness, NOT a defect of the site in real Firefox. Same synthetic page
   as before, no site code involved.
2. Dialog Tab: separate "advance between the two buttons" from "wrap around
   past the last button". Also record document.hasFocus() to detect focus that
   has left the page (browser chrome) instead of being trapped.
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
<div id="pane" style="position:fixed;left:40px;top:40px;width:200px;height:120px;
   background:rgba(6,20,28,0.84);backdrop-filter:blur(12px) saturate(1.2);"></div>
</body></html>
"""

DIALOG = """
<html><body>
<button id="opener">open</button>
<dialog id="d"><h2>T</h2><button id="cancel">cancel</button><button id="ok">ok</button></dialog>
<script>
window.__ev = [];
document.addEventListener('focusin', e => window.__ev.push('in:' + (e.target.id || e.target.tagName)));
document.addEventListener('focusout', e => window.__ev.push('out:' + (e.target.id || e.target.tagName)));
document.getElementById('opener').addEventListener('click', () => {
  document.getElementById('d').showModal(); document.getElementById('cancel').focus();
});
</script>
</body></html>
"""


def energy(path):
    g = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    o = np.zeros((g.shape[0] - 2, g.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            o += k[i, j] * g[i:g.shape[0] - 2 + i, j:g.shape[1] - 2 + j]
    return float(o.var())


def backdrop(b, tag):
    ctx = b.new_context(viewport={"width": 400, "height": 400}, device_scale_factor=1)
    pg = ctx.new_page()
    pg.set_content(SYNTH)
    pg.wait_for_timeout(500)
    shot = SHOTS / f"bfmode-{tag}.png"
    pg.screenshot(path=str(shot))
    e = energy(shot)
    # reference energy of the fully sharp checkerboard region
    ctx.close()
    return {"energy_full": round(e, 3), "blurred": e < 100}


out = {"when": now_iso()}

with sync_playwright() as p:
    # ---------- 1. headless vs headed ----------
    out["backdrop_modes"] = {}
    for mode in ("headless", "headed"):
        for eng in ("firefox", "chromium"):
            key = f"{eng}-{mode}"
            try:
                launcher = p.firefox if eng == "firefox" else p.chromium
                b = launcher.launch(headless=(mode == "headless"))
                out["backdrop_modes"][key] = {"version": b.version, **backdrop(b, key)}
                b.close()
            except Exception as exc:  # noqa: BLE001
                out["backdrop_modes"][key] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}

    # ---------- 2. dialog: advance vs wrap ----------
    out["dialog_tab"] = {}
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        ctx = b.new_context(viewport={"width": 800, "height": 600})
        pg = ctx.new_page()
        pg.set_content(DIALOG)
        pg.click("#opener")
        pg.wait_for_timeout(400)

        def rec(label):
            return {"label": label, **pg.evaluate("""() => {
                const a = document.activeElement;
                return {id: a.id || a.tagName.toLowerCase(),
                        hasFocus: document.hasFocus(),
                        inDialog: !!(a.closest && a.closest('#d'))};
            }""")}

        seq = [rec("open(cancel focused)")]
        seq.append({"label": "Tab#1 -> ?", **({} if not pg.keyboard.press("Tab") else {}), **pg.evaluate(
            """() => { const a = document.activeElement; return {id: a.id||a.tagName.toLowerCase(),
                 hasFocus: document.hasFocus(), inDialog: !!(a.closest && a.closest('#d'))}; }""")})
        pg.wait_for_timeout(150)
        seq.append({"label": "Tab#2 -> ?", **pg.evaluate(
            """() => { const a = document.activeElement; return {id: a.id||a.tagName.toLowerCase(),
                 hasFocus: document.hasFocus(), inDialog: !!(a.closest && a.closest('#d'))}; }"""),
            **({"__note": "measured after keypress"} if False else {})})
        # do it cleanly: press then measure
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(150)
        seq.append(rec("Tab(after 2 presses)"))
        ev = pg.evaluate("() => window.__ev")
        out["dialog_tab"][eng] = {"version": b.version, "seq": seq, "events": ev}
        ctx.close()
        b.close()

(RAW / "backdrop-modes-and-dialog-tab.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print("=== backdrop-filter by display mode ===")
for k, v in out["backdrop_modes"].items():
    print(f"  {k:20s} {v}")
print("\n=== dialog tab (cancel focused at open) ===")
for eng, d in out["dialog_tab"].items():
    print(f"  {eng} {d['version']}: {[(s['label'], s.get('id'), s.get('hasFocus'), s.get('inDialog')) for s in d['seq']]}")
    print(f"      events: {d['events']}")
print("-> raw/backdrop-modes-and-dialog-tab.json")
