# -*- coding: utf-8 -*-
"""Second pass: axis-direction and counting-convention stress tests."""
from itertools import permutations


def sols(items, rules):
    out = []
    for p in permutations(items):
        pos = {it: i + 1 for i, it in enumerate(p)}
        if all(r(pos) for r in rules):
            out.append(tuple(p))
    return out


def fmt(ss):
    if not ss:
        return "NONE"
    return " || ".join(" ".join(f"{i+1}:{it}" for i, it in enumerate(s)) for s in ss)


def between(p, a, b, x):
    return min(p[a], p[b]) < p[x] < max(p[a], p[b])


print("### NA-003: is the time axis <-> slot axis mapping stated?")
I = ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"]
rules_time_forward = [
    lambda p: p["星图"] == p["铜铃"] + 1,
    lambda p: p["红盒"] < p["铜铃"],          # earlier time = lower slot
    lambda p: p["星图"] != 5,
    lambda p: p["纸鹤"] == p["红盒"] + 1,
]
rules_time_reversed = [
    lambda p: p["星图"] == p["铜铃"] + 1,
    lambda p: p["红盒"] > p["铜铃"],          # earlier time = HIGHER slot
    lambda p: p["星图"] != 5,
    lambda p: p["纸鹤"] == p["红盒"] + 1,
]
print("  forward :", fmt(sols(I, rules_time_forward)))
print("  reversed:", fmt(sols(I, rules_time_reversed)))

print()
print("### NA-006: E01 counting conventions and E02 direction")
I6 = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]
for gap in (2, 3, 4):
    r = [
        lambda p, g=gap: abs(p["玻璃影"] - p["空白底片"]) == g,
        lambda p: p["灯塔影"] == p["雨幕影"] + 1,
        lambda p: between(p, "钟楼影", "空白底片", "灯塔影"),
        lambda p: p["纸船影"] == 2,
    ]
    s = sols(I6, r)
    print(f"  |glass-blank|=={gap}: {len(s)} sol -> {fmt(s)}")

for lbl, r2 in (("rain imm BEFORE light", lambda p: p["灯塔影"] == p["雨幕影"] + 1),
                ("light imm BEFORE rain", lambda p: p["雨幕影"] == p["灯塔影"] + 1)):
    r = [
        lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3,
        r2,
        lambda p: between(p, "钟楼影", "空白底片", "灯塔影"),
        lambda p: p["纸船影"] == 2,
    ]
    print(f"  E02 {lbl}: {len(sols(I6, r))} sol -> {fmt(sols(I6, r))}")

print()
print("### NA-004: counting convention for '差三格'")
I4 = ["铜铃", "值班簿", "玻璃罩", "旧透镜", "海图"]
for gap in (2, 3, 4):
    r = [
        lambda p: abs(p["铜铃"] - p["值班簿"]) == 1,
        lambda p, g=gap: abs(p["铜铃"] - p["旧透镜"]) == g,
        lambda p: p["旧透镜"] == 4,
        lambda p: between(p, "铜铃", "海图", "旧透镜"),
    ]
    s = sols(I4, r)
    print(f"  |bell-lens|=={gap}: {len(s)} sol -> {fmt(s)}")

print()
print("### NA-005: counting convention for '差三格'")
I5 = ["晨雾邮笺", "港口便条", "红蜡封信", "夜航申请", "空白回邮"]
for gap in (2, 3, 4):
    r = [
        lambda p: p["空白回邮"] != 1,
        lambda p: between(p, "晨雾邮笺", "空白回邮", "夜航申请"),
        lambda p, g=gap: abs(p["晨雾邮笺"] - p["夜航申请"]) == g,
        lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1,
    ]
    s = sols(I5, r)
    print(f"  |dawn-night|=={gap}: {len(s)} sol -> {fmt(s)}")

print()
print("### NA-001 / NA-002: does 'E01' direction actually matter?")
I1 = ["红票", "蓝票", "黄票", "绿票"]
for lbl, r1 in (("red imm BEFORE blue", lambda p: p["蓝票"] == p["红票"] + 1),
                ("blue imm BEFORE red", lambda p: p["红票"] == p["蓝票"] + 1)):
    r = [r1, lambda p: p["绿票"] > p["黄票"], lambda p: p["黄票"] != 1]
    print(f"  NA-001 {lbl}: {len(sols(I1, r))} sol -> {fmt(sols(I1, r))}")

I2 = ["铜钥匙", "银徽章", "航海图", "玻璃球"]
for lbl, r1 in (("silver imm LEFT of bronze", lambda p: p["铜钥匙"] == p["银徽章"] + 1),
                ("bronze imm LEFT of silver", lambda p: p["银徽章"] == p["铜钥匙"] + 1)):
    r = [r1, lambda p: p["玻璃球"] == 4, lambda p: p["航海图"] < p["银徽章"]]
    print(f"  NA-002 {lbl}: {len(sols(I2, r))} sol -> {fmt(sols(I2, r))}")
