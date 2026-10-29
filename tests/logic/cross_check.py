#!/usr/bin/env python3
"""Python ⇄ JavaScript 规则一致性交叉验证。

做法：Python 读完 6 个作者版案件后，生成一份「穷举真值表」交给 Node 的 solver.mjs
逐条比对。任一条主张不一致即失败退出。这样两套实现无法各自漂移而互相掩护。
"""
from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))

from verify_cases import check_rule, load_author_cases, solutions  # noqa: E402

NODE_SCRIPT = r"""
import { checkRule, countSolutions, SUPPORTED_OPS } from './engine/solver.mjs';
import { readFileSync } from 'node:fs';

const payload = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = { ok: true, errors: [], ops: SUPPORTED_OPS };

for (const c of payload.cases) {
  const seen = countSolutions(c.items, c.constraints);
  if (seen.count !== 1) {
    out.ok = false;
    out.errors.push(`${c.id}: JS 得到 ${seen.count} 个解，期望 1`);
  }
  for (const probe of c.probes) {
    let got;
    try {
      got = checkRule(probe.order, probe.rule);
    } catch (e) {
      got = `THROW:${e.message}`;
    }
    if (String(got) !== String(probe.expect)) {
      out.ok = false;
      out.errors.push(`${c.id}/${probe.rule.id}: JS=${got} PY=${probe.expect} order=${probe.order.join('>')}`);
    }
  }
}
process.stdout.write(JSON.stringify(out));
"""


def main() -> int:
    cases = load_author_cases()

    payload = {"cases": []}
    total_probes = 0

    for case in cases:
        items = case["items"]
        rules = case["constraints"]
        probes = []

        # 1) 作者答案的每条约束真值
        for rule in rules:
            probes.append({
                "rule": rule,
                "order": case["expected_solution"],
                "expect": check_rule(tuple(case["expected_solution"]), rule),
            })

        # 2) 全排列真值表：把每个排列 × 每条规则的结果都交给 JS 复核
        for perm in itertools.permutations(items):
            for rule in rules:
                probes.append({
                    "rule": rule,
                    "order": list(perm),
                    "expect": check_rule(perm, rule),
                })

        # 3) 去掉单条约束后的解数也必须一致
        for idx, rule in enumerate(rules):
            rest = rules[:idx] + rules[idx + 1:]
            remaining = len(solutions(case, rest))
            probes.append({
                "rule": rule,
                "order": case["expected_solution"],
                "expect": check_rule(tuple(case["expected_solution"]), rule),
                "remaining": remaining,
            })

        total_probes += len(probes)
        payload["cases"].append({"id": case["id"], "items": items, "constraints": rules, "probes": probes})

    tmp = ROOT / ".parity-payload.json"
    script = ROOT / ".parity-node.mjs"
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    script.write_text(NODE_SCRIPT, encoding="utf-8")

    try:
        proc = subprocess.run(
            ["node", str(script), str(tmp)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
    finally:
        tmp.unlink(missing_ok=True)
        script.unlink(missing_ok=True)

    if proc.returncode != 0:
        print("FAIL Node 执行失败：", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 1

    result = json.loads(proc.stdout)
    if not result["ok"]:
        print("FAIL 一致性检查未通过：", file=sys.stderr)
        for err in result["errors"][:20]:
            print("  " + err, file=sys.stderr)
        return 1

    expected_ops = {
        "at", "not_at", "before", "after",
        "immediately_before", "immediately_after",
        "adjacent", "distance", "between",
    }
    if set(result["ops"]) != expected_ops:
        print(f"FAIL 运算符集合不一致：JS={result['ops']}", file=sys.stderr)
        return 1

    print(f"PASS Python/JS 规则一致：{len(cases)} 案 · {total_probes} 条真值探针全部吻合")
    print(f"PASS 双方支持的运算符集合相同：{len(expected_ops)} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
