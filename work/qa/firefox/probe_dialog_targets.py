#!/usr/bin/env python3
"""Two focused audits.

A. Dialog focus cycle: step Tab through the modal one key press at a time and
   record the full identity of document.activeElement at every step, in BOTH
   engines, so we can say precisely whether the trap cycles or sticks.

B. Comprehensive touch-target audit at 390x844: every element that is actually
   interactive (buttons, links, inputs, [role=button], summary, [tabindex>=0])
   across home / cabinet / desk / verdict / manual, measured for >= 44x44 CSS px.
   This is broader than the selector list used by tests/browser/e2e.py.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

from fx_common import (LIVE_BASE, RAW, current_order, expected_solution,
                       fill_order, now_iso)

ACTIVE_JS = """() => {
  const a = document.activeElement;
  if (!a) return null;
  return {
    tag: a.tagName.toLowerCase(),
    id: a.id || '',
    confirm: a.getAttribute ? (a.getAttribute('data-confirm') || '') : '',
    cls: (a.className && a.className.baseVal !== undefined ? a.className.baseVal : a.className) || '',
    text: (a.textContent || '').trim().slice(0, 20),
    inDialog: !!(a.closest && a.closest('#confirm-dialog')),
  };
}"""

DIALOG_STATE = """() => {
  const d = document.querySelector('#confirm-dialog');
  return d ? {open: d.open, returnValue: d.returnValue} : null;
}"""

AUDIT_JS = """() => {
  const sel = 'a[href], button, input, select, textarea, summary, [role="button"], [tabindex]:not([tabindex="-1"])';
  const els = [...document.querySelectorAll(sel)];
  const rows = [];
  for (const e of els) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (e.closest('[hidden]')) continue;
    const r = e.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    if (parseFloat(cs.opacity) === 0) continue;
    rows.push({
      tag: e.tagName.toLowerCase(),
      id: e.id || '',
      cls: (e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className) || '',
      text: (e.textContent || '').trim().slice(0, 22),
      w: Math.round(r.width * 10) / 10,
      h: Math.round(r.height * 10) / 10,
      ok: r.width >= 44 && r.height >= 44,
      disabled: !!e.disabled,
    });
  }
  return rows;
}"""


def dialog_probe(p, eng):
    b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    pg = ctx.new_page()
    pg.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
    pg.wait_for_selector("#btn-reset")
    pg.mouse.click(5, 5)
    pg.click("#btn-reset")
    pg.wait_for_timeout(700)
    steps = [{"step": "open", **pg.evaluate(ACTIVE_JS)}]
    for i in range(6):
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(120)
        steps.append({"step": f"tab{i+1}", **pg.evaluate(ACTIVE_JS)})
    back = []
    for i in range(4):
        pg.keyboard.press("Shift+Tab")
        pg.wait_for_timeout(120)
        back.append({"step": f"shift{i+1}", **pg.evaluate(ACTIVE_JS)})
    state_open = pg.evaluate(DIALOG_STATE)
    # does Enter activate the focused control?
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    state_closed = pg.evaluate(DIALOG_STATE)
    ctx.close()
    b.close()
    return {"forward": steps, "backward": back,
            "state_while_open": state_open, "state_after_escape": state_closed}


def audit_probe(p, eng):
    b = (p.chromium if eng == "chromium" else p.firefox).launch(headless=True)
    results = {}
    routes = [("home", "#/"), ("cabinet", "#/cabinet"), ("desk", "#/case/NA-001"),
              ("manual", "#/manual"), ("about", "#/about")]
    for name, route in routes:
        ctx = b.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN",
                            is_mobile=True, has_touch=True, device_scale_factor=2)
        pg = ctx.new_page()
        pg.goto(LIVE_BASE + route, wait_until="networkidle", timeout=60000)
        if route.startswith("#/case"):
            pg.wait_for_selector("#slots .slot")
        pg.wait_for_timeout(600)
        rows = pg.evaluate(AUDIT_JS)
        results[name] = {
            "count": len(rows),
            "undersized": [r for r in rows if not r["ok"]],
            "min_w": min((r["w"] for r in rows), default=None),
            "min_h": min((r["h"] for r in rows), default=None),
        }
        # also open the mobile nav if a toggle exists, and re-audit
        if pg.query_selector("#nav-toggle") and pg.eval_on_selector("#nav-toggle", "e => getComputedStyle(e).display !== 'none'"):
            pg.click("#nav-toggle")
            pg.wait_for_timeout(400)
            rows2 = pg.evaluate(AUDIT_JS)
            results[name]["nav_open"] = {
                "count": len(rows2),
                "undersized": [r for r in rows2 if not r["ok"]],
            }
        ctx.close()

    # verdict view audit: solve NA-001 quickly, then audit
    ctx = b.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN",
                        is_mobile=True, has_touch=True, device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
    pg.wait_for_selector("#slots .slot")
    fill_order(pg, expected_solution("NA-001"))
    pg.click("#btn-submit")
    pg.wait_for_selector(".verdict", timeout=15000)
    pg.wait_for_timeout(500)
    rows = pg.evaluate(AUDIT_JS)
    results["verdict"] = {"count": len(rows), "undersized": [r for r in rows if not r["ok"]],
                          "min_w": min((r["w"] for r in rows), default=None),
                          "min_h": min((r["h"] for r in rows), default=None)}
    ctx.close()
    b.close()
    return results


out = {"when": now_iso(), "base": LIVE_BASE, "dialog": {}, "touch_targets_390": {}}
with sync_playwright() as p:
    for eng in ("chromium", "firefox"):
        print("dialog probe:", eng)
        out["dialog"][eng] = dialog_probe(p, eng)
        print("touch audit:", eng)
        out["touch_targets_390"][eng] = audit_probe(p, eng)

(RAW / "dialog-and-targets.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

for eng in ("chromium", "firefox"):
    print("=" * 66)
    print(eng, "DIALOG FOCUS")
    for s in out["dialog"][eng]["forward"]:
        print(f"   {s['step']:8s} -> {s.get('tag')} id={s.get('id')!r} confirm={s.get('confirm')!r} inDialog={s.get('inDialog')}")
    print("   backward:", [(s.get("confirm") or s.get("id")) for s in out["dialog"][eng]["backward"]])
    print("   open state:", out["dialog"][eng]["state_while_open"],
          "after esc:", out["dialog"][eng]["state_after_escape"])
    print(f"\n{eng} TOUCH TARGETS @390")
    for name, r in out["touch_targets_390"][eng].items():
        if "undersized" in r:
            print(f"   {name:8s} n={r['count']:3d} minW={r['min_w']} minH={r['min_h']} undersized={len(r['undersized'])}")
            for u in r["undersized"][:6]:
                print(f"        - {u['tag']}#{u['id']}.{u['cls'][:28]} {u['w']}x{u['h']} {u['text']!r}")
        if "nav_open" in r:
            print(f"        nav_open: n={r['nav_open']['count']} undersized={len(r['nav_open']['undersized'])}")
            for u in r["nav_open"]["undersized"][:6]:
                print(f"        - {u['tag']}#{u['id']}.{u['cls'][:28]} {u['w']}x{u['h']} {u['text']!r}")
print("-> raw/dialog-and-targets.json")
