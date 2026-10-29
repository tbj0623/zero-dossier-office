# -*- coding: utf-8 -*-
"""Variant sweep: for each case, replace ONE evidence's operator with a plausible
alternative reading and see whether the solution set changes. Detects wordings
that silently carry the answer.
"""
from itertools import permutations


def sols(items, rules):
    out = []
    for p in permutations(items):
        pos = {it: i + 1 for i, it in enumerate(p)}
        if all(r(pos) for r in rules):
            out.append(tuple(p))
    return out


def fmt(sols):
    if not sols:
        return "NONE (unsolvable under this reading)"
    if len(sols) > 6:
        return f"{len(sols)} solutions"
    return " || ".join(
        " ".join(f"{i+1}:{it}" for i, it in enumerate(s)) for s in sols
    )


def between(pos, a, b, x):
    return min(pos[a], pos[b]) < pos[x] < max(pos[a], pos[b])


CASES = []

# ---------------- NA-001
I = ["红票", "蓝票", "黄票", "绿票"]
base = [
    ("E01 imm dir 红->蓝", lambda p: p["蓝票"] == p["红票"] + 1),
    ("E02 绿>黄", lambda p: p["绿票"] > p["黄票"]),
    ("E03 黄!=1", lambda p: p["黄票"] != 1),
]
CASES.append(("NA-001", I, base, [
    ("E01 as symmetric adjacency", lambda p: abs(p["蓝票"] - p["红票"]) == 1),
    ("E01 as bare order 红<蓝", lambda p: p["红票"] < p["蓝票"]),
    ("E02 as immediate 绿=黄+1", lambda p: p["绿票"] == p["黄票"] + 1),
]))

# ---------------- NA-002
I = ["铜钥匙", "银徽章", "航海图", "玻璃球"]
base = [
    ("E01 银 imm-left 铜", lambda p: p["铜钥匙"] == p["银徽章"] + 1),
    ("E02 玻璃=4", lambda p: p["玻璃球"] == 4),
    ("E03 航海<银", lambda p: p["航海图"] < p["银徽章"]),
]
CASES.append(("NA-002", I, base, [
    ("E01 as symmetric adjacency", lambda p: abs(p["铜钥匙"] - p["银徽章"]) == 1),
    ("E03 as immediate-left 银=航海+1", lambda p: p["银徽章"] == p["航海图"] + 1),
    ("E02 as glass!=4", lambda p: p["玻璃球"] != 4),
]))

# ---------------- NA-003
I = ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"]
base = [
    ("E01 铜 imm-before 星", lambda p: p["星图"] == p["铜铃"] + 1),
    ("E02 红<铜", lambda p: p["红盒"] < p["铜铃"]),
    ("E03 星!=5", lambda p: p["星图"] != 5),
    ("E04 纸 imm-after 红", lambda p: p["纸鹤"] == p["红盒"] + 1),
]
CASES.append(("NA-003", I, base, [
    ("E01 as symmetric adjacency", lambda p: abs(p["星图"] - p["铜铃"]) == 1),
    ("E02 as immediate 铜=红+1", lambda p: p["铜铃"] == p["红盒"] + 1),
    ("E03 as 星=5", lambda p: p["星图"] == 5),
    ("E04 as symmetric adjacency", lambda p: abs(p["纸鹤"] - p["红盒"]) == 1),
]))

# ---------------- NA-004
I = ["铜铃", "值班簿", "玻璃罩", "旧透镜", "海图"]
base = [
    ("E01 |铃-簿|=1", lambda p: abs(p["铜铃"] - p["值班簿"]) == 1),
    ("E02 |铃-镜|=3", lambda p: abs(p["铜铃"] - p["旧透镜"]) == 3),
    ("E03 镜=4", lambda p: p["旧透镜"] == 4),
    ("E04 镜 between 铃/海", lambda p: between(p, "铜铃", "海图", "旧透镜")),
]
CASES.append(("NA-004", I, base, [
    ("E02 as 3 in between (diff 4)", lambda p: abs(p["铜铃"] - p["旧透镜"]) == 4),
    ("E04 as centered (镜 equidistant)", lambda p: abs(p["旧透镜"] - p["铜铃"]) == abs(p["旧透镜"] - p["海图"])),
    ("E01 as directional 铃=簿+1", lambda p: p["铜铃"] == p["值班簿"] + 1),
]))

# ---------------- NA-005
I = ["晨雾邮笺", "港口便条", "红蜡封信", "夜航申请", "空白回邮"]
base = [
    ("E01 空!=1", lambda p: p["空白回邮"] != 1),
    ("E02 夜 between 晨/空", lambda p: between(p, "晨雾邮笺", "空白回邮", "夜航申请")),
    ("E03 |晨-夜|=3", lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 3),
    ("E04 |蜡-夜|=1", lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1),
]
CASES.append(("NA-005", I, base, [
    ("E02 as centered", lambda p: abs(p["夜航申请"] - p["晨雾邮笺"]) == abs(p["夜航申请"] - p["空白回邮"])),
    ("E03 as 3 in between (diff 4)", lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 4),
    ("E04 as directional 蜡=夜+1", lambda p: p["红蜡封信"] == p["夜航申请"] + 1),
]))

# ---------------- NA-006
I = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]
base = [
    ("E01 |玻-空|=3", lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3),
    ("E02 灯 imm-after 雨", lambda p: p["灯塔影"] == p["雨幕影"] + 1),
    ("E03 灯 between 钟/空", lambda p: between(p, "钟楼影", "空白底片", "灯塔影")),
    ("E04 纸=2", lambda p: p["纸船影"] == 2),
]
CASES.append(("NA-006", I, base, [
    ("E01 as 3 in between (diff 4)", lambda p: abs(p["玻璃影"] - p["空白底片"]) == 4),
    ("E02 as symmetric adjacency", lambda p: abs(p["灯塔影"] - p["雨幕影"]) == 1),
    ("E03 as centered", lambda p: abs(p["灯塔影"] - p["钟楼影"]) == abs(p["灯塔影"] - p["空白底片"])),
]))

for name, items, base, variants in CASES:
    print("=" * 78)
    print(name, " PRIMARY:", fmt(sols(items, [r for _, r in base])))
    b = sols(items, [r for _, r in base])
    for label, varrule in variants:
        # swap in the variant rule at the matching index
        idx = int(label[1:3]) - 1
        rules = [r for _, r in base]
        rules[idx] = varrule
        s = sols(items, rules)
        same = "SAME SET" if set(s) == set(b) else "CHANGED"
        print(f"  variant {label:44s} -> {len(s):2d} sol | {same}")
        if set(s) != set(b):
            print(f"      {fmt(s)}")
    print()
