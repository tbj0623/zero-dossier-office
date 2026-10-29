from playwright.sync_api import sync_playwright
URL = 'https://tbj0623.github.io/zero-dossier-office/'
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1440, 'height': 900})
    pg.goto(URL + '#/case/NA-001', wait_until='domcontentloaded')
    pg.wait_for_selector('.desk')
    pg.keyboard.press('Tab')
    print(pg.evaluate("""() => {
      const a = document.activeElement;
      const cs = getComputedStyle(a);
      const r = a.getBoundingClientRect();
      return {tag:a.tagName, cls:a.className, top:cs.top, outline:cs.outline, outlineWidth:cs.outlineWidth,
              rect:{x:r.x,y:r.y,w:r.width,h:r.height}, matchesFV: a.matches(':focus-visible'),
              scrollY: window.scrollY, mainFocus: document.activeElement === a};
    }"""))
    print('--- skip link focus via JS focus()')
    print(pg.evaluate("""() => { const a=document.querySelector('.skip-link'); a.focus(); const cs=getComputedStyle(a); const r=a.getBoundingClientRect();
      return {top:cs.top, y:r.y, outline:cs.outline, fv:a.matches(':focus-visible')}; }"""))
    print('--- focus ring of a slot button')
    print(pg.evaluate("""() => { const btns=[...document.querySelectorAll('.icon-btn')].filter(b=>!b.disabled); btns[0].focus();
      const cs=getComputedStyle(btns[0]); return {outline:cs.outline, ow:cs.outlineWidth, os:cs.outlineOffset, boxShadow:cs.boxShadow, bg:cs.backgroundColor, border:cs.borderColor}; }"""))
    print('--- focus ring of button after keyboard (focus-visible)')
    pg.focus('#btn-submit'); pg.keyboard.press('Tab')
    print(pg.evaluate("""() => { const a=document.activeElement; const cs=getComputedStyle(a); return {cls:a.className, tag:a.tagName, outline:cs.outline, ow:cs.outlineWidth, fv:a.matches(':focus-visible')}; }"""))
    b.close()
