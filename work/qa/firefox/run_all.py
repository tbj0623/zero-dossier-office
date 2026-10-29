#!/usr/bin/env python3
"""Re-run every Firefox suite as ONE batch against a single, verified live build.

The live site was redeployed mid-run (only the BUILD constant changed). To make
the report defensible, this wrapper:
  1. records sha256 of the deployed app.mjs + index.html + css BEFORE the batch,
  2. runs each suite in its own process, with its own browser,
  3. records sha256 again AFTER the batch,
  4. fails loudly if the deployed bytes changed while we were measuring.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

QA = Path(__file__).resolve().parent
RAW = QA / "raw"
BASE = "https://tbj0623.github.io/zero-dossier-office/"
WATCH = ["app.mjs", "index.html", "styles/app.css", "styles/base.css", "styles/tokens.css"]


def snap(tag: str) -> dict:
    out = {}
    for f in WATCH:
        try:
            with urllib.request.urlopen(BASE + f, timeout=60) as r:
                data = r.read()
            out[f] = hashlib.sha256(data).hexdigest()
            if tag == "pre" and f == "app.mjs":
                (RAW / "batch-app-pre.mjs").write_bytes(data)
        except Exception as exc:  # noqa: BLE001
            out[f] = f"ERROR: {exc}"
    return out


SUITES = [
    ("journey", ["run_journey.py"]),
    ("six-cases", ["run_six_cases.py"]),
    ("firefox-specific", ["run_firefox_specific.py"]),
    ("layout-parity", ["run_layout_parity.py"]),
    ("css-risks", ["run_css_risks_final.py"]),
    ("scroll-isolated", ["probe_scroll_isolated.py"]),
    ("dialog-targets", ["probe_dialog_targets.py"]),
]

pre = snap("pre")
started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
print("PRE deployed hashes:")
for k, v in pre.items():
    print(f"  {k:20s} {v}")

results = []
for name, argv in SUITES:
    t0 = time.time()
    print(f"\n===== running {name} =====", flush=True)
    p = subprocess.run([sys.executable, *argv], cwd=str(QA), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    dur = round(time.time() - t0, 1)
    (RAW / f"log-{name}.txt").write_text(
        f"$ python {' '.join(argv)}\nexit={p.returncode} duration={dur}s\n\n"
        f"--- stdout ---\n{p.stdout}\n--- stderr ---\n{p.stderr}\n", encoding="utf-8")
    tail = [ln for ln in p.stdout.strip().splitlines() if ln.strip()][-3:]
    print(f"  exit={p.returncode} {dur}s | " + " || ".join(tail), flush=True)
    results.append({"suite": name, "exit": p.returncode, "seconds": dur, "tail": tail})

post = snap("post")
changed = [f for f in WATCH if pre.get(f) != post.get(f)]
payload = {"started": started, "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "pre": pre, "post": post, "changed_during_batch": changed,
           "stable_build": not changed, "suites": results}
(RAW / "batch-provenance.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n" + "=" * 60)
print("POST deployed hashes:")
for k, v in post.items():
    print(f"  {k:20s} {v}")
print("CHANGED DURING BATCH:", changed or "none")
print("-> raw/batch-provenance.json")
sys.exit(0 if not changed else 3)
