#!/usr/bin/env python3
"""Why is backdrop-filter not painted by this Firefox?

Gecko has supported backdrop-filter since Firefox 103, so a 153 build that parses
but does not paint it is suspicious. The likeliest cause in a test harness is the
compositor: backdrop-filter needs a composited layer, and without GPU/WebRender
acceleration Firefox may drop it. Probe the actual renderer in both engines.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import RAW, now_iso

JS = """() => {
  const gpu = {};
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
    if (gl) {
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      gpu.vendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
      gpu.renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
      gpu.version = gl.getParameter(gl.VERSION);
    } else { gpu.webgl = 'unavailable'; }
  } catch (e) { gpu.error = String(e); }
  return {
    gpu,
    dpr: window.devicePixelRatio,
    hardwareConcurrency: navigator.hardwareConcurrency,
    supportsBackdrop: CSS.supports('backdrop-filter', 'blur(4px)'),
    // does a backdrop-filter element create its own stacking/compositing layer?
    paintTest: (() => {
      const d = document.createElement('div');
      d.style.cssText = 'position:fixed;width:50px;height:50px;backdrop-filter:blur(4px)';
      document.body.appendChild(d);
      const cs = getComputedStyle(d);
      const out = {parsed: cs.backdropFilter, willChange: cs.willChange};
      d.remove();
      return out;
    })(),
  };
}"""

out = {"when": now_iso()}
with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        pg = b.new_page()
        pg.goto("about:blank")
        out[eng] = {"version": b.version, **pg.evaluate(JS)}
        b.close()


# Firefox prefs the browser reports about itself
with sync_playwright() as p:
    b = p.firefox.launch(headless=True)
    pg = b.new_page()
    try:
        pg.goto("about:support", wait_until="domcontentloaded", timeout=20000)
        txt = pg.inner_text("body")[:4000]
        out["firefox_about_support"] = txt
    except Exception as exc:  # noqa: BLE001
        out["firefox_about_support"] = f"unavailable: {type(exc).__name__}: {str(exc)[:150]}"
    b.close()

(RAW / "gpu-probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
for eng in ("chromium", "firefox"):
    print(eng, out[eng]["version"], json.dumps(out[eng]["gpu"], ensure_ascii=False))
    print("   supportsBackdrop:", out[eng]["supportsBackdrop"], "paintTest:", out[eng]["paintTest"])
print("\nabout:support (first 1200 chars):")
print(out["firefox_about_support"][:1200])
print("-> raw/gpu-probe.json")
