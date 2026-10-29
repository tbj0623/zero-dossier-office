#!/usr/bin/env python3
"""CI 门禁：仓库中每个受版本控制的文件都必须落在 ASSETS_LICENSE.md §1 的某一类里。

背景（红队 RT-005）：此前 LICENSE 只覆盖代码、ASSETS_LICENSE 只覆盖部分创作材料，
229/266 个文件处于「两种许可都不覆盖」的空白状态。这会让别人在法律上无法复用。

用法：python tools/check_license_coverage.py
退出码 0 = 全覆盖；1 = 有未覆盖文件。
"""
from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 与 ASSETS_LICENSE.md §1 表格一一对应
MIT_PATTERNS = [
    "engine/*", "site/*.mjs", "site/index.html", "site/engine/*", "site/styles/*", "site/tools/*",
    "tools/*", "tests/*",
    ".github/*", ".github/workflows/*",
    "README.md", "LICENSE", "ASSETS_LICENSE.md", ".gitignore",
    "docs/*", "marketing/*", "ops/*", "ops/owners/*",
    "review/*",
]

CC_PATTERNS = [
    "cases/*", "cases/author/*", "cases/public/*",
    "work/lore/*", "work/blind-src/*",
    "site/assets/*",
]

# 明确例外：第三方 / 文档性 / 非交付物
EXEMPT_PATTERNS = [
    "work/qa/a11y/axe.min.js",   # MPL-2.0，测试专用，不随游戏分发
    "work/blind/*",              # 盲审员的工作脚本与报告（内部审稿材料）
    "work/qa/*",                 # QA 脚本与原始数据
    "work/redteam/*",            # 红队报告与探针
    "docs/screenshots/*",        # 站点真实截图（CC BY-NC-SA，见 ASSETS §1.1 同款）
    "screenshots/*",             # 测试输出
]


def match(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    ).stdout
    return [p for p in out.split("\n") if p.strip()]


def main() -> int:
    files = tracked_files()
    if not files:
        print("git ls-files 没有返回任何文件（是否不在仓库根目录？）", file=sys.stderr)
        return 1

    uncovered: list[str] = []
    counts = {"MIT": 0, "CC": 0, "EXEMPT": 0}

    for path in files:
        if match(path, CC_PATTERNS):
            counts["CC"] += 1
        elif match(path, MIT_PATTERNS):
            counts["MIT"] += 1
        elif match(path, EXEMPT_PATTERNS):
            counts["EXEMPT"] += 1
        else:
            uncovered.append(path)

    print(f"受版本控制文件：{len(files)}")
    print(f"  MIT：{counts['MIT']}   CC BY-NC-SA：{counts['CC']}   例外（第三方/内部）：{counts['EXEMPT']}")

    if uncovered:
        print("\n::error::以下文件不在任何许可覆盖范围内：")
        for p in uncovered[:40]:
            print("  " + p)
        if len(uncovered) > 40:
            print(f"  ……共 {len(uncovered)} 个")
        return 1

    print("OK: 全部文件都有明确的许可归属")
    return 0


if __name__ == "__main__":
    sys.exit(main())
