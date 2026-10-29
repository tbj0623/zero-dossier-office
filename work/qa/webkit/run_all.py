#!/usr/bin/env python3
"""Final consolidated run: every suite, bracketed by build hashes, one report.

Runs each suite in a subprocess so a crash in one cannot silently truncate the
others, and records the served-file hashes before and after so the numbers are
provably tied to a single build.

Writes raw/final-summary.json + raw/provenance.json.
"""
from __future__ import annotations

import json
import subprocess
import sys

from wk_common import QA, RAW, file_provenance, now_iso

SUITES = [
    ("journey", "run_journey.py", "raw/journey-webkit.json"),
    ("six_cases", "run_six_cases.py", "raw/six-cases-webkit.json"),
    ("css_risks", "run_css_risks.py", "raw/css-risks-webkit.json"),
    ("tab_reach", "run_tab_reach.py", "raw/tab-reach-summary.json"),
    ("ax_names", "run_ax_names.py", "raw/ax-names-summary.json"),
]


def main() -> int:
    before = file_provenance()
    out = {"when": now_iso(), "suites": {}, "provenance_before": before}
    rc_all = 0

    for name, script, report in SUITES:
        print(f"\n{'='*70}\n== {name} ({script})\n{'='*70}")
        r = subprocess.run([sys.executable, script], cwd=str(QA),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        # echo the tail so the console shows real progress
        tail = "\n".join((r.stdout or "").splitlines()[-6:])
        print(tail)
        if r.returncode != 0:
            print(f"[suite exit {r.returncode}]")
            if r.stderr:
                print(r.stderr.strip().splitlines()[-6:])
        rc_all |= 1 if r.returncode != 0 else 0
        payload = None
        try:
            payload = json.loads((QA / report).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            payload = {"error": str(exc)[:200]}
        out["suites"][name] = {
            "returncode": r.returncode, "report": report,
            "pass": payload.get("pass"), "fail": payload.get("fail"),
            "total": (payload.get("pass") or 0) + (payload.get("fail") or 0),
            "failures": [x for x in payload.get("results", []) if not x.get("ok")],
        }

    after = file_provenance()
    out["provenance_after"] = after
    changed = [k for k in before if k.startswith("_") is False
               and before.get(k, {}).get("sha256") != after.get(k, {}).get("sha256")]
    out["build_changed_during_run"] = changed
    for name, script, report in SUITES:
        sh = out["suites"][name]
        print(f"  {name:12s} {sh['pass']}/{sh['total']} PASS  (rc={sh['returncode']})")

    print(f"\nbuild changed during run: {changed or 'none'}")
    (RAW / "provenance.json").write_text(json.dumps(
        {"when": out["when"], "before": before, "after": after, "changed": changed},
        ensure_ascii=False, indent=2), encoding="utf-8")
    (RAW / "final-summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    print(f"\nsummary -> {RAW / 'final-summary.json'}")
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
