"""Manual (non-axe) accessibility checks against the LIVE site."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}


def save(name, obj):
    OUT[name] = obj
    print(f'\n=== {name} ===')
    print(json.dumps(obj, ensure_ascii=False, indent=1)[:6000])


def desk(pg, route='#/case/NA-001'):
    pg.goto(BASE + route, wait_until='domcontentloaded', timeout=60000)
    pg.wait_for_selector('.desk', timeout=30000)
    pg.wait_for_timeout(600)


DESCRIBE_ACTIVE = """() => {
  const a = document.activeElement;
  if (!a) return null;
  const r = a.getBoundingClientRect();
  const cs = getComputedStyle(a);
  return {
    tag: a.tagName,
    id: a.id || null,
    cls: typeof a.className === 'string' ? a.className : null,
    name: (a.getAttribute('aria-label') || a.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 60),
    rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
    outlineWidth: cs.outlineWidth, outlineStyle: cs.outlineStyle, outlineColor: cs.outlineColor,
    outlineOffset: cs.outlineOffset, boxShadow: cs.boxShadow, bg: cs.backgroundColor,
    focusVisible: a.matches(':focus-visible'),
    inViewport: r.top >= -1 && r.bottom <= innerHeight + 1 && r.left >= -1 && r.right <= innerWidth + 1,
  };
}"""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()

        # ---------------- A. focus order on desk ----------------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        pg = ctx.new_page()
        desk(pg)
        # collect every focusable element the DOM exposes, for a completeness cross-check
        dom_focusables = pg.evaluate("""() => [...document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]')]
            .filter(e => !e.disabled && e.tabIndex >= 0 && e.offsetParent !== null)
            .map(e => ({tag:e.tagName, id:e.id||null, cls:typeof e.className==='string'?e.className:null,
                        name:(e.getAttribute('aria-label')||e.innerText||'').replace(/\\s+/g,' ').trim().slice(0,50)}))""")
        pg.evaluate('window.scrollTo(0,0)')
        pg.wait_for_timeout(200)
        stops = []
        seen = 0
        for _ in range(80):
            pg.keyboard.press('Tab')
            pg.wait_for_timeout(40)
            d = pg.evaluate(DESCRIBE_ACTIVE)
            if d is None:
                break
            d['page'] = pg.evaluate('location.hash')
            stops.append(d)
            if d['tag'] == 'BODY':
                seen += 1
                if seen >= 2:
                    break
        ctx.close()

        # ---------------- B. focus after re-render ----------------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        pg = ctx.new_page()
        desk(pg)
        restoration = {}
        # 1) keyboard-activate the ↑ on slot 3 (item 红票) via Enter
        pg.locator('#slots .slot[data-index="2"] [data-act="up"]').focus()
        before = pg.evaluate(DESCRIBE_ACTIVE)
        pg.keyboard.press('Enter')
        pg.wait_for_timeout(250)
        restoration['up_keyboard_enter'] = {
            'before': before,
            'after': pg.evaluate(DESCRIBE_ACTIVE),
            'order': pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())"),
        }
        # 2) pick (select) via keyboard Enter -> does focus survive drawSlots()?
        pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').focus()
        before = pg.evaluate(DESCRIBE_ACTIVE)
        pg.keyboard.press('Enter')
        pg.wait_for_timeout(250)
        restoration['pick_select'] = {
            'before': before,
            'after': pg.evaluate(DESCRIBE_ACTIVE),
            'selected': pg.evaluate("document.querySelector('.slot[data-selected=\"true\"]')?.dataset.index ?? null"),
        }
        # 3) pick a second slot -> swap; focus?
        pg.locator('#slots .slot[data-index="2"] [data-act="pick"]').focus()
        pg.keyboard.press('Enter')
        pg.wait_for_timeout(250)
        restoration['pick_swap'] = {
            'after': pg.evaluate(DESCRIBE_ACTIVE),
            'order': pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())"),
        }
        # 4) undo
        pg.locator('#btn-undo').focus()
        pg.keyboard.press('Enter')
        pg.wait_for_timeout(250)
        restoration['undo'] = {'after': pg.evaluate(DESCRIBE_ACTIVE)}
        # 5) wrong submit
        pg.locator('#btn-submit').focus()
        pg.keyboard.press('Enter')
        pg.wait_for_timeout(350)
        restoration['wrong_submit'] = {
            'after': pg.evaluate(DESCRIBE_ACTIVE),
            'msgShown': pg.evaluate("document.querySelector('#message').dataset.show"),
            'msgText': pg.evaluate("document.querySelector('#message').innerText.slice(0,120)"),
        }
        # 6) success -> verdict (fresh desk so prior manipulations don't skew the order)
        pg.evaluate("localStorage.clear()")
        desk(pg)

        def order_now():
            return pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())")

        def move_item_to(name, target):
            """Adjacent-swap `name` to index `target` using only ↑/↓ buttons."""
            for _ in range(12):
                cur = order_now()
                i = cur.index(name)
                if i == target:
                    return
                act = 'up' if i > target else 'down'
                pg.locator(f'#slots .slot[data-index="{i}"] [data-act="{act}"]').click()
                pg.wait_for_timeout(140)

        for pos, name in enumerate(['红票', '蓝票', '黄票', '绿票']):
            move_item_to(name, pos)
        pg.wait_for_timeout(150)
        order = pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())")
        pg.locator('#btn-submit').focus()
        pg.keyboard.press('Enter')
        pg.wait_for_selector('.verdict', timeout=15000)
        pg.wait_for_timeout(700)
        restoration['verdict'] = {
            'order_before_submit': order,
            'after': pg.evaluate(DESCRIBE_ACTIVE),
            'verdictTitleFocusable': pg.evaluate("document.querySelector('#verdict-title')?.tabIndex"),
            'h1count': pg.evaluate("document.querySelectorAll('h1').length"),
            'caseTitleExists': pg.evaluate("!!document.getElementById('case-title')"),
            'viewCaseLabelledby': pg.evaluate("document.querySelector('#view-case').getAttribute('aria-labelledby')"),
        }
        # 7) entering the case from cabinet: where does focus land?
        pg.goto(BASE + '#/cabinet', wait_until='domcontentloaded')
        pg.wait_for_selector('.case-card')
        pg.wait_for_timeout(300)
        link = pg.locator('.case-card a.case-card__cta').first
        link.focus()
        link.press('Enter')
        pg.wait_for_selector('.desk', timeout=20000)
        pg.wait_for_timeout(600)
        restoration['enter_case_from_cabinet'] = {'after': pg.evaluate(DESCRIBE_ACTIVE)}
        ctx.close()

        # ---------------- C. screen reader semantics ----------------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        pg = ctx.new_page()
        desk(pg)
        sem = pg.evaluate("""() => {
          const cards = [...document.querySelectorAll('.ev-card')].map(card => {
            const btn = card.querySelector('.ev-card__summary');
            const body = card.querySelector('.ev-card__body');
            return {
              evId: card.dataset.evId,
              buttonId: btn.id,
              expanded: btn.getAttribute('aria-expanded'),
              controls: btn.getAttribute('aria-controls'),
              controlsExists: !!(btn.getAttribute('aria-controls') && document.getElementById(btn.getAttribute('aria-controls'))),
              bodyHidden: body.hidden,
              ariaLabel: btn.getAttribute('aria-label'),
              textName: btn.innerText.replace(/\\s+/g,' ').trim(),
              tag: btn.tagName,
            };
          });
          const slots = [...document.querySelectorAll('#slots .slot')].map(li => ({
            index: li.dataset.index,
            slotLabel: li.querySelector('.slot__label').textContent,
            item: li.querySelector('.slot__item').textContent,
            liRole: li.getAttribute('role'),
            liTabIndex: li.tabIndex,
            draggable: li.getAttribute('draggable'),
            buttons: [...li.querySelectorAll('button')].map(x => ({
              act: x.dataset.act, ariaLabel: x.getAttribute('aria-label'),
              pressed: x.getAttribute('aria-pressed'), disabled: x.disabled,
              accessibleText: x.getAttribute('aria-label') || x.innerText,
            })),
          }));
          const allLabels = [...document.querySelectorAll('#slots button')].map(b => b.getAttribute('aria-label'));
          return {
            cards, slots,
            duplicateLabels: allLabels.filter((x,i) => allLabels.indexOf(x) !== i),
            labelCount: allLabels.length,
            listRole: document.querySelector('#slots').getAttribute('role') || document.querySelector('#slots').tagName,
            listLabel: document.querySelector('#slots').getAttribute('aria-label'),
            hintsRole: document.querySelector('#hints').getAttribute('role'),
            hintsLabel: document.querySelector('#hints').getAttribute('aria-label'),
          };
        }""")
        # selection state changes the swap-target labels?
        pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        pg.wait_for_timeout(250)
        sem['after_select_labels'] = pg.evaluate(
            "[...document.querySelectorAll('#slots button')].map(b=>b.getAttribute('aria-label'))")
        sem['after_select_pressed'] = pg.evaluate(
            "[...document.querySelectorAll('#slots [data-act=pick]')].map(b=>b.getAttribute('aria-pressed'))")
        ctx.close()

        # ---------------- D. live regions ----------------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        pg = ctx.new_page()
        attempts = []
        pg.expose_function('__note', lambda t: attempts.append(t))
        desk(pg)
        live = pg.evaluate("""() => {
          const msg = document.querySelector('#message');
          const toast = document.querySelector('#toast');
          const status = document.querySelector('#status-text');
          return {
            message: {role: msg.getAttribute('role'), ariaLive: msg.getAttribute('aria-live'),
                      ariaAtomic: msg.getAttribute('aria-atomic'), display: getComputedStyle(msg).display,
                      inA11yTree: msg.checkVisibility?.() ?? null},
            toast: {role: toast.getAttribute('role'), ariaLive: toast.getAttribute('aria-live'),
                    display: getComputedStyle(toast).display, opacity: getComputedStyle(toast).opacity,
                    text: toast.innerText, dataShow: toast.dataset.show},
            statusText: {role: status.getAttribute('role'), ariaLive: status.getAttribute('aria-live')},
            liveRegionCount: [...document.querySelectorAll('[aria-live],[role=status],[role=alert]')]
              .map(e => ({tag:e.tagName, id:e.id, cls:typeof e.className==='string'?e.className:null,
                          role:e.getAttribute('role'), live:e.getAttribute('aria-live')})),
          };
        }""")
        # wrong submit: count mutation events that would be announced
        pg.evaluate("""() => {
          window.__mut = [];
          const mo = new MutationObserver(muts => {
            for (const m of muts) {
              const el = m.target.nodeType === 3 ? m.target.parentElement : m.target;
              if (!el) continue;
              const live = el.closest('[aria-live],[role=status]');
              if (live) window.__mut.push({id: live.id, n: m.type});
            }
          });
          mo.observe(document.body, {subtree:true, childList:true, characterData:true, attributes:true});
        }""")
        pg.locator('#btn-submit').click()
        pg.wait_for_timeout(900)
        live['wrong_submit_mutations'] = pg.evaluate('window.__mut')
        live['wrong_submit_message_text'] = pg.evaluate("document.querySelector('#message').innerText")
        # hint: is the hint text itself inside a live region?
        pg.evaluate('window.__mut = []')
        pg.locator('#btn-hint').click()
        pg.wait_for_timeout(700)
        live['hint_mutations'] = pg.evaluate('window.__mut')
        live['hint_texts'] = pg.evaluate("[...document.querySelectorAll('.hint-card')].map(x=>x.innerText)")
        live['hint_button_label'] = pg.evaluate("document.querySelector('#btn-hint').innerText")
        live['hints_live'] = pg.evaluate("document.querySelector('#hints').getAttribute('aria-live')")
        live['message_after_hint'] = pg.evaluate("document.querySelector('#message').innerText")
        # toast stale text after hide
        pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        pg.wait_for_timeout(300)
        live['toast_after_pick'] = pg.evaluate("""() => {const t=document.querySelector('#toast');
            return {text:t.innerText, dataShow:t.dataset.show, opacity:getComputedStyle(t).opacity, display:getComputedStyle(t).display};}""")
        pg.wait_for_timeout(3000)
        live['toast_after_timeout'] = pg.evaluate("""() => {const t=document.querySelector('#toast');
            return {text:t.innerText, dataShow:t.dataset.show, opacity:getComputedStyle(t).opacity,
                    display:getComputedStyle(t).display, inTree: t.checkVisibility?.()};}""")
        ctx.close()

        # ---------------- E. reset dialog behaviour ----------------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        pg = ctx.new_page()
        desk(pg)
        pg.locator('#btn-reset').focus()
        pg.keyboard.press('Enter')
        pg.wait_for_selector('#confirm-dialog[open]', timeout=10000)
        pg.wait_for_timeout(300)
        dlg = pg.evaluate("""() => {
          const d = document.querySelector('#confirm-dialog');
          return {open: d.open, modal: d.matches(':modal'),
                  activeInDialog: d.contains(document.activeElement),
                  active: document.activeElement.tagName + '#' + (document.activeElement.id||document.activeElement.dataset.confirm),
                  labelledby: d.getAttribute('aria-labelledby'),
                  labelText: document.getElementById(d.getAttribute('aria-labelledby'))?.innerText,
                  describedby: d.getAttribute('aria-describedby'),
                  role: d.getAttribute('role')};
        }""")
        # tab cycle inside dialog
        cycle = []
        for _ in range(6):
            pg.keyboard.press('Tab')
            pg.wait_for_timeout(60)
            cycle.append(pg.evaluate("""() => {const a=document.activeElement;
                return {tag:a.tagName, id:a.id||null, confirm:a.dataset?.confirm||null,
                        inDialog: document.querySelector('#confirm-dialog').contains(a),
                        name:(a.getAttribute('aria-label')||a.innerText||'').trim().slice(0,20)};}"""))
        # escape closes and restores focus to the invoking button
        pg.keyboard.press('Escape')
        pg.wait_for_timeout(300)
        dlg['after_escape'] = pg.evaluate("""() => {const a=document.activeElement;
            return {tag:a.tagName, id:a.id, open:document.querySelector('#confirm-dialog').open};}""")
        dlg['tab_cycle'] = cycle
        ctx.close()

        # ---------------- F. touch targets @390 ----------------
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='zh-CN',
                            is_mobile=True, has_touch=True, device_scale_factor=2)
        pg = ctx.new_page()
        desk(pg)
        targets = pg.evaluate("""() => {
          const sel = 'a[href],button,[role=button],input,select,textarea,summary,[tabindex]:not([tabindex="-1"])';
          const out = [];
          for (const e of document.querySelectorAll(sel)) {
            if (e.offsetParent === null) continue;
            const cs = getComputedStyle(e);
            if (cs.visibility === 'hidden' || cs.display === 'none') continue;
            const r = e.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            out.push({tag:e.tagName, id:e.id||null, cls:typeof e.className==='string'?e.className:null,
                      name:(e.getAttribute('aria-label')||e.innerText||'').replace(/\\s+/g,' ').trim().slice(0,40),
                      w:+r.width.toFixed(1), h:+r.height.toFixed(1),
                      under44: r.width < 44 || r.height < 44,
                      under24: r.width < 24 || r.height < 24});
          }
          return {all: out, pageWidth: document.documentElement.clientWidth,
                  scrollWidth: document.documentElement.scrollWidth,
                  bodyScrollWidth: document.body.scrollWidth};
        }""")
        targets['manual_page'] = None
        pg.goto(BASE + '#/manual', wait_until='domcontentloaded')
        pg.wait_for_selector('#view-manual[data-active="true"]')
        pg.wait_for_timeout(500)
        targets['manual_page'] = pg.evaluate("""() => {
          const out = [];
          for (const e of document.querySelectorAll('a[href],button,[role=button]')) {
            if (e.offsetParent === null) continue;
            const r = e.getBoundingClientRect();
            if (!r.width || !r.height) continue;
            out.push({tag:e.tagName, id:e.id||null, cls:typeof e.className==='string'?e.className:null,
                      name:(e.getAttribute('aria-label')||e.innerText||'').replace(/\\s+/g,' ').trim().slice(0,40),
                      w:+r.width.toFixed(1), h:+r.height.toFixed(1), under44: r.width<44||r.height<44});
          }
          return out;
        }""")
        ctx.close()
        b.close()

    save('focus_order', {'stops': stops, 'dom_focusables': dom_focusables})
    save('focus_restoration', restoration)
    save('sr_semantics', sem)
    save('live_regions', live)
    save('dialog', dlg)
    save('targets', targets)
    (HERE / 'manual-raw.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
