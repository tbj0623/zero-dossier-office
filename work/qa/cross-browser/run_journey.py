#!/usr/bin/env python3
"""A+B: cross-engine user journey (Edge vs Chromium) on the LIVE site.

Mirrors the assertions in tests/browser/e2e.py but is a separate runner, adds
deeper keyboard / mobile / console / third-party checks, and records raw data.

Usage:
  python run_journey.py --engine chromium
  python run_journey.py --engine msedge
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from playwright.sync_api import sync_playwright

from qa_common import (
    LIVE_BASE, RAW, SHOTS, ConsoleCollector, Results, collect_requests,
    current_order, fill_order, load_case, no_horizontal_overflow, solve,
)


def launch(p, engine: str, headless: bool = True):
    if engine == "msedge":
        return p.chromium.launch(headless=headless, channel="msedge")
    return p.chromium.launch(headless=headless)


def run(engine: str, headless: bool = True) -> int:
    res = Results("journey", engine)
    console_all: list[str] = []
    external: list[str] = []

    with sync_playwright() as p:
        t0 = time.time()
        try:
            browser = launch(p, engine, headless)
        except Exception as exc:  # noqa: BLE001
            res.add("browser launch", False, f"{type(exc).__name__}: {exc}")
            res.extra["launch_error"] = f"{type(exc).__name__}: {exc}"
            res.dump(f"journey-{engine}.json")
            return 1
        res.extra["browser_version"] = browser.version
        res.add("browser launch", True, f"{engine} {browser.version}")

        # ---------------- desktop context ----------------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        cc = ConsoleCollector(page)
        collect_requests(page, LIVE_BASE, external)

        page.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
        res.add("home loads", page.title().startswith("第零证物局"), page.title())
        res.add("home CTA #cta-first present", page.query_selector("#cta-first") is not None)

        page.click('a[data-nav="cabinet"]')
        page.wait_for_selector("#cabinet .case-card", timeout=15000)
        cards = page.query_selector_all("#cabinet .case-card")
        res.add("cabinet shows 6 cards", len(cards) == 6, f"{len(cards)} cards")

        # ---------------- NA-001 vertical slice ----------------
        page.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot", timeout=20000)
        res.add("NA-001 desk opens", page.query_selector("#case-title") is not None,
                page.inner_text("#case-title"))

        ev_count = len(page.query_selector_all(".ev-card"))
        res.add("NA-001 has 3 evidence cards", ev_count == 3, f"{ev_count} cards")

        for i in range(ev_count):
            btn = page.query_selector_all(".ev-card__summary")[i]
            if btn.get_attribute("aria-expanded") == "false":
                btn.click()
        bodies = page.eval_on_selector_all(".ev-card__body", "els => els.filter(e => !e.hidden).length")
        res.add("all evidence expandable", bodies == 3, f"{bodies}/3 expanded")

        case = load_case("NA-001")
        answer = solve(case)
        start = current_order(page)
        res.add("default order is not the answer", start != answer, f"start={start}")

        # wrong submit keeps arrangement
        wrong = list(reversed(answer))
        fill_order(page, wrong)
        before_submit = current_order(page)
        page.click("#btn-submit")
        page.wait_for_selector("#message[data-show='true']", timeout=8000)
        msg = page.inner_text("#message")
        res.add("wrong submit: non-spoiler feedback",
                "不一致" in msg and "→" not in msg, msg.split("\n")[0][:90])
        kept = current_order(page)
        res.add("wrong submit keeps order", kept == wrong and before_submit == wrong, f"{kept}")

        # three hints
        hints_seen = 0
        hint_lens = []
        for _ in range(3):
            page.click("#btn-hint")
            time.sleep(0.15)
            hints_seen = len(page.query_selector_all(".hint-card"))
            hint_lens.append(hints_seen)
        res.add("three hints appear one by one", hints_seen == 3, f"counts={hint_lens}")
        res.add("hints do not auto-fill the answer", current_order(page) == wrong,
                "order unchanged by hints")
        hint_btn_state = page.evaluate("() => {const b=document.querySelector('#btn-hint'); return {disabled:b.disabled,text:b.textContent};}")
        res.add("hint button exhausted state", hint_btn_state["disabled"] is True, json.dumps(hint_btn_state, ensure_ascii=False))

        # correct solve
        fill_order(page, answer)
        page.click("#btn-submit")
        page.wait_for_selector(".verdict", timeout=12000)
        vtitle = page.inner_text("#verdict-title")
        res.add("correct solve reaches verdict", "档案归位" in vtitle, vtitle)

        logic = page.inner_text(".recap-block")
        story = page.inner_text(".recap-block--story")
        res.add("logic recap and story recap separated",
                "逻辑复盘" in logic and "档案后记" in story)
        res.add("logic recap cites every evidence id",
                all(f"E0{i}" in logic for i in (1, 2, 3)))
        # divergent extra: the two blocks must contain different text
        res.add("recap blocks are not duplicated",
                logic.strip() != story.strip(), f"logic={len(logic)}ch story={len(story)}ch")
        page.screenshot(path=str(SHOTS / f"verdict-{engine}.png"), full_page=True)

        # cabinet progress badge
        page.goto(f"{LIVE_BASE}#/cabinet", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#cabinet .case-card", timeout=15000)
        badge = page.inner_text("#progress-badge")
        res.add("archive progress persisted", "1 / 6" in badge, badge)

        # refresh restores arrangement
        page.goto(f"{LIVE_BASE}#/case/NA-002", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot", timeout=20000)
        before = current_order(page)
        page.click('#slots .slot[data-index="0"] [data-act="down"]')
        moved = current_order(page)
        page.reload(wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot", timeout=20000)
        after = current_order(page)
        res.add("reload restores arrangement", after == moved and after != before,
                f"before={before} moved={moved} after={after}")

        # ---------------- keyboard ----------------
        page.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot", timeout=20000)
        page.evaluate("() => { document.body.focus(); }")

        # Tab order from the top of the document
        tab_chain = []
        for _ in range(12):
            page.keyboard.press("Tab")
            tab_chain.append(page.evaluate(
                "() => {const a=document.activeElement; return {tag:a.tagName, id:a.id||null, cls:(a.className||'').toString().slice(0,40), act:a.dataset?a.dataset.act||null:null, text:(a.textContent||'').trim().slice(0,18)};}"))
        res.extra["tab_chain"] = tab_chain
        reachable_slot = any(e["act"] in ("up", "down", "pick") or e["cls"].startswith("slot") for e in tab_chain)
        res.add("Tab order reaches the slot controls", reachable_slot,
                " > ".join(f'{e["tag"]}#{e["id"] or ""}.{e["cls"][:14]}' for e in tab_chain[:8]))

        # Enter on a move button actually reorders
        page.focus('#slots .slot[data-index="0"] [data-act="down"]')
        k_before = current_order(page)
        page.keyboard.press("Enter")
        time.sleep(0.2)
        k_after = current_order(page)
        res.add("Enter on move button reorders", k_before != k_after, f"{k_before} -> {k_after}")

        # ArrowUp / ArrowDown on a slot
        page.focus('#slots .slot[data-index="1"] [data-act="pick"]')
        a_before = current_order(page)
        page.keyboard.press("ArrowUp")
        time.sleep(0.2)
        a_up = current_order(page)
        res.add("ArrowUp reorders", a_before != a_up, f"{a_before} -> {a_up}")

        # Reorder re-renders the board, so focus is moved to the moved row's same
        # relative control. Follow the item itself: after ArrowUp the pick button
        # for the same item lives at index 0.
        page.focus('#slots .slot[data-index="0"] [data-act="pick"]')
        a_focused = page.evaluate("() => {const li=document.activeElement.closest('.slot'); return li ? Number(li.dataset.index) : null;}")
        page.keyboard.press("ArrowDown")
        time.sleep(0.2)
        a_down = current_order(page)
        res.add("ArrowDown reorders", a_up != a_down, f"focused_index={a_focused} {a_up} -> {a_down}")
        res.add("ArrowDown reverses ArrowUp", a_down == a_before, f"back to {a_down}")

        # boundary: ArrowUp on the first row must not move or throw
        page.focus('#slots .slot[data-index="0"] [data-act="pick"]')
        edge_before = current_order(page)
        page.keyboard.press("ArrowUp")
        time.sleep(0.2)
        res.add("ArrowUp at top row is a no-op", current_order(page) == edge_before,
                f"{edge_before}")
        page.focus('#slots .slot[data-index="3"] [data-act="pick"]')
        edge2 = current_order(page)
        page.keyboard.press("ArrowDown")
        time.sleep(0.2)
        res.add("ArrowDown at last row is a no-op", current_order(page) == edge2, f"{edge2}")

        # focus ring visible + focus survives re-render
        page.focus("#btn-submit")
        outline = page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle")
        res.add("focus outline visible", outline not in ("none", ""), f"outline-style={outline}")
        page.focus('#slots .slot[data-index="0"] [data-act="down"]')
        page.keyboard.press("Enter")
        time.sleep(0.2)
        focused_act = page.evaluate("() => document.activeElement?.dataset?.act || document.activeElement?.id || null")
        res.add("focus retained after keyboard reorder", focused_act is not None, f"active={focused_act}")

        # ---------------- mobile 390x844 ----------------
        page.goto(f"{LIVE_BASE}#/case/NA-004", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#slots .slot", timeout=20000)
        m = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN",
                                is_mobile=True, has_touch=True, device_scale_factor=3)
        mp = m.new_page()
        mcc = ConsoleCollector(mp)
        collect_requests(mp, LIVE_BASE, external)
        mp.goto(f"{LIVE_BASE}#/case/NA-004", wait_until="networkidle", timeout=60000)
        mp.wait_for_selector("#slots .slot", timeout=20000)
        res.add("390x844 no horizontal overflow", no_horizontal_overflow(mp),
                mp.evaluate("() => document.documentElement.scrollWidth + 'x' + document.documentElement.clientWidth"))
        small = mp.evaluate("""() => {
          const els = [...document.querySelectorAll('#slots button, .actions button, .site-header button, .site-header a, .nav-toggle')];
          return els.filter(e => {
            const r = e.getBoundingClientRect();
            return r.width > 0 && (r.width < 44 || r.height < 44);
          }).map(e => (e.className||'') + ':' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height));
        }""")
        res.add("390x844 targets >= 44px", len(small) == 0, "; ".join(small[:5]))
        # tap a real control with touch
        tap_ok = True
        try:
            mp.tap('#slots .slot[data-index="0"] [data-act="down"]')
            time.sleep(0.2)
        except Exception as exc:  # noqa: BLE001
            tap_ok = False
            res.extra["tap_error"] = f"{type(exc).__name__}: {exc}"
        res.add("390x844 touch tap works", tap_ok)
        mp.screenshot(path=str(SHOTS / f"mobile390-{engine}.png"), full_page=True)

        # ---------------- console / third party ----------------
        page.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
        time.sleep(0.6)
        all_errs = cc.all + mcc.all
        res.add("no console errors (desktop)", len(cc.all) == 0, "; ".join(cc.all[:4]))
        res.add("no console errors (390 mobile)", len(mcc.all) == 0, "; ".join(mcc.all[:4]))
        res.add("no third-party requests", len(external) == 0,
                f"{len(external)}: {external[:5]}")

        res.extra["external_requests"] = external
        res.extra["console_errors_desktop"] = cc.console_errors
        res.extra["pageerrors_desktop"] = cc.pageerrors
        res.extra["console_errors_mobile"] = mcc.console_errors
        res.extra["pageerrors_mobile"] = mcc.pageerrors
        res.extra["request_failures"] = cc.request_failures + mcc.request_failures
        res.extra["elapsed_s"] = round(time.time() - t0, 2)

        browser.close()

    res.dump(f"journey-{engine}.json")
    return 0 if all(r["ok"] for r in res.rows) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="chromium", choices=["chromium", "msedge"])
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    sys.exit(run(a.engine, headless=not a.headed))
