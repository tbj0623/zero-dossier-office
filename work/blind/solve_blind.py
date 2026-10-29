# -*- coding: utf-8 -*-
"""Blind reviewer's own enumerator. Rules hand-encoded from the Chinese evidence
bodies in work/blind-src/*.json only. No project code imported.

Slot numbering is 1-based, left-to-right / bottom-to-top as stated in each case.
"""
from itertools import permutations


def solutions(items, rules):
    out = []
    for p in permutations(items):
        pos = {it: i + 1 for i, it in enumerate(p)}
        if all(r(pos) for r in rules):
            out.append(p)
    return out


def show(tag, items, sols):
    print(f"--- {tag}: {len(sols)} solution(s)")
    for s in sols:
        print("    " + " | ".join(f"{i+1}:{it}" for i, it in enumerate(s)))
    print()


# ---------------------------------------------------------------- NA-001
# E01 红票的时间紧接着就是蓝票的时间，中间没有其他票
#   -> 红 immediately before 蓝  (pos(蓝) = pos(红)+1)
# E02 绿票的登记晚于黄票 -> pos(绿) > pos(黄)
# E03 22:00(=slot1) 打印的并不是黄票 -> pos(黄) != 1
I1 = ["红票", "蓝票", "黄票", "绿票"]
R1 = [
    lambda p: p["蓝票"] == p["红票"] + 1,
    lambda p: p["绿票"] > p["黄票"],
    lambda p: p["黄票"] != 1,
]
show("NA-001 primary", I1, solutions(I1, R1))

# ---------------------------------------------------------------- NA-002
# E01 银徽章的格子紧挨着铜钥匙左侧，中间没有其它抽屉
#   -> 银 immediately left of 铜  (pos(铜) = pos(银)+1)
# E02 最右侧的第四格抽屉一直装着玻璃球 -> pos(玻璃球) == 4
# E03 航海图的抽屉在银徽章的左边 -> pos(航海图) < pos(银徽章)
I2 = ["铜钥匙", "银徽章", "航海图", "玻璃球"]
R2 = [
    lambda p: p["铜钥匙"] == p["银徽章"] + 1,
    lambda p: p["玻璃球"] == 4,
    lambda p: p["航海图"] < p["银徽章"],
]
show("NA-002 primary", I2, solutions(I2, R2))

# variant: if 紧挨着 read as symmetric adjacent (dropping 左侧) -- NOT my reading
R2v = [
    lambda p: abs(p["铜钥匙"] - p["银徽章"]) == 1,
    lambda p: p["玻璃球"] == 4,
    lambda p: p["航海图"] < p["银徽章"],
]
show("NA-002 variant symmetric E01", I2, solutions(I2, R2v))

# ---------------------------------------------------------------- NA-003
# E01 铜铃所在格位紧接在星图之前，彼此相邻
#   -> 铜铃 immediately before 星图 (pos(星图) = pos(铜铃)+1)
# E02 红盒经过传感器的时间早于铜铃 -> pos(红盒) < pos(铜铃)
# E03 最末的第五格并不是星图 -> pos(星图) != 5
# E04 纸鹤紧接在红盒之后，位于两个相邻格位
#   -> 纸鹤 immediately after 红盒 (pos(纸鹤) = pos(红盒)+1)
I3 = ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"]
R3 = [
    lambda p: p["星图"] == p["铜铃"] + 1,
    lambda p: p["红盒"] < p["铜铃"],
    lambda p: p["星图"] != 5,
    lambda p: p["纸鹤"] == p["红盒"] + 1,
]
show("NA-003 primary", I3, solutions(I3, R3))

R3v = [
    lambda p: abs(p["星图"] - p["铜铃"]) == 1,   # if E01 read as bare adjacency
    lambda p: p["红盒"] < p["铜铃"],
    lambda p: p["星图"] != 5,
    lambda p: p["纸鹤"] == p["红盒"] + 1,
]
show("NA-003 variant symmetric E01", I3, solutions(I3, R3v))

