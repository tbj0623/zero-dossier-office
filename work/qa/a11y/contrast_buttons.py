"""Isolated re-measure of the primary button (gradient background) + a few spot checks."""
import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent


def srgb(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = (srgb(x) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_rgb(s):
    nums = [x.strip() for x in s.replace('rgba(', '').replace('rgb(', '').replace(')', '').replace('/', ',').split(',')]
    return tuple(float(x) for x in nums if x)


def measure_center(pg, selector, nth=0):
    info = pg.evaluate("""([sel,nth]) => { const el = document.querySelectorAll(sel)[nth];
        el.scrollIntoView({block:'center', behavior:'instant'});
        const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
        return {color: cs.color, bgImage: cs.backgroundImage, bgColor: cs.backgroundColor,
                fontSize: cs.fontSize, fontWeight: cs.fontWeight,
                rect: {x: r.x, y: r.y, width: r.width, height: r.height}}; }""", [selector, nth])
    pg.wait_for_timeout(150)
    pg.evaluate("""([sel,nth]) => { const el = document.querySelectorAll(sel)[nth];
        el.style.setProperty('color','transparent','important');
        for (const c of el.querySelectorAll('*')) c.style.setProperty('color','transparent','important'); }""",
                [selector, nth])
    pg.wait_for_timeout(80)
    r = info['rect']
    # sample the middle band only, away from the border and edges
    box = {'x': r['x'] + r['width'] * 0.25, 'y': r['y'] + r['height'] * 0.3,
           'width': max(1, r['width'] * 0.5), 'height': max(1, r['height'] * 0.4)}
    png = pg.screenshot(clip=box)
    img = Image.open(io.BytesIO(png)).convert('RGB')
    px = sorted(img.getdata(), key=lambda p: sum(p))
    med = px[len(px) // 2]
    text = parse_rgb(info['color'])
    return {'selector': selector, 'text_color': info['color'], 'bg_image': info['bgImage'][:120],
            'bg_color': info['bgColor'], 'sampled_bg': '#%02x%02x%02x' % med,
            'ratio_median': round(ratio(text, med), 2),
            'ratio_min': round(min(ratio(text, p) for p in px[:len(px)//10]), 2),
            'ratio_max': round(max(ratio(text, p) for p in px[-len(px)//10:]), 2),
            'font': f"{info['fontSize']}/{info['fontWeight']}"}


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk')
    pg.wait_for_timeout(700)
    out = {}
    out['btn_primary'] = measure_center(pg, '#btn-submit')
    out['btn_primary_hover'] = None
    # hover state
    pg.hover('#btn-submit')
    pg.wait_for_timeout(200)
    out['btn_primary_hover'] = measure_center(pg, '#btn-submit')
    # nav current link (brass on translucent bg over header)
    out['nav_current'] = measure_center(pg, '.site-nav a[aria-current="page"]')
    # brand
    out['brand_name'] = measure_center(pg, '.brand__name')
    # verdict page primary/secondary buttons
    pg.goto(BASE + '#/manual', wait_until='domcontentloaded')
    pg.wait_for_selector('#view-manual[data-active="true"]')
    pg.wait_for_timeout(500)
    out['clear_progress_small_btn'] = measure_center(pg, '#clear-progress')
    b.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
(HERE / 'contrast-buttons.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
