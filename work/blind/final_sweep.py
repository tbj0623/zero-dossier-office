# -*- coding: utf-8 -*-
"""Final adversarial sweep on the revised material (NA-003, NA-005, NA-006)."""
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
        print(f"    {tag:52s} -> 0 sol  (self-correcting)")
    elif len(ss) == 1:
        a = " ".join(f"{i+1}:{it}" for i, it in enumerate(ss[0]))
        print(f"    {tag:52s} -> 1 sol  {a}")
    else:
        print(f"    {tag:52s} -> {len(ss)} sol (under-determined, self-correcting)")


print("=" * 100)
print("NA-006 — exhaustive alternative-reading sweep on the NEW E01")
print("=" * 100)
I6 = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]
E2 = lambda p: p["灯塔影"] == p["雨幕影"] + 1
E3 = lambda p: between(p, "钟楼影", "空白底片", "灯塔影")
E4 = lambda p: p["纸船影"] == 2

variants6 = {
  "A blank=glass+3 (full new text, literal)": lambda p: p["空白底片"] == p["玻璃影"] + 3,
  "B |blank-glass|=3 (ignore formula)":       lambda p: abs(p["空白底片"] - p["玻璃影"]) == 3,
  "C parenthetical alone as diff=2":          lambda p: abs(p["空白底片"] - p["玻璃影"]) == 2,
  "D parenthetical alone as diff=3":          lambda p: abs(p["空白底片"] - p["玻璃影"]) == 3,
  "E old gap-4 reading (now unsupported)":    lambda p: abs(p["空白底片"] - p["玻璃影"]) == 4,
  "F formula reversed glass=blank+3":         lambda p: p["玻璃影"] == p["空白底片"] + 3,
  "G 'n+3' as inclusive (diff 4)":            lambda p: p["空白底片"] == p["玻璃影"] + 4,
}
for lbl, e1 in variants6.items():
    rep(lbl, sols(I6, [e1, E2, E3, E4]))
print()

print("=" * 100)
print("NA-003 — axis sweep on NEW E02")
print("=" * 100)
I3 = ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"]
G1 = lambda p: p["星图"] == p["铜铃"] + 1
G3 = lambda p: p["星图"] != 5
G4 = lambda p: p["纸鹤"] == p["红盒"] + 1
variants3 = {
  "A red<bell (explicit 'bigger=later')": lambda p: p["红盒"] < p["铜铃"],
  "B red>bell (contradicts axis sentence)": lambda p: p["红盒"] > p["铜铃"],
  "C red<bell but E01 undirected": None,  # handled below
}
for lbl, e2 in variants3.items():
    if e2 is None:
        s = sols(I3, [lambda p: abs(p["星图"] - p["铜铃"]) == 1,
                      lambda p: p["红盒"] < p["铜铃"], G3, G4])
        rep(lbl, s)
    else:
        rep(lbl, sols(I3, [G1, e2, G3, G4]))
print()

print("=" * 100)
print("NA-005 — the SILENTLY revised E03 parenthetical")
print("=" * 100)
I5 = ["晨雾邮笺", "港口便条", "红蜡封信", "夜航申请", "空白回邮"]
H1 = lambda p: p["空白回邮"] != 1
H2 = lambda p: between(p, "晨雾邮笺", "空白回邮", "夜航申请")
H4 = lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1
for lbl, e3 in {
  "A |dawn-night|=3 (both clauses agree)": lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 3,
  "B '两个格位之间' read as diff 2":        lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 2,
  "C old gap-4 misreading":                 lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 4,
}.items():
    rep(lbl, sols(I5, [H1, H2, e3, H4]))

# verify NA-005 parenthetical arithmetic on the answer
ans5 = {"晨雾邮笺":1,"港口便条":2,"红蜡封信":3,"夜航申请":4,"空白回邮":5}
a, b = ans5["晨雾邮笺"], ans5["夜航申请"]
print(f"\n    NA-005 answer check: dawn={a}, night={b}, diff={b-a}, "
      f"strictly between={[k for k,v in ans5.items() if a<v<b]} (count={len([k for k,v in ans5.items() if a<v<b])})")
print(f"    -> '相差三格'+'隔着两个格位' consistent: {b-a == 3 and len([k for k,v in ans5.items() if a<v<b]) == 2}")

ans6 = {"钟楼影":1,"纸船影":2,"玻璃影":3,"雨幕影":4,"灯塔影":5,"空白底片":6}
g, bl = ans6["玻璃影"], ans6["空白底片"]
print(f"    NA-006 answer check: glass={g}, blank={bl}, diff={bl-g}, "
      f"between={[k for k,v in ans6.items() if g<v<bl]} (count={len([k for k,v in ans6.items() if g<v<bl])})")
print(f"    -> 'n+3'+'隔着两次曝光' consistent: {bl-g == 3 and len([k for k,v in ans6.items() if g<v<bl]) == 2}")
