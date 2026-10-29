# -*- coding: utf-8 -*-
"""Direction-flip audit: for each directional evidence, reverse it and see whether
the case still yields exactly one (wrong) answer, or collapses to 0 / many."""
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


def fmt(ss):
    if not ss:
        return "0 sol (self-correcting: contradiction)"
    if len(ss) == 1:
        return "1 sol (DANGEROUS: wrong-but-unique) -> " + " ".join(
            f"{i+1}:{it}" for i, it in enumerate(ss[0]))
    return f"{len(ss)} sol (self-correcting: ambiguous)"


TESTS = [
    ("NA-001", ["红票", "蓝票", "黄票", "绿票"], [
        ("E01", "红 immediately before 蓝", lambda p: p["蓝票"] == p["红票"] + 1,
                 "REVERSED: 蓝 immediately before 红", lambda p: p["红票"] == p["蓝票"] + 1),
    ], [
        lambda p: p["绿票"] > p["黄票"], lambda p: p["黄票"] != 1]),
    ("NA-002", ["铜钥匙", "银徽章", "航海图", "玻璃球"], [
        ("E01", "银 immediately LEFT of 铜", lambda p: p["铜钥匙"] == p["银徽章"] + 1,
                 "REVERSED: 铜 immediately LEFT of 银", lambda p: p["银徽章"] == p["铜钥匙"] + 1),
        ("E03", "航海图 strictly LEFT of 银", lambda p: p["航海图"] < p["银徽章"],
                 "REVERSED: 银 strictly LEFT of 航海图", lambda p: p["银徽章"] < p["航海图"]),
    ], [lambda p: p["玻璃球"] == 4]),
    ("NA-003", ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"], [
        ("E01", "铜 immediately before 星", lambda p: p["星图"] == p["铜铃"] + 1,
                 "REVERSED: 星 immediately before 铜", lambda p: p["铜铃"] == p["星图"] + 1),
        ("E04", "纸 immediately after 红", lambda p: p["纸鹤"] == p["红盒"] + 1,
                 "REVERSED: 纸 immediately before 红", lambda p: p["红盒"] == p["纸鹤"] + 1),
    ], [lambda p: p["红盒"] < p["铜铃"], lambda p: p["星图"] != 5]),
    ("NA-006", ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"], [
        ("E02", "雨幕 immediately before 灯塔", lambda p: p["灯塔影"] == p["雨幕影"] + 1,
                 "REVERSED: 灯塔 immediately before 雨幕", lambda p: p["雨幕影"] == p["灯塔影"] + 1),
    ], [lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3,
        lambda p: between(p, "钟楼影", "空白底片", "灯塔影"),
        lambda p: p["纸船影"] == 2]),
]

for name, items, dirs, others in TESTS:
    print("=" * 84)
    print(name)
    base_rules = [o for o in others]
    for did, lbl_ok, r_ok, lbl_bad, r_bad in dirs:
        idx = len(base_rules)
        ok = sols(items, base_rules + [r_ok])
        bad = sols(items, base_rules + [r_bad])
        print(f"  {did} AS WRITTEN  {lbl_ok:38s}: {fmt(ok)}")
        print(f"  {did} IF REVERSED  {lbl_bad:38s}: {fmt(bad)}")
    print()
