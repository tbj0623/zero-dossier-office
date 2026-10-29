#!/usr/bin/env python3
"""D: deep-link / refresh / back-forward / invalid-route behaviour on the LIVE site.

Chromium + Edge both run the same checks so divergence is visible.

Usage: python run_deeplink.py --engine chromium|msedge
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from playwright.sync_api import sync_playwright

from qa_common import LIVE_BASE, RAW, SHOTS, ConsoleCollector, Results, collect_requests, current_order, load_case

CABINET_CARDS = "#cabinet .case-card"


def wait_desk(page, timeout=20000):
    page.wait_for_selector("#slots .slot", timeout=timeout)


def cabinet_count(page) -> int:
    page.wait_for_selector(CABINET_CARDS, timeout=15000)
    return len(page.query_selector_all(CABINET_CARDS))


def app_state(page) -> dict:
    return page.evaluate("""() => {
        const caseView = document.querySelector('#view-case');
        const homeView = document.querySelector('#view-home');
        const cabView = document.querySelector('#view-cabinet');
        const visible = (el) => !!el && el.dataset.active === 'true' &&
            getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().height > 0;
        return {
            hash: location.hash,
            title: document.title,
            homeActive: homeView?.dataset.active,
            cabinetActive: cabView?.dataset.active,
            caseActive: caseView?.dataset.active,
            homeVisible: visible(homeView),
            cabinetVisible: visible(cabView),
            caseVisible: visible(caseView),
            hasSlots: !!document.querySelector('#slots .slot'),
            hasErrorHeadline: document.body.innerText.includes('这份档案尚未完整送达'),
            hasEmptyState: !!document.querySelector('.empty-state'),
            caseRootLen: document.querySelector('#case-root')?.innerText.trim().length || 0,
            navCurrent: document.querySelector('.site-nav a[aria-current="page"]')?.textContent?.trim() || null,
        };
    }""")


def run(engine: str) -> int:
    res = Results("deeplink", engine)
    external: list[str] = []

    with sync_playwright() as p:
        try:
            browser = (p.chromium.launch(headless=True, channel="msedge") if engine == "msedge"
                       else p.chromium.launch(headless=True))
        except Exception as exc:  # noqa: BLE001
            res.add("browser launch", False, f"{type(exc).__name__}: {exc}")
            res.dump(f"deeplink-{engine}.json")
            return 1
        res.extra["browser_version"] = browser.version

        # ---------- 1. cold deep link to NA-004 in a brand-new context ----------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()
        cc = ConsoleCollector(page)
        collect_requests(page, LIVE_BASE, external)
        page.goto(f"{LIVE_BASE}#/case/NA-004", wait_until="networkidle", timeout=60000)
        wait_desk(page)
        st = app_state(page)
        title = page.inner_text("#case-title")
        res.add("cold deep-link #/case/NA-004 opens the desk", st["hasSlots"] and st["caseVisible"],
                f"title={title!r} hash={st['hash']} caseActive={st['caseActive']}")
        res.add("cold deep-link renders a real case, not an error",
                not st["hasErrorHeadline"] and not st["hasEmptyState"],
                f"rootLen={st['caseRootLen']}")
        res.add("cold deep-link sets the document title",
                "第五盏灯" in st["title"] or st["title"].count("第零证物局") >= 1, st["title"])
        page.screenshot(path=str(SHOTS / f"deeplink-NA004-{engine}.png"), full_page=False)

        # refresh while deep-linked
        page.reload(wait_until="networkidle", timeout=60000)
        wait_desk(page)
        rs = app_state(page)
        res.add("refresh on a deep link keeps the case", rs["caseVisible"] and rs["hasSlots"],
                rs["hash"])

        # ---------- 2. partial progress survives refresh ----------
        page.goto(f"{LIVE_BASE}#/case/NA-002", wait_until="networkidle", timeout=60000)
        wait_desk(page)
        page.click('#slots .slot[data-index="0"] [data-act="down"]')
        page.wait_for_timeout(200)
        moved = current_order(page)
        # also open one hint so the saved blob has more than order
        page.click("#btn-hint")
        page.wait_for_timeout(200)
        hint_count = len(page.query_selector_all(".hint-card"))
        page.reload(wait_until="networkidle", timeout=60000)
        wait_desk(page)
        after = current_order(page)
        hint_after = len(page.query_selector_all(".hint-card"))
        res.add("arrangement restored after refresh", after == moved, f"{moved} -> {after}")
        res.add("hint progress restored after refresh", hint_after == hint_count,
                f"{hint_count} -> {hint_after}")

        # ---------- 3. Back / Forward ----------
        page.goto(f"{LIVE_BASE}#/cabinet", wait_until="networkidle", timeout=60000)
        n_before = cabinet_count(page)
        page.click(f'a[href="#/case/NA-003"]')
        wait_desk(page)
        on_case = app_state(page)
        page.go_back()
        page.wait_for_timeout(700)
        back_state = app_state(page)
        page.wait_for_selector(CABINET_CARDS, timeout=15000)
        n_back = len(page.query_selector_all(CABINET_CARDS))
        res.add("Back from a case returns to the cabinet",
                back_state["cabinetVisible"] and not back_state["caseVisible"],
                f"hash={back_state['hash']} cabinetActive={back_state['cabinetActive']} cards={n_back}")
        res.add("cabinet still renders all cards after Back", n_back == n_before == 6, f"{n_back} cards")

        page.go_forward()
        page.wait_for_timeout(900)
        fwd = app_state(page)
        res.add("Forward returns to the same case",
                fwd["hasSlots"] and fwd["caseVisible"] and "NA-003" in fwd["hash"],
                f"hash={fwd['hash']} slots={fwd['hasSlots']}")

        # Back from a deep link when there IS a same-origin predecessor (the real
        # user flow: land on home, follow a link into a case, press Back).
        ctx2 = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        p2 = ctx2.new_page()
        cc2 = ConsoleCollector(p2)
        p2.goto(LIVE_BASE, wait_until="networkidle", timeout=60000)
        p2.goto(f"{LIVE_BASE}#/case/NA-005", wait_until="networkidle", timeout=60000)
        wait_desk(p2)
        p2.go_back()
        p2.wait_for_timeout(1000)
        st2 = app_state(p2)
        res.add("Back from a deep link returns to the previous in-site page",
                (st2["homeVisible"] or st2["cabinetVisible"]) and not st2["caseVisible"],
                f"hash={st2['hash']!r} homeVisible={st2['homeVisible']} cabinetVisible={st2['cabinetVisible']} caseVisible={st2['caseVisible']}")

        # Informational: in a *cold* tab the only history entry before the deep
        # link is the browser's own new-tab page, so Back leaves the site. This is
        # standard browser behaviour, not an app defect; recorded, not scored.
        ctx3 = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        p3 = ctx3.new_page()
        p3.goto(f"{LIVE_BASE}#/case/NA-005", wait_until="networkidle", timeout=60000)
        wait_desk(p3)
        hist_len = p3.evaluate("() => history.length")
        p3.go_back()
        p3.wait_for_timeout(900)
        res.extra["cold_tab_back"] = {
            "history_length": hist_len,
            "url_after_back": p3.url,
            "note": "about:blank = the tab's initial page (harness artefact / normal browser behaviour); the app itself did not blank",
        }
        print(f"[INFO] cold-tab Back -> {p3.url!r} (history.length={hist_len}); app not at fault")

        # ---------- 4. invalid routes ----------
        for bad, label in [("#/case/NA-999", "invalid case id"), ("#/nonsense", "unknown route"),
                           ("#/case/NA-00", "malformed case id"), ("#/case/na-001", "lowercase id")]:
            p2.goto(f"{LIVE_BASE}{bad}", wait_until="networkidle", timeout=60000)
            p2.wait_for_timeout(900)
            s = app_state(p2)
            usable = (s["caseVisible"] or s["cabinetVisible"] or s["homeVisible"]
                      or s["hasErrorHeadline"] or s["caseRootLen"] > 0)
            res.add(f"{label} ({bad}) does not blank the app", usable,
                    f"hash={s['hash']} home={s['homeActive']} cabinet={s['cabinetActive']} "
                    f"slots={s['hasSlots']} err={s['hasErrorHeadline']} rootLen={s['caseRootLen']}")
            if s["hasEmptyState"]:
                txt = p2.inner_text(".empty-state").replace("\n", " | ")[:140]
                res.extra.setdefault("invalid_route_text", {})[bad] = txt

        # NA-999 is a *valid-looking* id: what does the user actually get?
        p2.goto(f"{LIVE_BASE}#/case/NA-999", wait_until="networkidle", timeout=60000)
        p2.wait_for_timeout(1200)
        s999 = app_state(p2)
        text999 = p2.evaluate("() => document.querySelector('#case-root')?.innerText.trim().slice(0,200) || ''")
        res.extra["na999"] = {"state": s999, "text": text999}
        res.add("NA-999 shows a clear in-app explanation",
                bool(text999) and (s999["hasErrorHeadline"] or s999["hasEmptyState"]),
                text999.replace("\n", " | ")[:120])

        # ---------- 5. clear localStorage then reload on NA-001 ----------
        p3 = ctx2.new_page()
        cc3 = ConsoleCollector(p3)
        p3.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
        wait_desk(p3)
        original = current_order(p3)
        p3.click('#slots .slot[data-index="0"] [data-act="down"]')
        p3.click("#btn-hint")
        p3.wait_for_timeout(250)
        p3.evaluate("() => localStorage.clear()")
        p3.reload(wait_until="networkidle", timeout=60000)
        wait_desk(p3)
        cleared = current_order(p3)
        hints_cleared = len(p3.query_selector_all(".hint-card"))
        s3 = app_state(p3)
        res.add("after clearing localStorage the case still loads", s3["caseVisible"] and s3["hasSlots"], f"order={cleared}")
        res.add("after clearing localStorage the order resets to the default",
                cleared == original, f"default={original} now={cleared}")
        res.add("after clearing localStorage hints are gone", hints_cleared == 0,
                f"{hints_cleared} hint cards")
        p3.goto(f"{LIVE_BASE}#/cabinet", wait_until="networkidle", timeout=60000)
        badge = p3.inner_text("#progress-badge")
        res.add("after clearing localStorage progress badge is zero", "0 / 6" in badge, badge)
        p3.screenshot(path=str(SHOTS / f"cleared-{engine}.png"), full_page=False)

        # ---------- console / third-party over the whole run ----------
        all_errs = cc.all + cc2.all + cc3.all
        res.add("no console errors across the deep-link run", len(all_errs) == 0,
                "; ".join(all_errs[:4]))
        res.add("no third-party requests", len(external) == 0, f"{len(external)}: {external[:4]}")
        res.extra["external_requests"] = external
        res.extra["console_errors"] = cc.console_errors + cc2.console_errors + cc3.console_errors
        res.extra["pageerrors"] = cc.pageerrors + cc2.pageerrors + cc3.pageerrors

        browser.close()

    res.dump(f"deeplink-{engine}.json")
    return 0 if all(r["ok"] for r in res.rows) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="chromium", choices=["chromium", "msedge"])
    a = ap.parse_args()
    sys.exit(run(a.engine))
