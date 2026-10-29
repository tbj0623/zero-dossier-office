#!/usr/bin/env python3
"""CI 门禁：案件封面图不得按答案顺序排列物件。

背景（叙事审稿 C-04）：evidence-case-001.webp 与 evidence-case-003.webp 曾把物件
**按唯一解顺序**画出来，而这两张图在玩家进入案件前的档案柜卡片上就展示了 ——
等于直接送答案。

本脚本无法识别"图里画的是什么"，所以采用可维护的约定：
每张 cover 旁的 `cover-art.json` 记录图中文物从左到右的标签顺序；
若该顺序等于该案唯一解，则判定为泄题。

用法：python tools/check_cover_art.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "site" / "assets" / "cover-art.json"


def main() -> int:
    if not MANIFEST.exists():
        print(f"缺少 {MANIFEST}", file=sys.stderr)
        return 1

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems: list[str] = []

    for entry in data.get("covers", []):
        case_id = entry["case"]
        labels = entry.get("left_to_right", [])
        author = ROOT / "cases" / "author" / f"{case_id}.json"
        if not author.exists():
            problems.append(f"{case_id}: 找不到作者版案件")
            continue
        case = json.loads(author.read_text(encoding="utf-8"))
        solution = case["expected_solution"]

        if not labels:
            # 明确标注为"不含可辨认物件"的封面（例如空抽屉），合法
            if entry.get("contains_no_objects"):
                continue
            problems.append(f"{case_id}: 未记录封面物件顺序，也未声明 contains_no_objects")
            continue

        if labels == solution:
            problems.append(
                f"{case_id}: 封面物件顺序 == 答案顺序 {solution} —— 直接泄题"
            )
        elif sorted(labels) != sorted(solution):
            problems.append(
                f"{case_id}: 封面物件 {labels} 与案件物件 {solution} 不是同一集合"
            )

    if problems:
        print("::error::封面图泄题检查未通过")
        for p in problems:
            print("  " + p)
        return 1

    print(f"OK: {len(data.get('covers', []))} 张封面的物件顺序均不等于答案顺序")
    return 0


if __name__ == "__main__":
    sys.exit(main())
