"""Dialog-specific: axe scope under modal inerting, contrast of the 4 dialog nodes, inertness of page behind."""
import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}


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


def measure(pg, selector, nth=0):
    info = pg.evaluate("""([sel,nth]) => { const el = document.querySelectorAll(sel)[nth];
        el.scrollIntoView({block:'center', behavior:'instant'});
        const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
        return {color: cs.color, fontSize: cs.fontSize, fontWeight: cs.fontWeight,
                rect: {x:r.x, y:r.y, width:r.width, height:r.height}}; }""", [selector, nth])
    pg.wait_for_timeout(150)
    pg.evaluate("""([sel,nth]) => { const el = document.querySelectorAll(sel)[nth];
        el.style.setProperty('color','transparent','important');
        for (const c of el.querySelectorAll('*')) c.style.setProperty('color','transparent','important'); }""",
                [selector, nth])
    pg.wait_for_timeout(80)
    r = info['rect']
    box = {'x': max(0, r['x'] + r['width'] * 0.2), 'y': max(0, r['y'] + r['height'] * 0.25),
           'width': max(1, min(r['width'] * 0.6, 1440 - r['x'])), 'height': max(1, r['height'] * 0.5)}
    png = pg.screenshot(clip=box)
    img = Image.open(io.BytesIO(png)).convert('RGB')
    px = sorted(img.getdata(), key=lambda p: sum(p))
    med = px[len(px) // 2]
    text = parse_rgb(info['color'])
    return {'selector': selector, 'text': info['color'], 'bg': '#%02x%02x%02x' % med,
            'ratio': round(ratio(text, med), 2),
            'font': f"{info['fontSize']}/{info['fontWeight']}"}


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(500)
    pg.locator('#btn-reset').click()
    pg.wait_for_selector('#confirm-dialog[open]'); pg.wait_for_timeout(500)

    OUT['modal'] = pg.evaluate("""() => {
      const d = document.querySelector('#confirm-dialog');
      const btn = document.querySelector('#btn-submit');
      return {modal: d.matches(':modal'),
              pageInert: btn.matches(':disabled') || btn.closest('[inert]') !== null,
              bodyInertAttr: document.body.hasAttribute('inert'),
              canFocusOutside: (() => { try { btn.focus(); return document.activeElement === btn; }
                                        catch { return false; } })(),
              activeStillInDialog: d.contains(document.activeElement),
              dialogSize: {w: Math.round(d.getBoundingClientRect().width),
                           h: Math.round(d.getBoundingClientRect().height)}};
    }""")

    # contrast of the 4 dialog nodes axe flagged incomplete
    OUT['contrast'] = {
        'title': measure(pg, '#confirm-title'),
        'body': measure(pg, '#confirm-body'),
        'cancel': measure(pg, 'button[data-confirm="cancel"]'),
        'ok': measure(pg, 'button[data-confirm="ok"]'),
    }

    # axe rule coverage difference: how many nodes did axe actually see while modal open?
    pg.add_script_tag(path=str(HERE / 'axe.min.js'))
    cov = pg.evaluate("""async () => {
      const r = await axe.run(document, {runOnly: {type:'tag', values:['wcag2aa','best-practice']}});
      return {passes: r.passes.length, inapplicable: r.inapplicable.length,
              violations: r.violations.map(v => ({id:v.id, n:v.nodes.length})),
              incomplete: r.incomplete.map(v => ({id:v.id, n:v.nodes.length})),
              nodesChecked: r.passes.reduce((a,p)=>a+p.nodes.length,0)};
    }""")
    OUT['axe_coverage'] = cov
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1))
(HERE / 'dialog-detail.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
