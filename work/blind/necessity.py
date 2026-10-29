# -*- coding: utf-8 -*-
"""Necessity analysis: drop each evidence in turn, see if uniqueness survives."""
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


def fmt(ss, cap=8):
    if not ss:
        return "NONE"
    head = " || ".join(" ".join(f"{i+1}:{it}" for i, it in enumerate(s)) for s in ss[:cap])
    return head + (f"  (+{len(ss)-cap} more)" if len(ss) > cap else "")


CASES = {
 "NA-001": (["红票","蓝票","黄票","绿票"], {
   "E01 红紧接蓝(imm dir)": lambda p: p["蓝票"] == p["红票"] + 1,
   "E02 绿晚于黄(>)": lambda p: p["绿票"] > p["黄票"],
   "E03 黄!=第1格": lambda p: p["黄票"] != 1,
 }),
 "NA-002": (["铜钥匙","银徽章","航海图","玻璃球"], {
   "E01 银紧挨铜左侧": lambda p: p["铜钥匙"] == p["银徽章"] + 1,
   "E02 玻璃球=第4格": lambda p: p["玻璃球"] == 4,
   "E03 航海图<银徽章": lambda p: p["航海图"] < p["银徽章"],
 }),
 "NA-003": (["红盒","纸鹤","铜铃","星图","蓝灯"], {
   "E01 铜铃紧接星图前": lambda p: p["星图"] == p["铜铃"] + 1,
   "E02 红盒早于铜铃": lambda p: p["红盒"] < p["铜铃"],
   "E03 星图!=第5格": lambda p: p["星图"] != 5,
   "E04 纸鹤紧接红盒后": lambda p: p["纸鹤"] == p["红盒"] + 1,
 }),
 "NA-004": (["铜铃","值班簿","玻璃罩","旧透镜","海图"], {
   "E01 |铃-簿|=1(无向)": lambda p: abs(p["铜铃"] - p["值班簿"]) == 1,
   "E02 |铃-镜|=3": lambda p: abs(p["铜铃"] - p["旧透镜"]) == 3,
   "E03 镜=第4格": lambda p: p["旧透镜"] == 4,
   "E04 镜 strictly between 铃/海": lambda p: between(p, "铜铃", "海图", "旧透镜"),
 }),
 "NA-005": (["晨雾邮笺","港口便条","红蜡封信","夜航申请","空白回邮"], {
   "E01 空白!=第1格": lambda p: p["空白回邮"] != 1,
   "E02 夜航 between 晨/空": lambda p: between(p, "晨雾邮笺", "空白回邮", "夜航申请"),
   "E03 |晨-夜|=3": lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 3,
   "E04 |蜡-夜|=1(无向)": lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1,
 }),
 "NA-006": (["钟楼影","纸船影","玻璃影","雨幕影","灯塔影","空白底片"], {
   "E01 |玻-空|=3": lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3,
   "E02 雨紧接灯前(imm)": lambda p: p["灯塔影"] == p["雨幕影"] + 1,
   "E03 灯 between 钟/空": lambda p: between(p, "钟楼影", "空白底片", "灯塔影"),
   "E04 纸船=第2格": lambda p: p["纸船影"] == 2,
 }),
}

for name, (items, rules) in CASES.items():
    keys = list(rules)
    full = sols(items, [rules[k] for k in keys])
    print("=" * 80)
    print(f"{name}: full = {len(full)} sol")
    for k in keys:
        rest = [rules[x] for x in keys if x != k]
        s = sols(items, rest)
        status = "REDUNDANT (still unique)" if len(s) == 1 else f"LOAD-BEARING ({len(s)} sol without it)"
        print(f"  drop {k:34s} -> {status}")
        if len(s) != 1:
            print(f"        {fmt(s)}")
    print()
