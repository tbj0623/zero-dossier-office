# -*- coding: utf-8 -*-
"""Print exact alternative arrangements cited in the report."""
from itertools import permutations


def sols(items, rules):
    out = []
    for p in permutations(items):
        pos = {it: i + 1 for i, it in enumerate(p)}
        if all(r(pos) for r in rules):
            out.append(tuple(p))
    return out


def pr(tag, ss):
    print(tag)
    for s in ss:
        print("   " + "  ".join(f"{i+1}={it}" for i, it in enumerate(s)))
    print()


# NA-003 with E02 time axis reversed (earlier time = HIGHER slot)
I3 = ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"]
pr("NA-003 if slot1 were the LATEST position (E02 reversed):", sols(I3, [
    lambda p: p["星图"] == p["铜铃"] + 1,
    lambda p: p["红盒"] > p["铜铃"],
    lambda p: p["星图"] != 5,
    lambda p: p["纸鹤"] == p["红盒"] + 1,
]))

# NA-006 under the competing "three exposures in between" reading
I6 = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]
pr("NA-006 if E01 means 'three exposures in between' (|diff|=4):", sols(I6, [
    lambda p: abs(p["玻璃影"] - p["空白底片"]) == 4,
    lambda p: p["灯塔影"] == p["雨幕影"] + 1,
    lambda p: min(p["钟楼影"], p["空白底片"]) < p["灯塔影"] < max(p["钟楼影"], p["空白底片"]),
    lambda p: p["纸船影"] == 2,
]))

# NA-006 E01 diff=2, to show only diff 3 / 4 give uniqueness
pr("NA-006 if E01 means |diff|=2:", sols(I6, [
    lambda p: abs(p["玻璃影"] - p["空白底片"]) == 2,
    lambda p: p["灯塔影"] == p["雨幕影"] + 1,
    lambda p: min(p["钟楼影"], p["空白底片"]) < p["灯塔影"] < max(p["钟楼影"], p["空白底片"]),
    lambda p: p["纸船影"] == 2,
]))
