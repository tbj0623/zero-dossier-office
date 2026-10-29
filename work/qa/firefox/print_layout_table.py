#!/usr/bin/env python3
"""Print the compact layout-delta table used in FIREFOX_REPORT.md."""
import json

from fx_common import RAW

d = json.loads((RAW / "layout-parity.json").read_text(encoding="utf-8"))
print("engines:", d["engines"])
KEYS = ("header", "heroH1", "evidenceCol", "board", "actions", "btnSubmit")
print()
print(f"{'scene':18s} {'maxAbs':>7s} {'worst':14s} {'pixDiff%':>9s}  detail")
for name, s in d["scenes"].items():
    parts = []
    for k in KEYS:
        e = s["elements"].get(k)
        if e and e.get("present"):
            dl = e["delta"]
            parts.append(f"{k}[dx{dl['x']:+.2f} dy{dl['y']:+.2f} dw{dl['w']:+.2f} dh{dl['h']:+.2f}]")
    print(f"{name:18s} {s['maxAbsDelta']:7.2f} {str(s['worstElement']):14s} "
          f"{str(s['image'].get('pixels_diff_gt2_pct')):>9s}  " + " ".join(parts))
print()
# per-element max across all scenes
worst = {}
for name, s in d["scenes"].items():
    for k, e in s["elements"].items():
        if e.get("present"):
            worst[k] = max(worst.get(k, 0), e["maxAbsDelta"])
print("max |delta| per element across all scenes:")
for k, v in sorted(worst.items(), key=lambda kv: -kv[1]):
    print(f"   {k:16s} {v:.2f} px")
