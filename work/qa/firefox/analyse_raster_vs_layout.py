#!/usr/bin/env python3
"""Is the Chromium/Firefox pixel delta RASTERIZATION or LAYOUT?

Three independent tests on the same settled screenshots:
  1. SHIFT: recompute the diff after translating Firefox by -1/0/+1 px in x and y.
     A big drop at a non-zero shift means a systematic sub-pixel offset.
  2. BLUR: blur both by 1 px then diff. Rasterizer noise lives at glyph edges and
     mostly vanishes; a real block move (different layout) survives blurring.
  3. EDGE LOCALITY: for every differing pixel, is it within 2 px of a high-gradient
     (edge) pixel in the Chromium image? Rasterization noise is edge-local; a moved
     or recoloured block is not.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from fx_common import RAW, SHOTS

SCENES = ["home-1440", "cabinet-1440", "case-NA001-1440", "home-768", "home-390", "case-NA004-390"]


def load(name):
    a = Image.open(SHOTS / f"chromium-{name}.png").convert("RGB")
    b = Image.open(SHOTS / f"firefox-{name}.png").convert("RGB")
    if a.size != b.size:
        h = min(a.size[1], b.size[1])
        a, b = a.crop((0, 0, a.size[0], h)), b.crop((0, 0, b.size[0], h))
    return a, b


def mean_abs(a, b):
    d = np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16))
    return float(d.mean())


def pct_gt2(a, b):
    d = np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16)).max(axis=2)
    return float((d > 2).mean() * 100)


def shift_img(im, dx, dy):
    arr = np.asarray(im)
    out = np.full_like(arr, 0)
    h, w = arr.shape[:2]
    xs0, xs1 = max(0, dx), min(w, w + dx)
    ys0, ys1 = max(0, dy), min(h, h + dy)
    out[ys0:ys1, xs0:xs1] = arr[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return Image.fromarray(out)


def edge_mask(im, thresh=24):
    g = np.asarray(im.convert("L"), dtype=np.int16)
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
    e = (gx + gy) > thresh
    # dilate by 2 px
    out = e.copy()
    for dy in (-2, -1, 1, 2):
        for dx in (-2, -1, 1, 2):
            out |= np.roll(np.roll(e, dy, axis=0), dx, axis=1)
    return out


res = {}
for name in SCENES:
    a, b = load(name)
    base = mean_abs(a, b)
    shifts = {}
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            shifts[f"{dx},{dy}"] = round(mean_abs(a, shift_img(b, dx, dy)), 4)
    best_shift = min(shifts, key=shifts.get)
    blur_a, blur_b = a.filter(ImageFilter.GaussianBlur(1.0)), b.filter(ImageFilter.GaussianBlur(1.0))
    em = edge_mask(a)
    da = np.asarray(a, dtype=np.int16)
    db = np.asarray(b, dtype=np.int16)
    diff_px = np.abs(da - db).max(axis=2) > 2
    edge_local = float((diff_px & em).sum() / max(1, diff_px.sum()) * 100)
    res[name] = {
        "mean_abs_base": round(base, 4),
        "mean_abs_after_1px_blur": round(mean_abs(blur_a, blur_b), 4),
        "blur_reduction_pct": round(100 * (1 - mean_abs(blur_a, blur_b) / base), 2),
        "pct_gt2_base": round(pct_gt2(a, b), 4),
        "pct_gt2_after_blur": round(pct_gt2(blur_a, blur_b), 4),
        "best_shift": best_shift,
        "mean_abs_best_shift": shifts[best_shift],
        "shift_gain_pct": round(100 * (1 - shifts[best_shift] / base), 2),
        "all_shifts": shifts,
        "diff_pixels_on_edges_pct": round(edge_local, 2),
        "diff_pixels_off_edges_pct": round(100 - edge_local, 2),
    }
    print(name, json.dumps(res[name], ensure_ascii=False))

(RAW / "raster-vs-layout.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print("-> raw/raster-vs-layout.json")
