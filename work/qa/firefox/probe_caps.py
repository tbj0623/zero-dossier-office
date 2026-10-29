#!/usr/bin/env python3
"""Capability probe: what Playwright 1.62 + Firefox 153 actually supports here."""
import json
from playwright.sync_api import sync_playwright

Q = """() => ({
  hoverHover: matchMedia('(hover: hover)').matches,
  hoverNone: matchMedia('(hover: none)').matches,
  pointerCoarse: matchMedia('(pointer: coarse)').matches,
  pointerFine: matchMedia('(pointer: fine)').matches,
  anyHover: matchMedia('(any-hover: hover)').matches,
  maxTouchPoints: navigator.maxTouchPoints,
  touchEvent: 'ontouchstart' in window,
  ua: navigator.userAgent,
})"""

out = {}
with sync_playwright() as p:
    b = p.firefox.launch(headless=True)
    for label, kw in [
        ("desktop-1440", dict(viewport={"width": 1440, "height": 900})),
        ("mobile-390-ismobile", dict(viewport={"width": 390, "height": 844},
                                     is_mobile=True, has_touch=True, device_scale_factor=2)),
        ("mobile-390-touch-only", dict(viewport={"width": 390, "height": 844},
                                       has_touch=True, device_scale_factor=2)),
    ]:
        try:
            c = b.new_context(**kw)
            pg = c.new_page()
            pg.goto("about:blank")
            out[label] = {"ok": True, **pg.evaluate(Q)}
            c.close()
        except Exception as e:  # noqa: BLE001
            out[label] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    b.close()

print(json.dumps(out, ensure_ascii=False, indent=2))
