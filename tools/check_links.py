#!/usr/bin/env python3
"""CI 门禁：构建产物中的站内链接与资源引用必须真实可解析。

背景（红队 RT-026）：把 site/tools/ 从发布包排除后，index.html 里指向
./tools/editor.html 与 ./status.html 的链接没有一起删掉，玩家点主导航第二项会 404，
而当时所有测试都是绿的——因为没有任何测试检查"链接能不能打开"。

本脚本扫描 dist/ 下所有 HTML/CSS/JS，提取站内引用并逐个检查文件是否存在。
用法：python tools/check_links.py [dist]
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT_DEFAULT = "dist"

# 站内引用提取（相对路径 / 根相对；排除 external、data:、mailto:、#锚点）
HTML_ATTR = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
CSS_URL = re.compile(r"""url\(\s*["']?([^)"']+)["']?\s*\)""", re.I)
CSS_IMPORT = re.compile(r"""@import\s+["']([^"']+)["']""", re.I)
JS_IMPORT = re.compile(r"""(?:import\s+[^'"]*from\s*|import\s*)["']([^"']+)["']""")
JS_FETCH = re.compile(r"""fetch\(\s*["']([^"']+)["']""")

SKIP_PREFIX = ("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:")
SCAN_EXT = {".html", ".css", ".mjs", ".js"}


def is_internal(url: str) -> bool:
    u = url.strip()
    if not u or u.startswith("#"):
        return False
    return not u.lower().startswith(SKIP_PREFIX)


def resolve(root: pathlib.Path, source: pathlib.Path, url: str) -> pathlib.Path | None:
    """把引用解析为 dist 内的绝对路径；无法判定为站内文件时返回 None。"""
    clean = url.split("#")[0].split("?")[0]
    if not clean:
        return None
    if clean.startswith("/"):
        return (root / clean.lstrip("/")).resolve()
    return (source.parent / clean).resolve()


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT_DEFAULT).resolve()
    if not root.is_dir():
        print(f"目录不存在：{root}", file=sys.stderr)
        return 1

    missing: list[str] = []
    checked = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCAN_EXT:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel_source = path.relative_to(root).as_posix()

        urls: list[str] = []
        if path.suffix.lower() == ".html":
            urls += HTML_ATTR.findall(text)
        elif path.suffix.lower() == ".css":
            urls += CSS_URL.findall(text) + CSS_IMPORT.findall(text)
        else:
            urls += JS_IMPORT.findall(text) + JS_FETCH.findall(text)

        for url in urls:
            if not is_internal(url):
                continue
            target = resolve(root, path, url)
            if target is None:
                continue
            # 只检查目标落在 dist 内的引用
            try:
                target.relative_to(root)
            except ValueError:
                continue
            checked += 1
            if not target.exists():
                missing.append(f"{rel_source}  ->  {url}")

    if missing:
        print("::error::站内引用指向不存在的文件")
        for line in missing[:40]:
            print("  " + line)
        print(f"共 {len(missing)} 处失效引用（已检查 {checked} 条）")
        return 1

    print(f"OK: {checked} 条站内引用全部可解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
