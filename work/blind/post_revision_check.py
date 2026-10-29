# -*- coding: utf-8 -*-
"""Comprehensive post-revision check across all six cases + leak check."""
from itertools import permutations
import json, os

SRC = r"C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\work\blind-src"


def load(cid):
    with open(os.path.join(SRC, cid + ".json"), encoding="utf-8") as f:
        return json.load(f)


def sols(items, rules):
    out = []
    for p in permutations(items):
        pos = {it: i + 1 for i, it in enumerate(p)}
        if all(r(pos) for r in rules):
            out.append(tuple(p))
    return out


def between(p, a, b, x):
    return min(p[a], p[b]) < p[x] < max(p[a], p[b])


CASES = {
 "NA-001": [
   lambda p: p["蓝票"] == p["红票"] + 1,
   lambda p: p["绿票"] > p["黄票"],
   lambda p: p["黄票"] != 1,
 ],
 "NA-002": [
   lambda p: p["铜钥匙"] == p["银徽章"] + 1,
   lambda p: p["玻璃球"] == 4,
   lambda p: p["航海图"] < p["银徽章"],
 ],
 "NA-003": [
   lambda p: p["星图"] == p["铜铃"] + 1,
   lambda p: p["红盒"] < p["铜铃"],          # now justified by explicit axis sentence
   lambda p: p["星图"] != 5,
   lambda p: p["纸鹤"] == p["红盒"] + 1,
 ],
 "NA-004": [
   lambda p: abs(p["铜铃"] - p["值班簿"]) == 1,
   lambda p: abs(p["铜铃"] - p["旧透镜"]) == 3,
   lambda p: p["旧透镜"] == 4,
   lambda p: between(p, "铜铃", "海图", "旧透镜"),
 ],
 "NA-005": [
   lambda p: p["空白回邮"] != 1,
   lambda p: between(p, "晨雾邮笺", "空白回邮", "夜航申请"),
   lambda p: abs(p["晨雾邮笺"] - p["夜航申请"]) == 3,
   lambda p: abs(p["红蜡封信"] - p["夜航申请"]) == 1,
 ],
 "NA-006": [
   lambda p: p["空白底片"] == p["玻璃影"] + 3,       # n -> n+3, directional per new text
   lambda p: p["灯塔影"] == p["雨幕影"] + 1,
   lambda p: between(p, "钟楼影", "空白底片", "灯塔影"),
   lambda p: p["纸船影"] == 2,
 ],
}

print("=" * 96)
print("FULL RE-CHECK (post-revision files)")
print("=" * 96)
for cid, rules in CASES.items():
    d = load(cid)
    items = d["items"]
    s = sols(items, rules)
    print(f"\n{cid}  rev={d.get('revision', '(none)')}   solutions={len(s)}")
    for p in s:
        print("   ANSWER: " + " -> ".join(f"{i+1}.{it}" for i, it in enumerate(p)))
    print(f"   items array: {items}")
    if len(s) == 1:
        print(f"   items == answer order ? {list(s[0]) == items}   <-- leak if True")

print()
print("=" * 96)
print("ITEMS-ORDER LEAK SWEEP (all six)")
print("=" * 96)
ANSWERS = {cid: sols(load(cid)["items"], r) for cid, r in CASES.items()}
for cid, s in ANSWERS.items():
    d = load(cid)
    if len(s) == 1:
        leak = list(s[0]) == d["items"]
        print(f"  {cid}: {'LEAK' if leak else 'ok  '}  items={d['items']}")
    else:
        print(f"  {cid}: not unique, skip")
