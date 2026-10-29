#!/usr/bin/env python3
"""构建 itch.io HTML5 发行包。

要求（见 https://itch.io/docs/creators/html5）：
  - ZIP **根目录**必须有 index.html
  - 全部资源用相对路径
  - 解压后文件数 ≤ 1000，总体积远小于 500MB

用法：python tools/build_itch.py
产出：release/itch-html5-release.zip
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
ZIP_PATH = RELEASE / "itch-html5-release.zip"

MAX_FILES = 1000
MAX_TOTAL = 500 * 1024 * 1024
MAX_SINGLE = 200 * 1024 * 1024

# 不进发行包的纯仓库用素材（README 横幅、GitHub 社交图）——游戏里用不到
EXCLUDE = {
    "assets/readme-hero.png",
    "assets/github-social-preview.png",
    "assets/archive-desk-background.webp",   # 当前版本未引用
}


def main() -> int:
    if not (DIST / "index.html").exists():
        print("先运行 node tools/build.mjs 生成 dist/", file=sys.stderr)
        return 1

    RELEASE.mkdir(exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    files = [
        p for p in DIST.rglob("*")
        if p.is_file() and p.relative_to(DIST).as_posix() not in EXCLUDE
    ]
    total = sum(p.stat().st_size for p in files)

    if len(files) > MAX_FILES:
        print(f"文件数 {len(files)} 超过 {MAX_FILES}", file=sys.stderr)
        return 1
    if total > MAX_TOTAL:
        print(f"总体积 {total/1024/1024:.1f}MB 超过限制", file=sys.stderr)
        return 1
    for p in files:
        if p.stat().st_size > MAX_SINGLE:
            print(f"单文件过大：{p}", file=sys.stderr)
            return 1

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(files):
            # 关键：arcname 相对 dist 根，保证 index.html 在 ZIP 根目录
            zf.write(p, p.relative_to(DIST).as_posix())

    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        if "index.html" not in names:
            print("ZIP 根目录缺少 index.html", file=sys.stderr)
            return 1
        bad = [n for n in names if n.startswith("/") or ".." in n.split("/")]
        if bad:
            print(f"存在绝对路径或路径穿越：{bad[:5]}", file=sys.stderr)
            return 1

    size_mb = ZIP_PATH.stat().st_size / 1024 / 1024
    print(f"OK  itch 包：{ZIP_PATH}")
    print(f"    文件 {len(files)} 个 · 解压 {total/1024/1024:.2f} MB · ZIP {size_mb:.2f} MB")
    print(f"    index.html 位于 ZIP 根目录 ✓")

    # 同时登记到发布清单
    manifest = RELEASE / "RELEASE_MANIFEST.json"
    manifest.write_text(json.dumps({
        "itch_zip": ZIP_PATH.name,
        "files": len(files),
        "uncompressed_bytes": total,
        "zip_bytes": ZIP_PATH.stat().st_size,
        "index_at_root": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
