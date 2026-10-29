"""Targeted follow-ups:
 1. Does the case title (h1 / #case-title) exist on the desk page? heading structure.
 2. Verdict page heading structure + missing h1 / dangling aria-labelledby.
 3. Hint text announcement: is the revealed hint itself announced, or only a generic message?
 4. Toast double-announce on select (toast + status text + message).
 5. aria-expanded/aria-controls across expand/collapse.
 6. Keyboard-only solve end-to-end (Enter/Space/Arrow) - can a keyboard user finish the game?
 7. Error message: announced once per submit? Does it re-announce on repeated identical submit?
 8. Escape cancel selection: focus state.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}


def desk(pg, fresh=False):
    # leave the current route first so a same-hash goto actually re-routes
    pg.goto(BASE + '#/about', wait_until='domcontentloaded')
    pg.wait_for_timeout(150)
    if fresh:
        pg.evaluate('localStorage.clear()')
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk', timeout=30000)
    pg.wait_for_timeout(600)


def headings(pg):
    return pg.evaluate("""() => [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
        .filter(h => h.offsetParent !== null || getComputedStyle(h).position === 'fixed')
        .map(h => ({lvl: +h.tagName[1], text: h.innerText.replace(/\\s+/g,' ').trim().slice(0,44),
                    inMain: !!h.closest('main')}))""")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()

    # ---- 1. desk headings ----
    desk(pg)
    OUT['headings_desk'] = headings(pg)
    OUT['desk_h1'] = pg.evaluate("""() => { const h = document.querySelector('main h1');
        return h ? {text: h.innerText.slice(0,40), visible: h.offsetParent !== null} : null; }""")
    OUT['case_title_tag'] = pg.evaluate("document.querySelector('#case-title')?.tagName || null")
    OUT['view_case_aria'] = pg.evaluate("""() => { const v = document.querySelector('#view-case');
        return {labelledby: v.getAttribute('aria-labelledby'),
                targetExists: !!document.getElementById(v.getAttribute('aria-labelledby'))}; }""")

    # ---- 3/4. hint + toast live behaviour ----
    pg.evaluate("""() => { window.__log = [];
        const mo = new MutationObserver(ms => { for (const m of ms) {
          const el = m.target.nodeType === 3 ? m.target.parentElement : m.target;
          const live = el?.closest?.('[aria-live],[role=status]');
          if (live) window.__log.push({id: live.id, type: m.type,
              text: (live.innerText || '').replace(/\\s+/g,' ').slice(0, 90)});
        }});
        mo.observe(document.body, {subtree:true, childList:true, characterData:true, attributes:true}); }""")
    pg.locator('#btn-hint').click()
    pg.wait_for_timeout(900)
    OUT['hint_live_log'] = pg.evaluate("window.__log")
    OUT['hint_dom'] = pg.evaluate("""() => ({
        hintsLive: document.querySelector('#hints').getAttribute('aria-live'),
        hintsRole: document.querySelector('#hints').getAttribute('role'),
        hintInA11yTree: document.querySelector('.hint-card')?.checkVisibility?.(),
        hintText: document.querySelector('.hint-card')?.innerText,
        messageText: document.querySelector('#message').innerText,
        messageLive: document.querySelector('#message').getAttribute('aria-live'),
    })""")

    # repeated identical wrong submit: does the message re-announce?
    pg.evaluate("window.__log = []")
    pg.locator('#btn-submit').click()
    pg.wait_for_timeout(600)
    first = pg.evaluate("window.__log.length")
    pg.evaluate("window.__log = []")
    pg.locator('#btn-submit').click()
    pg.wait_for_timeout(600)
    OUT['repeat_wrong_submit'] = {
        'first_mutations': first,
        'second_mutations': pg.evaluate("window.__log.length"),
        'message_identical': pg.evaluate("document.querySelector('#message').innerText.slice(0,60)"),
        'second_log': pg.evaluate("window.__log"),
    }

    # toast + live: selecting a slot
    pg.evaluate("window.__log = []")
    pg.locator('#slots .slot[data-index="1"] [data-act="pick"]').click()
    pg.wait_for_timeout(700)
    OUT['select_live_log'] = pg.evaluate("window.__log")
    OUT['select_state'] = pg.evaluate("""() => ({
        toast: document.querySelector('#toast').innerText,
        toastLive: document.querySelector('#toast').getAttribute('aria-live'),
        statusText: document.querySelector('#status-text').innerText,
        statusLive: document.querySelector('#status-text').getAttribute('aria-live'),
        message: document.querySelector('#message').innerText,
    })""")

    # ---- 6. keyboard-only solve ----
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk')
    pg.evaluate('localStorage.clear()')
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk')
    pg.wait_for_timeout(500)

    def order():
        return pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())")

    def kb_move(name, target):
        for _ in range(8):
            cur = order()
            i = cur.index(name)
            if i == target:
                return True
            act = 'up' if i > target else 'down'
            btn = pg.locator(f'#slots .slot[data-index="{i}"] [data-act="{act}"]')
            btn.focus()
            pg.keyboard.press('Enter')
            pg.wait_for_timeout(120)
        return False

    kb = {}
    kb['start'] = order()
    kb['moves'] = []
    for pos, name in enumerate(['红票', '蓝票', '黄票', '绿票']):
        ok = kb_move(name, pos)
        kb['moves'].append({'item': name, 'target': pos, 'ok': ok, 'order': order()})
    kb['final'] = order()
    # arrow-key path too: focus a row and press ArrowUp
    bb = pg.locator('#slots .slot[data-index="0"] [data-act="down"]')
    bb.focus()
    before_arrow = order()
    pg.keyboard.press('ArrowUp')
    pg.wait_for_timeout(200)
    kb['arrow_key'] = {'before': before_arrow, 'after': order(),
                       'focus': pg.evaluate("document.activeElement.getAttribute('aria-label')"),
                       'preventedScroll': True}
    # submit with keyboard
    pg.locator('#btn-submit').focus()
    pg.keyboard.press('Enter')
    try:
        pg.wait_for_selector('.verdict', timeout=12000)
        kb['submit_reached_verdict'] = True
    except Exception:
        kb['submit_reached_verdict'] = False
        kb['submit_message'] = pg.evaluate("document.querySelector('#message').innerText")
    pg.wait_for_timeout(500)
    kb['verdict_headings'] = headings(pg)
    kb['verdict_h1_count'] = pg.evaluate("document.querySelectorAll('main h1').length")
    kb['verdict_aria'] = pg.evaluate("""() => { const v = document.querySelector('#view-case');
        return {labelledby: v.getAttribute('aria-labelledby'),
                targetExists: !!document.getElementById(v.getAttribute('aria-labelledby')),
                activeTag: document.activeElement.tagName, activeId: document.activeElement.id}; }""")
    kb['verdict_buttons'] = pg.evaluate("""() => [...document.querySelectorAll('.verdict a, .verdict button')]
        .map(x => ({tag: x.tagName, text: (x.innerText||'').replace(/\\s+/g,' ').trim().slice(0,24),
                    href: x.getAttribute('href')}))""")
    OUT['keyboard_solve'] = kb

    # ---- 8. Escape cancels selection, focus ----
    desk(pg)
    pg.locator('#slots .slot[data-index="2"] [data-act="pick"]').focus()
    pg.keyboard.press('Enter')
    pg.wait_for_timeout(250)
    after_pick = pg.evaluate("document.activeElement.tagName + '|' + (document.activeElement.getAttribute('aria-label')||document.activeElement.id)")
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(250)
    OUT['escape_cancel'] = {
        'after_pick_focus': after_pick,
        'after_escape_focus': pg.evaluate("document.activeElement.tagName + '|' + (document.activeElement.getAttribute('aria-label')||document.activeElement.id)"),
        'selected_now': pg.evaluate("document.querySelectorAll('.slot[data-selected=\"true\"]').length"),
        'status': pg.evaluate("document.querySelector('#status-text').innerText"),
    }

    # ---- 5. expanded toggling ----
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk')
    pg.wait_for_timeout(400)
    toggle = []
    for _ in range(3):
        pg.locator('#ev-btn-E02').click()
        pg.wait_for_timeout(200)
        toggle.append(pg.evaluate("""() => {const b=document.querySelector('#ev-btn-E02');
            const body=document.getElementById(b.getAttribute('aria-controls'));
            return {expanded:b.getAttribute('aria-expanded'), hidden:body.hidden,
                    visible: body.checkVisibility?.()};}"""))
    OUT['toggle_sequence'] = toggle
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1)[:9000])
(HERE / 'followups.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
