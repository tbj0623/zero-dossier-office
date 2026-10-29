"""Precise verdict focus handoff test."""
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
    pg.goto(BASE + '#/about', wait_until='domcontentloaded'); pg.wait_for_timeout(150)
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(500)

    def order():
        return pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())")

    def move_to(name, target):
        for _ in range(10):
            cur = order(); i = cur.index(name)
            if i == target: return
            act = 'up' if i > target else 'down'
            pg.locator(f'#slots .slot[data-index="{i}"] [data-act="{act}"]').click(); pg.wait_for_timeout(130)

    for pos, name in enumerate(['红票', '蓝票', '黄票', '绿票']):
        move_to(name, pos)
    pg.locator('#btn-submit').focus()
    OUT['focus_before_submit'] = pg.evaluate("document.activeElement.id")
    pg.keyboard.press('Enter')

    # sample focus over time
    samples = []
    for i in range(14):
        pg.wait_for_timeout(200)
        samples.append(pg.evaluate("""() => ({t: Math.round(performance.now()),
            tag: document.activeElement.tagName, id: document.activeElement.id || null,
            verdict: !!document.querySelector('.verdict')})"""))
    OUT['focus_samples'] = samples
    pg.wait_for_timeout(600)

    # where does the next Tab land?
    before = pg.evaluate("document.activeElement.tagName + '#' + (document.activeElement.id||'')")
    pg.keyboard.press('Tab'); pg.wait_for_timeout(250)
    after1 = pg.evaluate("document.activeElement.tagName + '|' + (document.activeElement.innerText||'').trim().slice(0,24)")
    pg.keyboard.press('Tab'); pg.wait_for_timeout(250)
    after2 = pg.evaluate("document.activeElement.tagName + '|' + (document.activeElement.innerText||'').trim().slice(0,24)")
    OUT['verdict_tab'] = {'before': before, 'tab1': after1, 'tab2': after2}

    # Is the verdict content announced at all? does anything have aria-live?
    OUT['verdict_live'] = pg.evaluate("""() => ({
        caseRootLive: document.querySelector('#case-root').getAttribute('aria-live'),
        verdictLive: document.querySelector('.verdict')?.getAttribute('aria-live'),
        messageText: document.querySelector('#message')?.innerText,
        messageLive: document.querySelector('#message')?.getAttribute('aria-live'),
        documentTitle: document.title,
        activeInVerdict: !!document.activeElement.closest?.('.verdict'),
    })""")
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1))
(HERE / 'verdict-focus.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
