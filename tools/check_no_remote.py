#!/usr/bin/env python3
"""CI 门禁：构建产物中不得出现第三方运行时资源引用。

历史坑：早期实现用 `not any(host in u for host in ALLOW)` 判断，检查的是
「整条 URL 里是否出现过白名单字符串」，于是
`https://github.com.evil.example/pixel.js`、`https://evil.example/?u=github.com`
这类 URL 会被误判成白名单。门禁的承诺（没有第三方请求）因此被弱化。
现在一律用 `urllib.parse.urlsplit` 解析后取 `.hostname`，只做**精确主机名
相等**匹配（唯一的规范化是去掉单个尾点），不做子串匹配、不做后缀匹配、
也不做通配子域名匹配——没有「事前明确批准的子域名」，只有下面两张显式表。

同时区分两类上下文（验收报告明确要求）：
  - 取回类（fetching）：浏览器会真的发请求的引用位置。只允许同源主机。
  - 非取回类（non-fetching）：文档元数据链接（canonical / license / author …），
    页面加载时不会取回，额外允许文档类主机。

检查范围：
  - 取回类位置（会真正发起运行时请求）：
    <script src> / <img src> / <iframe src> / <source src> / <video poster> /
    <embed|object src|data> / srcset / <form action> / CSS url(...) 与 @import /
    JS fetch() / XHR .open() / .src= / import() / sendBeacon() / WebSocket / EventSource
  - 非取回类位置（页面加载时不会取回）：
    <link rel=canonical|alternate|license|author|me|prev|next|help>
    只校验主机归属，允许文档类主机；其余 rel（含 rel 缺失）一律按取回类从严。
  - 通用标签扫描：任意标签的 src / poster / srcset / action / object[data]，
    **无论属性值有没有引号**（`<script src=//evil/x.js>` 这类写法旧正则整个漏过）。

用法：python tools/check_no_remote.py [dist]
退出码 0 = 干净；1 = 发现第三方引用。
"""
from __future__ import annotations

import pathlib
import re
import sys
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# 主机白名单：按「会不会真的发请求」拆成两组
# ---------------------------------------------------------------------------
# 取回类上下文只允许同源主机：这些是本站自己（本地预览 / GitHub Pages 生产域名）。
# 任何第三方主机出现在 <script src>、fetch()、CSS url() 等位置都等于向第三方
# 发请求，破坏「零第三方运行时请求」的承诺，因此这里不允许任何额外主机。
ALLOW_FETCH = frozenset({
    "127.0.0.1",
    "localhost",
    "tbj0623.github.io",
})

# 非取回类上下文额外允许文档类主机：它们只出现在 <link rel="canonical"> /
# rel="license" / rel="author" 之类的元数据链接里，浏览器不会在页面加载时去取，
# 不会产生运行时请求。把它们放进取回类白名单才是真正的漏洞
# （那样 `<script src="https://github.com/x.js">` 也会被放行）。
ALLOW_DOC_ONLY = frozenset({
    "github.com",             # 仓库说明链接
    "docs.github.com",        # Issue / 文档跳转
    "creativecommons.org",    # 许可证
    "www.creativecommons.org",
    "w3.org",                 # 规范 / SVG 命名空间说明
    "www.w3.org",
    "schema.org",             # 结构化数据词汇表
    "itch.io",                # 发行页
    "tbj0623.itch.io",
})

# 非取回上下文 = 同源 ∪ 文档主机
ALLOW_DOC = ALLOW_FETCH | ALLOW_DOC_ONLY

# <link> 的 rel 分类。rel 是空格分隔的 token 列表（大小写不敏感）。
# 取回类 rel：会触发网络请求（样式表、图标、预加载、预连接、manifest…）。
FETCH_RELS = frozenset({
    "stylesheet",
    "icon",
    "shortcut",              # rel="shortcut icon"
    "apple-touch-icon",
    "apple-touch-icon-precomposed",
    "mask-icon",
    "manifest",
    "preload",
    "modulepreload",
    "prefetch",
    "preconnect",
    "dns-prefetch",
    "prerender",
})

