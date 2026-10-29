#!/usr/bin/env python3
"""WebKit core-journey runner for 第零证物局.

Mirrors the assertions of tests/browser/cross_engine.py and tests/browser/e2e.py,
but launched with p.webkit.launch() and pointed at the LOCAL server
http://127.0.0.1:8140.

Writes raw/journey-webkit.json.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright
from wk_common import (BASE, ConsoleCollector, Results, collect_requests, current_order,
                       expected_solution, fill_order, goto, now_iso, open_case, RAW)

R = Results("journey", "webkit")


def main() -> int:
    requests_seen: dict[str, list[str]] = {}

    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        R.extra["webkit_version"] = browser.version
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        cc = ConsoleCollector(page)
        external: list[str] = []
        collect_requests(page, external)

        # ---------------- 1. home ----------------
        page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(700)
        title = page.title()
        R.add("1. 首页加载并有标题", bool(title.strip()), title)
        R.add("1. #cta-first 可见", page.is_visible("#cta-first"),
              page.inner_text("#cta-first")[:40] if page.is_visible("#cta-first") else "not visible")
        R.add("1. 首页 view 处于激活态",
              page.get_attribute("#view-home", "data-active") == "true",
              page.get_attribute("#view-home", "data-active"))

        page.screenshot(path=str(RAW.parent / "shots" / "wk-01-home-1440.png"), full_page=True)

        # ---------------- 2. sticky header ----------------
        # scroll on the home page itself, then verify top == 0
        hdr_before = page.evaluate("() => document.querySelector('.site-header').getBoundingClientRect().top")
        page.evaluate("() => window.scrollTo(0, 600)")
        page.wait_for_timeout(450)
        hdr_after = page.evaluate("""() => {
            const h = document.querySelector('.site-header');
            const r = h.getBoundingClientRect();
            const cs = getComputedStyle(h);
            return { top: r.top, bottom: r.bottom, height: r.height, position: cs.position,
                     scrollY: window.scrollY };
        }""")
        R.add("2. 头部 position: sticky", hdr_after["position"] == "sticky", hdr_after["position"])
        R.add("2. 滚动 600px 后头部仍 top=0",
              abs(hdr_after["top"]) < 1 and abs(hdr_after["scrollY"] - 600) < 2,
              f"top={hdr_after['top']:.2f} scrollY={hdr_after['scrollY']} h={hdr_after['height']:.1f}")
        R.add("2. 头部未随滚动移出（top 与滚动前一致）",
              abs(hdr_before - hdr_after["top"]) < 1,
              f"before={hdr_before:.2f} after={hdr_after['top']:.2f}")
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(250)

        # ---------------- 3. cabinet ----------------
        goto(page, "#/cabinet", 700)
        page.wait_for_selector("#view-cabinet .case-card", timeout=15000)
        cards = page.query_selector_all("#view-cabinet .case-card")
        R.add("3. 档案柜恰好 6 张卡", len(cards) == 6, f"{len(cards)} 张")
        links = page.eval_on_selector_all(
            "#view-cabinet .case-card .case-card__cta",
            "e=>e.map(x=>x.getAttribute('href'))")
        want_ids = [f"#/case/NA-00{i}" for i in range(1, 7)]
        R.add("3. 六张卡各自链接到一个案件", links == want_ids,
              f"{links}")
        page.screenshot(path=str(RAW.parent / "shots" / "wk-02-cabinet-1440.png"), full_page=True)

        # ---------------- 4. NA-001 desk ----------------
        open_case(page, "NA-001")
        R.add("4. NA-001 调查桌打开",
              page.query_selector("#case-title") is not None,
              page.inner_text("#case-title") if page.query_selector("#case-title") else "missing")
        ev_count = len(page.query_selector_all(".ev-card"))
        R.add("4. NA-001 三张证据卡", ev_count == 3, f"{ev_count} 张")
        # expand all (first is open by default)
        for i in range(ev_count):
            btn = page.query_selector_all(".ev-card__summary")[i]
            if btn.get_attribute("aria-expanded") == "false":
                btn.click()
                page.wait_for_timeout(120)
        bodies = page.eval_on_selector_all(".ev-card__body", "e=>e.filter(x=>!x.hidden).length")
        R.add("4. 三张证据全部可展开", bodies == 3, f"{bodies}/3 展开")
        state = page.eval_on_selector_all(".ev-card__summary", "e=>e.map(x=>x.getAttribute('aria-expanded'))")
        R.add("4. aria-expanded 全部为 true", state == ["true", "true", "true"], str(state))

        # ---------------- 5. default != answer ----------------
        answer = expected_solution("NA-001")
        start = current_order(page)
        R.add("5. 默认排列 ≠ 答案", start != answer, f"初始 {start} vs 答案 {answer}")

        page.screenshot(path=str(RAW.parent / "shots" / "wk-03-desk-NA001-1440.png"), full_page=True)

        # ---------------- 6. one click == one slot ----------------
        before = current_order(page)
        page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
        page.wait_for_timeout(350)
        after = current_order(page)
        want = [before[1], before[0], *before[2:]]
        R.add("6. 单击「下移」恰好移动一格（防双绑定）", after == want,
              f"{before} -> {after}，期望 {want}")

        # and one click on "up" of slot 1 moves it back exactly one
        page.locator('#slots .slot[data-index="1"] [data-act="up"]').click()
        page.wait_for_timeout(350)
        back = current_order(page)
        R.add("6b. 反向单击也恰好移动一格", back == before, f"{after} -> {back}，期望 {before}")

        # pick/swap: one click on pick selects, second click on another slot swaps once
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        page.wait_for_timeout(200)
        sel = page.get_attribute('#slots .slot[data-index="0"]', "data-selected")
        page.locator('#slots .slot[data-index="2"] [data-act="pick"]').click()
        page.wait_for_timeout(300)
        swapped = current_order(page)
        want_swap = [before[2], before[1], before[0], *before[3:]]
        R.add("6c. 点选两格仅交换一次", sel == "true" and swapped == want_swap,
              f"selected={sel} {before} -> {swapped}, 期望 {want_swap}")
        # restore
        page.locator('#slots .slot[data-index="2"] [data-act="pick"]').click()
        page.wait_for_timeout(150)
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        page.wait_for_timeout(250)

        # ---------------- 7. arrow keys ----------------
        base_order = current_order(page)
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').focus()
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(300)
        k1 = current_order(page)
        R.add("7. ArrowDown 重排焦点格位", k1 != base_order and k1[0] == base_order[1] and k1[1] == base_order[0],
              f"{base_order} -> {k1}")
        page.keyboard.press("ArrowUp")
        page.wait_for_timeout(300)
        k2 = current_order(page)
        R.add("7b. ArrowUp 回到原排列", k2 == base_order, f"{k1} -> {k2}")
        # boundary: ArrowUp in slot 0 must be a no-op, not a wrap-around
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').focus()
        page.keyboard.press("ArrowUp")
        page.wait_for_timeout(250)
        k3 = current_order(page)
        R.add("7c. 首格 ArrowUp 不环绕", k3 == base_order, f"{k3}")

        # ---------------- 8. hints ----------------
        order_before_hints = current_order(page)
        counts = []
        for _ in range(3):
            page.locator("#btn-hint").click()
            page.wait_for_timeout(300)
            counts.append(len(page.query_selector_all(".hint-card")))
        R.add("8. 三条提示逐条出现 counts==[1,2,3]", counts == [1, 2, 3], str(counts))
        order_after_hints = current_order(page)
        R.add("8b. 提示不自动排列", order_after_hints == order_before_hints,
              f"{order_before_hints} -> {order_after_hints}")
        hint_btn_disabled = page.get_attribute("#btn-hint", "disabled")
        R.add("8c. 三条用尽后提示按钮禁用", hint_btn_disabled is not None, str(hint_btn_disabled))
        hint_texts = page.eval_on_selector_all(".hint-card", "e=>e.map(x=>x.textContent.slice(0,60))")
        R.add("8d. 三条提示内容彼此不同", len(set(hint_texts)) == 3, str(hint_texts))

        page.screenshot(path=str(RAW.parent / "shots" / "wk-04-hints-NA001-1440.png"), full_page=True)

        # ---------------- 9. correct solve -> verdict ----------------
        fill_order(page, answer, pause=70)
        R.add("9. 排列达到答案", current_order(page) == answer, str(current_order(page)))
        page.locator("#btn-submit").click()
        ok = False
        try:
            page.wait_for_selector(".verdict", timeout=12000)
            ok = True
        except Exception as exc:  # noqa: BLE001
            R.add("9. 未出现结案页（异常）", False, str(exc)[:160])
        R.add("9. 正确复原后出现结案页", ok, "")
        if ok:
            vtitle = page.inner_text("#verdict-title")
            R.add("9b. 结案标题正确", "档案归位" in vtitle, vtitle)
            labels = page.eval_on_selector_all(".recap-block__label", "e=>e.map(x=>x.textContent.trim())")
            R.add("9c. 两个不同的复盘区块", len(labels) >= 2 and len(set(labels)) == len(labels),
                  str([x[:20] for x in labels]))
            logic = page.inner_text(".recap-block")
            story = page.inner_text(".recap-block--story")
            R.add("9d. 逻辑复盘与档案后记分离",
                  "逻辑复盘" in logic and "档案后记" in story,
                  f"logic={logic[:26]!r} story={story[:26]!r}")
            R.add("9e. 逻辑复盘覆盖每条证据",
                  all(f"E0{i}" in logic for i in (1, 2, 3)),
                  str([f"E0{i}" in logic for i in (1, 2, 3)]))
            R.add("9f. 复盘两段文本不同源",
                  logic.replace("逻辑复盘", "") != story.replace("档案后记", ""),
                  f"{len(logic)} vs {len(story)} chars")
            page.screenshot(path=str(RAW.parent / "shots" / "wk-05-verdict-NA001-1440.png"), full_page=True)

        # ---------------- 10. console / network ----------------
        R.add("10. 无控制台错误", len(cc.console_errors) == 0, "; ".join(cc.console_errors[:3]))
        R.add("10b. 无未捕获页面异常", len(cc.pageerrors) == 0, "; ".join(cc.pageerrors[:3]))
        R.add("10c. 无失败请求", len(cc.request_failures) == 0, "; ".join(cc.request_failures[:3]))
        R.add("10d. 无第三方网络请求", len(external) == 0,
              f"{len(external)}: {external[:4]}")
        requests_seen["external"] = external

        ctx.close()
        browser.close()

    R.extra["external_requests"] = requests_seen.get("external", [])
    R.dump("journey-webkit.json")
    return 0 if R.rows and all(r["ok"] for r in R.rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
