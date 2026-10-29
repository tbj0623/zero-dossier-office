#!/usr/bin/env python3
"""What changed on the live site between the start and the end of the QA run?"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

QA = Path(__file__).resolve().parent
RAW = QA / "raw"
a = (RAW / "live-app.mjs").read_text(encoding="utf-8", errors="replace").splitlines()
b = (RAW / "live-end" / "app.mjs").read_text(encoding="utf-8", errors="replace").splitlines()
d = list(difflib.unified_diff(a, b, "live-at-start(33f9ae0c)", "live-at-end(b29f5d61)",
                              lineterm="", n=1))
print("diff hunks:", sum(1 for x in d if x.startswith("@@")), " lines:", len(d))
print("\n".join(d[:120]))
# does the new build reference i18n?
txt = "\n".join(b)
print("\nmentions i18n.mjs:", "i18n.mjs" in txt)
print("mentions itemLabel:", "itemLabel" in txt)
print("mentions localizeCase:", "localizeCase" in txt)
