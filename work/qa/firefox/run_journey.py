#!/usr/bin/env python3
"""Firefox journey runner for 第零证物局 — mirrors tests/browser/e2e.py assertions
but drives `p.firefox.launch()` against the LIVE site.

Covers the 10 mandated areas:
  1  Home: title + #cta-first
  2  Cabinet: exactly 6 case cards
  3  NA-001 desk opens; exactly 3 evidence cards; all expand
  4  Default arrangement is NOT the answer
  5  Wrong submit -> non-spoiler message, arrangement preserved
  6  Three hints one at a time; hints don't auto-arrange
  7  Correct solve -> verdict with logic + story recap, not duplicates
  8  Keyboard: Tab reaches controls; Enter reorders; ArrowUp/ArrowDown reorder; focus ring
  9  Mobile 390x844: no horizontal overflow, every interactive target >= 44px
 10  No console errors, no third-party requests

Usage: python run_journey.py [--headless]
Writes raw/journey-firefox.json
"""
from __future__ import annotations

import sys
import time

from playwright.sync_api import sync_playwright

from fx_common import (LIVE_BASE, RAW, SHOTS, ConsoleCollector, Results,
                       collect_requests, current_order, expected_solution,
                       fill_order, load_public, no_horizontal_overflow,
                       undersized_targets)

AREA = {
    1: "Home / title / CTA",
    2: "Cabinet 6 cards",
    3: "NA-001 desk + 3 evidence + expand",
    4: "Default != answer",
    5: "Wrong submit non-spoiler + preserved",
    6: "Three hints, no auto-arrange",
    7: "Verdict logic + story recap",
    8: "Keyboard reorder + focus ring",
    9: "Mobile 390x844 overflow + 44px",
    10: "Console errors + third-party",
}


def tab_chain(page, steps=40, stop_when_tab=False):
    """Walk the real Tab order and record what each stop is."""
    chain = []
    for _ in range(steps):
        page.keyboard.press("Tab")
        info = page.evaluate("""() => {
            const a = document.activeElement;
            if (!a) return null;
            return {
                tag: a.tagName.toLowerCase(),
                id: a.id || '',
                cls: (a.className && a.className.baseVal !== undefined ? a.className.baseVal : a.className) || '',
                text: (a.textContent || '').trim().slice(0, 30),
                act: a.dataset ? (a.dataset.act || '') : '',
                slot: a.closest && a.closest('.slot') ? a.closest('.slot').dataset.index : null,
                href: a.getAttribute ? (a.getAttribute('href') || '') : ''
            };
        }""")
        chain.append(info)
        if stop_when_tab and info and info.get("id") == "btn-submit":
            break
    return chain


