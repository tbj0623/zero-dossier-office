#!/usr/bin/env python3
"""验证 **itch.io 上真实托管**的游戏能完整通关——匿名访客视角。

这是发布后最重要的一条验证：不是本地 dist、也不是自己搭的 iframe 模拟，
而是 itch.io 域名 + itch CDN（html-classic.itch.zone）里跑的实例。

检查项：
  1. 公开页面可访问（HTTP 200），标题正确
  2. Run game 能启动，游戏在 itch 的 iframe 中加载
  3. 游戏内导航、档案柜、案件桌面都渲染
  4. NA-001 用真实按钮完成排列并提交，出结案页
  5. 无控制台错误、无第三方异常

用法：python tests/browser/test_itch_live.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
URL = "https://tbj0623.itch.io/zero-dossier-office"

results: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def find_game_frame(page):
    """在 itch 页面里找出承载游戏的那个 iframe。"""
    for f in page.frames:
        if "itch.zone" not in f.url:
            continue
        try:
            if f.locator("#view-home, #slots").count() > 0:
                return f
        except Exception:
            continue
    return None


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        # 1) 公开页面
        resp = page.goto(URL, wait_until="networkidle", timeout=60000)
        record(resp is not None and resp.status == 200, "公开页面 HTTP 200",
               f"status={resp.status if resp else '?'}")
        title = page.title()
        record("第零证物局" in title, "页面标题正确", title[:50])

        # 2) 启动游戏
        launched = False
        for sel in ("button:has-text('Run game')", "a:has-text('Run game')", ".play_btn"):
            try:
                if page.is_visible(sel):
                    page.click(sel)
                    launched = True
                    break
            except Exception:
                continue
        record(launched, "Run game 可点击")

        frame = None
        for _ in range(20):
            page.wait_for_timeout(1000)
            frame = find_game_frame(page)
            if frame:
                break
        record(frame is not None, "游戏在 itch iframe 中加载",
               frame.url[:60] if frame else "未找到")

        if not frame:
            browser.close()
            return finish()

        # 3) 游戏内导航
        frame.wait_for_timeout(800)
        record(frame.locator("#view-home").count() > 0, "首页视图存在")
        record(frame.locator("html").get_attribute("lang") == "zh-CN", "默认中文")

        frame.locator('a[data-nav="cabinet"]').click()
        frame.wait_for_timeout(1200)
        cards = frame.locator("#view-cabinet .case-card").count()
        record(cards == 6, "档案柜 6 张卡", f"{cards} 张")

        # 4) 进入 NA-001
        frame.locator('#view-cabinet a[href="#/case/NA-001"]').first.click()
        frame.wait_for_timeout(1500)
        slots = frame.locator("#slots .slot").count()
        record(slots == 4, "NA-001 四个格位", f"{slots} 个")

        # 5) 用真实按钮排列到答案
        auth = json.loads((ROOT / "cases" / "author" / "NA-001.json").read_text(encoding="utf-8"))
        target = auth["expected_solution"]
        ok_order = True
        for want in range(len(target)):
            labels = frame.locator("#slots .slot__item").all_inner_texts()
            if target[want] not in labels:
                ok_order = False
                break
            cur = labels.index(target[want])
            while cur > want:
                frame.locator(f'#slots .slot[data-index="{cur}"] [data-act="up"]').click()
                frame.wait_for_timeout(90)
                cur -= 1
            while cur < want:
                frame.locator(f'#slots .slot[data-index="{cur}"] [data-act="down"]').click()
                frame.wait_for_timeout(90)
                cur += 1
        record(ok_order, "排列到答案顺序")

        frame.locator("#btn-submit").click()
        try:
            frame.wait_for_selector(".verdict", timeout=10000)
            solved = True
        except Exception:
            solved = False
        record(solved, "提交后出现结案页")

        if solved:
            h1 = frame.locator(".verdict__h1").inner_text(timeout=5000)
            record("档案归位" in h1, "结案标题正确", h1[:20])
            labels = frame.locator(".recap-block__label").all_inner_texts()
            record(len(labels) >= 2, "逻辑复盘 + 档案后记两段", str([x.strip()[:12] for x in labels]))

        # 6) 无异常
        record(not page_errors, "无未捕获异常", str(page_errors[:2]))
        page.screenshot(path=str(ROOT / "work" / "qa" / "itch-iframe" / "live-itch-solved.png"))
        browser.close()

    return finish()


def finish() -> int:
    passed = sum(1 for ok, _, _ in results if ok)
    print()
    print("=" * 56)
    print(f"共 {len(results)} 项：{passed} PASS / {len(results) - passed} FAIL")
    out = ROOT / "screenshots" / "itch-live-report.json"
    out.write_text(json.dumps(
        {"url": URL, "checks": len(results), "passed": passed,
         "results": [{"ok": o, "name": n, "detail": d} for o, n, d in results]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告：{out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
