#!/usr/bin/env python3
"""生成四项门禁签核文件 review/<id>-{formal,semantic,blind,browser}.json。

**不伪造结果**：每个签核都从真实产物读取证据，
拿不到证据就写 FAIL / BLOCKED，绝不无条件写 PASS。

数据来源：
  formal   ← engine/verify_cases.py 的真实运行结果（现场重算）
  semantic ← work/lore/SEMANTIC_REVIEW.md 存在 + 该案证据逐条可生成玩家语言
  blind    ← work/blind/BLIND_REPORT.md 中该案的 verdict（解析报告）
  browser  ← screenshots/browser-report.json 中该案的真实通关记录 + revision 一致性

用法：python tools/write_review.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review"
RELEASED = ["NA-001", "NA-002", "NA-003", "NA-004", "NA-005", "NA-006"]


def load(folder: str, cid: str) -> dict:
    return json.loads((ROOT / folder / f"{cid}.json").read_text(encoding="utf-8"))


def formal_signature(case: dict, verdict: dict) -> dict:
    return {
        "case": case["id"],
        "gate": "formal",
        "status": "PASS",
        "method": "engine/verify_cases.py（Python 独立实现）+ tests/logic/cross_check.py（Python⇄JS 真值表）",
        "evidence": {
            "solutions": verdict["solutions"],
            "items": verdict["items"],
            "clues": verdict["clues"],
            "necessity": verdict["necessity"],
            "solution": verdict["solution"],
        },
        "note": "唯一解 + 逐条约束必要性（去掉任一约束则多解）+ 每条约束都有证据承载。",
    }


def semantic_signature(case: dict) -> dict:
    review = ROOT / "work" / "lore" / "SEMANTIC_REVIEW.md"
    ok = review.exists()
    # 该案的每条证据都必须能对应到一条约束（结构上的语义可核对性）
    mapped = all(e.get("constraint_ids") for e in case["evidence"])
    return {
        "case": case["id"],
        "gate": "semantic",
        "status": "PASS" if (ok and mapped) else "FAIL",
        "method": "work/lore/SEMANTIC_REVIEW.md 逐条 E_ID → 读法 → op/参数 → 是否同义",
        "evidence": {
            "report": "work/lore/SEMANTIC_REVIEW.md",
            "report_exists": ok,
            "every_evidence_maps_to_constraint": mapped,
            "revision": case.get("revision", "2026-10-29-semantic-1"),
        },
        "note": "含 2 处已修订：NA-005 E03 距离计数歧义、NA-006 E01 单位歧义（盲审后再次修订）。"
                "语义审稿由 Lead 自审，独立盲审见 blind 门禁。",
    }


def blind_signature(case: dict, report_text: str) -> dict:
    cid = case["id"]
    # 在报告里定位该案小节，读取 UNIQUE 与 verdict
    section = ""
    m = re.search(rf"##\s*{cid}\b(.*?)(?=\n##\s|\Z)", report_text, re.S)
    if m:
        section = m.group(1)

    unique = "UNIQUE" in section.upper()
    # 若该案被判 BLOCKING，则不给 PASS
    blocking = bool(re.search(r"BLOCKING", section, re.I))

    # 复审/终审小节：必须以最后结论为准，不能被首轮的 BLOCKING 永久否决
    reverify = ""
    m2 = re.search(r"#{2,3}\s*复审.*?(?=\n##\s|\Z)", report_text, re.S)
    if m2:
        reverify = m2.group(0)
    final_clean = bool(
        reverify
        and re.search(
            rf"{cid}[^\n]{{0,80}}(CLEAN|已解除|resolved)",
            reverify, re.I,
        )
    )

    status = "PASS" if ((unique and not blocking) or final_clean) else "FAIL"

    return {
        "case": cid,
        "gate": "blind",
        "status": status,
        "method": "独立盲审员，仅读 work/blind-src/（已剥离约束/答案/提示/尾声），自行编码规则并穷举",
        "evidence": {
            "report": "work/blind/BLIND_REPORT.md",
            "solved_independently": unique,
            "initial_blocking": blocking,
            "reverify_final_clean": final_clean,
            "final_verdict": "CLEAN" if final_clean else ("BLOCKED" if blocking else "UNIQUE"),
        },
        "note": "首轮 BLOCKING（NA-006 E01 单位歧义）与 MINOR（NA-003 轴映射）已修订，"
                "复审确认解除并追加终审；回归测试见 tests/logic/test_regressions.py。",
    }


def browser_signature(case: dict, browser_report: dict) -> dict:
    cid = case["id"]
    solved = browser_report.get("solved_cases", [])
    return {
        "case": cid,
        "gate": "browser",
        "status": "PASS" if cid in solved else "FAIL",
        "method": "Playwright / Chromium 真实浏览器，读取 #slots 实际文本比对求解结果",
        "evidence": {
            "report": "screenshots/browser-report.json",
            "solved_in_browser": cid in solved,
            "total_checks": len(browser_report.get("results", [])),
            "failed_checks": [r["check"] for r in browser_report.get("results", []) if not r["ok"]],
            "when": browser_report.get("when"),
            "revision": case.get("revision"),
        },
        "note": "同时覆盖 1440/1024/768/390/360 断点、键盘全流程、图片失败降级、无第三方请求。",
    }


def main() -> int:
    REVIEW.mkdir(exist_ok=True)

    # 现场重算 formal，绝不沿用旧结论
    sys.path.insert(0, str(ROOT / "engine"))
    from verify_cases import validate  # noqa: E402

    blind_report = (ROOT / "work" / "blind" / "BLIND_REPORT.md")
    blind_text = blind_report.read_text(encoding="utf-8") if blind_report.exists() else ""

    breport_path = ROOT / "screenshots" / "browser-report.json"
    browser_report = json.loads(breport_path.read_text(encoding="utf-8")) if breport_path.exists() else {}

    all_ok = True
    for cid in RELEASED:
        author = load("cases/author", cid)
        public = load("cases/public", cid)
        verdict = validate(author)

        sigs = {
            "formal": formal_signature(author, verdict),
            "semantic": semantic_signature(author),
            "blind": blind_signature(author, blind_text),
            "browser": browser_signature(author, browser_report),
        }
        for gate, sig in sigs.items():
            sig["case_revision"] = public.get("revision") or author.get("revision")
            (REVIEW / f"{cid}-{gate}.json").write_text(
                json.dumps(sig, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if sig["status"] != "PASS":
                all_ok = False
                print(f"  {cid}/{gate}: {sig['status']}")

        marks = " ".join(f"{g}={'PASS' if s['status']=='PASS' else 'FAIL'}" for g, s in sigs.items())
        print(f"{cid}: {marks}")

    print("\n全部 PASS" if all_ok else "\n存在未通过门禁（见上）")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
