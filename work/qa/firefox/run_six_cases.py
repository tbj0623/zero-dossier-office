#!/usr/bin/env python3
"""Solve all six cases in Firefox using the real UI.

Oracle: `expected_solution` from cases/author/*.json (the authored answer).
Cross-check: the independent constraint solver in fx_common.solve().
For every case we additionally assert that:
  * the freshly-opened default order is NOT the answer,
  * the board really reaches the oracle order through the UI buttons,
  * submit produces a verdict and NOT an error message,
  * the logical recap of that case is rendered.

Usage: python run_six_cases.py
Writes raw/six-cases-firefox.json
"""
from __future__ import annotations

import sys
import time

from playwright.sync_api import sync_playwright

from fx_common import (LIVE_BASE, RAW, SHOTS, ConsoleCollector, Results,
                       collect_requests, current_order, expected_solution,
                       fill_order, load_public, solve)

CASES = [f"NA-00{i}" for i in range(1, 7)]


def run(headless: bool = True) -> int:
    R = Results("six-cases", "firefox")
    rows = []
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        cc = ConsoleCollector(page)
        external: list[str] = []
        collect_requests(page, LIVE_BASE, external)

        for cid in CASES:
            row = {"case": cid}
            page.goto(f"{LIVE_BASE}#/case/{cid}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector("#slots .slot", timeout=30000)

            pub = load_public(cid)
            oracle = expected_solution(cid)
            solver = solve(pub)
            row["oracle"] = oracle
            row["solver"] = solver
            row["oracle_matches_solver"] = oracle == solver
            row["items_n"] = len(pub["items"])
            row["title"] = page.inner_text("#case-title")
            row["evidence_n"] = len(page.query_selector_all(".ev-card"))

            default_order = current_order(page)
            row["default_order"] = default_order
            row["default_is_answer"] = default_order == oracle

            # expand all evidence before solving (also proves they render)
            for btn in page.query_selector_all(".ev-card__summary"):
                if btn.get_attribute("aria-expanded") == "false":
                    btn.click()

            fill_order(page, oracle)
            row["reached_order"] = current_order(page)
            row["reached_oracle"] = row["reached_order"] == oracle
            assert row["reached_oracle"], f"{cid}: could not reach oracle order through UI"

            page.click("#btn-submit")
            try:
                page.wait_for_selector(".verdict", timeout=15000)
                row["verdict"] = True
                row["verdict_title"] = page.inner_text("#verdict-title")
                logic = page.inner_text(".recap-block:not(.recap-block--story)")
                story = page.inner_text(".recap-block--story")
                row["logic_len"] = len(logic)
                row["story_len"] = len(story)
                row["has_logic"] = "逻辑复盘" in logic
                row["has_story"] = "档案后记" in story
                row["recaps_differ"] = logic.strip() != story.strip()
                # the verdict view replaces the desk DOM, so #message no longer
                # exists; query it without auto-waiting instead of get_attribute(sel).
                msg_el = page.query_selector("#message")
                row["msg_shown"] = msg_el.get_attribute("data-show") if msg_el else None
                row["verdict_replaced_desk"] = page.query_selector("#slots") is None
            except Exception as exc:  # noqa: BLE001
                row["verdict"] = False
                row["error"] = f"{type(exc).__name__}: {exc}"
                try:
                    row["message_text"] = page.inner_text("#message")
                except Exception:  # noqa: BLE001
                    pass

            ok = (row.get("verdict") and row["reached_oracle"] and row["oracle_matches_solver"]
                  and not row["default_is_answer"] and row.get("has_logic") and row.get("has_story")
                  and row.get("recaps_differ"))
            row["ok"] = bool(ok)
            rows.append(row)
            R.add(f"{cid} solved in Firefox ({row['items_n']} items)", bool(ok),
                  f"title={row['title'][:18]} | default!=answer={not row['default_is_answer']} "
                  f"| verdict={row.get('verdict_title', row.get('error', 'NONE'))}")
            page.screenshot(path=str(SHOTS / f"fx-verdict-{cid}.png"), full_page=True)

        page.goto(f"{LIVE_BASE}#/cabinet", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#cabinet .case-card")
        badge = page.inner_text("#progress-badge")
        R.add("All six archived: progress badge shows 6 / 6", "6 / 6" in badge, badge)
        done_cards = page.evaluate("""() => document.querySelectorAll('#cabinet .case-card__status--done').length""")
        R.add("All six cabinet cards marked 已归档", done_cards == 6, f"{done_cards}/6")
        page.screenshot(path=str(SHOTS / "fx-07-cabinet-all-done.png"), full_page=True)

        R.add("No console errors during six-case run", len(cc.all) == 0, "; ".join(cc.all[:3]))
        R.add("No third-party requests during six-case run", len(external) == 0, f"{len(external)}")
        browser.close()

    R.extra = {"cases": rows, "solved": sum(1 for r in rows if r["ok"]),
               "console": cc.all, "external": external, "progress_badge": badge}
    R.dump("six-cases-firefox.json")
    return 0 if all(r["ok"] for r in R.rows) else 1


if __name__ == "__main__":
    sys.exit(run(headless="--headed" not in sys.argv))