# 非取回类 rel：纯文档元数据，允许 ALLOW_DOC。
# 注意：rel 里只要混入任何一个取回类 token（如 rel="alternate stylesheet"），
# 整条链接按取回类从严处理。
DOC_RELS = frozenset({
    "canonical",
    "alternate",
    "license",
    "author",
    "me",
    "prev",
    "next",
    "help",
})

# ---------------------------------------------------------------------------
# 可疑字符
# ---------------------------------------------------------------------------
# 反斜杠：浏览器把 `\` 规范成 `/`，`https://evil.example\@github.com/x.js`
# 的真实主机是 evil.example，但 Python urlsplit 会给出 hostname=github.com。
# 这是真绕过，URL 里出现反斜杠一律判可疑。
_BACKSLASH = "\\"

# C0/C1 控制字符（含 \t \n \r）、零宽字符、双向控制字符、BOM。
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028\u2029\u2060\ufeff]")

# strip 之后仍然残留的空白（含 NBSP、全角空格）：URL 中间不该有空白。
_SPACE = re.compile(r"[\s\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]")

# 主机名只允许 ASCII 小写字母、数字、点和连字符。
# 这一条同时干掉 Unicode 同形字主机（西里尔 `і` 冒充 `i`）、百分号编码主机、
# 带方括号的 IPv6 字面量、以及任何没进白名单表的 IDN。
_HOST = re.compile(r"[a-z0-9.-]+")

