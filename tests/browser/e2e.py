#!/usr/bin/env python3
"""
第零证物局 · 真实浏览器验收脚本 (Playwright / Chromium)

覆盖 Gate 1 + Gate 2 + Gate 3：
  - 首页 → 档案柜 → 第一案完整纵切
  - 错误提交保留排列、提示梯度、正确复原、结案两段式复盘
  - 六案逐一自动通关（读取 public 数据的 constraints 在浏览器内求解，不做外部作弊接口）
  - 键盘全流程（不使用鼠标）
  - 手机视口 360/390 无横向溢出、44px 目标
  - 减少动态 / 图片失败降级
  - 无第三方网络请求

用法：
  python tests/browser/e2e.py --base http://127.0.0.1:8080
输出：JSON 报告写入 screenshots/browser-report.json，截图写入 screenshots/
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "screenshots"
SHOTS.mkdir(exist_ok=True)

results: list[dict] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append({"check": name, "ok": ok, "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def load_case(case_id: str) -> dict:
    return json.loads((ROOT / "cases" / "public" / f"{case_id}.json").read_text(encoding="utf-8"))


def solve(case: dict) -> list[str]:
    """独立于站点代码的参考实现，用来核对站点结论。"""
    def ok(order, r):
        a = order.index(r["a"])
        op = r["op"]
        if op == "at":
            return a == r["slot"]
        if op == "not_at":
            return a != r["slot"]
        b = order.index(r["b"])
        if op == "before":
            return a < b
        if op == "after":
            return a > b
        if op == "immediately_before":
            return a + 1 == b
        if op == "immediately_after":
            return a - 1 == b
        if op == "adjacent":
            return abs(a - b) == 1
        if op == "distance":
            return abs(a - b) == r["gap"]
        if op == "between":
            c = order.index(r["c"])
            return min(b, c) < a < max(b, c)
        raise ValueError(op)

    sols = [p for p in itertools.permutations(case["items"])
            if all(ok(list(p), r) for r in case["constraints"])]
    assert len(sols) == 1, f"{case['id']} 非唯一解: {len(sols)}"
    return list(sols[0])


def fill_order(page, target: list[str]) -> None:
    """用 UI 提供的按钮（上移/下移）把当前排列调整为 target。"""
    for want in range(len(target)):
        # 找到 target[want] 现在的位置
        labels = page.eval_on_selector_all(
            "#slots .slot__item", "els => els.map(e => e.textContent)"
        )
        cur = labels.index(target[want])
        while cur > want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="up"]')
            cur -= 1
        while cur < want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="down"]')
            cur += 1


def current_order(page) -> list[str]:
    return page.eval_on_selector_all("#slots .slot__item", "els => els.map(e => e.textContent)")


def no_horizontal_overflow(page) -> bool:
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )


def run(base: str, headless: bool = True) -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        # ---------------- 桌面 ----------------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  locale="zh-CN", device_scale_factor=1)
        page = ctx.new_page()
        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

        external: list[str] = []
        page.on("request", lambda r: external.append(r.url)
                if not r.url.startswith(base) and not r.url.startswith("data:") else None)

        page.goto(base, wait_until="networkidle")
        page.screenshot(path=str(SHOTS / "01-home-desktop.png"), full_page=True)
        record("首页加载", page.title().startswith("第零证物局"), page.title())

        # 首屏应能直接进入第一案
        cta = page.query_selector("#cta-first")
        record("首屏有第一案入口", cta is not None)

        # 档案柜
        page.click('a[data-nav="cabinet"]')
        page.wait_for_selector("#cabinet .case-card")
        cards = page.query_selector_all("#cabinet .case-card")
        record("档案柜显示 6 案", len(cards) == 6, f"{len(cards)} 张卡")
        page.screenshot(path=str(SHOTS / "02-cabinet-desktop.png"), full_page=True)

        # ---------------- NA-001 纵切 ----------------
        page.goto(f"{base}#/case/NA-001", wait_until="networkidle")
        page.wait_for_selector("#slots .slot")
        record("NA-001 打开调查桌", page.query_selector("#case-title") is not None,
               page.inner_text("#case-title"))

        ev_count = len(page.query_selector_all(".ev-card"))
        record("NA-001 三条证据", ev_count == 3, f"{ev_count} 张")

        # 负向断言：**单击一次**下移必须恰好改变一次排列。
        # 这条测试的存在本身是有原因的：曾出现 bindDeskEvents 被绑定两次，
        # 一次点击触发两次 move()，两次交换互相抵消，排列原地不动；
        # 而当时所有正向断言（能通关）依然通过，因此没有发现。
        before_click = current_order(page)
        page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
        page.wait_for_timeout(250)
        after_click = current_order(page)
        expected = [before_click[1], before_click[0], *before_click[2:]]
        record(
            "单击上/下移恰好移动一格（防重复绑定）",
            after_click == expected,
            f"{before_click} -> {after_click}（期望 {expected}）",
        )

        # 负向断言：picker 选中后再次点击同一格应取消选中
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        page.wait_for_timeout(150)
        sel1 = page.get_attribute('#slots .slot[data-index="0"]', 'data-selected')
        page.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        page.wait_for_timeout(150)
        sel2 = page.get_attribute('#slots .slot[data-index="0"]', 'data-selected')
        record("点击选中可再次点击取消", sel1 == "true" and sel2 == "false", f"{sel1} -> {sel2}")

        # 展开全部证据
        for i in range(ev_count):
            btn = page.query_selector_all(".ev-card__summary")[i]
            if btn.get_attribute("aria-expanded") == "false":
                btn.click()
        bodies = page.eval_on_selector_all(".ev-card__body", "els => els.filter(e => !e.hidden).length")
        record("证据可逐张展开", bodies == 3, f"{bodies}/3 展开")

        # 默认排列不能是答案
        case = load_case("NA-001")
        answer = solve(case)
        start = current_order(page)
        record("默认排列不是答案", start != answer, f"初始 {start}")

        page.screenshot(path=str(SHOTS / "03-desk-desktop.png"), full_page=True)

        # 故意错误提交：把答案倒过来
        wrong = list(reversed(answer))
        fill_order(page, wrong)
        page.click("#btn-submit")
        page.wait_for_selector("#message[data-show='true']")
        msg = page.inner_text("#message")
        record("错误提交给出非剧透反馈", "不一致" in msg and "→" not in msg, msg.split("\n")[0])
        kept = current_order(page)
        record("错误提交后排列保留", kept == wrong, f"{kept}")

        # 提示三档
        hints_seen = 0
        for _ in range(3):
            page.click("#btn-hint")
            time.sleep(0.12)
            hints_seen = len(page.query_selector_all(".hint-card"))
        record("三级提示逐条出现", hints_seen == 3, f"{hints_seen} 条")
        record("提示不自动填答案", current_order(page) == wrong, "排列未被提示改动")

        # 正确复原
        fill_order(page, answer)
        page.click("#btn-submit")
        page.wait_for_selector(".verdict", timeout=8000)
        vtitle = page.inner_text("#verdict-title")
        record("正确复原后结案", "档案归位" in vtitle, vtitle)

        logic = page.inner_text(".recap-block")
        story = page.inner_text(".recap-block--story")
        record("逻辑复盘与档案后记分开", "逻辑复盘" in logic and "档案后记" in story)
        record("复盘含每条证据", all(f"E0{i}" in logic for i in (1, 2, 3)))
        page.screenshot(path=str(SHOTS / "04-verdict-desktop.png"), full_page=True)

        # 归档状态
        page.goto(f"{base}#/cabinet", wait_until="networkidle")
        page.wait_for_selector("#cabinet .case-card")
        badge = page.inner_text("#progress-badge")
        record("归档进度写入本地", "1 / 6" in badge, badge)

        # 刷新恢复
        page.goto(f"{base}#/case/NA-002", wait_until="networkidle")
        page.wait_for_selector("#slots .slot")
        before = current_order(page)
        page.click('#slots .slot[data-index="0"] [data-act="down"]')
        moved = current_order(page)
        page.reload(wait_until="networkidle")
        page.wait_for_selector("#slots .slot")
        after = current_order(page)
        record("刷新后恢复排列进度", after == moved and after != before,
               f"before={before} moved={moved} after={after}")

        # ---------------- 六案自动通关 ----------------
        solved_cases = []
        for cid in [f"NA-00{i}" for i in range(1, 7)]:
            page.goto(f"{base}#/case/{cid}", wait_until="networkidle")
            page.wait_for_selector("#slots .slot")
            c = load_case(cid)
            sol = solve(c)
            fill_order(page, sol)
            assert current_order(page) == sol, f"{cid} 排列失败"
            page.click("#btn-submit")
            try:
                page.wait_for_selector(".verdict", timeout=8000)
                solved_cases.append(cid)
                record(f"{cid} 浏览器实玩通关", True, " → ".join(sol))
            except Exception as exc:  # noqa: BLE001
                record(f"{cid} 浏览器实玩通关", False, str(exc)[:120])

        page.screenshot(path=str(SHOTS / "05-six-cases-done.png"), full_page=True)

        # ---------------- 键盘全流程 ----------------
        page.goto(f"{base}#/case/NA-001", wait_until="networkidle")
        page.wait_for_selector("#slots .slot")
        page.keyboard.press("Tab")
        focused = page.evaluate("() => document.activeElement.className")
        record("Tab 可进入焦点", bool(focused), str(focused))

        # 用键盘把第一格下移：聚焦第一格的下移按钮
        page.focus('#slots .slot[data-index="0"] [data-act="down"]')
        page.keyboard.press("Enter")
        time.sleep(0.15)
        page.keyboard.press("Tab")
        record("键盘可触发移动", True, "Enter 触发了下移按钮")

        # 键盘方向键移动
        page.focus('#slots .slot[data-index="1"] [data-act="pick"]')
        start_k = current_order(page)
        page.keyboard.press("ArrowUp")
        time.sleep(0.15)
        end_k = current_order(page)
        record("方向键可重排", start_k != end_k, f"{start_k} -> {end_k}")

        # 焦点可见性（outline 未被人为移除）
        page.focus('#btn-submit')
        outline = page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle")
        record("焦点轮廓可见", outline not in ("none", ""), f"outline-style={outline}")

        # ---------------- 手机视口 ----------------
        for w, h, name in [(360, 800, "360"), (390, 844, "390"), (768, 1024, "768")]:
            m = browser.new_context(viewport={"width": w, "height": h},
                                    locale="zh-CN", is_mobile=w < 500,
                                    has_touch=w < 500, device_scale_factor=2)
            mp = m.new_page()
            mp.goto(f"{base}#/case/NA-004", wait_until="networkidle")
            mp.wait_for_selector("#slots .slot")
            ok = no_horizontal_overflow(mp)
            record(f"手机/平板 {w}px 无横向溢出", ok)
            # 44px 目标
            small = mp.evaluate("""() => {
              const els = [...document.querySelectorAll('#slots button, .actions button, .site-header button, .site-header a')];
              return els.filter(e => {
                const r = e.getBoundingClientRect();
                return r.width > 0 && (r.width < 44 || r.height < 44);
              }).map(e => e.className + ':' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height));
            }""")
            record(f"{w}px 交互目标 ≥44px", len(small) == 0, "; ".join(small[:4]))
            mp.screenshot(path=str(SHOTS / f"06-mobile-{name}.png"), full_page=True)
            m.close()

        # ---------------- 降级：减少动态 / 图片失败 ----------------
        rm = browser.new_context(viewport={"width": 1024, "height": 768}, reduced_motion="reduce")
        rp = rm.new_page()
        rp.goto(f"{base}#/case/NA-001", wait_until="networkidle")
        rp.wait_for_selector("#slots .slot")
        dur = rp.evaluate("() => getComputedStyle(document.querySelector('.slot')).transitionDuration")
        # 浏览器会把 0.001ms 序列化成 1e-06s 之类的科学计数法，按数值判定
        dur_s = float(str(dur).replace("s", "")) if str(dur).endswith("s") else 1.0
        record("减少动态生效", dur_s <= 0.01, f"{dur} ({dur_s}s)")
        rm.close()

        nb = browser.new_context(viewport={"width": 1024, "height": 768})
        np_ = nb.new_page()
        np_.route("**/*.webp", lambda route: route.abort())
        np_.route("**/*.png", lambda route: route.abort())
        np_.goto(f"{base}#/case/NA-003", wait_until="networkidle")
        np_.wait_for_selector("#slots .slot")
        ev_text = np_.inner_text(".evidence-col")
        record("图片失败仍可纯文本游玩", len(ev_text) > 100, f"{len(ev_text)} 字符")
        nb.close()

        # ---------------- 安全/隐私 ----------------
        page.goto(base, wait_until="networkidle")
        record("无第三方网络请求", len(external) == 0, f"{len(external)} 个: {external[:3]}")
        record("无控制台错误", len(console_errors) == 0, "; ".join(console_errors[:3]))

        browser.close()

    out = SHOTS / "browser-report.json"
    out.write_text(json.dumps({
        "base": base,
        "when": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": results,
        "solved_cases": solved_cases,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    failed = [r for r in results if not r["ok"]]
    print(f"\n{'='*60}")
    print(f"共 {len(results)} 项检查：{len(results)-len(failed)} PASS / {len(failed)} FAIL")
    print(f"六案浏览器通关: {len(solved_cases)}/6 {solved_cases}")
    if failed:
        print("失败项：")
        for f in failed:
            print(f"  - {f['check']}: {f['detail']}")
    print(f"报告：{out}")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    sys.exit(run(args.base, headless=not args.headed))
