# -*- coding: utf-8 -*-
"""Re-verification after 2026-10-29 revision (blind-2).
Rules re-encoded by hand from the UPDATED Chinese bodies only.
"""
from itertools import permutations
import json, os

SRC = r"C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\work\blind-src"


def sols(items, rules):
    out = []
    for p in permutations(items):
        pos = {it: i + 1 for i, it in enumerate(p)}
        if all(r(pos) for r in rules):
            out.append(tuple(p))
    return out


def between(p, a, b, x):
    return min(p[a], p[b]) < p[x] < max(p[a], p[b])


def fmt(ss, cap=10):
    if not ss:
        return "0 sol (contradiction)"
    lines = [" ".join(f"{i+1}:{it}" for i, it in enumerate(s)) for s in ss[:cap]]
    extra = f"  (+{len(ss)-cap} more)" if len(ss) > cap else ""
    return f"{len(ss)} sol\n      " + "\n      ".join(lines) + extra


print("=" * 92)
print("NA-006  E01 NEW WORDING — directional test")
print('  body: "玻璃影和空白底片的曝光序号相差三：若玻璃影是第 n 次曝光，'
      '空白底片就是第 n+3 次（两者之间隔着两次曝光）。"')
print("=" * 92)

I6 = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]

# Other three evidences are unchanged.
def others6(e1):
    return [
        e1,
        lambda p: p["灯塔影"] == p["雨幕影"] + 1,                       # E02
        lambda p: between(p, "钟楼影", "空白底片", "灯塔影"),           # E03
        lambda p: p["纸船影"] == 2,                                    # E04
    ]

readings = {
    "R1 DIRECTIONAL  blank = glass + 3  (literal 'n+3')":
        lambda p: p["空白底片"] == p["玻璃影"] + 3,
    "R2 SYMMETRIC    |blank - glass| = 3  (only '相差三')":
        lambda p: abs(p["空白底片"] - p["玻璃影"]) == 3,
    "R3 gap-4 forward  blank = glass + 4  (old literal misreading)":
        lambda p: p["空白底片"] == p["玻璃影"] + 4,
    "R4 gap-4 sym      |blank - glass| = 4":
        lambda p: abs(p["空白底片"] - p["玻璃影"]) == 4,
    "R5 reversed     glass = blank + 3":
        lambda p: p["玻璃影"] == p["空白底片"] + 3,
    "R6 'n+3' but '2 between' ignored as diff 2":
        lambda p: abs(p["空白底片"] - p["玻璃影"]) == 2,
}

results6 = {}
for label, e1 in readings.items():
    s = sols(I6, others6(e1))
    results6[label] = s
    print(f"  {label}\n      {fmt(s)}\n")

# Which readings agree with the intended answer?
INTENDED6 = ("钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片")
print("  Intended arrangement present in each reading?")
for label, s in results6.items():
    print(f"    {'YES' if INTENDED6 in s else 'NO ':3s}  {label}")
print()

print("=" * 92)
print("NA-003  E02 NEW WORDING — axis test")
print('  body: "传送带由第 1 格向第 5 格依次运行，编号越大表示经过传感器越晚。'
      '红盒经过传感器的时间早于铜铃。"')
print("=" * 92)

I3 = ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"]


def others3(e2):
    return [
        lambda p: p["星图"] == p["铜铃"] + 1,   # E01
        e2,                                    # E02
        lambda p: p["星图"] != 5,              # E03
        lambda p: p["纸鹤"] == p["红盒"] + 1,   # E04
    ]

axis_readings = {
    "A1 '编号越大=越晚' -> earlier = SMALLER  (red < bell)":
        lambda p: p["红盒"] < p["铜铃"],
    "A2 REVERSE 'earlier = larger' (red > bell)":
        lambda p: p["红盒"] > p["铜铃"],
    "A3 belt 1->5 but earlier=LARGER (contradicts sentence)":
        lambda p: p["红盒"] > p["铜铃"],
}

for label, e2 in axis_readings.items():
    s = sols(I3, others3(e2))
    print(f"  {label}\n      {fmt(s)}\n")