# ---------------------------------------------------------------------------
# 检测向量（全部属于取回类上下文）
# ---------------------------------------------------------------------------
# 每条：(名称, 正则)；只捕获 URL 本身
# 红队第二轮指出原实现漏了 srcset / poster / iframe / new Image() / XHR，
# 这些都是能真正发起网络请求的路径，必须一并拦住。
# <link> 因为要解析 rel 才能定上下文，单独在 scan_link_tags() 里处理。
PATTERNS = [
    # --- HTML 元素属性（均为取回类）---
    ("script-src", re.compile(r"""<script[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("img-src", re.compile(r"""<img[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("iframe-src", re.compile(r"""<iframe[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("source-src", re.compile(r"""<source[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)),
    ("video-poster", re.compile(r"""<video[^>]*\bposter\s*=\s*["']([^"']+)["']""", re.I)),
    ("embed-object", re.compile(r"""<(?:embed|object)[^>]*\b(?:src|data)\s*=\s*["']([^"']+)["']""", re.I)),
    ("form-action", re.compile(r"""<form[^>]*\baction\s*=\s*["']([^"']+)["']""", re.I)),
    ("srcset", re.compile(r"""\bsrcset\s*=\s*["']([^"']+)["']""", re.I)),
    # --- CSS（取回类）---
    ("css-url", re.compile(r"""url\(\s*["']?([^)"']+)["']?\s*\)""", re.I)),
    ("css-import", re.compile(r"""@import\s+(?:url\(\s*)?["']?([^)"'\s;]+)""", re.I)),
    # --- JS 网络调用（取回类）---
    ("js-fetch", re.compile(r"""\bfetch\(\s*["']([^"']+)["']""", re.I)),
    ("js-xhr-open", re.compile(r""".open\(\s*["'][A-Za-z]+["']\s*,\s*["']([^"']+)["']""", re.I)),
    ("js-image-src", re.compile(r"""\.src\s*=\s*["']([^"']+)["']""", re.I)),
    ("js-import", re.compile(r"""\bimport\(\s*["']([^"']+)["']""", re.I)),
    ("js-sendbeacon", re.compile(r"""\bsendBeacon\(\s*["']([^"']+)["']""", re.I)),
    ("js-websocket", re.compile(r"""new\s+WebSocket\(\s*["']([^"']+)["']""", re.I)),
    ("js-eventsource", re.compile(r"""new\s+EventSource\(\s*["']([^"']+)["']""", re.I)),
]

# <link> 标签：quote-aware，属性值里出现 `>`（例如 data: URI 图标）也不会截断。
LINK_TAG = re.compile(r"<link\b((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>", re.I)

# 标签内属性：支持双引号 / 单引号 / 无引号；属性名大小写不敏感。
ATTR = re.compile(
    r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>`]+))"""
)

# srcset 一个属性里可能有多条 URL（"a.webp 1x, b.webp 2x"）
SRCSET_SPLIT = re.compile(r"\s*,\s*")

SKIP_EXT = {".map"}

SCAN_EXT = {".html", ".css", ".mjs", ".js", ".json", ".svg"}


def _attr_map(tag_inner: str) -> dict[str, str]:
    """解析一个标签里的属性。重复属性取第一个（与浏览器行为一致）。"""
    attrs: dict[str, str] = {}
    for match in ATTR.finditer(tag_inner):
        name = match.group(1).lower()
        value = match.group(2)
        if value is None:
            value = match.group(3)
        if value is None:
            value = match.group(4)
        attrs.setdefault(name, value or "")
    return attrs


def _link_is_non_fetching(rel: str | None) -> bool:
    """<link rel=...> 是否属于非取回类。

    解析不到 rel / rel 为空 / 出现未知 token → 按取回类从严。
    只有全部 token 都在 DOC_RELS 里、且不含任何取回类 token 时才放行文档主机。
    """
    if rel is None:
        return False
    tokens = {token.lower() for token in rel.split()}
    if not tokens:
        return False
    if tokens & FETCH_RELS:
        return False
    return tokens <= DOC_RELS


def is_remote(url: str, *, fetching: bool = True) -> bool:
    """URL 是否指向不被允许的主机（True = 可疑 / 第三方，应当报错）。

    fetching=True  取回类上下文：只允许 ALLOW_FETCH。
    fetching=False 非取回类上下文：允许 ALLOW_FETCH | ALLOW_DOC_ONLY。

    匹配规则：解析后取 .hostname，仅做精确相等（允许去掉单个尾点）。
    绝不使用子串 / 后缀 / 通配匹配。
    """
    raw = url
    if not raw:
        return False

    # 控制字符 / 换行 / 制表符：浏览器会静默去掉或截断，直接判可疑。
    if _CTRL.search(raw):
        return True

    u = raw.strip()
    if not u:
        return False

    # 内部空白（含 NBSP / 全角空格）
    if _SPACE.search(u):
        return True

    # 反斜杠绕过
    if _BACKSLASH in u:
        return True

    # 协议相对（//host/x）：等于外部主机，且验收要求一律拒绝
    if u.startswith("//"):
        return True

    # data: 不发起网络请求（老实现已允许，保持不放宽也不收紧）
    if u[:5].lower() == "data:":
        return False

    try:
        parts = urlsplit(u)
    except ValueError:
        return True

    scheme = parts.scheme.lower()

    # 无 scheme：相对路径 / 根相对 / 锚点 / 查询串，永远不跨主机
    if not scheme:
        return False

    # 意外 scheme：wss/ws/ftp/blob/filesystem/javascript/mailto/... 一律可疑。
    # blob:/filesystem: 里裹着的 https URL 也不会因为"看起来含白名单"而漏过。
    if scheme not in ("http", "https"):
        return True

    # 缺 `//`（netloc 为空）：浏览器会把 `https:github.com/x.js`
    # 规范成 `https://github.com/x.js`，Python 却给出 hostname=None。
    # 一律拒绝，不做"猜测解析"。
    if not parts.netloc:
        return True

    # userinfo 混淆：`https://github.com@evil.example/x.js`
    # 真实主机是 evil.example；而带 userinfo 的 URL 本身就可疑，直接拒绝。
    if "@" in parts.netloc:
        return True

    # 端口合法性（`https://host:99999/` 会抛 ValueError）
    try:
        parts.port
    except ValueError:
        return True

    host = parts.hostname
    if not host:
        return True

    # 单个尾点规范化：`github.com.` 是合法的 FQDN 写法，去掉尾点后参与匹配；
    # `github.com.evil.example.` 去尾点后仍是 github.com.evil.example，照样拒绝。
    if host.endswith("."):
        host = host[:-1]
    if not host or host.endswith("."):
        return True

    # 主机名只允许 [a-z0-9.-]（.hostname 已转小写）
    if not _HOST.fullmatch(host):
        return True

    allowed = ALLOW_FETCH if fetching else ALLOW_DOC
    return host not in allowed


# 通用标签解析：捕获任意 HTML 标签及其属性串。
#
# 为什么需要它：上面 PATTERNS 里的正则都要求属性值**带引号**
# （`["']...["']`），所以
#     <script src=//evil.example/x.js>
# 这种**无引号属性**会整个漏过 —— 而浏览器完全接受这种写法，照样发请求。
# 这是整改前就存在的真缺口，这里补上：先按标签切块（引号内的 `>` 不截断），
# 再用与 <link> 相同的那套属性解析器取值，无论有没有引号都能拿到。
ANY_TAG = re.compile(r"<([a-zA-Z][-a-zA-Z0-9:]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>", re.I)

# 会真的发起网络请求的属性 → 限定标签集合（None 表示任何标签都算）。
# 刻意不含 href：href 出现在 <a> 上只是导航，不是运行时资源取回；
# <link href> 走 scan_link_tags() 按 rel 单独判定。
FETCH_ATTRS: dict[str, set[str] | None] = {
    "src": None,
    "poster": {"video"},
    "srcset": {"img", "source"},
    "action": {"form"},
    "data": {"object"},
}


def scan_generic_tags(text: str, rel_path: str) -> list[str]:
    """扫描所有标签的取回类属性，覆盖无引号写法。"""
    hits: list[str] = []
    for tag in ANY_TAG.finditer(text):
        tag_name = tag.group(1).lower()
        attrs = _attr_map(tag.group(2))
        for attr, limited_to in FETCH_ATTRS.items():
            if limited_to is not None and tag_name not in limited_to:
                continue
            value = attrs.get(attr)
            if not value:
                continue
            candidates = SRCSET_SPLIT.split(value) if attr == "srcset" else [value]
            for candidate in candidates:
                url = candidate.strip().split()[0] if candidate.strip() else ""
                if not url or not is_remote(url):
                    continue
                hits.append(f"{rel_path}  [{tag_name}-{attr}]  {url}")
    return hits


def scan_link_tags(text: str, rel_path: str) -> list[str]:
    """扫描 <link> 标签，按 rel 判定上下文，返回问题行列表。"""
    hits: list[str] = []
    for tag in LINK_TAG.finditer(text):
        attrs = _attr_map(tag.group(1))
        href = attrs.get("href")
        if not href:
            continue
        fetching = not _link_is_non_fetching(attrs.get("rel"))
        if not is_remote(href, fetching=fetching):
            continue
        context = "link-href(fetch)" if fetching else "link-href(doc)"
        hits.append(f"{rel_path}  [{context}]  {href}")
    return hits


def scan(root: pathlib.Path) -> list[str]:
    bad: list[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        # 通用标签扫描与专用正则会有重叠命中，去重避免同一处报两遍
        if line not in seen:
            seen.add(line)
            bad.append(line)

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() in SKIP_EXT:
            continue
        if path.suffix.lower() not in SCAN_EXT:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel_path = path.relative_to(root).as_posix()

        # <link> 需要解析 rel 才能区分取回 / 非取回
        for hit in scan_link_tags(text, rel_path):
            add(hit)

        # 通用标签扫描：覆盖无引号属性写法
        for hit in scan_generic_tags(text, rel_path):
            add(hit)

        for name, pattern in PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(1)
                # srcset 是候选列表，逐条检查
                candidates = SRCSET_SPLIT.split(raw) if name == "srcset" else [raw]
                for candidate in candidates:
                    url = candidate.strip().split()[0] if candidate.strip() else ""
                    if not url or not is_remote(url):
                        continue
                    add(f"{rel_path}  [{name}]  {url}")
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
