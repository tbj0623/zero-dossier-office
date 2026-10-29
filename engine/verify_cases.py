#!/usr/bin/env python3
"""第零证物局 · 确定性有限约束求解与作者级校验。

不联网、不依赖第三方包。
注意：本程序只证明「结构化规则推导出唯一排列」，**不证明**自然语言读法与规则等价，
也不证明关卡好玩。语义审稿与真实浏览器测试是另外两道独立门禁。
"""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = ROOT / "cases" / "author"

OPS = {
    "at", "not_at", "before", "after",
    "immediately_before", "immediately_after",
    "adjacent", "distance", "between",
}


class CaseError(ValueError):
    """案件数据不合法。"""


def check_rule(order: tuple[str, ...], rule: dict) -> bool:
    op = rule.get("op")
    if op not in OPS:
        raise CaseError(f"未知约束运算符：{op}")
    a = rule.get("a")
    if a not in order:
        raise CaseError(f"未知物件：{a}")
    i = order.index(a)

    if op in {"at", "not_at"}:
        slot = rule.get("slot")
        if type(slot) is not int or not 0 <= slot < len(order):
            raise CaseError("非法的 slot")
        return i == slot if op == "at" else i != slot

    b = rule.get("b")
    if b not in order or b == a:
        raise CaseError(f"非法的第二物件：{b}")
    j = order.index(b)

    if op == "before":
        return i < j
    if op == "after":
        return i > j
    if op == "immediately_before":
        return i + 1 == j
    if op == "immediately_after":
        return i - 1 == j
    if op == "adjacent":
        return abs(i - j) == 1
    if op == "distance":
        gap = rule.get("gap")
        if type(gap) is not int or not 1 <= gap < len(order):
            raise CaseError("非法的 distance")
        return abs(i - j) == gap
    if op == "between":
        c = rule.get("c")
        if c not in order or len({a, b, c}) != 3:
            raise CaseError("非法的第三物件")
        k = order.index(c)
        return min(j, k) < i < max(j, k)
    raise AssertionError("不可达分支")


def solutions(case: dict, rules: list[dict] | None = None) -> list[tuple[str, ...]]:
    items = case["items"]
    if not 3 <= len(items) <= 8:
        raise CaseError("穷举求解器仅支持 3..8 件物品")
    constraints = case["constraints"] if rules is None else rules
    return [p for p in itertools.permutations(items) if all(check_rule(p, c) for c in constraints)]


def validate(case: dict, *, require_necessity: bool = True) -> dict:
    cid = case.get("id", "?")
    required = [
        "id", "slug", "title", "difficulty", "setting", "objective", "slots",
        "items", "constraints", "evidence", "hints", "expected_solution",
        "resolution", "twist",
    ]
    for key in required:
        if key not in case:
            raise CaseError(f"{cid}: 缺少字段 {key}")

    if case.get("mechanic") != "order":
        raise CaseError(f"{cid}: 不支持的 mechanic")
    if not re.fullmatch(r"NA-\d{3}", cid):
        raise CaseError(f"{cid}: 案件编号格式不合法")

    items = case["items"]
    slots = case["slots"]
    clues = case["constraints"]
    evidence = case["evidence"]

    if len(items) != len(slots):
        raise CaseError(f"{cid}: items 与 slots 长度不一致")
    if len(set(items)) != len(items) or len(set(slots)) != len(slots):
        raise CaseError(f"{cid}: items 或 slots 存在重复")

    ids = [c.get("id") for c in clues]
    if not clues or len(set(ids)) != len(ids) or any(not x for x in ids):
        raise CaseError(f"{cid}: 约束 ID 重复或缺失")
    for clue in clues:
        check_rule(tuple(items), clue)  # 触发格式与参照校验

    used: list[str] = []
    ev_ids: set[str] = set()
    for ev in evidence:
        if ev.get("id") in ev_ids:
            raise CaseError(f"{cid}: 证据 ID 重复")
        ev_ids.add(ev.get("id"))
        if not ev.get("body") or not ev.get("constraint_ids"):
            raise CaseError(f"{cid}: 证据 {ev.get('id')} 缺少正文或形式化引用")
        for ref in ev["constraint_ids"]:
            if ref not in ids:
                raise CaseError(f"{cid}: 证据 {ev['id']} 引用了不存在的约束 {ref}")
        used.extend(ev["constraint_ids"])

    if set(used) != set(ids):
        raise CaseError(f"{cid}: 存在没有证据承载的隐藏约束，或有多余引用")

    if not 3 <= len(case["hints"]) <= 4:
        raise CaseError(f"{cid}: 需要 3–4 段分级提示")
    if sorted(case["expected_solution"]) != sorted(items):
        raise CaseError(f"{cid}: expected_solution 不是有效排列")

    sols = solutions(case)
    if len(sols) != 1:
        raise CaseError(f"{cid}: 非唯一解；共 {len(sols)} 组，例如 {sols[:3]}")
    if list(sols[0]) != case["expected_solution"]:
        raise CaseError(f"{cid}: 作者答案与求解器结果不一致")

    necessity = []
    for idx, clue in enumerate(clues):
        remaining = solutions(case, clues[:idx] + clues[idx + 1:])
        necessity.append({
            "id": clue["id"],
            "remaining": len(remaining),
            "essential": len(remaining) > 1,
        })
    if require_necessity:
        redundant = [n["id"] for n in necessity if not n["essential"]]
        if redundant:
            raise CaseError(f"{cid}: 冗余约束 {redundant}；请修改，或显式归类为非必要风味")

    return {
        "id": cid,
        "solutions": len(sols),
        "items": len(items),
        "clues": len(clues),
        "solution": case["expected_solution"],
        "necessity": necessity,
    }


def load_author_cases() -> list[dict]:
    files = sorted(AUTHOR.glob("NA-*.json"))
    if not files:
        raise CaseError(f"在 {AUTHOR} 找不到任何案件")
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def main() -> int:
    try:
        data = load_author_cases()
        ids = [x["id"] for x in data]
        if len(set(ids)) != len(ids):
            raise CaseError("案件编号重复")
        for case in data:
            verdict = validate(case)
            ess = sum(1 for n in verdict["necessity"] if n["essential"])
            print(
                f"PASS {verdict['id']} items {verdict['items']} clues {verdict['clues']} "
                f"unique {verdict['solutions']} essential {ess}/{verdict['clues']} "
                f"answer {' → '.join(verdict['solution'])}"
            )
    except CaseError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(
        f"PASS {len(data)} author cases FORMALLY valid. "
        "NOTE: literary fairness and live UI NOT established by this program."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
