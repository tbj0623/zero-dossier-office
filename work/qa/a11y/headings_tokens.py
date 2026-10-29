"""Heading order per page + exact token-pair contrast + 2.5.8 spacing geometry."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}


def lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def L(hexstr):
    h = hexstr.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def cr(a, b):
    la, lb = L(a), L(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


TOK = {
    '--ink': '#081821', '--panel': '#132b36', '--paper': '#e7d7b7', '--paper-dim': '#d6c49f',
    '--brass': '#dfb978', '--mist': '#9eb7b4', '--error': '#ffb0a2', '--text': '#f2ece0',
    '--text-dim': '#b9c8c5', 'ev-card-fg': '#20180d', 'ev-card-bg': '#e7d7b7',
    'msg-bad-fg': '#ffd8cf', 'msg-bad-bg': '#1b2b33', 'toast-bg': '#14333f',
}
pairs = {
    'body text --text-dim on --ink': ('--text-dim', '--ink'),
    'body text --text on --ink': ('--text', '--ink'),
    'ev-card #20180d on paper #e7d7b7': ('ev-card-fg', 'ev-card-bg'),
    '.pill brass on --panel': ('--brass', '--panel'),
    '.pill--mist mist on --panel': ('--mist', '--panel'),
    '.message--bad #ffd8cf on panel': ('msg-bad-fg', 'msg-bad-bg'),
    '.slot__label --mist on --panel': ('--mist', '--panel'),
    '--brass on --ink (links)': ('--brass', '--ink'),
    '--error on --ink': ('--error', '--ink'),
    'toast --text on #14333f': ('--text', 'toast-bg'),
}
OUT['token_pairs'] = {k: {'ratio': cr(TOK[a], TOK[b]), 'a': a, 'b': b} for k, (a, b) in pairs.items()}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()
    headings = {}
    for route, sel in [('#/', '#view-home[data-active="true"]'),
                       ('#/cabinet', '#view-cabinet[data-active="true"] .case-card'),
                       ('#/case/NA-001', '.desk'),
                       ('#/manual', '#view-manual[data-active="true"]'),
                       ('#/about', '#view-about[data-active="true"]')]:
        pg.goto(BASE + '#/about', wait_until='domcontentloaded'); pg.wait_for_timeout(120)
        pg.goto(BASE + route, wait_until='domcontentloaded')
        pg.wait_for_selector(sel, timeout=30000)
        pg.wait_for_timeout(500)
        headings[route] = pg.evaluate("""() => [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
            .filter(h => h.offsetParent !== null).map(h => h.tagName + ':' + h.innerText.replace(/\\s+/g,' ').trim().slice(0,26))""")
    OUT['heading_order'] = headings
    ctx.close()

    # ---- mobile geometry for 2.5.8 spacing ----
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='zh-CN', is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(600)
    OUT['geom_crumb'] = pg.evaluate("""() => {
      const a = document.querySelector('.desk-crumbs a'); const r = a.getBoundingClientRect();
      const sib = a.nextElementSibling?.getBoundingClientRect();
      return {w: +r.width.toFixed(1), h: +r.height.toFixed(1), cx: +(r.x + r.width/2).toFixed(1),
              cy: +(r.y + r.height/2).toFixed(1),
              nextX: sib ? +sib.x.toFixed(1) : null, gapToNext: sib ? +(sib.x - r.right).toFixed(1) : null};
    }""")
    OUT['geom_footer'] = pg.evaluate("""() => [...document.querySelectorAll('.site-footer a')].map(a => {
      const r = a.getBoundingClientRect();
      return {text: a.innerText, w: +r.width.toFixed(1), h: +r.height.toFixed(1),
              cx: +(r.x + r.width/2).toFixed(1), cy: +(r.y + r.height/2).toFixed(1)}; });""")
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1))
(HERE / 'headings-tokens-geometry.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
