# -*- coding: utf-8 -*-
"""终审 blind-3: NA-006 E01 after removing the `n+3` formula.

Final E01 body:
  "玻璃影和空白底片的曝光序号相差三，两者之间隔着两次曝光。"

Question: does removing `n+3` reopen any second reading, especially gap=4?
"""
from itertools import permutations


def sols(items, rules):
    out = []
    for p in permutations(items):
        pos = {it: i + 1 for i, it in enumerate(p)}
        if all(r(pos) for r in rules):
            out.append(tuple(p))
    return out


def between(p, a, b, x):
    return min(p[a], p[b]) < p[x] < max(p[a], p[b])


def rep(tag, ss):
    if not ss:
        print(f"  {tag:50s} -> 0 sol   [WALL: self-correcting]")
    elif len(ss) == 1:
        a = " ".join(f"{i+1}:{it}" for i, it in enumerate(ss[0]))
        print(f"  {tag:50s} -> 1 sol   {a}")
    else:
        print(f"  {tag:50s} -> {len(ss)} sol  [under-determined, self-correcting]")


I6 = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]

E2 = lambda p: p["灯塔影"] == p["雨幕影"] + 1
E3 = lambda p: between(p, "钟楼影", "空白底片", "灯塔影")
E4 = lambda p: p["纸船影"] == 2

print("=" * 100)
print("E01 ALONE — constrain strength of each clause (720 permutations)")
print("=" * 100)
clauses = {
  "① 曝光序号相差三  -> |diff| = 3": lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3,
  "② 隔着两次曝光    -> exactly 2 between": lambda p: sum(
        1 for v in p.values() if min(p["玻璃影"], p["空白底片"]) < v < max(p["玻璃影"], p["空白底片"])) == 2,
}
for lbl, r in clauses.items():
    s = sols(I6, [r])
    print(f"  {lbl:46s} -> {len(s):3d} sols")
# do the two clauses define the SAME set?
s1 = set(sols(I6, [clauses["① 曝光序号相差三  -> |diff| = 3"]]))
s2 = set(sols(I6, [clauses["② 隔着两次曝光    -> exactly 2 between"]]))
print(f"\n  Clause ① and ② define identical solution sets? {s1 == s2}")
print("  => the two clauses are logically EQUIVALENT (both mean |diff|=3).")
print()

print("=" * 100)
print("FULL CASE — all defensible readings of final E01")
print("=" * 100)
readings = {
  "A |diff|=3  (literal ①, and ② is equivalent)": lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3,
  "B blank = glass + 3 (directional, one side only)": lambda p: p["空白底片"] == p["玻璃影"] + 3,
  "C glass = blank + 3 (other direction)": lambda p: p["玻璃影"] == p["空白底片"] + 3,
  "D DIRECTIONAL gap=4: blank = glass + 4": lambda p: p["空白底片"] == p["玻璃影"] + 4,
  "E SYMMETRIC gap=4: |diff| = 4": lambda p: abs(p["空白底片"] - p["玻璃影"]) == 4,
  "F gap=4 other direction: glass = blank + 4": lambda p: p["玻璃影"] == p["空白底片"] + 4,
  "G |diff|=2 ('三次' counted as 3 incl. both ends)": lambda p: abs(p["玻璃影"] - p["空白底片"]) == 2,
}
res = {}
for lbl, e1 in readings.items():
    s = sols(I6, [e1, E2, E3, E4])
    res[lbl] = s
    rep(lbl, s)
print()

INTENDED = ("钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片")
print("  Does each reading produce the INTENDED arrangement?")
for lbl, s in res.items():
    print(f"    {'YES' if INTENDED in s else 'NO ':3s}  [{len(s)} sol]  {lbl}")
