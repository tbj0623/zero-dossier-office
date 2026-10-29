#!/usr/bin/env python3
"""Cross-check cases/author/*.json -> expected_solution against the independent solver.

No browser involved: this only proves the oracle we will drive the UI with is
self-consistent.
"""
import json

from fx_common import CASE_AUTHOR, RAW, expected_solution, load_author, load_public, solve

rows = []
for i in range(1, 7):
    cid = f"NA-00{i}"
    author = load_author(cid)
    try:
        sol_author = expected_solution(cid)
    except KeyError as e:
        rows.append({"case": cid, "ok": False, "error": str(e),
                     "author_keys": sorted(author.keys())})
        continue
    pub = load_public(cid)
    sol_solver = solve(pub)
    items = pub["items"]
    rows.append({
        "case": cid,
        "ok": sol_author == sol_solver and sorted(sol_author) == sorted(items),
        "author_expected_solution": sol_author,
        "solver_solution": sol_solver,
        "same": sol_author == sol_solver,
        "is_permutation_of_items": sorted(sol_author) == sorted(items),
        "items_n": len(items),
        "constraints_n": len(pub["constraints"]),
        "hints_n": len(pub.get("hints", [])),
        "evidence_n": len(pub.get("evidence", [])),
        "author_has_expected_solution": True,
    })
    print(cid, "OK" if rows[-1]["ok"] else "MISMATCH", sol_author)

payload = {"when": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
           "check": "author.expected_solution == independent solver, and is a permutation of items",
           "rows": rows,
           "all_ok": all(r["ok"] for r in rows)}
(RAW / "oracle-crosscheck.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
