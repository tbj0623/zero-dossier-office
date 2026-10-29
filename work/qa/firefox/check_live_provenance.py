#!/usr/bin/env python3
"""Prove the LIVE site did not change between the start and the end of this QA run.

Compares sha256 of the assets downloaded at the start (raw/live-*) with the same
assets downloaded now (raw/live-end/*), and reports the deployed BUILD constant.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

BASE = "https://tbj0623.github.io/zero-dossier-office/"
QA = Path(__file__).resolve().parent
RAW = QA / "raw"
END = RAW / "live-end"
END.mkdir(parents=True, exist_ok=True)

FILES = ["index.html", "app.mjs", "styles/app.css", "styles/base.css",
         "styles/tokens.css", "engine/solver.mjs", "cases/NA-001.json", "cases/NA-006.json"]

for f in FILES:
    dest = END / f.replace("/", "_")
    try:
        with urllib.request.urlopen(BASE + f, timeout=60) as r:
            dest.write_bytes(r.read())
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH FAIL {f}: {exc}")

rows = []
for f in FILES:
    a = RAW / f"live-{f.replace('/', '_')}"
    b = END / f.replace("/", "_")
    ha = hashlib.sha256(a.read_bytes()).hexdigest() if a.exists() else None
    hb = hashlib.sha256(b.read_bytes()).hexdigest() if b.exists() else None
    rows.append({"file": f, "sha256_start": ha, "sha256_end": hb,
                 "identical": ha == hb,
                 "bytes_start": a.stat().st_size if a.exists() else None,
                 "bytes_end": b.stat().st_size if b.exists() else None})
    print(("SAME    " if ha == hb else "CHANGED "), f, (ha or "")[:16], "->", (hb or "")[:16])

app = (END / "app.mjs").read_text(encoding="utf-8", errors="replace")
m = re.search(r"const BUILD = '([^']+)'", app)
payload = {"rows": rows, "live_build": m.group(1) if m else None,
           "all_identical": all(r["identical"] for r in rows),
           "local_app_mjs_bytes": (QA.parents[2] / "site" / "app.mjs").stat().st_size}
(RAW / "live-provenance.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("LIVE BUILD =", payload["live_build"])
print("ALL IDENTICAL:", payload["all_identical"])
print("local site/app.mjs bytes (may differ; another agent is editing it):",
      payload["local_app_mjs_bytes"])
print("-> raw/live-provenance.json")
