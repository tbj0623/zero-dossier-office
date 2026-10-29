#!/usr/bin/env python3
"""给站内所有 <a href> 补 tabindex="0"，修复 Safari/WebKit 默认跳过链接的键盘可达性。

背景（WebKit QA 实测）：Safari 的"按 Tab 高亮项目"默认为仅表单控件，
普通 <a href> 不在 Tab 序列里。实测首页有 20 个链接，WebKit 按 Tab
只能到 2 个按钮，Chromium 能到全部 20 个 —— 键盘用户在 Safari 上无法到达任何导航。

`tabindex="0"` 把元素显式放进 Tab 序列，且不改变视觉顺序（仍按 DOM 顺序）。
这是 WebKit 官方推荐的做法之一，对 Chromium/Firefox 无副作用（本来就是 0）。

只处理 index.html 里静态写死的 <a>；运行时 via el() 创建的链接在 app.mjs 里单独处理。

用法：python tools/add_tabindex.py [--check]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "site" / "index.html"

# 匹配 <a ...> 但跳过：已带 tabindex、纯锚点跳转(#)、以及 skip-link（它本来就要最先到）
ANCHOR = re.compile(r"<a\b([^>]*?)>")


def main() -> int:
    check_only = "--check" in sys.argv
    html = HTML.read_text(encoding="utf-8")

    added = 0
    already = 0
    skipped = 0

    def repl(m: re.Match) -> str:
        nonlocal added, already, skipped
        attrs = m.group(1)
        if "tabindex=" in attrs:
            already += 1
            return m.group(0)
        if not re.search(r"\bhref\s*=", attrs):
            skipped += 1
            return m.group(0)
        added += 1
        return f"<a{attrs} tabindex=\"0\">"

    new_html = ANCHOR.sub(repl, html)

    total = len(re.findall(r"<a\b[^>]*\btabindex=", new_html))
    print(f"新增 tabindex：{added}（原有 {already}，现共 {total}，跳过 {skipped}）")

    if check_only:
        missing = len(re.findall(r"<a\b(?![^>]*\btabindex)[^>]*\bhref\s*=", new_html))
        if missing:
            print(f"::error::仍有 {missing} 个链接缺少 tabindex", file=sys.stderr)
            return 1
        return 0

    if added:
        HTML.write_text(new_html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
