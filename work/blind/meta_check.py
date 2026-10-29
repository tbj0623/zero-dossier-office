# -*- coding: utf-8 -*-
"""Meta-check: does the `items` array order equal the derived solution order?
(If so, a UI that renders items in array order hands the player the answer.)"""
import json, os

ANSWERS = {
    "NA-001": ["红票", "蓝票", "黄票", "绿票"],
    "NA-002": ["航海图", "银徽章", "铜钥匙", "玻璃球"],
    "NA-003": ["红盒", "纸鹤", "铜铃", "星图", "蓝灯"],
    "NA-004": ["铜铃", "值班簿", "玻璃罩", "旧透镜", "海图"],
    "NA-005": ["晨雾邮笺", "港口便条", "红蜡封信", "夜航申请", "空白回邮"],
    "NA-006": ["钟楼影", "纸船影", "玻璃影", "雨幕影", "灯塔影", "空白底片"],
}
SRC = r"C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\work\blind-src"

for cid, ans in ANSWERS.items():
    with open(os.path.join(SRC, cid + ".json"), encoding="utf-8") as f:
        d = json.load(f)
    items = d["items"]
    same = items == ans
    print(f"{cid}: items == answer order ? {same}")
    if not same:
        print(f"   items : {items}")
        print(f"   answer: {ans}")
