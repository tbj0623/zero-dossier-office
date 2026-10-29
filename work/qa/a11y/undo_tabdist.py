"""Undo reachability after a move, tab distance back into the board, mobile-menu Escape."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}


def fresh(pg):
    pg.goto(BASE + '#/about', wait_until='domcontentloaded'); pg.wait_for_timeout(150)
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk', timeout=30000); pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()
    fresh(pg)

    # undo is disabled before any move -> is it in tab order?
    OUT['undo_initial'] = pg.evaluate("""() => {const u=document.querySelector('#btn-undo');
        return {disabled:u.disabled, tabIndex:u.tabIndex, ariaDisabled:u.getAttribute('aria-disabled'),
                inTabOrder: !u.disabled};}""")
    # make a move
    pg.locator('#slots .slot[data-index="2"] [data-act="up"]').click(); pg.wait_for_timeout(300)
    OUT['undo_after_move'] = pg.evaluate("""() => {const u=document.querySelector('#btn-undo');
        return {disabled:u.disabled, inTabOrder: !u.disabled};}""")

    # after a pick-select drops focus to body, how many Tab presses to get back to the board?
    pg.evaluate("document.querySelector('#slots .slot[data-index=\"1\"] [data-act=\"pick\"]').focus()")
    pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    start = pg.evaluate("document.activeElement.tagName")
    presses = 0
    for i in range(40):
        pg.keyboard.press('Tab'); presses += 1
        if pg.evaluate("!!document.activeElement.closest('#slots, .actions')"):
            break
    OUT['tab_distance_after_select'] = {
        'focus_after_select': start, 'tab_presses_to_reach_board': presses,
        'landed_on': pg.evaluate("document.activeElement.getAttribute('aria-label') || document.activeElement.innerText"),
    }

    # after the verdict handoff, how many tabs to reach the verdict actions?
    fresh(pg)
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
    pg.keyboard.press('Enter')
    pg.wait_for_selector('.verdict', timeout=15000); pg.wait_for_timeout(900)
    presses = 0
    for i in range(60):
        pg.keyboard.press('Tab'); presses += 1
        if pg.evaluate("!!document.activeElement.closest('.verdict')"):
            break
    OUT['tab_distance_after_verdict'] = {
        'focus_after_verdict': pg.evaluate("document.activeElement.tagName"),
        'tab_presses_to_reach_verdict_content': presses,
        'landed_on': pg.evaluate("document.activeElement.innerText?.trim().slice(0,30) || document.activeElement.tagName"),
    }
    ctx.close()

    # mobile menu Escape + focus after closing
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='zh-CN', is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(500)
    pg.click('#nav-toggle'); pg.wait_for_timeout(300)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    OUT['mobile_menu'] = pg.evaluate("""() => ({
        openAfterEscape: document.querySelector('#site-nav').dataset.open,
        expanded: document.querySelector('#nav-toggle').getAttribute('aria-expanded'),
        linksStillVisible: getComputedStyle(document.querySelector('#site-nav')).display,
        focusOnToggle: document.activeElement === document.querySelector('#nav-toggle')})""")
    # close by clicking toggle -> where does focus go?
    pg.click('#nav-toggle'); pg.wait_for_timeout(300)
    OUT['mobile_menu']['after_toggle_close'] = pg.evaluate("""() => ({
        open: document.querySelector('#site-nav').dataset.open,
        focus: document.activeElement.tagName + '#' + (document.activeElement.id || '')})""")
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1))
(HERE / 'undo-tabdist.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
