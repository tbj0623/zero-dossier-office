"""Skip-link vs hash-router interaction: does activating 'skip to main' navigate away?"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()
    results = {}
    for route in ['#/case/NA-001', '#/cabinet', '#/manual', '#/about']:
        pg.goto(BASE + '#/about', wait_until='domcontentloaded'); pg.wait_for_timeout(200)
        pg.goto(BASE + route, wait_until='domcontentloaded')
        pg.wait_for_selector('.view[data-active="true"]', timeout=30000)
        pg.wait_for_timeout(600)
        before = pg.evaluate("""() => ({hash: location.hash,
            activeView: document.querySelector('.view[data-active="true"]')?.id,
            deskExists: !!document.querySelector('.desk')})""")
        # focus the skip link and activate it with Enter (keyboard path)
        pg.evaluate("document.querySelector('.skip-link').focus()")
        pg.wait_for_timeout(120)
        pg.keyboard.press('Enter')
        pg.wait_for_timeout(800)
        after = pg.evaluate("""() => ({hash: location.hash,
            activeView: document.querySelector('.view[data-active="true"]')?.id,
            deskExists: !!document.querySelector('.desk'),
            active: document.activeElement.tagName + '#' + (document.activeElement.id || '')})""")
        results[route] = {'before': before, 'after': after, 'navigated_away': before['activeView'] != after['activeView']}
    OUT['skip_link_routing'] = results
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1))
(HERE / 'skip-link-routing.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
