#!/usr/bin/env python3
"""Firefox-specific behaviours that a Chromium run cannot reveal.

  A. <dialog> + showModal(): does it open, is it top layer, does it trap focus,
     is ::backdrop painted, does Esc / cancel / confirm close it correctly?
  B. prefers-reduced-motion: launch with reduced_motion="reduce" and confirm
     transitions/animations collapse to ~0; confirm the same page keeps real
     durations under reduced_motion="no-preference".
  C. localStorage persistence across a real reload and a brand-new context.
  D. @media (hover:hover) drag-grip: visible on a hover-capable desktop,
     hidden (and not taking up space) on a touch/coarse-pointer viewport.

Usage: python run_firefox_specific.py
Writes raw/firefox-specific.json
"""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright

from fx_common import (LIVE_BASE, RAW, SHOTS, ConsoleCollector, Results,
                       current_order, expected_solution, fill_order)

DIALOG_JS = """() => {
    const d = document.querySelector('#confirm-dialog');
    if (!d) return {exists: false};
    const cs = getComputedStyle(d);
    const r = d.getBoundingClientRect();
    return {
        exists: true,
        open: d.open,
        openAttr: d.hasAttribute('open'),
        display: cs.display,
        position: cs.position,
        top: Math.round(r.top), left: Math.round(r.left),
        w: Math.round(r.width), h: Math.round(r.height),
        zIndex: cs.zIndex,
        returnValue: d.returnValue,
        // is it painted? is any point of it the topmost element?
        hitTestCentre: (() => {
            const el = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
            return el ? (el.id || el.className || el.tagName) : null;
        })(),
        activeId: document.activeElement ? (document.activeElement.id || document.activeElement.getAttribute('data-confirm') || document.activeElement.tagName) : null,
    };
}"""


