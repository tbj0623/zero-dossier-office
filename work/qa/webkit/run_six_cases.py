#!/usr/bin/env python3
"""WebKit: solve all six cases through the real UI.

Answers come from cases/author/*.json -> expected_solution (read-only), and are
cross-checked against an independent constraint solver on cases/public/*.json.
Writes raw/six-cases-webkit.json.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright
from wk_common import (BASE, ConsoleCollector, RAW, Results, current_order, expected_solution,
                       fill_order, load_public, open_case, solve)

R = Results("six_cases", "webkit")
CASE_IDS = [f"NA-00{i}" for i in range(1, 7)]


def main() -> int:
    detail_rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        R.extra["webkit_version"] = browser.version
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        cc = ConsoleCollector(page)

        for cid in CASE_IDS:
            pub = load_public(cid)
            auth = expected_solution(cid)
            ref = solve(pub)
            row = {"case": cid, "author_solution": auth, "solver_solution": ref,
                   "author_equals_solver": auth == ref}

            # answer data integrity first (this is a data check, not a browser check)
            R.add(f"{cid} 作者答案 == 独立求解器", auth == ref,
                  "" if auth == ref else f"{auth} vs {ref}")

            open_case(page, cid)
            row["deadline_open"] = True
            n_slots = len(page.query_selector_all("#slots .slot"))
            row["slots"] = n_slots
            R.add(f"{cid} 格位数与案件一致", n_slots == len(pub["slots"]),
                  f"{n_slots} vs {len(pub['slots'])}")

            start = current_order(page)
            row["start"] = start
            R.add(f"{cid} 初始排列 ≠ 答案", start != auth, f"{start}")

            n_ev = len(page.query_selector_all(".ev-card"))
            row["evidence_cards"] = n_ev
            R.add(f"{cid} 证据卡数量", n_ev == len(pub["evidence"]),
                  f"{n_ev} vs {len(pub['evidence'])}")

            # one-click-moves-one-slot guard, on every case (not just NA-001)
            b = current_order(page)
            page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
            page.wait_for_timeout(260)
            a = current_order(page)
            exp = [b[1], b[0], *b[2:]]
            R.add(f"{cid} 单击恰好移动一格", a == exp, f"{b} -> {a}")

            # solve via UI buttons
            fill_order(page, auth, pause=55)
            row["final"] = current_order(page)
            R.add(f"{cid} 可通过 UI 排到答案", row["final"] == auth, str(row["final"]))

            page.locator("#btn-submit").click()
            solved = False
            try:
                page.wait_for_selector(".verdict", timeout=12000)
                solved = True
            except Exception:  # noqa: BLE001
                pass
            row["solved"] = solved
            if solved:
                row["verdict_title"] = page.inner_text("#verdict-title")
                labels = page.eval_on_selector_all(".recap-block__label", "e=>e.map(x=>x.textContent.trim())")
                row["recap_labels"] = labels
                row["recap_blocks"] = len(labels)
                row["progress_badge"] = page.inner_text("#progress-badge") if page.query_selector("#progress-badge") else None
                page.screenshot(path=str(RAW.parent / "shots" / f"wk-six-{cid}.png"), full_page=True)
            R.add(f"{cid} 通关出结案页", solved, row.get("verdict_title", "")[:30])
            R.add(f"{cid} 结案页有两段不同复盘",
                  solved and len(row.get("recap_labels", [])) >= 2,
                  str(row.get("recap_labels", []))[:80])
            detail_rows.append(row)

        # final progress check
        page.goto(f"{BASE}/#/cabinet", wait_until="networkidle", timeout=45000)
        page.wait_for_selector("#progress-badge", timeout=15000)
        page.wait_for_timeout(500)
        badge = page.inner_text("#progress-badge")
        R.add("全部通关后归档进度 6 / 6", "6 / 6" in badge, badge)
        page.screenshot(path=str(RAW.parent / "shots" / "wk-six-all-done-cabinet.png"), full_page=True)

        R.add("六案全程无控制台错误", len(cc.console_errors) == 0, "; ".join(cc.console_errors[:3]))
        R.add("六案全程无页面异常", len(cc.pageerrors) == 0, "; ".join(cc.pageerrors[:3]))
        ctx.close()
        browser.close()

    R.extra["cases"] = detail_rows
    R.extra["solved_count"] = sum(1 for r in detail_rows if r["solved"])
    R.dump("six-cases-webkit.json")
    print(f"\nSOLVED: {R.extra['solved_count']}/6")
    return 0 if R.extra["solved_count"] == 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
