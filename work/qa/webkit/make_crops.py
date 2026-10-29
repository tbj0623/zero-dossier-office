#!/usr/bin/env python3
"""Build side-by-side WebKit|Chromium crops for the three mandated scenes, plus
a per-scene difference heatmap so any visual divergence is visible rather than
inferred from numbers.

For each scene and viewport:
  shots/crop-<scene>-webkit.png    header+hero band, WebKit
  shots/crop-<scene>-chromium.png  same band, Chromium
  crops/side-<scene>.png           the two stacked with a divider + labels
  crops/diff-<scene>.png           absolute pixel difference, amplified

Writes raw/crop-manifest.json.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from wk_common import BASE, CROPS, RAW, SHOTS, now_iso

SCENES = [
    ("home-1440", "#/", 1440, 900, {"x": 0, "y": 0, "width": 1440, "height": 780}),
    ("home-768", "#/", 768, 1024, {"x": 0, "y": 0, "width": 768, "height": 780}),
    ("home-390", "#/", 390, 844, {"x": 0, "y": 0, "width": 390, "height": 640}),
    ("cabinet-1440", "#/cabinet", 1440, 900, {"x": 0, "y": 0, "width": 1440, "height": 700}),
    ("cabinet-390", "#/cabinet", 390, 844, {"x": 0, "y": 0, "width": 390, "height": 700}),
    ("desk-1440", "#/case/NA-001", 1440, 900, {"x": 0, "y": 0, "width": 1440, "height": 900}),
    ("desk-390", "#/case/NA-001", 390, 844, {"x": 0, "y": 0, "width": 390, "height": 844}),
]

SETTLE = """async () => {
    if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (e) {} }
    const imgs = [...document.images];
    await Promise.all(imgs.map(i => (i.complete && i.naturalWidth > 0) ? Promise.resolve()
        : new Promise(r => { i.addEventListener('load', r, {once:true}); i.addEventListener('error', r, {once:true}); setTimeout(r, 3000); })));
    window.scrollTo(0,0);
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
}"""


def label(img: Image.Image, text: str, color=(230, 190, 120)) -> Image.Image:
    bar = Image.new("RGB", (img.width, 26), (10, 24, 32))
    d = ImageDraw.Draw(bar)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 15)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    d.text((8, 5), text, fill=color, font=font)
    out = Image.new("RGB", (img.width, img.height + 26), (10, 24, 32))
    out.paste(bar, (0, 0))
    out.paste(img, (0, 26))
    return out


def main() -> int:
    manifest: dict = {"when": now_iso(), "base": BASE, "scenes": {}}
    with sync_playwright() as p:
        for name, route, w, h, clip in SCENES:
            imgs = {}
            for eng, launcher in (("webkit", p.webkit), ("chromium", p.chromium)):
                b = launcher.launch(headless=True)
                pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1,
                                locale="zh-CN")
                pg.goto(f"{BASE}/{route}", wait_until="networkidle", timeout=45000)
                if "case" in route:
                    pg.wait_for_selector("#slots .slot", timeout=15000)
                pg.wait_for_timeout(500)
                pg.evaluate(SETTLE)
                pg.wait_for_timeout(400)
                path = SHOTS / f"crop-{name}-{eng}.png"
                pg.screenshot(path=str(path), clip=clip)
                imgs[eng] = Image.open(path).convert("RGB")
                b.close()

            a, c = imgs["webkit"], imgs["chromium"]
            # pad to the same size (they should already match)
            W = max(a.width, c.width)
            H = max(a.height, c.height)
            side = Image.new("RGB", (W, H * 2 + 26 * 2 + 6), (0, 0, 0))
            side.paste(label(a, f"WebKit 26.5  |  {name}  {w}x{h}"), (0, 0))
            side.paste(label(c, f"Chromium 151.0.7922.34  |  {name}  {w}x{h}", (120, 200, 230)),
                       (0, H + 26 + 6))
            side_path = CROPS / f"side-{name}.png"
            side.save(side_path)

            # difference heatmap
            hh = min(a.height, c.height)
            ww = min(a.width, c.width)
            aa = np.array(a)[:hh, :ww].astype(int)
            cc = np.array(c)[:hh, :ww].astype(int)
            diff = np.abs(aa - cc).max(axis=2)
            manifest.setdefault("scenes", {})[name] = {
                "side_by_side": str(side_path),
                "webkit_crop": str(SHOTS / f"crop-{name}-webkit.png"),
                "chromium_crop": str(SHOTS / f"crop-{name}-chromium.png"),
                "pixels_compared": int(hh * ww),
                "mean_abs_diff": round(float(diff.mean()), 3),
                "pct_pixels_over_8": round(float((diff > 8).mean() * 100), 3),
                "pct_pixels_over_32": round(float((diff > 32).mean() * 100), 3),
                "max_diff": int(diff.max()),
            }
            heat = np.clip(diff * 4, 0, 255).astype(np.uint8)
            heat_img = Image.fromarray(np.stack([heat, heat // 3, heat // 3], axis=2))
            heat_path = CROPS / f"diff-{name}.png"
            heat_img.save(heat_path)
            manifest["scenes"][name]["diff_heatmap"] = str(heat_path)
            print(f"{name}: meanAbsDiff={manifest['scenes'][name]['mean_abs_diff']} "
                  f"pct>8={manifest['scenes'][name]['pct_pixels_over_8']}% "
                  f"pct>32={manifest['scenes'][name]['pct_pixels_over_32']}%")

    (RAW / "crop-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    print(f"\nside-by-sides -> {CROPS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
