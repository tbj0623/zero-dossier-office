#!/usr/bin/env python3
"""证明「站内链接完整性」门禁真的会拦住每种失效引用。

红队第二轮指出原实现只扫 href/src，漏了 srcset、内联 style、内联 script
里的 import()/fetch()。这个脚本对每种向量都植入一次，要求门禁 exit 1，
同时对合法写法要求 exit 0（防止误杀）。

用法：python tests/logic/test_gate_links.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "check_links.py"

BROKEN = [
    ("a href", '<a href="./nope.html">x</a>'),
    ("iframe src", '<iframe src="./nope.html"></iframe>'),
    ("source src", '<source src="./nope.webm">'),
    ("img src", '<img src="./nope.png" alt="">'),
    ("srcset 单条", '<img srcset="./nope.webp 1x" alt="">'),
    ("srcset 多条", '<source srcset="./a.webp 1x, ./b.webp 2x">'),
    ("style 属性 url()", '<p style="background:url(./nope2.png)">x</p>'),
    ("内联 <style> url()", '<style>body{background:url(./nope.png)}</style>'),
    ("内联 <style> @import", '<style>@import "./nope.css";</style>'),
    ("内联 script import()", '<script>import("./nope.mjs")</script>'),
    ("内联 script fetch()", '<script>fetch("./nope.json")</script>'),
]

LEGIT = [
    ("页面链接", '<a href="./index.html">x</a>'),
    ("存在的图片", '<img src="./ok.png" alt="">'),
    ("存在的 srcset", '<img srcset="./ok.png 1x">'),
    ("锚点", '<a href="#/cabinet">x</a>'),
    ("外链", '<a href="https://example.com">x</a>'),
    ("data URI", '<img src="data:image/png;base64,AAAA" alt="">'),
]


def run(dist: Path) -> int:
    r = subprocess.run(
        [sys.executable, str(GATE), str(dist)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return r.returncode


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        dist = Path(tmp) / "dist"
        dist.mkdir()
        (dist / "index.html").write_text("<p>ok</p>", encoding="utf-8")
        (dist / "ok.png").write_bytes(b"x")
        probe = dist / "p.html"

        caught = 0
        for name, html in BROKEN:
            probe.write_text(html, encoding="utf-8")
            if run(dist) == 1:
                caught += 1
            else:
                failures.append(f"漏过：{name}")

        allowed = 0
        for name, html in LEGIT:
            probe.write_text(html, encoding="utf-8")
            if run(dist) == 0:
                allowed += 1
            else:
                failures.append(f"误杀：{name}")

    print(f"拦住坏引用：{caught}/{len(BROKEN)}")
    print(f"放行好引用：{allowed}/{len(LEGIT)}")

    if failures:
        print("\n失败项：")
        for f in failures:
            print("  " + f)
        return 1

    real = ROOT / "dist"
    if real.is_dir() and run(real) != 0:
        print("失败：真实 dist 未通过")
        return 1

    print("PASS 链接门禁对全部已知向量有效，且不误杀合法写法")
    return 0


if __name__ == "__main__":
    sys.exit(main())
