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
# 红队第二轮指出原实现漏了 srcset / poster / iframe / new Image() / XHR，
# 这些都是能真正发起网络请求的路径，必须一并拦住。
PATTERNS = [
    # --- HTML 元素属性 ---
    ("script-src", re.compile(r"""<script[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("link-href", re.compile(r"""<link[^>]*\bhref\s*=\s*["']([^"']+)["']""", re.I)),
    ("img-src", re.compile(r"""<img[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("iframe-src", re.compile(r"""<iframe[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("source-src", re.compile(r"""<source[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("video-poster", re.compile(r"""<video[^>]*\bposter\s*=\s*["']([^"']+)["']""", re.I)),
    ("embed-object", re.compile(r"""<(?:embed|object)[^>]*\b(?:src|data)\s*=\s*["']([^"']+)["']""", re.I)),
    ("form-action", re.compile(r"""<form[^>]*\baction\s*=\s*["']([^"']+)["']""", re.I)),
    ("srcset", re.compile(r"""\bsrcset\s*=\s*["']([^"']+)["']""", re.I)),
    # --- CSS ---
    ("css-url", re.compile(r"""url\(\s*["']?([^)"']+)["']?\s*\)""", re.I)),
    ("css-import", re.compile(r"""@import\s+(?:url\(\s*)?["']?([^)"'\s;]+)""", re.I)),
    # --- JS 网络调用 ---
    ("js-fetch", re.compile(r"""\bfetch\(\s*["']([^"']+)["']""", re.I)),
    ("js-xhr-open", re.compile(r"""\.open\(\s*["'][A-Za-z]+["']\s*,\s*["']([^"']+)["']""", re.I)),
    ("js-image-src", re.compile(r"""\.src\s*=\s*["']([^"']+)["']""", re.I)),
    ("js-import", re.compile(r"""\bimport\(\s*["']([^"']+)["']""", re.I)),
    ("js-sendbeacon", re.compile(r"""\bsendBeacon\(\s*["']([^"']+)["']""", re.I)),
    ("js-websocket", re.compile(r"""new\s+WebSocket\(\s*["']([^"']+)["']""", re.I)),
    ("js-eventsource", re.compile(r"""new\s+EventSource\(\s*["']([^"']+)["']""", re.I)),
]

# srcset 一个属性里可能有多条 URL（"a.webp 1x, b.webp 2x"）
SRCSET_SPLIT = re.compile(r"\s*,\s*")

SKIP_EXT = {".map"}


def is_remote(url: str) -> bool:
    u = url.strip()
    if u.startswith("//"):          # 协议相对，等于外部
        return True
    if u.startswith("data:"):
        return False
    # wss: 是 WebSocket 的外部协议，必须一并拦；ftp: 等也按外部处理
    if u.lower().startswith(("wss://", "ws://", "ftp://")):
        return True
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
                raw = match.group(1)
                # srcset 是候选列表，逐条检查
                candidates = SRCSET_SPLIT.split(raw) if name == "srcset" else [raw]
                for candidate in candidates:
                    url = candidate.strip().split()[0] if candidate.strip() else ""
                    if not url or not is_remote(url):
                        continue
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
