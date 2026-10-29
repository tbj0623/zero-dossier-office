#!/usr/bin/env python3
"""打乱发布版与盲审版中 items 数组的顺序，避免「数组顺序 == 答案顺序」。

作者版 cases/author/ 保留 items 原顺序（便于人工核对），但 **发布版与盲审版一律打乱**，
且打乱结果确定（同一 seed 可复现），并与 expected_solution 必然不同。

用法：python tools/scramble_items.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = ROOT / "cases" / "author"
PUBLIC = ROOT / "cases" / "public"
BLIND = ROOT / "work" / "blind-src"


def seeded_shuffle(items: list[str], seed: str, forbid: list[str]) -> list[str]:
    """确定性 Fisher-Yates，seed 由案件 ID 派生；结果不允许等于 forbid。"""
    out = list(items)
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    state = int.from_bytes(h[:8], "big")

    def nxt(n: int) -> int:
        nonlocal state
        # xorshift64*
        state ^= (state >> 12) & 0xFFFFFFFFFFFFFFFF
        state ^= (state << 25) & 0xFFFFFFFFFFFFFFFF
        state ^= (state >> 27) & 0xFFFFFFFFFFFFFFFF
        state &= 0xFFFFFFFFFFFFFFFF
        return ((state * 0x2545F4914F6CDD1D) & 0xFFFFFFFFFFFFFFFF) % n

    for attempt in range(50):
        out = list(items)
        for i in range(len(out) - 1, 0, -1):
            j = nxt(i + 1)
            out[i], out[j] = out[j], out[i]
        if out != forbid:
            return out
        # 极小概率撞上，换一个种子再来
        state ^= (attempt + 1) * 0x9E3779B97F4A7C15
    return out


def main() -> int:
    changed = 0
    for src in sorted(AUTHOR.glob("NA-*.json")):
        cid = src.stem
        author = json.loads(src.read_text(encoding="utf-8"))
        solution = author["expected_solution"]
        canon = author["items"]

        scrambled = seeded_shuffle(canon, f"zd-items-{cid}", forbid=solution)

        for folder in (PUBLIC, BLIND):
            p = folder / f"{cid}.json"
            if not p.exists():
                print(f"跳过（不存在）：{p}")
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            before = d["items"]
            d["items"] = list(scrambled)
            if before != scrambled:
                changed += 1
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        flag = "LEAK" if canon == solution else "ok  "
        print(f"{flag} {cid}: items==solution? {canon == solution} → 发布版打乱为 {scrambled}")

    print(f"\n完成：{changed} 个文件被重新排序。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
