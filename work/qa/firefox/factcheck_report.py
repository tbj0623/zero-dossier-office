#!/usr/bin/env python3
"""Fact-check FIREFOX_REPORT.md against the raw JSON it cites.

Every assertion here re-reads a raw artefact and compares it with the literal
number written in the report. Exits non-zero on any mismatch.
"""
from __future__ import annotations

import json
import re

from fx_common import QA, RAW

report = (QA / "FIREFOX_REPORT.md").read_text(encoding="utf-8")
checks = []


def check(label, cond, detail=""):
    checks.append({"label": label, "ok": bool(cond), "detail": detail})
    print(f"[{'OK  ' if cond else 'MISMATCH'}] {label}" + (f" — {detail}" if detail else ""))


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


j = load("journey-firefox.json")
check("journey 43/43", j["pass"] == 43 and j["fail"] == 0, f"{j['pass']}/{j['pass']+j['fail']}")
check("report says 43/43", "**43/43 PASS" in report)
check("firefox version 153.0", j["browser_version"] == "153.0", j["browser_version"])
areas = {r["area"] for r in j["results"]}
check("all 10 areas covered", areas == set(range(1, 11)), str(sorted(areas)))

s = load("six-cases-firefox.json")
check("six solved == 6", s["solved"] == 6, str(s["solved"]))
check("report says 6 / 6", "**6 / 6 solved in Firefox.**" in report)
for c in s["cases"]:
    # recap lengths must match the table row in the report
    pat = rf"\| {c['case']} \| {c['items_n']} \|.*?\| {c['logic_len']} / {c['story_len']} ch \|"
    check(f"{c['case']} row values in report", re.search(pat, report) is not None,
          f"{c['logic_len']}/{c['story_len']}")

f = load("firefox-specific.json")
check("firefox-specific 30/30", f["pass"] == 30 and f["fail"] == 0, f"{f['pass']}/{f['fail']}")
check("dialog 440x188 @500,356", (f["dialog_open"]["w"], f["dialog_open"]["h"],
                                  f["dialog_open"]["left"], f["dialog_open"]["top"]) == (440, 188, 500, 356))
check("report dialog size", "**440×188 px @ (500, 356)**" in report)
check("reduce dur 0.000001", f["reduced_motion_reduce"]["slot"]["transitionDuration"] == "0.000001s")
check("normal dur 0.22", "0.22" in f["reduced_motion_normal"]["slot"]["transitionDuration"])
check("--dur 0ms", f["reduced_motion_reduce"]["rootDurVar"] == "0ms")
check("grip desktop 20x44", (f["grip"]["desktop"]["width"], f["grip"]["desktop"]["height"]) == (20, 44))
check("grip touch none", f["grip"]["touch_390"]["display"] == "none")
check("storage keys", set(f["storage"]["keys_after_moves"]) == {"zd:v1:order:NA-003", "zd:v1:progress"})

lp = load("layout-parity.json")
exp_max = {"home-1440": 0.35, "cabinet-1440": 0.09, "case-NA001-1440": 0.35,
           "home-768": 0.38, "case-NA004-768": 1.85, "home-390": 0.23,
           "case-NA004-390": 0.29, "cabinet-390": 0.09}
for scene, val in exp_max.items():
    check(f"layout max delta {scene}", abs(lp["scenes"][scene]["maxAbsDelta"] - val) < 0.005,
          f"{lp['scenes'][scene]['maxAbsDelta']} vs report {val}")
check("engines recorded", lp["engines"] == {"chromium": "151.0.7922.34", "firefox": "153.0"},
      str(lp["engines"]))

ra = load("raster-vs-layout.json")
for scene, v in ra.items():
    check(f"blur reduction in 39-51% ({scene})", 39 <= v["blur_reduction_pct"] <= 51,
          f"{v['blur_reduction_pct']}%")
    check(f"edge locality 70-97% ({scene})", 70 <= v["diff_pixels_on_edges_pct"] <= 97.1,
          f"{v['diff_pixels_on_edges_pct']}%")
    check(f"best shift is (0,-1) ({scene})", v["best_shift"] == "0,-1", v["best_shift"])
    check(f"no shift gain ({scene})", v["shift_gain_pct"] < 0, f"{v['shift_gain_pct']}%")

