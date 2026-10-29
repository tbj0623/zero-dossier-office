#!/usr/bin/env python3
"""Is the dialog Tab-cycle difference caused by the SITE or by Gecko/Playwright?

Minimal repro with no site code at all: a native <dialog> with two buttons and
showModal(), opened from a button. Tab is pressed 8 times; we record the identity
of document.activeElement and the focusin target at every step, in both engines.
If Firefox also "sticks" here, the behaviour is the engine's, not the site's.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import RAW, now_iso

HTML = """
<html><body>
<button id="before">before</button>
<button id="opener">open</button>
<button id="after">after</button>
<dialog id="d">
  <h2>Title</h2>
  <button id="cancel">cancel</button>
  <button id="ok">ok</button>
</dialog>
<script>
  window.__events = [];
  document.addEventListener('focusin', e => window.__events.push('focusin:' + (e.target.id || e.target.tagName)));
  document.getElementById('opener').addEventListener('click', () => {
    const d = document.getElementById('d');
    d.showModal();
    document.getElementById('ok').focus();
  });
</script>
</body></html>
"""

REC = """() => {
  const a = document.activeElement;
  return {tag: a.tagName.toLowerCase(), id: a.id || '',
          inDialog: !!(a.closest && a.closest('#d')),
          isBody: a === document.body, isDialogEl: a.id === 'd'};
}"""

out = {"when": now_iso()}
with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
        ctx = b.new_context(viewport={"width": 800, "height": 600})
        pg = ctx.new_page()
        pg.set_content(HTML)
        pg.click("#opener")
        pg.wait_for_timeout(400)
        steps = [{"step": "open", **pg.evaluate(REC)}]
        for i in range(8):
            pg.keyboard.press("Tab")
            pg.wait_for_timeout(100)
            steps.append({"step": f"tab{i+1}", **pg.evaluate(REC)})
        for i in range(4):
            pg.keyboard.press("Shift+Tab")
            pg.wait_for_timeout(100)
            steps.append({"step": f"shift{i+1}", **pg.evaluate(REC)})
        events = pg.evaluate("() => window.__events")
        out[eng] = {"version": b.version, "steps": steps, "focusin_events": events}
        ctx.close()
        b.close()

(RAW / "dialog-minimal-repro.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
for eng in ("chromium", "firefox"):
    print("=" * 60)
    print(eng, out[eng]["version"])
    for s in out[eng]["steps"]:
        print(f"   {s['step']:8s} -> {s['tag']}#{s['id']} inDialog={s['inDialog']} body={s['isBody']}")
    print("   focusin:", out[eng]["focusin_events"])
print("-> raw/dialog-minimal-repro.json")