# ---------------------------------------------------------------- NA-004
# shelf counted from bottom up: slot 1 = lowest.
# E01 铜铃和值班簿挨在一起；没有记下谁高谁低 -> |pos(铃)-pos(簿)| == 1
# E02 铜铃与旧透镜的格位编号相差整整三格 -> |pos(铃)-pos(镜)| == 3
# E03 旧透镜属于从下往上数第四格 -> pos(镜) == 4
# E04 旧透镜处在铜铃和海图之间，但不是等距 -> 铃 < 镜 < 海图 or 海图 < 镜 < 铃
I4 = ["铜铃", "值班簿", "玻璃罩", "旧透镜", "海图"]
R4 = [
    lambda p: abs(p["铜铃"] - p["值班簿"]) == 1,
    lambda p: abs(p["铜铃"] - p["旧透镜"]) == 3,
    lambda p: p["旧透镜"] == 4,
    lambda p: min(p["铜铃"], p["海图"]) < p["旧透镜"] < max(p["铜铃"], p["海图"]),
]
show("NA-004 primary (编号差3)", I4, solutions(I4, R4))

R4v = [
    lambda p: abs(p["铜铃"] - p["值班簿"]) == 1,
    lambda p: abs(p["铜铃"] - p["旧透镜"]) == 4,   # "3 slots between" reading
    lambda p: p["旧透镜"] == 4,
    lambda p: min(p["铜铃"], p["海图"]) < p["旧透镜"] < max(p["铜铃"], p["海图"]),
]
show("NA-004 variant gap-of-3-slots (diff 4)", I4, solutions(I4, R4v))

# ---------------------------------------------------------------- NA-005
# E01 空白回邮没有占用第一格 -> pos(空) != 1
# E02 夜航申请的格位在晨雾邮笺与空白回邮之间 -> strictly between
# E03 晨雾邮笺与夜航申请的格位数字相差三格 -> |pos(晨)-pos(夜)| == 3
# E04 红蜡封信和夜航申请相邻，无方向 -> |pos(蜡)-pos(夜)| == 1
I5 = ["晨雾邮笺", "港口便条", "红蜡封信", "夜航申请", "空白回邮"]
R5 = [
    lambda p: p["空白回邮"] != 1,
    lambda p: min(p["晨雾邮笺"], p["空白回邮"]) < p["夜航申请"] < max(p["晨雾邮笺"], p["空白回邮"]),
    lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 3,
    lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1,
]
show("NA-005 primary", I5, solutions(I5, R5))

R5v = [
    lambda p: p["空白回邮"] != 1,
    lambda p: min(p["晨雾邮笺"], p["空白回邮"]) < p["夜航申请"] < max(p["晨雾邮笺"], p["空白回邮"]),
    lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 4,
    lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1,
]
show("NA-005 variant diff 4", I5, solutions(I5, R5v))

# ---------------------------------------------------------------- NA-006
# E01 玻璃影和空白底片的曝光格位相距整整三次
#   primary: |pos(玻)-pos(空)| == 3
# E02 雨幕影的曝光紧接着就是灯塔影 -> pos(灯) == pos(雨)+1
# E03 灯塔影的曝光发生在钟楼影与空白底片之间 -> strictly between
# E04 纸船影的正确格位是第二次曝光 -> pos(纸船) == 2
I6 = ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"]
R6 = [
    lambda p: abs(p["玻璃影"] - p["空白底片"]) == 3,
    lambda p: p["灯塔影"] == p["雨幕影"] + 1,
    lambda p: min(p["钟楼影"], p["空白底片"]) < p["灯塔影"] < max(p["钟楼影"], p["空白底片"]),
    lambda p: p["纸船影"] == 2,
]
show("NA-006 primary (相距三次 -> 差3)", I6, solutions(I6, R6))

R6v = [
    lambda p: abs(p["玻璃影"] - p["空白底片"]) == 4,   # "3 exposures in between"
    lambda p: p["灯塔影"] == p["雨幕影"] + 1,
    lambda p: min(p["钟楼影"], p["空白底片"]) < p["灯塔影"] < max(p["钟楼影"], p["空白底片"]),
    lambda p: p["纸船影"] == 2,
]
show("NA-006 variant 3-between (差4)", I6, solutions(I6, R6v))
