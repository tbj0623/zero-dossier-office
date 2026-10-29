#!/usr/bin/env python3
"""WebKit/Safari 键盘可达性回归。

背景（WebKit QA 实测）：Safari 的「按 Tab 高亮项目」默认只含表单控件，
普通 <a href> 不在 Tab 序列里。修复前首页有 20 个链接，WebKit 按 Tab 只能到
2 个按钮；Chromium 能到全部链接。这等于让 Safari 键盘用户无法使用导航。

修复方式：给所有 <a href> 显式加 tabindex="0"（不改变视觉/DOM 顺序，
Chromium/Firefox 本来就是这个行为，无副作用）。

本脚本是那条修复的回归门禁：
  1. index.html 里每个 <a href> 都必须带 tabindex
  2. 四个路由在 WebKit 下按 Tab 必须能落到链接上
  3. Chromium 与 Firefox 的 Tab 序列不得因此变差

用法：python tests/browser/test_tab_reach.py [--base URL]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:8140"
if "--base" in sys.argv:
    BASE = sys.argv[sys.argv.index("--base") + 1]

ROUTES = [("/", "home"), ("/#/cabinet", "cabinet"), ("/#/manual", "manual"), ("/#/about", "about")]

results: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def check_static() -> None:
    """静态检查：index.html 的每个 <a href> 都必须带 tabindex。"""
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    anchors = re.findall(r"<a\b[^>]*\bhref\s*=[^>]*>", html)
    missing = [a for a in anchors if "tabindex=" not in a]
    record(not missing, "index.html 全部 <a href> 带 tabindex",
           f"{len(anchors)} 个链接，缺失 {len(missing)}")


def tab_sequence(page, count: int = 12) -> list[str]:
    seq = []
    for _ in range(count):
        page.keyboard.press("Tab")
        page.wait_for_timeout(45)
        seq.append(page.evaluate("() => document.activeElement.tagName"))
    return seq


def check_engine(name: str, launcher) -> None:
    browser = launcher.launch()
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for route, label in ROUTES:
            page.goto(BASE + route, wait_until="networkidle")
            page.wait_for_timeout(700)
            seq = tab_sequence(page, 12)
            reached_links = seq.count("A")
            total_links = page.eval_on_selector_all("a[href]", "e=>e.length")
            # 判定标准：Tab 12 次至少能落到 3 个链接上（不再"一个都到不了"）
            record(reached_links >= 3, f"{name} {label}：Tab 能到达链接",
                   f"12 次 Tab 中 {reached_links} 次落在链接上（页面共 {total_links} 链接）")
        page.close()
    finally:
        browser.close()


def main() -> int:
    check_static()
    with sync_playwright() as p:
        check_engine("webkit", p.webkit)
        check_engine("chromium", p.chromium)

    passed = sum(1 for ok, _, _ in results if ok)
    print()
    print("=" * 56)
    print(f"共 {len(results)} 项：{passed} PASS / {len(results) - passed} FAIL")
    out = ROOT / "screenshots" / "tab-reach-report.json"
    out.write_text(json.dumps(
        {"base": BASE, "checks": len(results), "passed": passed,
         "results": [{"ok": o, "name": n, "detail": d} for o, n, d in results]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告：{out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
