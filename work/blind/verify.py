# -*- coding: utf-8 -*-
"""Final check: verify derived arrangements evidence-by-evidence, and record
enumeration counts. Independent of any project code."""
from itertools import permutations
from math import factorial


def between(p, a, b, x):
    return min(p[a], p[b]) < p[x] < max(p[a], p[b])


CASES = [
    ("NA-001", ["红票", "蓝票", "黄票", "绿票"], [
        ("E01 红 immediately before 蓝", lambda p: p["蓝票"] == p["红票"] + 1),
        ("E02 绿 strictly later than 黄", lambda p: p["绿票"] > p["黄票"]),
        ("E03 黄 is not slot 1 (22:00)", lambda p: p["黄票"] != 1),
    ]),
    ("NA-002", ["铜钥匙", "银徽章", "航海图", "玻璃球"], [
        ("E01 银 immediately LEFT of 铜", lambda p: p["铜钥匙"] == p["银徽章"] + 1),
        ("E02 玻璃球 is slot 4 (rightmost)", lambda p: p["玻璃球"] == 4),
        ("E03 航海图 strictly left of 银", lambda p: p["航海图"] < p["银徽章"]),
    ]),
    ("NA-003", ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"], [
        ("E01 铜铃 immediately before 星图", lambda p: p["星图"] == p["铜铃"] + 1),
        ("E02 红盒 strictly earlier than 铜铃", lambda p: p["红盒"] < p["铜铃"]),
        ("E03 星图 is not slot 5", lambda p: p["星图"] != 5),
        ("E04 纸鹤 immediately after 红盒", lambda p: p["纸鹤"] == p["红盒"] + 1),
    ]),
    ("NA-004", ["铜铃", "值班簿", "玻璃罩", "旧透镜", "海图"], [
        ("E01 |铜铃-值班簿| == 1 (no direction)", lambda p: abs(p["铜铃"] - p["值班簿"]) == 1),
        ("E02 |铜铃-旧透镜| == 3", lambda p: abs(p["铜铃"] - p["旧透镜"]) == 3),
        ("E03 旧透镜 is slot 4 (from bottom)", lambda p: p["旧透镜"] == 4),
        ("E04 旧透镜 strictly between 铜铃 and 海图", lambda p: between(p, "铜铃", "海图", "旧透镜")),
    ]),
    ("NA-005", ["晨雾邮笺", "港口便条", "红蜡封信", "夜航申请", "空白回邮"], [
        ("E01 空白回邮 is not slot 1", lambda p: p["空白回邮"] != 1),
        ("E02 夜航 strictly between 晨雾 and 空白", lambda p: between(p, "晨雾邮笺", "空白回邮", "夜航申请")),
        ("E03 |晨雾-夜航| == 3", lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 3),
        ("E04 |红蜡-夜航| == 1 (no direction)", lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1),
    ]),
    ("NA-006", ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"], [
        ("E01 |玻璃-空白| == 3  (PRIMARY reading)", lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3),
        ("E02 雨幕 immediately before 灯塔", lambda p: p["灯塔影"] == p["雨幕影"] + 1),
        ("E03 灯塔 strictly between 钟楼 and 空白", lambda p: between(p, "钟楼影", "空白底片", "灯塔影")),
        ("E04 纸船 is exposure 2", lambda p: p["纸船影"] == 2),
    ]),
]

for name, items, ev in CASES:
    sols = [p for p in permutations(items)
            if all(r({it: i + 1 for i, it in enumerate(p)}) for _, r in ev)]
    print("=" * 84)
    print(f"{name}  items={len(items)}  permutations={factorial(len(items))}  solutions={len(sols)}")
    for p in sols:
        pos = {it: i + 1 for i, it in enumerate(p)}
        print("  ARRANGEMENT: " + " -> ".join(f"{i+1}.{it}" for i, it in enumerate(p)))
        for label, r in ev:
            print(f"    [{'PASS' if r(pos) else 'FAIL'}] {label}")
    print()
