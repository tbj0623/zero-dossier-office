"""Last precision round: arrow-key shortcut, active-view crumb geometry, toast stale/duplicate announce."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}


def fresh_desk(pg, w=1440, h=900):
    pg.goto(BASE + '#/about', wait_until='domcontentloaded'); pg.wait_for_timeout(150)
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk', timeout=30000); pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()

    # ---- arrow keys with focus on an ENABLED button inside a slot ----
    fresh_desk(pg)
    def order():
        return pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())")
    res = {}
    res['start'] = order()
    pg.evaluate("document.querySelector('#slots .slot[data-index=\"2\"] [data-act=\"pick\"]').focus()")
    res['focus_on'] = pg.evaluate("document.activeElement.getAttribute('aria-label')")
    pg.keyboard.press('ArrowUp'); pg.wait_for_timeout(300)
    res['after_arrowup'] = order()
    res['focus_after_arrowup'] = pg.evaluate("document.activeElement.tagName + '|' + (document.activeElement.getAttribute('aria-label')||'')")
    res['scrollY'] = pg.evaluate('Math.round(scrollY)')
    pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(300)
    res['after_arrowdown'] = order()
    # ArrowUp on the first row (boundary) - does the page scroll instead?
    pg.evaluate("window.scrollTo(0, 600)")
    pg.evaluate("document.querySelector('#slots .slot[data-index=\"0\"] [data-act=\"down\"]').focus()")
    before_scroll = pg.evaluate('Math.round(scrollY)')
    pg.keyboard.press('ArrowUp'); pg.wait_for_timeout(300)
    res['boundary_arrow_scroll'] = {'before': before_scroll, 'after': pg.evaluate('Math.round(scrollY)'),
                                    'order': order()}
    OUT['arrow_keys'] = res

    # ---- toast: stale text retained + duplicate announce suppression ----
    fresh_desk(pg)
    pg.evaluate("""() => { window.__t = [];
        const mo = new MutationObserver(ms => { for (const m of ms) {
          const el = m.target.nodeType === 3 ? m.target.parentElement : m.target;
          const l = el?.closest?.('[role=status]'); if (l) window.__t.push({id: l.id, type: m.type}); }});
        mo.observe(document.body, {subtree:true, childList:true, characterData:true}); }""")
    pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').click(); pg.wait_for_timeout(300)
    first = pg.evaluate('window.__t.length')
    pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').click(); pg.wait_for_timeout(300)  # deselect
    pg.evaluate('window.__t = []')
    pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').click(); pg.wait_for_timeout(300)  # reselect same item
    OUT['toast_dup'] = {
        'first_select_mutations': first,
        'reselect_same_text_mutations': pg.evaluate('window.__t.length'),
        'toast_text_after_hide': pg.evaluate("""() => {const t=document.querySelector('#toast');
            return {text: t.innerText, show: t.dataset.show, opacity: getComputedStyle(t).opacity,
                    inA11yTree: t.checkVisibility?.()};}"""),
    }
    ctx.close()

    # ---- active-view crumb geometry on mobile ----
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='zh-CN', is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    fresh_desk(pg)
    OUT['crumb_mobile'] = pg.evaluate("""() => {
      const view = document.querySelector('#view-case');
      const a = view.querySelector('.desk-crumbs a');
      const r = a.getBoundingClientRect();
      const span = a.nextElementSibling.getBoundingClientRect();
      return {text: a.innerText, w: +r.width.toFixed(1), h: +r.height.toFixed(1),
              cx: +(r.x + r.width/2).toFixed(1), cy: +(r.y + r.height/2).toFixed(1),
              gapToNext: +(span.x - r.right).toFixed(1),
              gapToPrevEdge: +(r.x).toFixed(1)};
    }""")
    # vertical gap between crumb and the h1 below it
    OUT['crumb_context'] = pg.evaluate("""() => {
      const a = document.querySelector('#view-case .desk-crumbs a').getBoundingClientRect();
      const h = document.querySelector('#case-title').getBoundingClientRect();
      return {crumbBottom: +a.bottom.toFixed(1), h1Top: +h.top.toFixed(1), gap: +(h.top - a.bottom).toFixed(1)}; }""")
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1))
(HERE / 'last-round.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
