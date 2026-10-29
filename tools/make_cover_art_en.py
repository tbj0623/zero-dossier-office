#!/usr/bin/env python3
"""生成案件封面的英文版（-en.webp），供 ?lang=en 时切换。

封面图里烘死了中文标题与物件名，这些是"图片里的文字"，无法靠 DOM 替换，
所以必须重绘一套英文版。中文版原样保留，两套并存，按语言切换。

用法：python tools/make_cover_art_en.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "site" / "assets"

W, H = 1150, 700
BG = (7, 26, 35)
CARD = (228, 214, 182)
EDGE = (150, 130, 95)
INK = (32, 24, 13)
HEAD = (64, 48, 20)

# 英文术语表（与 i18n 包一致）
GLOSS = {
    "红票": "Red Ticket", "蓝票": "Blue Ticket", "黄票": "Yellow Ticket", "绿票": "Green Ticket",
    "红盒": "Red Box", "纸鹤": "Paper Crane", "铜铃": "Brass Bell",
    "星图": "Star Chart", "蓝灯": "Blue Lamp",
    "银徽": "Silver Badge", "海图": "Sea Chart", "玻璃球": "Glass Sphere", "铜钥匙": "Brass Key",
    "铜哨": "Brass Whistle", "灰灯": "Grey Lamp", "黄灯": "Amber Lamp", "绿灯": "Green Lamp",
    "空白底片": "Blank Negative", "曝光": "Exposure", "回信": "Reply",
}


def font(size: int, bold: bool = False):
    cands = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def en(text: str) -> str:
    return GLOSS.get(text, text)


def base(num: str, subtitle: str, footer: str):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([70, 55, 1080, 645], 26, fill=CARD, outline=(190, 172, 138), width=3)
    d.rounded_rectangle([100, 135, 1050, 580], 14, outline=EDGE, width=2)
    d.text((140, 115), f"EVIDENCE ARCHIVE / {num}", font=font(26, True), fill=HEAD)
    d.text((140, 185), subtitle, font=font(52, True), fill=INK)
    d.text((140, 600), footer, font=font(24), fill=HEAD)
    return im, d


def centered(d, text, f, cx, y, fill):
    w = d.textlength(text, font=f)
    d.text((cx - w / 2, y), text, font=f, fill=fill)


def make_001() -> None:
    """四张车票 —— 打乱顺序（黄 绿 红 蓝），与唯一解 红→蓝→黄→绿 不同。"""
    im, d = base("001", "The Last Tram · Tickets Restored",
                 "Four stubs · four recorded times")
    tickets = [("红票", (139, 74, 74)), ("蓝票", (58, 96, 140)),
               ("黄票", (176, 150, 58)), ("绿票", (74, 124, 88))]
    order = [2, 3, 0, 1]
    x = 132
    for idx in order:
        name, col = tickets[idx]
        d.rounded_rectangle([x, 330, x + 215, 530], 10, fill=(236, 224, 196), outline=col, width=5)
        d.line([x + 30, 395, x + 185, 395], fill=col, width=5)
        centered(d, en(name), font(30, True), x + 107, 445, INK)
        x += 240
    im.save(ASSETS / "evidence-case-001-en.webp", "WEBP", quality=90)


def make_002() -> None:
    """四格抽屉 —— 不含物件，只画编号（正确做法，不泄题）。"""
    im, d = base("002", "The Sealed Room · Drawer Record",
                 "Four drawers · all locked")
    x = 175
    for i in range(1, 5):
        d.rounded_rectangle([x, 330, x + 180, 530], 8, fill=(150, 124, 88), outline=(96, 74, 48), width=4)
        d.rounded_rectangle([x + 20, 350, x + 160, 510], 6, fill=(168, 142, 104), outline=(120, 96, 66), width=2)
        # 抽屉拉手
        d.rounded_rectangle([x + 72, 420, x + 108, 436], 8, fill=(96, 74, 48))
        centered(d, str(i), font(30, True), x + 90, 470, (96, 74, 48))
        x += 205
    im.save(ASSETS / "evidence-case-002-en.webp", "WEBP", quality=90)


def make_003() -> None:
    """五个包裹 —— 打乱顺序（星图 蓝灯 红盒 纸鹤 铜铃），且不标序号。"""
    im, d = base("003", "Sorting Line · The Missing Slot",
                 "Five parcels · three non-overlapping logs")
    boxes = [("红盒", (150, 74, 74)), ("纸鹤", (190, 170, 120)), ("铜铃", (168, 132, 60)),
             ("星图", (66, 88, 140)), ("蓝灯", (74, 132, 150))]
    order = [3, 4, 0, 1, 2]
    x = 128
    for idx in order:
        name, col = boxes[idx]
        d.rounded_rectangle([x, 320, x + 172, 540], 10, fill=(236, 224, 196), outline=col, width=4)
        for gy in range(360, 520, 26):
            d.line([x + 18, gy, x + 154, gy], fill=(200, 188, 160), width=1)
        d.rounded_rectangle([x + 34, 388, x + 138, 468], 6, fill=col)
        centered(d, en(name), font(19, True), x + 86, 492, INK)
        x += 186
    im.save(ASSETS / "evidence-case-003-en.webp", "WEBP", quality=90)


def main() -> int:
    make_001()
    make_002()
    make_003()
    for f in ("evidence-case-001-en.webp", "evidence-case-002-en.webp", "evidence-case-003-en.webp"):
        p = ASSETS / f
        print(f"OK  {f}  {p.stat().st_size / 1024:.1f} KB  {Image.open(p).size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