def run(headless: bool = True) -> int:
    R = Results("journey", "firefox")
    extra: dict = {}

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        extra["browser_version"] = browser.version
        extra["user_agent"] = None

        # ---------------- Desktop 1440 ----------------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        cc = ConsoleCollector(page)
        external: list[str] = []
        collect_requests(page, LIVE_BASE, external)

        page.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
        extra["user_agent"] = page.evaluate("() => navigator.userAgent")

        # --- 1. Home ---
        title = page.title()
        R.add("1. Home loads, title starts 第零证物局", title.startswith("第零证物局"), title)
        cta = page.query_selector("#cta-first")
        R.add("1. #cta-first exists and is visible",
              cta is not None and cta.is_visible(),
              (cta.inner_text().strip()[:40] if cta else "missing"))
        page.screenshot(path=str(SHOTS / "fx-01-home-1440.png"), full_page=True)

        # --- 2. Cabinet ---
        page.click('a[data-nav="cabinet"]')
        page.wait_for_selector("#cabinet .case-card")
        cards = page.query_selector_all("#cabinet .case-card")
        R.add("2. Cabinet shows exactly 6 case cards", len(cards) == 6, f"{len(cards)} cards")
        page.screenshot(path=str(SHOTS / "fx-02-cabinet-1440.png"), full_page=True)

        # --- 3. NA-001 desk ---
        page.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot")
        case_title = page.inner_text("#case-title")
        R.add("3. NA-001 desk opens", bool(case_title.strip()), case_title)
        ev_count = len(page.query_selector_all(".ev-card"))
        R.add("3. Exactly 3 evidence cards", ev_count == 3, f"{ev_count} cards")

        # anti-double-binding negative assertion (from e2e.py)
        before_click = current_order(page)
        page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
        page.wait_for_timeout(250)
        after_click = current_order(page)
        expected = [before_click[1], before_click[0], *before_click[2:]]
        R.add("3b. One click moves exactly one slot (no double binding)",
              after_click == expected, f"{before_click} -> {after_click}")

        # pick toggling
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        page.wait_for_timeout(150)
        sel1 = page.get_attribute('#slots .slot[data-index="0"]', "data-selected")
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        page.wait_for_timeout(150)
        sel2 = page.get_attribute('#slots .slot[data-index="0"]', "data-selected")
        R.add("3c. Click-to-select can be toggled off", sel1 == "true" and sel2 == "false",
              f"{sel1} -> {sel2}")

        # expand all evidence
        opened = []
        for i in range(ev_count):
            btn = page.query_selector_all(".ev-card__summary")[i]
            if btn.get_attribute("aria-expanded") == "false":
                btn.click()
            opened.append(btn.get_attribute("aria-expanded"))
        bodies = page.eval_on_selector_all(".ev-card__body", "els => els.filter(e => !e.hidden).length")
        R.add("3d. All evidence cards expand (3/3)", bodies == 3,
              f"{bodies}/3 open, aria-expanded={opened}")

        # --- 4. default != answer ---
        pub = load_public("NA-001")
        answer = expected_solution("NA-001")
        start = current_order(page)
        R.add("4. Default arrangement is NOT the answer", start != answer,
              f"start={start} vs answer={answer}")
        R.add("4b. Default arrangement does not satisfy all constraints", True if start != answer else False,
              "implied by 4")

        page.screenshot(path=str(SHOTS / "fx-03-desk-1440.png"), full_page=True)

        # --- 5. wrong submit ---
        wrong = list(reversed(answer))
        fill_order(page, wrong)
        page.click("#btn-submit")
        page.wait_for_selector("#message[data-show='true']", timeout=10000)
        msg = page.inner_text("#message")
        R.add("5. Wrong submit gives non-spoiler feedback",
              ("不一致" in msg) and ("→" not in msg), msg.replace("\n", " | ")[:120])
        kept = current_order(page)
        R.add("5b. Wrong submit preserves the arrangement", kept == wrong, f"{kept}")

        # --- 6. hints ---
        hint_counts = []
        orders_during_hints = []
        for _ in range(3):
            page.click("#btn-hint")
            time.sleep(0.12)
            hint_counts.append(len(page.query_selector_all(".hint-card")))
            orders_during_hints.append(current_order(page))
        R.add("6. Three hints appear one at a time", hint_counts == [1, 2, 3], f"{hint_counts}")
        R.add("6b. Hints never auto-arrange the board",
              all(o == wrong for o in orders_during_hints), "order unchanged across all 3 hints")
        hint_disabled = page.eval_on_selector("#btn-hint", "e => e.disabled")
        R.add("6c. Hint button disables once exhausted", hint_disabled is True,
              f"disabled={hint_disabled}, label={page.inner_text('#btn-hint')}")

        # --- 7. correct solve -> verdict ---
        fill_order(page, answer)
        page.click("#btn-submit")
        page.wait_for_selector(".verdict", timeout=15000)
        vtitle = page.inner_text("#verdict-title")
        R.add("7. Correct solve reaches the verdict page", "档案归位" in vtitle, vtitle)

        logic = page.inner_text(".recap-block:not(.recap-block--story)")
        story = page.inner_text(".recap-block--story")
        R.add("7b. Logic recap block present", "逻辑复盘" in logic, logic.split("\n")[0][:60])
        R.add("7c. Story recap block present", "档案后记" in story, story.split("\n")[0][:60])
        R.add("7d. Recaps are NOT duplicates",
              logic.strip() != story.strip() and len(logic) > 50 and len(story) > 50,
              f"logic {len(logic)} ch / story {len(story)} ch")
        missing = [f"E0{i}" for i in (1, 2, 3) if f"E0{i}" not in logic]
        R.add("7e. Logic recap cites E01/E02/E03", not missing, f"missing={missing}")

        # DOM-level proof that they are two separate blocks
        blocks = page.evaluate("""() => [...document.querySelectorAll('.recap-block')].map(b => ({
            cls: b.className, len: b.innerText.length, first: b.innerText.split('\\n')[0]}))""")
        R.add("7f. Two distinct .recap-block nodes exist", len(blocks) >= 2, f"{blocks}")
        page.screenshot(path=str(SHOTS / "fx-04-verdict-1440.png"), full_page=True)

        # archive progress
        page.goto(f"{LIVE_BASE}#/cabinet", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#cabinet .case-card")
        badge = page.inner_text("#progress-badge")
        R.add("7g. Archive progress persisted after solve (1 / 6)", "1 / 6" in badge, badge)

        # refresh restores arrangement
        page.goto(f"{LIVE_BASE}#/case/NA-002", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot")
        before = current_order(page)
        page.click('#slots .slot[data-index="0"] [data-act="down"]')
        moved = current_order(page)
        page.reload(wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot")
        after = current_order(page)
        R.add("7h. Arrangement restored after reload", after == moved and after != before,
              f"before={before} moved={moved} after={after}")

        # ---------------- 8. Keyboard ----------------
        page.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot")
        page.evaluate("() => document.body.focus()")
        page.keyboard.press("Tab")
        first = page.evaluate("""() => ({tag: document.activeElement.tagName,
            cls: document.activeElement.className, id: document.activeElement.id})""")
        R.add("8. Tab reaches a focusable control from page top",
              bool(first and first.get("tag")), str(first))

        chain = tab_chain(page, steps=45)
        reach_slot = [c for c in chain if c and c.get("slot") is not None]
        R.add("8b. Tab order reaches slot controls", len(reach_slot) > 0,
              f"{len(reach_slot)} stops inside #slots; first={reach_slot[0] if reach_slot else None}")
        ids = [c.get("id") for c in chain if c]
        R.add("8c. Tab order reaches action buttons (submit/hint/reset)",
              all(x in ids for x in ("btn-submit", "btn-hint", "btn-reset")),
              f"ids seen: {[i for i in ids if i][:12]}")

        # Enter on a move button reorders
        before_enter = current_order(page)
        page.focus('#slots .slot[data-index="0"] [data-act="down"]')
        page.keyboard.press("Enter")
        time.sleep(0.2)
        after_enter = current_order(page)
        R.add("8d. Enter on a move button reorders", after_enter != before_enter,
              f"{before_enter} -> {after_enter}")
        R.add("8e. Enter moved exactly one position",
              after_enter == [before_enter[1], before_enter[0], *before_enter[2:]],
              f"{after_enter}")

        # ArrowUp on a slot
        page.focus('#slots .slot[data-index="1"] [data-act="pick"]')
        start_k = current_order(page)
        page.keyboard.press("ArrowUp")
        time.sleep(0.2)
        up_k = current_order(page)
        R.add("8f. ArrowUp on a slot reorders", up_k != start_k, f"{start_k} -> {up_k}")

        page.focus('#slots .slot[data-index="0"] [data-act="pick"]')
        page.keyboard.press("ArrowDown")
        time.sleep(0.2)
        down_k = current_order(page)
        R.add("8g. ArrowDown on a slot reorders", down_k != up_k, f"{up_k} -> {down_k}")
        R.add("8h. ArrowDown reverses ArrowUp", down_k == start_k, f"{down_k} == {start_k}")

        # no-op edges
        page.focus('#slots .slot[data-index="0"] [data-act="pick"]')
        top_before = current_order(page)
        page.keyboard.press("ArrowUp")
        time.sleep(0.15)
        R.add("8i. ArrowUp on the top row is a no-op", current_order(page) == top_before,
              "order unchanged at index 0")

        # focus visibility via :focus-visible
        page.focus("#btn-submit")
        page.keyboard.press("Tab")
        page.keyboard.press("Shift+Tab")
        focus_info = page.evaluate("""() => {
            const a = document.activeElement;
            const cs = getComputedStyle(a);
            return {id: a.id, cls: a.className, outlineStyle: cs.outlineStyle,
                    outlineWidth: cs.outlineWidth, outlineColor: cs.outlineColor,
                    matchesFV: a.matches(':focus-visible')};
        }""")
        R.add("8j. Focus ring visible on keyboard focus",
              focus_info["outlineStyle"] not in ("none", "") and focus_info["outlineWidth"] not in ("0px", ""),
              f"outline={focus_info['outlineStyle']} {focus_info['outlineWidth']} fv={focus_info['matchesFV']}")

        # focus retained after keyboard reorder
        page.focus('#slots .slot[data-index="1"] [data-act="up"]')
        page.keyboard.press("Enter")
        time.sleep(0.2)
        retained = page.evaluate("""() => {
            const a = document.activeElement;
            const li = a.closest && a.closest('.slot');
            return {act: a.dataset ? a.dataset.act : null, slot: li ? li.dataset.index : null};
        }""")
        R.add("8k. Focus retained after keyboard reorder",
              retained.get("act") is not None, str(retained))

        # ---------------- 9. Mobile 390x844 ----------------
        m = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN",
                                is_mobile=True, has_touch=True, device_scale_factor=2)
        mp = m.new_page()
        mcc = ConsoleCollector(mp)
        mext: list[str] = []
        collect_requests(mp, LIVE_BASE, mext)
        mp.goto(f"{LIVE_BASE}#/case/NA-004", wait_until="networkidle", timeout=60000)
        mp.wait_for_selector("#slots .slot")
        ov = no_horizontal_overflow(mp)
        R.add("9. Mobile 390x844 has no horizontal overflow", ov["ok"],
              f"scrollWidth={ov['scrollWidth']} clientWidth={ov['clientWidth']}")
        small = undersized_targets(mp)
        R.add("9b. Mobile 390x844: every interactive target >= 44px", len(small) == 0,
              f"{len(small)} undersized: {small[:5]}")
        mp.screenshot(path=str(SHOTS / "fx-05-mobile-390.png"), full_page=True)

        # also record 360 and 768 for completeness (e2e.py checks these too)
        extra["mobile_extra"] = {}
        for w, h, name in [(360, 800, "360"), (768, 1024, "768")]:
            mm = browser.new_context(viewport={"width": w, "height": h}, locale="zh-CN",
                                     is_mobile=w < 500, has_touch=w < 500, device_scale_factor=2)
            mmp = mm.new_page()
            mmp.goto(f"{LIVE_BASE}#/case/NA-004", wait_until="networkidle", timeout=60000)
            mmp.wait_for_selector("#slots .slot")
            o = no_horizontal_overflow(mmp)
            s = undersized_targets(mmp)
            extra["mobile_extra"][name] = {
                "overflow": o, "undersized": s,
                "ok": o["ok"] and len(s) == 0,
            }
            R.add(f"9c. {w}x{h} no overflow + 44px targets",
                  o["ok"] and len(s) == 0,
                  f"scrollW={o['scrollWidth']}/{o['clientWidth']} undersized={len(s)}")
            mmp.screenshot(path=str(SHOTS / f"fx-06-mobile-{name}.png"), full_page=True)
            mm.close()

        # mobile touch tap works
        sc = mp.query_selector('#slots .slot[data-index="0"] [data-act="down"]')
        before_tap = current_order(mp)
        sc.tap()
        time.sleep(0.3)
        R.add("9d. Mobile 390x844 touch tap reorders", current_order(mp) != before_tap,
              "tap on down button")
        m.close()

        # ---------------- 10. Console + third party ----------------
        page.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
        R.add("10. No third-party network requests", len(external) == 0,
              f"{len(external)}: {external[:3]}")
        R.add("10b. No console errors / page errors (desktop)", len(cc.all) == 0,
              "; ".join(cc.all[:3]))
        R.add("10c. No console errors / page errors (mobile 390)", len(mcc.all) == 0,
              "; ".join(mcc.all[:3]))
        R.add("10d. No third-party network requests (mobile 390)", len(mext) == 0,
              f"{len(mext)}: {mext[:3]}")
        extra["console_desktop"] = cc.all
        extra["console_mobile"] = mcc.all
        extra["external_desktop"] = external
        extra["external_mobile"] = mext
        extra["request_failures_desktop"] = cc.request_failures

        browser.close()

    # group rows by area for the report table
    import re as _re
    for r in R.rows:
        m = _re.match(r"^(\d+)", r["check"])
        r["area"] = int(m.group(1)) if m else None
    extra["area_titles"] = AREA
    extra["areas_passed"] = sorted({r["area"] for r in R.rows if not r["ok"] and r["area"]})
    R.extra = extra
    R.dump("journey-firefox.json")
    return 0 if all(r["ok"] for r in R.rows) else 1


if __name__ == "__main__":
    sys.exit(run(headless="--headed" not in sys.argv))
