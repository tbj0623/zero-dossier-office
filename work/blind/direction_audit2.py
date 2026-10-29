# -*- coding: utf-8 -*-
"""Corrected direction audit: flip exactly ONE directional evidence, keep ALL
other rules of that case intact, and report what the solver would experience."""
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
        return "0 sol -> player hits a wall (self-correcting)"
    if len(ss) == 1:
        return ("1 sol -> player gets a CONFIDENT WRONG ANSWER: "
                + " ".join(f"{i+1}:{it}" for i, it in enumerate(ss[0])))
    return f"{len(ss)} sol -> player sees under-determined (self-correcting)"


CASES = {
 "NA-001": (["红票", "蓝票", "黄票", "绿票"], [
   ("E01", lambda p: p["蓝票"] == p["红票"] + 1, lambda p: p["红票"] == p["蓝票"] + 1),
   ("E02", lambda p: p["绿票"] > p["黄票"],       lambda p: p["绿票"] < p["黄票"]),
   ("E03", lambda p: p["黄票"] != 1,             lambda p: p["黄票"] == 1),
 ]),
 "NA-002": (["铜钥匙", "银徽章", "航海图", "玻璃球"], [
   ("E01", lambda p: p["铜钥匙"] == p["银徽章"] + 1, lambda p: p["银徽章"] == p["铜钥匙"] + 1),
   ("E02", lambda p: p["玻璃球"] == 4,             lambda p: p["玻璃球"] != 4),
   ("E03", lambda p: p["航海图"] < p["银徽章"],     lambda p: p["航海图"] > p["银徽章"]),
 ]),
 "NA-003": (["红盒", "纸鹤", "铜铃", "星图", "蓝灯"], [
   ("E01", lambda p: p["星图"] == p["铜铃"] + 1, lambda p: p["铜铃"] == p["星图"] + 1),
   ("E02", lambda p: p["红盒"] < p["铜铃"],       lambda p: p["红盒"] > p["铜铃"]),
   ("E03", lambda p: p["星图"] != 5,             lambda p: p["星图"] == 5),
   ("E04", lambda p: p["纸鹤"] == p["红盒"] + 1, lambda p: p["红盒"] == p["纸鹤"] + 1),
 ]),
 "NA-004": (["铜铃", "值班簿", "玻璃罩", "旧透镜", "海图"], [
   ("E01", lambda p: abs(p["铜铃"] - p["值班簿"]) == 1,
           lambda p: p["铜铃"] == p["值班簿"] + 1),
   ("E02", lambda p: abs(p["铜铃"] - p["旧透镜"]) == 3,
           lambda p: abs(p["铜铃"] - p["旧透镜"]) == 4),
   ("E03", lambda p: p["旧透镜"] == 4, lambda p: p["旧透镜"] == 2),
   ("E04", lambda p: between(p, "铜铃", "海图", "旧透镜"),
           lambda p: abs(p["旧透镜"] - p["铜铃"]) == abs(p["旧透镜"] - p["海图"])),
 ]),
 "NA-005": (["晨雾邮笺", "港口便条", "红蜡封信", "夜航申请", "空白回邮"], [
   ("E01", lambda p: p["空白回邮"] != 1, lambda p: p["空白回邮"] == 1),
   ("E02", lambda p: between(p, "晨雾邮笺", "空白回邮", "夜航申请"),
           lambda p: abs(p["夜航申请"] - p["晨雾邮笺"]) == abs(p["夜航申请"] - p["空白回邮"])),
   ("E03", lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 3,
           lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 4),
   ("E04", lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1,
           lambda p: p["红蜡封信"] == p["夜航申请"] + 1),
 ]),
 "NA-006": (["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"], [
   ("E01", lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3,
           lambda p: abs(p["玻璃影"] - p["空白底片"]) == 4),
   ("E02", lambda p: p["灯塔影"] == p["雨幕影"] + 1,
           lambda p: p["雨幕影"] == p["灯塔影"] + 1),
   ("E03", lambda p: between(p, "钟楼影", "空白底片", "灯塔影"),
           lambda p: abs(p["灯塔影"] - p["钟楼影"]) == abs(p["灯塔影"] - p["空白底片"])),
   ("E04", lambda p: p["纸船影"] == 2, lambda p: p["纸船影"] == 5),
 ]),
}

for name, (items, ev) in CASES.items():
    print("=" * 88)
    base = sols(items, [r for _, r, _ in ev])
    print(f"{name}  AS WRITTEN -> {len(base)} solution(s)")
    for eid, rok, rbad in ev:
        idx = [e[0] for e in ev].index(eid)
        others = [r for j, (_, r, _) in enumerate(ev) if j != idx]
        ok = sols(items, others + [rok])
        bad = sols(items, others + [rbad])
        tag = "SAME" if set(ok) == set(bad) else "DIFFERENT"
        print(f"   {eid}: written={len(ok)}  misread={len(bad)}  [{tag}]")
        if tag == "DIFFERENT":
            print(f"        misread outcome: {fmt(bad)}")
    print()
