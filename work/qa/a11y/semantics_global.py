"""Dialog semantics + placeholder alt + iframe/lang checks + any duplicated ids."""
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
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(500)

    OUT['global'] = pg.evaluate("""() => {
      const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
      const dup = ids.filter((x,i) => ids.indexOf(x) !== i);
      return {
        lang: document.documentElement.lang,
        title: document.title,
        duplicateIds: [...new Set(dup)],
        imgsNoAlt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt'))
          .map(i => i.getAttribute('src')),
        imgsEmptyAlt: [...document.querySelectorAll('img')].filter(i => i.getAttribute('alt') === '').length,
        iframes: document.querySelectorAll('iframe').length,
        buttonsNoName: [...document.querySelectorAll('button')].filter(x => {
           if (x.offsetParent === null && !x.closest('dialog')) return false;
           const name = (x.getAttribute('aria-label') || x.innerText || '').trim();
           return !name; }).map(x => x.outerHTML.slice(0, 90)),
        linksNoName: [...document.querySelectorAll('a[href]')].filter(x => {
           const name = (x.getAttribute('aria-label') || x.innerText || '').trim();
           return !name; }).map(x => x.outerHTML.slice(0, 90)),
        landmarks: [...document.querySelectorAll('header,nav,main,footer,aside,[role]')]
          .map(x => ({tag: x.tagName, role: x.getAttribute('role'),
                      label: x.getAttribute('aria-label'),
                      count: 1})).slice(0, 12),
        tabindexPositive: [...document.querySelectorAll('[tabindex]')]
          .filter(x => +x.getAttribute('tabindex') > 0).map(x => x.outerHTML.slice(0, 60)),
        ariaHiddenFocusable: [...document.querySelectorAll('[aria-hidden="true"]')]
          .filter(x => x.matches('a[href],button,input,select,textarea,[tabindex]'))
          .map(x => x.outerHTML.slice(0, 60)),
      };
    }""")

    # dialog semantics
    pg.locator('#btn-reset').focus()
    pg.keyboard.press('Enter')
    pg.wait_for_selector('#confirm-dialog[open]')
    pg.wait_for_timeout(400)
    OUT['dialog'] = pg.evaluate("""() => {
      const d = document.querySelector('#confirm-dialog');
      const cs = getComputedStyle(d);
      return {open: d.open, modal: d.matches(':modal'),
              labelledby: d.getAttribute('aria-labelledby'),
              labelledbyText: document.getElementById(d.getAttribute('aria-labelledby'))?.innerText,
              describedby: d.getAttribute('aria-describedby'),
              bodyId: document.getElementById('confirm-body')?.id,
              role: d.getAttribute('role'),
              activeTag: document.activeElement.tagName,
              activeConfirm: document.activeElement.dataset?.confirm || null,
              // accessible description is empty without aria-describedby
              descriptionExposed: d.getAttribute('aria-describedby') !== null,
              cancelledViaBackdrop: null};
    }""")
    # click backdrop -> does dialog close?
    pg.mouse.click(30, 30)
    pg.wait_for_timeout(400)
    OUT['dialog']['backdrop_click_closes'] = pg.evaluate("document.querySelector('#confirm-dialog').open")

    # reopen and cancel
    if not pg.evaluate("document.querySelector('#confirm-dialog').open"):
        pg.locator('#btn-reset').click(); pg.wait_for_timeout(400)
    pg.locator('[data-confirm="cancel"]').click(); pg.wait_for_timeout(400)
    OUT['dialog']['after_cancel'] = pg.evaluate("""() => ({
        open: document.querySelector('#confirm-dialog').open,
        focus: document.activeElement.id || document.activeElement.tagName})""")
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1)[:6000])
(HERE / 'semantics-global.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
