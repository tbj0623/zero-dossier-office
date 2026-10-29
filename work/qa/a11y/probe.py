import json
from playwright.sync_api import sync_playwright

URL = 'https://tbj0623.github.io/zero-dossier-office/'

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
    pg = ctx.new_page()
    pg.goto(URL + '#/case/NA-001', wait_until='domcontentloaded', timeout=60000)
    pg.wait_for_selector('.desk', timeout=30000)
    print('== desk head ==')
    print(pg.evaluate("document.querySelector('.desk-head__title')?.textContent"))
    print('evidence buttons:')
    print(pg.evaluate("""() => [...document.querySelectorAll('.ev-card__summary')].map(b => ({
      id: b.id, name: b.getAttribute('aria-label'), expanded: b.getAttribute('aria-expanded'),
      controls: b.getAttribute('aria-controls'), ctrlExists: !!document.getElementById(b.getAttribute('aria-controls')),
      text: b.innerText.replace(/\\n/g,' | ')
    }))"""))
    print('slots:')
    print(pg.evaluate("""() => [...document.querySelectorAll('#slots .slot')].map(li => ({
      idx: li.dataset.index, label: li.querySelector('.slot__label').textContent,
      item: li.querySelector('.slot__item').textContent,
      btns: [...li.querySelectorAll('button')].map(x=>({act:x.dataset.act, al:x.getAttribute('aria-label'), pressed:x.getAttribute('aria-pressed'), dis:x.disabled}))
    }))"""))
    print('order:', pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent)"))
    print('message attrs:', pg.evaluate("(()=>{const m=document.querySelector('#message'); return {role:m.getAttribute('role'), live:m.getAttribute('aria-live'), show:m.dataset.show, text:m.innerText}})()"))
    print('toast attrs:', pg.evaluate("(()=>{const t=document.querySelector('#toast'); return {role:t.getAttribute('role'), live:t.getAttribute('aria-live'), show:t.dataset.show, text:t.innerText, opacity:getComputedStyle(t).opacity}})()"))
    print('status text live?', pg.evaluate("(()=>{const s=document.querySelector('#status-text'); return {role:s.getAttribute('role'), live:s.getAttribute('aria-live')}})()"))
    print('dialog:', pg.evaluate("(()=>{const d=document.querySelector('#confirm-dialog'); return {open:d.open, labelledby:d.getAttribute('aria-labelledby'), modal: d.matches(':modal')}})()"))
    # focus order sample
    pg.evaluate("window.scrollTo(0,0)")
    pg.keyboard.press('Tab')
    order = []
    for i in range(30):
        info = pg.evaluate("""() => { const a=document.activeElement; if(!a) return null;
          const r=a.getBoundingClientRect();
          return {tag:a.tagName, id:a.id, cls:a.className && String(a.className), txt:(a.innerText||a.getAttribute('aria-label')||'').replace(/\\s+/g,' ').slice(0,40), x:Math.round(r.x), y:Math.round(r.y)}; }""")
        order.append(info)
        pg.keyboard.press('Tab')
    for i, o in enumerate(order):
        print(i, o)
    b.close()
