#!/usr/bin/env python3
"""案件导出工具：作者版 → 发布版 / 盲审包。

用法：
  python tools/export_case.py NA-001            # 生成 cases/public/NA-001.json
  python tools/export_case.py NA-001 --blind    # 生成 work/blind-src/NA-001.json
  python tools/export_case.py --all             # 全部案件（两种产物都生成）

白名单机制：只拷贝允许公开的字段，绝不是"删除几个字段"。
这样新增内部字段时不会意外泄漏。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = ROOT / "cases" / "author"
PUBLIC = ROOT / "cases" / "public"
BLIND = ROOT / "work" / "blind-src"

# 发布版允许出现的字段（白名单，不是黑名单）
PUBLIC_FIELDS = [
    "id", "slug", "title", "subtitle", "difficulty", "play_minutes", "chapter",
    "theme", "mechanic", "setting", "objective", "slots", "items", "evidence",
    "constraints", "hints", "resolution", "twist", "motif", "logic_recap", "epilogue",
    "revision",
]

EVIDENCE_PUBLIC_FIELDS = ["id", "title", "type", "body", "constraint_ids", "illustration_hint"]

# 盲审包允许出现的字段（让独立解题者能真正读题、但拿不到规则/答案/提示/结局）
BLIND_FIELDS = [
    "id", "slug", "title", "subtitle", "difficulty", "chapter", "mechanic",
    "setting", "objective", "slots", "items", "evidence",
]
BLIND_EVIDENCE_FIELDS = ["id", "title", "type", "body", "illustration_hint"]

FORBIDDEN_ANYWHERE = {"expected_solution", "editorial_note", "status"}


def pick(obj: dict, fields: list[str]) -> dict:
    return {k: obj[k] for k in fields if k in obj}


def build_public(case: dict) -> dict:
    out = pick(case, PUBLIC_FIELDS)
    out["evidence"] = [
        pick(e, EVIDENCE_PUBLIC_FIELDS) for e in case["evidence"]
    ]
    for field in FORBIDDEN_ANYWHERE:
        out.pop(field, None)
    assert "expected_solution" not in out
    return out


def build_blind(case: dict) -> dict:
    out = pick(case, BLIND_FIELDS)
    out["evidence"] = [pick(e, BLIND_EVIDENCE_FIELDS) for e in case["evidence"]]
    for field in ("constraints", "expected_solution", "hints", "epilogue",
                  "logic_recap", "twist", "resolution", "editorial_note", "status"):
        out.pop(field, None)
    return out


def export_one(case_id: str, blind: bool = False) -> Path:
    src = AUTHOR / f"{case_id}.json"
    if not src.exists():
        raise SystemExit(f"找不到作者版：{src}")
    case = json.loads(src.read_text(encoding="utf-8"))

    if blind:
        BLIND.mkdir(parents=True, exist_ok=True)
        out = BLIND / f"{case_id}.json"
        data = build_blind(case)
    else:
        PUBLIC.mkdir(parents=True, exist_ok=True)
        out = PUBLIC / f"{case_id}.json"
        data = build_public(case)

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id", nargs="?", help="如 NA-001")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--blind", action="store_true")
    args = ap.parse_args()

    ids = ([p.stem for p in sorted(AUTHOR.glob("NA-*.json"))]
           if args.all else [args.case_id] if args.case_id else [])
    if not ids:
        ap.error("请给出案件 ID 或使用 --all")

    for cid in ids:
        if args.all or not args.blind:
            print("导出发布版:", export_one(cid, blind=False))
        if args.all or args.blind:
            print("导出盲审包:", export_one(cid, blind=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
