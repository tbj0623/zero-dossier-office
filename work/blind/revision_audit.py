# -*- coding: utf-8 -*-
"""Post-revision: necessity + difficulty impact of the new E01 wording."""
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


print("=" * 90)
print("NA-006 E01 NEW WORDING — internal consistency audit")
print("=" * 90)
text = "玻璃影和空白底片的曝光序号相差三：若玻璃影是第 n 次曝光，空白底片就是第 n+3 次（两者之间隔着两次曝光）。"
print("  " + text)
print()
print("  Claim 1: '曝光序号相差三'          -> |diff| = 3")
print("  Claim 2: '玻璃=n => 空白=n+3'      -> blank - glass = 3 (directional)")
print("  Claim 3: '之间隔着两次曝光'         -> items strictly between = 2 -> |diff| = 3")
print()
# Verify claim 3 arithmetic against the intended answer
p = {"钟楼影":1,"纸船影":2,"玻璃影":3,"雨幕影":4,"灯塔影":5,"空白底片":6}
g, b = p["玻璃影"], p["空白底片"]
inb = [k for k,v in p.items() if g < v < b]
print(f"  Intended answer: glass={g}, blank={b}")
print(f"    diff = {b-g}  -> agrees with '相差三' and 'n+3': {b-g == 3}")
print(f"    strictly between them = {len(inb)} item(s) {inb} -> agrees with '隔着两次': {len(inb) == 2}")
print("  => all three clauses mutually consistent. No internal contradiction.")
print()

print("  Can the gap=4 reading find ANY surviving textual anchor?")
anchors = [
    ("'次' used as distance unit", "REMOVED - now says '曝光序号相差三', unit is 序号/格"),
    ("'相距' spatial/interval word", "REMOVED - '相距' no longer appears"),
    ("'整整' intensifier suggesting wide gap", "REMOVED - no longer present"),
    ("'n+3' formula", "CONTRADICTS gap-4 (formula fixes diff=3)"),
    ("'隔着两次曝光' explicit count", "CONTRADICTS gap-4 (2 between => diff=3)"),
]
for a, b_ in anchors:
    print(f"    - {a:38s}: {b_}")
print("  => gap-4 now requires OVERRIDING the explicit formula. Not a defensible reading.")
print()

print("=" * 90)
print("NA-006 DIFFICULTY IMPACT")
print("=" * 90)
I6 = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]
E1 = lambda p: p["空白底片"] == p["玻璃影"] + 3
E2 = lambda p: p["灯塔影"] == p["雨幕影"] + 1
E3 = lambda p: between(p, "钟楼影", "空白底片", "灯塔影")
E4 = lambda p: p["纸船影"] == 2
subsets = {
    "E01 only": [E1],
    "E01+E02": [E1, E2],
    "E01+E02+E03": [E1, E2, E3],
    "all four (final)": [E1, E2, E3, E4],
    "all but E01": [E2, E3, E4],
    "all but E02": [E1, E3, E4],
    "all but E03": [E1, E2, E4],
    "all but E04": [E1, E2, E3],
}
for lbl, r in subsets.items():
    print(f"  {lbl:20s} -> {len(sols(I6, r)):4d} solution(s)")
print()
print("  (Old wording, diff=3 version, for comparison of leverage:)")
print("  E01 alone under old wording was just '|diff|=3' — same constraint strength.")
print("  The new wording adds EXPLANATION, not new constraint. Deduction load unchanged;")
print("  only the chance of mis-parsing the unit is removed.")

print()
print("=" * 90)
print("NA-003 DIFFICULTY / NECESSITY AFTER AXIS SENTENCE")
print("=" * 90)
I3 = ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"]
F1 = lambda p: p["星图"] == p["铜铃"] + 1
F2 = lambda p: p["红盒"] < p["铜铃"]
F3 = lambda p: p["星图"] != 5
F4 = lambda p: p["纸鹤"] == p["红盒"] + 1
for lbl, r in {
    "E01 only": [F1], "E01+E02": [F1,F2], "E01+E02+E03": [F1,F2,F3],
    "all four (final)": [F1,F2,F3,F4],
    "all but E01": [F2,F3,F4], "all but E02": [F1,F3,F4],
    "all but E03": [F1,F2,F4], "all but E04": [F1,F2,F3],
}.items():
    print(f"  {lbl:20s} -> {len(sols(I3, r)):4d} solution(s)")
