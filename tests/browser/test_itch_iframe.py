#!/usr/bin/env python3
"""验证游戏在**跨源 iframe** 里能不能正常玩——这是 itch.io 的真实运行方式。

itch.io 的 HTML5 游戏不是直接打开，而是被塞进 itchi.io 域名下的一个 iframe。
这和"直接访问"有几个真实差异，任何一条踩中都会让上架后翻车：

1. **`localStorage` 可能被拒**：浏览器对第三方存储做隔离/限制，
   `localStorage.getItem` 会直接抛 SecurityError。游戏必须优雅降级而不是白屏。
2. **焦点与键盘**：iframe 未获得焦点时按键不进去；Tab 会先在宿主页里循环。
3. **`window.top` 相关操作**：任何 frame-busting 或读取父窗口都会报错。
4. **CSS `100dvh`**：iframe 高度由宿主决定，dvh 表现不同。
5. **锚点路由**：`location.hash` 在 iframe 里仍然可用，但父页面不影响。

用法：python tests/browser/test_itch_iframe.py
前置：本地 8140 服务 dist，8188 服务本脚本同目录的 host.html
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
GAME = "http://127.0.0.1:8140/"
HOST = "http://127.0.0.1:8188/host.html"

results: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(HOST, wait_until="networkidle")
        frame = page.frame_locator("#frame")

        # 1) 游戏本体能在 iframe 里渲染出来
        frame.locator("#view-home").wait_for(state="attached", timeout=15000)
        page.wait_for_timeout(1500)
        record(True, "游戏在跨源 iframe 中渲染")

        hero = frame.locator("h1").first
        record(hero.count() > 0, "首屏标题存在", (hero.inner_text(timeout=8000) or "")[:24])

        nav = frame.locator(".site-nav a")
        record(nav.count() == 3, "导航三项可点", f"{nav.count()} 项")

        # 2) 档案柜 6 张卡
        frame.locator('a[data-nav="cabinet"]').click()
        page.wait_for_timeout(1200)
        cards = frame.locator("#view-cabinet .case-card")
        record(cards.count() == 6, "档案柜 6 张卡", f"{cards.count()} 张")

        # 3) 进入 NA-001，按钮是否可点（焦点/布局正常）
        frame.locator('#view-cabinet .case-card a, #view-cabinet a[href="#/case/NA-001"]').first.click()
        page.wait_for_timeout(1500)
        slot = frame.locator("#slots .slot")
        record(slot.count() == 4, "NA-001 四个格位", f"{slot.count()} 个")

        before = frame.locator("#slots .slot__item").all_inner_texts()
        frame.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
        page.wait_for_timeout(500)
        after = frame.locator("#slots .slot__item").all_inner_texts()
        expected = [before[1], before[0], *before[2:]]
        record(after == expected, "iframe 内移动按钮生效", f"{before} -> {after}")

        # 4) iframe 内部自己的 localStorage 是否可用。
        #    注意：从父页访问 f.contentWindow.localStorage 一定抛 SecurityError ——
        #    那是跨源访问限制，不代表游戏自己写不了。必须在 iframe 内部测。
        ls = frame.locator("body").evaluate(
            """() => {
              try {
                localStorage.setItem('__probe__', '1');
                localStorage.removeItem('__probe__');
                return 'usable';
              } catch (e) { return 'blocked:' + e.name; }
            }"""
        )
        note_shown = frame.locator("#storage-note").is_visible()
        # 两者必须一致：能存就别打扰玩家；不能存就必须如实提示
        record(
            (ls == "usable") != note_shown,
            "存储可用性与提示条一致",
            f"storage={ls} 提示条={note_shown}",
        )

        # 5) 父窗口未被劫持（frame-busting 会破坏 itch 页面）
        parent_url = page.evaluate("() => location.href")
        record(parent_url == HOST, "宿主页未被游戏劫持", parent_url.split("/")[-1])

        # 6) 无未捕获异常
        record(not errors, "iframe 内无未捕获异常", str(errors[:2]))

        # 7) 键盘可用（先点进 iframe 建立焦点）
        frame.locator("#slots").click(position={"x": 5, "y": 5})
        page.wait_for_timeout(300)
        before_kb = frame.locator("#slots .slot__item").all_inner_texts()
        frame.locator('#slots .slot[data-index="0"] [data-act="pick"]').focus()
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(500)
        after_kb = frame.locator("#slots .slot__item").all_inner_texts()
        record(after_kb != before_kb, "iframe 内键盘重排生效", f"{before_kb} -> {after_kb}")

        browser.close()

    passed = sum(1 for ok, _, _ in results if ok)
    print()
    print("=" * 56)
    print(f"共 {len(results)} 项：{passed} PASS / {len(results) - passed} FAIL")
    out = ROOT / "screenshots" / "itch-iframe-report.json"
    out.write_text(json.dumps(
        {"host": HOST, "game": GAME, "checks": len(results), "passed": passed,
         "results": [{"ok": o, "name": n, "detail": d} for o, n, d in results]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告：{out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