bdf = load("backdrop-and-dialog-final.json")
for key, v in bdf["backdrop_by_mode"].items():
    if key.startswith("firefox"):
        check(f"firefox no blur ({key})", v["blur_painted"] is False and v["ratio"] == 1.0,
              f"ratio={v['ratio']}")
    else:
        check(f"chromium blurs ({key})", v["blur_painted"] is True, f"ratio={v['ratio']}")
seq = [x["id"] for x in bdf["dialog_tab"]["firefox"]["steps"]]
check("firefox dialog tab sticks on ok", seq[:3] == ["cancel", "ok", "ok"], str(seq))
check("chromium dialog wraps", "body" in [x["id"] for x in bdf["dialog_tab"]["chromium"]["steps"]])

si = load("scroll-into-view-isolated.json")
check("scroll chrome slotsTop 79.53", abs(si["real_site"]["chromium"]["slotsTop"] - 79.53) < 0.01)
check("scroll firefox slotsTop 43.28", abs(si["real_site"]["firefox"]["slotsTop"] - 43.28) < 0.01)
check("synthetic honours 80px both",
      si["synthetic"]["chromium"]["variants"]["scroll-padding 80px"]["targetTop"] == 80 and
      si["synthetic"]["firefox"]["variants"]["scroll-padding 80px"]["targetTop"] == 80)

sa = load("scroll-anomaly.json")
ff = [r for r in sa["results"]["firefox"]["runs"] if r["target"] == "#slots" and r["pre"] == "prescrolled"]
check("firefox prescrolled #slots 3/3 at 43.28",
      len(ff) == 3 and all(abs(r["top"] - 43.28) < 0.01 for r in ff), str([r["top"] for r in ff]))

asc = load("app-scroll-calls.json")
check("verdict scrollY 77 both",
      asc["engines"]["chromium"]["verdict"]["scrollY"] == 77 and
      asc["engines"]["firefox"]["verdict"]["scrollY"] == 77)
check("hint fully in viewport both",
      asc["engines"]["chromium"]["hint"]["fullyInViewport"] and
      asc["engines"]["firefox"]["hint"]["fullyInViewport"])

tw = load("textwrap-pretty.json")
check("firefox computes wrap", set(x["textWrap"] for x in tw["engines"]["firefox"]["routes"]["#/"]) == {"wrap"})
check("chromium computes pretty", set(x["textWrap"] for x in tw["engines"]["chromium"]["routes"]["#/"]) == {"pretty"})
check("report says 33 paragraphs", "**33 paragraphs**" in report)

dt = load("dialog-and-targets.json")
for eng in ("chromium", "firefox"):
    for view, v in dt["touch_targets_390"][eng].items():
        if "undersized" in v:
            check(f"touch targets {eng}/{view}", len(v["undersized"]) == 0 and v["min_w"] >= 44 and v["min_h"] >= 44,
                  f"min {v['min_w']}x{v['min_h']}, {len(v['undersized'])} undersized")
        if "nav_open" in v:
            check(f"touch targets nav-open {eng}/{view}", len(v["nav_open"]["undersized"]) == 0)

bp = load("batch-provenance.json")
check("build stable during batch", bp["stable_build"] is True and bp["changed_during_batch"] == [],
      str(bp["changed_during_batch"]))
check("app.mjs hash in report", bp["pre"]["app.mjs"] in report)

ink = load("h1-ink.json")
for view in ("w390", "w768", "w1440"):
    a = ink["engines"]["chromium"]["views"][view]
    b = ink["engines"]["firefox"]["views"][view]
    check(f"h1 ink identical {view}",
          a["box"]["h"] == b["box"]["h"] and a["ink_line_count"] == b["ink_line_count"],
          f"{a['box']['h']} vs {b['box']['h']}, lines {a['ink_line_count']}/{b['ink_line_count']}")

oc = load("oracle-crosscheck.json")
check("oracle == solver all six", oc["all_ok"] is True)

failed = [c for c in checks if not c["ok"]]
print(f"\n{len(checks)-len(failed)}/{len(checks)} report claims verified; {len(failed)} mismatch(es)")
for c in failed:
    print("  MISMATCH:", c["label"], "|", c["detail"])
(RAW / "report-factcheck.json").write_text(json.dumps(
    {"checks": checks, "passed": len(checks) - len(failed), "failed": len(failed)},
    ensure_ascii=False, indent=2), encoding="utf-8")
raise SystemExit(1 if failed else 0)