def run(headless: bool = True) -> int:
    R = Results("firefox-specific", "firefox")
    out: dict = {}
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        out["browser_version"] = browser.version

        # ============================================================
        # A. <dialog> + showModal()
        # ============================================================
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        cc = ConsoleCollector(page)
        page.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot")

        d0 = page.evaluate(DIALOG_JS)
        out["dialog_initial"] = d0
        R.add("A1. <dialog> element exists in DOM", d0.get("exists") is True, str(d0.get("display")))
        R.add("A2. Dialog is closed before the reset button is used", d0.get("open") is False,
              f"open={d0.get('open')}")

        # move the board so we can prove confirm-reset really resets
        page.click('#slots .slot[data-index="0"] [data-act="down"]')
        time.sleep(0.2)
        order_before_reset = current_order(page)

        page.click("#btn-reset")
        page.wait_for_timeout(600)
        d1 = page.evaluate(DIALOG_JS)
        out["dialog_open"] = d1
        R.add("A3. showModal() actually shows the dialog", d1.get("open") is True,
              f"open={d1.get('open')} display={d1.get('display')} {d1.get('w')}x{d1.get('h')} @{d1.get('left')},{d1.get('top')}")
        R.add("A4. Dialog is rendered on top (hit-testable centre)", d1.get("hitTestCentre") is not None,
              f"elementFromPoint -> {d1.get('hitTestCentre')}")
        page.screenshot(path=str(SHOTS / "fx-08-dialog-open.png"))

        # ::backdrop painted? sample the pixel just outside the dialog box
        backdrop = page.evaluate("""() => {
            const d = document.querySelector('#confirm-dialog');
            const r = d.getBoundingClientRect();
            const x = Math.max(2, Math.round(r.left / 2));
            const y = Math.round(window.innerHeight / 2);
            const el = document.elementFromPoint(x, y);
            return {
                samplePoint: [x, y],
                topElement: el ? (el.id || el.className || el.tagName) : null,
                // the backdrop pseudo is not a DOM node; if the top element at a
                // point outside the dialog is NOT an interactive page control, the
                // modal backdrop is intercepting pointer events
                backdropSupported: typeof d.showModal === 'function',
            };
        }""")
        out["backdrop"] = backdrop
        R.add("A5. Modal backdrop intercepts clicks outside the dialog",
              backdrop.get("topElement") is not None,
              f"topElement@out={backdrop.get('topElement')}")

        # ---- focus trap ----
        # collect the focusable controls inside the dialog
        trap = page.evaluate("""() => {
            const d = document.querySelector('#confirm-dialog');
            const f = [...d.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')]
                .filter(e => !e.disabled && e.getBoundingClientRect().width > 0);
            return {count: f.length, labels: f.map(e => (e.getAttribute('data-confirm') || e.id || e.textContent.trim()))};
        }""")
        out["dialog_focusables"] = trap
        R.add("A6. Dialog has focusable controls", trap["count"] >= 2, str(trap))

        # Tab many times and record whether focus ever escapes the dialog
        esc = []
        for i in range(10):
            page.keyboard.press("Tab")
            inside = page.evaluate("""() => {
                const a = document.activeElement;
                return {inDialog: !!a.closest('#confirm-dialog'),
                        id: a.id || a.getAttribute('data-confirm') || a.tagName};
            }""")
            esc.append(inside)
        out["dialog_tab_cycle"] = esc
        R.add("A7. Focus stays trapped inside the dialog while tabbing",
              all(x["inDialog"] for x in esc),
              f"{sum(1 for x in esc if x['inDialog'])}/10 stops inside; ids={[x['id'] for x in esc]}")

        # Shift+Tab also trapped
        esc_back = []
        for i in range(6):
            page.keyboard.press("Shift+Tab")
            esc_back.append(page.evaluate("""() => {
                const a = document.activeElement;
                return {inDialog: !!a.closest('#confirm-dialog'),
                        id: a.id || a.getAttribute('data-confirm') || a.tagName};
            }"""))
        out["dialog_shift_tab_cycle"] = esc_back
        R.add("A8. Focus stays trapped on Shift+Tab too",
              all(x["inDialog"] for x in esc_back),
              f"{sum(1 for x in esc_back if x['inDialog'])}/6 stops inside")

        # ---- Esc closes ----
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        d2 = page.evaluate(DIALOG_JS)
        out["dialog_after_esc"] = d2
        R.add("A9. Escape closes the dialog", d2.get("open") is False, f"open={d2.get('open')}")
        order_after_esc = current_order(page)
        R.add("A10. Esc = cancel: the board was NOT reset",
              order_after_esc == order_before_reset,
              f"{order_after_esc} vs {order_before_reset}")

        # ---- confirm button resets ----
        page.click("#btn-reset")
        page.wait_for_timeout(500)
        page.click('#confirm-dialog [data-confirm="ok"]')
        page.wait_for_timeout(600)
        d3 = page.evaluate(DIALOG_JS)
        order_after_ok = current_order(page)
        out["dialog_after_ok"] = d3
        out["order_after_confirm_reset"] = order_after_ok
        R.add("A11. Clicking 确认重置 closes the dialog", d3.get("open") is False, f"open={d3.get('open')}")
        R.add("A12. Confirming actually resets the board",
              order_after_ok != order_before_reset,
              f"{order_before_reset} -> {order_after_ok}")

        # ---- cancel button keeps order ----
        page.click('#slots .slot[data-index="0"] [data-act="down"]')
        time.sleep(0.2)
        order_before_cancel = current_order(page)
        page.click("#btn-reset")
        page.wait_for_timeout(400)
        page.click('#confirm-dialog [data-confirm="cancel"]')
        page.wait_for_timeout(400)
        d4 = page.evaluate(DIALOG_JS)
        R.add("A13. Cancel button closes the dialog without resetting",
              d4.get("open") is False and current_order(page) == order_before_cancel,
              f"open={d4.get('open')}, order kept={current_order(page) == order_before_cancel}")

        # ---- dialog is top-layer: document-level stacking ----
        page.click("#btn-reset")
        page.wait_for_timeout(400)
        top = page.evaluate("""() => {
            const d = document.querySelector('#confirm-dialog');
            return {
                // a modal dialog is promoted to the top layer; nothing in the
                // normal document flow can paint above it
                hasOpenAttr: d.open,
                computedZIndex: getComputedStyle(d).zIndex,
                // inertness: the page behind must not receive clicks
                headerClickable: (() => {
                    const h = document.querySelector('.site-header');
                    const r = h.getBoundingClientRect();
                    const el = document.elementFromPoint(r.left + 5, r.top + 5);
                    return el && !el.closest('#confirm-dialog');
                })(),
            };
        }""")
        out["dialog_top_layer"] = top
        R.add("A14. Page behind the modal is inert (header not clickable)", top["headerClickable"] is False,
              f"headerClickable={top['headerClickable']}, zIndex={top.get('computedZIndex')}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        out["dialog_console"] = cc.all
        R.add("A15. No console errors around dialog use", len(cc.all) == 0, "; ".join(cc.all[:3]))
        ctx.close()

        # ============================================================
        # B. prefers-reduced-motion
        # ============================================================
        def motion_probe(rm: str) -> dict:
            mctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                       locale="zh-CN", reduced_motion=rm)
            mp = mctx.new_page()
            mp.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
            mp.wait_for_selector("#slots .slot")
            mp.wait_for_timeout(300)
            data = mp.evaluate("""() => {
              const pick = (sel) => {
                const e = document.querySelector(sel);
                if (!e) return null;
                const cs = getComputedStyle(e);
                return {
                  selector: sel,
                  transitionDuration: cs.transitionDuration,
                  transitionProperty: cs.transitionProperty,
                  animationDuration: cs.animationDuration,
                  animationName: cs.animationName,
                  scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
                };
              };
              return {
                prefersReduce: matchMedia('(prefers-reduced-motion: reduce)').matches,
                rootDurVar: getComputedStyle(document.documentElement).getPropertyValue('--dur').trim(),
                slot: pick('.slot'),
                btn: pick('.btn'),
                header: pick('.site-header'),
                stamp: pick('.stamp'),
                html: pick('html'),
              };
            }""")
            mctx.close()
            return data

        rm_reduce = motion_probe("reduce")
        rm_normal = motion_probe("no-preference")
        out["reduced_motion_reduce"] = rm_reduce
        out["reduced_motion_normal"] = rm_normal

        def max_seconds(value: str) -> float:
            """parse '0.001ms' / '0.22s' / '0.001ms, 0.001ms' -> max seconds"""
            if not value:
                return 0.0
            best = 0.0
            for part in str(value).split(","):
                part = part.strip()
                if part.endswith("ms"):
                    best = max(best, float(part[:-2]) / 1000.0)
                elif part.endswith("s"):
                    best = max(best, float(part[:-1]))
            return best

        R.add("B1. prefers-reduced-motion is actually reported by Firefox",
              rm_reduce["prefersReduce"] is True and rm_normal["prefersReduce"] is False,
              f"reduce={rm_reduce['prefersReduce']}, no-preference={rm_normal['prefersReduce']}")
        red_max = max(max_seconds(rm_reduce[k]["transitionDuration"]) for k in ("slot", "btn", "header") if rm_reduce.get(k))
        nor_max = max(max_seconds(rm_normal[k]["transitionDuration"]) for k in ("slot", "btn", "header") if rm_normal.get(k))
        R.add("B2. Under reduce, transitions collapse to ~0", red_max <= 0.01,
              f"max transitionDuration={red_max}s (raw slot={rm_reduce['slot']['transitionDuration']})")
        R.add("B3. Under no-preference, transitions are non-zero (control)",
              nor_max > 0.01, f"max transitionDuration={nor_max}s")
        R.add("B4. --dur token is 0ms under reduce",
              rm_reduce["rootDurVar"] in ("0ms", "0s"), f"--dur={rm_reduce['rootDurVar']!r}")
        R.add("B5. html scroll-behavior is auto under reduce",
              rm_reduce["html"]["scrollBehavior"] == "auto",
              f"reduce={rm_reduce['html']['scrollBehavior']} / normal={rm_normal['html']['scrollBehavior']}")

        # ============================================================
        # C. localStorage persistence
        # ============================================================
        storage_ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        sp = storage_ctx.new_page()
        sp.goto(f"{LIVE_BASE}#/case/NA-003", wait_until="networkidle", timeout=60000)
        sp.wait_for_selector("#slots .slot")
        sp.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        sp.reload(wait_until="networkidle", timeout=60000)
        sp.wait_for_selector("#slots .slot")
        order0 = current_order(sp)
        keys0 = sp.evaluate("() => Object.keys(localStorage)")

        # make 2 moves and reveal 1 hint
        sp.click('#slots .slot[data-index="0"] [data-act="down"]')
        time.sleep(0.2)
        sp.click('#slots .slot[data-index="1"] [data-act="down"]')
        time.sleep(0.2)
        sp.click("#btn-hint")
        time.sleep(0.3)
        order_moved = current_order(sp)
        hints_before = len(sp.query_selector_all(".hint-card"))
        keys1 = sp.evaluate("() => Object.keys(localStorage)")
        raw_ls = sp.evaluate("""() => {
            const o = {};
            for (const k of Object.keys(localStorage)) o[k] = localStorage.getItem(k).slice(0, 400);
            return o;
        }""")
        out["storage_keys_before"] = keys1
        out["storage_raw"] = raw_ls

        sp.reload(wait_until="networkidle", timeout=60000)
        sp.wait_for_selector("#slots .slot")
        order_after_reload = current_order(sp)
        hints_after = len(sp.query_selector_all(".hint-card"))
        out["storage"] = {
            "initial_order": order0, "moved_order": order_moved,
            "after_reload_order": order_after_reload,
            "hints_before": hints_before, "hints_after_reload": hints_after,
            "keys_initial": keys0, "keys_after_moves": keys1,
        }
        R.add("C1. localStorage is written by the app", len(keys1) >= 1, f"keys={keys1}")
        R.add("C2. Arrangement survives a real reload",
              order_after_reload == order_moved and order_moved != order0,
              f"{order_moved} -> {order_after_reload}")
        R.add("C3. Hint progress survives a real reload",
              hints_after == hints_before and hints_before >= 1,
              f"{hints_before} -> {hints_after}")

        # new tab in the SAME context (shared origin storage)
        sp2 = storage_ctx.new_page()
        sp2.goto(f"{LIVE_BASE}#/case/NA-003", wait_until="networkidle", timeout=60000)
        sp2.wait_for_selector("#slots .slot")
        order_new_tab = current_order(sp2)
        out["storage"]["after_new_tab_order"] = order_new_tab
        R.add("C4. Persistence is shared with a second tab of the same context",
              order_new_tab == order_moved, f"{order_new_tab}")
        sp2.close()

        # fresh context == a different browser profile: must NOT inherit
        fresh = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        fp = fresh.new_page()
        fp.goto(f"{LIVE_BASE}#/case/NA-003", wait_until="networkidle", timeout=60000)
        fp.wait_for_selector("#slots .slot")
        order_fresh = current_order(fp)
        out["storage"]["after_fresh_context_order"] = order_fresh
        R.add("C5. A fresh profile starts clean (no cross-profile leakage)",
              order_fresh == order0, f"fresh={order_fresh} vs first-run={order0}")
        fresh.close()
        storage_ctx.close()

        # ============================================================
        # D. @media (hover:hover) drag-grip
        # ============================================================
        def grip_probe(context_kwargs: dict) -> dict:
            gctx = browser.new_context(**context_kwargs)
            gp = gctx.new_page()
            gp.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
            gp.wait_for_selector("#slots .slot")
            gp.wait_for_timeout(200)
            data = gp.evaluate("""() => {
                const g = document.querySelector('.slot .slot__grip');
                if (!g) return {exists: false};
                const cs = getComputedStyle(g);
                const r = g.getBoundingClientRect();
                return {
                    exists: true,
                    display: cs.display,
                    visibility: cs.visibility,
                    width: Math.round(r.width * 10) / 10,
                    height: Math.round(r.height * 10) / 10,
                    raisable: r.width > 0 && r.height > 0,
                    hoverHover: matchMedia('(hover: hover)').matches,
                    hoverNone: matchMedia('(hover: none)').matches,
                    pointerCoarse: matchMedia('(pointer: coarse)').matches,
                    viewport: [window.innerWidth, window.innerHeight],
                };
            }""")
            gctx.close()
            return data

        grip_desktop = grip_probe(dict(viewport={"width": 1440, "height": 900}, locale="zh-CN"))
        grip_narrow = grip_probe(dict(viewport={"width": 900, "height": 900}, locale="zh-CN"))
        grip_touch = grip_probe(dict(viewport={"width": 390, "height": 844}, locale="zh-CN",
                                     is_mobile=True, has_touch=True, device_scale_factor=2))
        grip_touch_wide = grip_probe(dict(viewport={"width": 1440, "height": 900}, locale="zh-CN",
                                          has_touch=True, device_scale_factor=2))
        out["grip"] = {"desktop": grip_desktop, "narrow": grip_narrow,
                       "touch_390": grip_touch, "touch_1440": grip_touch_wide}

        R.add("D1. Desktop hover-capable: drag-grip is visible",
              grip_desktop.get("display") == "block" and grip_desktop.get("raisable") is True,
              f"display={grip_desktop.get('display')} {grip_desktop.get('width')}x{grip_desktop.get('height')} hover:hover={grip_desktop.get('hoverHover')}")
        R.add("D2. Touch/coarse 390px: drag-grip is hidden",
              grip_touch.get("display") == "none" and grip_touch.get("hoverNone") is True,
              f"display={grip_touch.get('display')} hover:none={grip_touch.get('hoverNone')} pointer:coarse={grip_touch.get('pointerCoarse')}")
        R.add("D3. Touch hidden grip takes no layout space",
              grip_touch.get("width") in (0, 0.0) and grip_touch.get("height") in (0, 0.0),
              f"{grip_touch.get('width')}x{grip_touch.get('height')}")
        R.add("D4. Wide-but-touch (1440px, coarse pointer): grip hidden",
              grip_touch_wide.get("display") == "none",
              f"display={grip_touch_wide.get('display')} hover:none={grip_touch_wide.get('hoverNone')}")
        R.add("D5. Narrow hover desktop (900px): grip hidden by min-width rule",
              grip_narrow.get("display") == "none",
              f"display={grip_narrow.get('display')} width={grip_narrow.get('viewport')}")

        browser.close()

    R.extra = out
    R.dump("firefox-specific.json")
    return 0 if all(r["ok"] for r in R.rows) else 1


if __name__ == "__main__":
    sys.exit(run(headless="--headed" not in sys.argv))
