"""Final targeted checks: skip link, Esc semantics, mobile nav, footer/crumb targets, verdict focus."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- skip link ----
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk')
    pg.wait_for_timeout(500)
    pg.keyboard.press('Tab')
    samples = []
    for t in (0, 100, 300, 600):
        if t:
            pg.wait_for_timeout(t)
        samples.append(pg.evaluate("""() => { const a = document.querySelector('.skip-link');
            const r = a.getBoundingClientRect(); const cs = getComputedStyle(a);
            return {top: cs.top, y: Math.round(r.y), h: Math.round(r.height),
                    visibleFraction: +((Math.min(r.bottom, innerHeight) - Math.max(r.top, 0)) / r.height).toFixed(2)}; }"""))
    OUT['skip_link'] = samples
    # does activating it move focus to main?
    pg.keyboard.press('Enter')
    pg.wait_for_timeout(400)
    OUT['skip_link_activation'] = pg.evaluate("""() => ({activeTag: document.activeElement.tagName,
        activeId: document.activeElement.id, hash: location.hash, scrollY: Math.round(scrollY)})""")

    # ---- Esc with focus genuinely inside a slot ----
    pg.goto(BASE + '#/about', wait_until='domcontentloaded')
    pg.wait_for_timeout(150)
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk')
    pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('#slots .slot[data-index=\"1\"] [data-act=\"pick\"]').focus()")
    pg.keyboard.press('Enter')
    pg.wait_for_timeout(250)
    after_enter = pg.evaluate("""() => ({active: document.activeElement.tagName + '#' + (document.activeElement.id || ''),
        selected: document.querySelectorAll('.slot[data-selected="true"]').length,
        pickLabel: document.querySelector('.slot[data-selected="true"] [data-act=pick]')?.getAttribute('aria-label')})""")
    # now move focus back into a slot manually and press Escape (does the shortcut work at all?)
    pg.evaluate("document.querySelector('#slots .slot[data-index=\"1\"] [data-act=\"pick\"]').focus()")
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(250)
    OUT['escape'] = {
        'after_pick_enter': after_enter,
        'after_escape_with_focus_in_slot': pg.evaluate("""() => ({
            selected: document.querySelectorAll('.slot[data-selected="true"]').length,
            status: document.querySelector('#status-text').innerText,
            active: document.activeElement.tagName + '#' + (document.activeElement.id || ''),
            activeName: document.activeElement.getAttribute?.('aria-label') || ''})"""),
    }
    # and the realistic path: keyboard user selects, focus is on BODY, presses Escape
    pg.goto(BASE + '#/about', wait_until='domcontentloaded'); pg.wait_for_timeout(150)
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('#slots .slot[data-index=\"1\"] [data-act=\"pick\"]').focus()")
    pg.keyboard.press('Enter'); pg.wait_for_timeout(250)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    OUT['escape_after_focus_loss'] = pg.evaluate("""() => ({
        selected: document.querySelectorAll('.slot[data-selected="true"]').length,
        active: document.activeElement.tagName,
        status: document.querySelector('#status-text').innerText})""")
    ctx.close()

    # ---- mobile nav ----
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='zh-CN',
                        is_mobile=True, has_touch=True, device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(600)
    pg.click('#nav-toggle')
    pg.wait_for_timeout(350)
    nav = pg.evaluate("""() => {
      const t = document.querySelector('#nav-toggle'); const n = document.querySelector('#site-nav');
      const links = [...n.querySelectorAll('a')].map(a => { const r = a.getBoundingClientRect();
        return {text: a.innerText, w: +r.width.toFixed(1), h: +r.height.toFixed(1), visible: a.offsetParent !== null}; });
      return {expanded: t.getAttribute('aria-expanded'), label: t.getAttribute('aria-label'),
              controls: t.getAttribute('aria-controls'), controlsExists: !!document.getElementById(t.getAttribute('aria-controls')),
              navOpen: n.dataset.open, display: getComputedStyle(n).display, links,
              activeIsToggle: document.activeElement === t,
              activeTag: document.activeElement.tagName};
    }""")
    # Tab from toggle into the menu
    pg.keyboard.press('Tab'); pg.wait_for_timeout(150)
    nav['after_tab'] = pg.evaluate("""() => ({tag: document.activeElement.tagName,
        text: (document.activeElement.innerText||'').trim().slice(0,20),
        inNav: !!document.activeElement.closest('#site-nav')})""")
    # does Escape close the menu?
    pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    nav['after_escape'] = pg.evaluate("""() => ({navOpen: document.querySelector('#site-nav').dataset.open,
        expanded: document.querySelector('#nav-toggle').getAttribute('aria-expanded'),
        display: getComputedStyle(document.querySelector('#site-nav')).display})""")
    # tap a menu link -> does it close and move focus?
    if not pg.evaluate("document.querySelector('#site-nav').dataset.open === 'true'"):
        pg.click('#nav-toggle'); pg.wait_for_timeout(300)
    pg.click('#site-nav a[href="#/cabinet"]'); pg.wait_for_timeout(700)
    nav['after_nav'] = pg.evaluate("""() => ({navOpen: document.querySelector('#site-nav').dataset.open,
        display: getComputedStyle(document.querySelector('#site-nav')).display,
        active: document.activeElement.tagName, hash: location.hash})""")
    OUT['mobile_nav'] = nav

    # ---- mobile: crumbs / footer link sizes ----
    pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk'); pg.wait_for_timeout(500)
    OUT['small_targets_mobile'] = pg.evaluate("""() => {
      const out = [];
      for (const e of document.querySelectorAll('a[href]')) {
        if (e.offsetParent === null) continue;
        const r = e.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        if (r.width < 44 || r.height < 44) {
          out.push({name: (e.innerText||'').replace(/\\s+/g,' ').trim().slice(0,24),
                    area: e.closest('.site-footer') ? 'footer' : e.closest('.desk-crumbs') ? 'crumbs' : 'other',
                    w: +r.width.toFixed(1), h: +r.height.toFixed(1)});
        }
      }
      return out;
    }""")
    # vertical gap between stacked footer links (centre-to-centre) — spacing exception check
    OUT['footer_link_spacing'] = pg.evaluate("""() => {
      const links = [...document.querySelectorAll('.site-footer a')];
      return links.map(a => { const r = a.getBoundingClientRect();
        return {text: a.innerText, h: +r.height.toFixed(1), y: +r.y.toFixed(1)}; });
    }""")
    OUT['crumb_spacing'] = pg.evaluate("""() => {
      const a = document.querySelector('.desk-crumbs a'); const r = a.getBoundingClientRect();
      return {h: +r.height.toFixed(1), y: +r.y.toFixed(1)}; }""")
    ctx.close()
    b.close()

print(json.dumps(OUT, ensure_ascii=False, indent=1)[:7000])
(HERE / 'final-checks.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=1), encoding='utf-8')
