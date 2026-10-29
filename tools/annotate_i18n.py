#!/usr/bin/env python3
"""把 site/i18n/<locale>.json 的 key 自动标注到 site/index.html 的对应文本节点上。

处理两类节点：
  1. 叶子文本：<p>纯文本</p>（单行）
  2. 多行文本：<p>\n  跨行\n  文本\n</p> —— 先把空白归一化再比对

幂等：已经带 data-i18n 的不会重复标注。
用法：python tools/annotate_i18n.py en
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "site" / "index.html"


def normalize(text: str) -> str:
    """去掉所有空白再比对。

    中文换行会引入空格（"…位置关系，
 再把…" → "…， 再…"），
    而语言包里没有这个空格。中日文没有词间空格，所以直接删掉所有空白
    是安全的，并能同时匹配单行与多行写法。
    """
    return re.sub(r"\s+", "", text)


def main() -> int:
    locale = sys.argv[1] if len(sys.argv) > 1 else "en"
    pack_path = ROOT / "site" / "i18n" / f"{locale}.json"
    if not pack_path.exists():
        print(f"找不到 {pack_path}", file=sys.stderr)
        return 1

    strings = json.loads(pack_path.read_text(encoding="utf-8"))["strings"]
    html = HTML.read_text(encoding="utf-8")

    by_text: dict[str, str] = {}
    for key, v in strings.items():
        zh = normalize(v.get("zh", ""))
        if zh and len(zh) > 1:
            by_text.setdefault(zh, key)

    # 元素体里不含任何子标签（允许跨行、允许空白）
    pattern = re.compile(r"<([a-zA-Z][\w-]*)([^>]*)>((?:(?!<[a-zA-Z/]).)*?)</\1>", re.S)

    applied = 0
    already = len(re.findall(r"data-i18n=", html))

    def repl(m: re.Match) -> str:
        nonlocal applied
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        if "data-i18n=" in attrs or not inner.strip():
            return m.group(0)
        key = by_text.get(normalize(inner))
        if not key:
            return m.group(0)
        applied += 1
        return f'<{tag}{attrs} data-i18n="{key}">{inner}</{tag}>'

    new_html = pattern.sub(repl, html)
    HTML.write_text(new_html, encoding="utf-8")
    total = len(re.findall(r"data-i18n=", new_html))
    print(f"新增 {applied} 处标注（原有 {already} 处，现共 {total} 处）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
