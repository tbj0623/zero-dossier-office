#!/usr/bin/env python3
"""CI 门禁：构建产物中不得出现第三方运行时资源引用。

替代原先依赖 `grep -E` 负向前瞻的实现（GNU grep 不支持 `(?!...)`，
旧写法永远匹配不到任何东西，等于门禁失效）。

只检查"会真正发起运行时请求"的位置：
  - <script src> / <link href> / <img src>
  - CSS url(...) 与 @import
  - JS fetch("...")

用法：python tools/check_no_remote.py [dist]
退出码 0 = 干净；1 = 发现第三方引用。
"""
from __future__ import annotations

import pathlib
import re
import sys

# 允许出现的主机（同源文档链接、许可证文本里的说明性链接）
ALLOW = (
    "127.0.0.1",
    "localhost",
    "github.com",            # README/仓库链接（非运行时请求）
    "creativecommons.org",   # 许可证链接（非运行时请求）
    "w3.org",                # SVG 命名空间（不是网络请求）
    "schema.org",
)

# 每条：(名称, 正则)；只捕获 URL 本身
PATTERNS = [
    ("script-src", re.compile(r"""<script[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("link-href", re.compile(r"""<link[^>]*\bhref\s*=\s*["']([^"']+)["']""", re.I)),
    ("img-src", re.compile(r"""<img[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("css-url", re.compile(r"""url\(\s*["']?([^)"']+)["']?\s*\)""", re.I)),
    ("css-import", re.compile(r"""@import\s+["']([^"']+)["']""", re.I)),
    ("js-fetch", re.compile(r"""\bfetch\(\s*["']([^"']+)["']""", re.I)),
]

SKIP_EXT = {".map"}


def is_remote(url: str) -> bool:
    u = url.strip()
    if u.startswith("//"):          # 协议相对，等于外部
        return True
    if u.startswith("data:"):
        return False
    if not u.lower().startswith(("http://", "https://")):
        return False                # 相对路径，永远允许
    return not any(host in u for host in ALLOW)


def scan(root: pathlib.Path) -> list[str]:
    bad: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() in SKIP_EXT:
            continue
        if path.suffix.lower() not in {".html", ".css", ".mjs", ".js", ".json", ".svg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in PATTERNS:
            for match in pattern.finditer(text):
                url = match.group(1)
                if is_remote(url):
                    rel = path.relative_to(root).as_posix()
                    bad.append(f"{rel}  [{name}]  {url}")
    return bad


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    if not root.is_dir():
        print(f"目录不存在：{root}", file=sys.stderr)
        return 1

    bad = scan(root)
    if bad:
        print("::error::发现第三方运行时资源引用")
        for line in bad[:30]:
            print("  " + line)
        print(f"共 {len(bad)} 处")
        return 1

    print(f"OK: {root} 中无第三方运行时资源引用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
