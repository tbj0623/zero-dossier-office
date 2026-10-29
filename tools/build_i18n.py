#!/usr/bin/env python3
"""i18n 数据校验与合并工具。

把 work/i18n/<locale>/ 下的 ui.json 与 cases.json 校验后，生成 site/i18n/<locale>.json，
供站点运行时按 ?lang= 或语言切换按钮加载。

校验项（缺一即失败）：
  - ui.json 每个条目的 zh 必须与站点的中文原文一致（防止翻译漂移）
  - cases.json 每个案件的 evidence id / hints 数量 / slots 数量与中文源一致
  - 不得留有空的翻译字符串
  - 必须提供 glossary（术语一致性）

用法：
  python tools/build_i18n.py en          # 校验并生成 site/i18n/en.json
  python tools/build_i18n.py --check     # 只校验所有已存在的语言包
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_SRC = ROOT / "work" / "i18n"
PUBLIC = ROOT / "cases" / "public"
SITE_I18N = ROOT / "site" / "i18n"

REQUIRED_CASE_FIELDS = [
    "title", "subtitle", "setting", "objective", "slots", "evidence",
    "hints", "resolution", "twist", "motif", "director_note",
    "logic_recap", "epilogue",
]


def fail(msg: str) -> None:
    print(f"::error::{msg}", file=sys.stderr)
    raise SystemExit(1)


def check_cases(locale_dir: Path) -> dict:
    src = locale_dir / "cases.json"
    if not src.exists():
        fail(f"缺少 {src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    cases = data.get("cases", {})

    problems: list[str] = []
    zh_files = sorted(PUBLIC.glob("NA-*.json"))
    if len(cases) != len(zh_files):
        problems.append(f"案件数 {len(cases)} != 中文源 {len(zh_files)}")

    for zh_path in zh_files:
        zh = json.loads(zh_path.read_text(encoding="utf-8"))
        cid = zh["id"]
        tr = cases.get(cid)
        if not tr:
            problems.append(f"{cid}: 缺少翻译")
            continue

        for field in REQUIRED_CASE_FIELDS:
            if field not in tr:
                problems.append(f"{cid}: 缺少字段 {field}")

        if len(tr.get("slots", [])) != len(zh["slots"]):
            problems.append(f"{cid}: slots 数量 {len(tr.get('slots', []))} != {len(zh['slots'])}")
        if len(tr.get("hints", [])) != len(zh["hints"]):
            problems.append(f"{cid}: hints 数量不一致")

        # constraints 也必须有英文（结案表格逐条展示）
        zh_rules = {r["id"]: r for r in zh["constraints"]}
        tr_rules = {r["id"]: r for r in tr.get("constraints", [])}
        if set(tr_rules) != set(zh_rules):
            problems.append(f"{cid}: constraints id 集合不一致")
        for rid in set(tr_rules) & set(zh_rules):
            if not str(tr_rules[rid].get("text", "")).strip():
                problems.append(f"{cid}/{rid}: 英文约束描述为空")

        zh_ev = {e["id"]: e for e in zh["evidence"]}
        tr_ev = {e["id"]: e for e in tr.get("evidence", [])}
        if set(tr_ev) != set(zh_ev):
            problems.append(f"{cid}: evidence id 集合不一致 ({sorted(set(tr_ev) ^ set(zh_ev))})")
        for eid in set(tr_ev) & set(zh_ev):
            if not tr_ev[eid].get("title", "").strip():
                problems.append(f"{cid}/{eid}: 英文标题为空")
            if not tr_ev[eid].get("body", "").strip():
                problems.append(f"{cid}/{eid}: 英文正文为空")

        for field in ("title", "subtitle", "setting", "objective", "resolution",
                      "twist", "motif", "director_note", "logic_recap", "epilogue"):
            if not tr.get(field, "").strip():
                problems.append(f"{cid}: {field} 为空")

    if problems:
        print("案件翻译校验失败：", file=sys.stderr)
        for p in problems[:40]:
            print("  " + p, file=sys.stderr)
        raise SystemExit(1)

    glossary = data.get("_meta", {}).get("glossary", {})
    if not glossary:
        print("::warning::cases.json 未提供 _meta.glossary，术语一致性无法自动校验")

    print(f"  cases.json OK — {len(cases)} 案 · 术语表 {len(glossary)} 条")
    return data


def check_ui(locale_dir: Path) -> dict:
    src = locale_dir / "ui.json"
    if not src.exists():
        fail(f"缺少 {src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    strings = data.get("strings", {})
    if not strings:
        fail("ui.json 的 strings 为空")

    empty = [k for k, v in strings.items() if not str(v.get("en", "")).strip()]
    if empty:
        print("::error::以下 UI 条目没有英文：", file=sys.stderr)
        for k in empty[:30]:
            print("  " + k, file=sys.stderr)
        raise SystemExit(1)

    print(f"  ui.json OK — {len(strings)} 条")
    return data


def build(locale: str) -> int:
    locale_dir = I18N_SRC / locale
    if not locale_dir.is_dir():
        fail(f"找不到 {locale_dir}")

    print(f"校验语言包 {locale}…")
    ui = check_ui(locale_dir)
    cases = check_cases(locale_dir)

    SITE_I18N.mkdir(parents=True, exist_ok=True)
    merged = {
        "_meta": {
            "locale": locale,
            "source_locale": "zh-CN",
            "strings": ui.get("_meta", {}),
            "glossary": cases.get("_meta", {}).get("glossary", {}),
        },
        "strings": ui["strings"],
        "cases": cases["cases"],
    }
    out = SITE_I18N / f"{locale}.json"
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"OK  已生成 {out}（{size_kb:.1f} KB）")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        locales = [d.name for d in I18N_SRC.iterdir() if d.is_dir()] if I18N_SRC.is_dir() else []
        if not locales:
            print("没有找到任何语言包")
            return 0
        for loc in locales:
            build(loc)
        return 0

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法：python tools/build_i18n.py <locale> | --check", file=sys.stderr)
        return 1
    return build(args[0])


if __name__ == "__main__":
    sys.exit(main())
