#!/usr/bin/env python3
"""V4 navigation and feedback regression.  No mocking: real browser, real case JSON."""
import re
import sys
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8140'
if '--base' in sys.argv:
    BASE = sys.argv[sys.argv.index('--base')+1]
tests = 0

def check(value, label):
    global tests
    assert value, f'FAIL: {label}'
    tests += 1
    print(f'[PASS] {label}', flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (320, 360, 390, 768, 980):
        page = browser.new_page(viewport={'width':width,'height':810}, reduced_motion='reduce')
        errors = []
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/#/case/NA-001',wait_until='networkidle')
        page.wait_for_selector('#slots .slot')
        go = page.locator('[data-jump="board"]')
        back = page.locator('[data-jump="evidence"]')
        check(go.is_visible() and back.is_visible(), f'{width}px mobile: evidence/board jumps visible')
        go.click()
        check(page.evaluate('document.activeElement.id')=='board-heading', f'{width}px: jump focuses board heading')
        back.click()
        check(page.evaluate('document.activeElement.id')=='ev-heading', f'{width}px: return focuses evidence heading')
        page.locator('#btn-submit').click()
        locators = page.locator('[data-open-evidence]')
        check(locators.count()>=1, f'{width}px: invalid submit has evidence links')
        ref = locators.first.get_attribute('data-open-evidence')
        locators.first.click()
        card = page.locator(f'.ev-card[data-ev-id="{ref}"]')
        check(card.get_attribute('data-open')=='true' and
              card.locator('.ev-card__summary').get_attribute('aria-expanded')=='true'
              and not card.locator('.ev-card__body').is_hidden(),
              f'{width}px: locator expands exactly matching evidence')
        check(page.evaluate('document.activeElement.id')==f'ev-btn-{ref}',
              f'{width}px: locator focuses selected evidence')
        picks = page.locator('#slots .slot [data-act="pick"]')
        picks.nth(0).click()
        picks.nth(1).click()
        check(page.evaluate('document.activeElement.getAttribute("data-act")')=='pick'
              and page.evaluate('document.activeElement.closest(".slot").dataset.index')=='1',
              f'{width}px: swap restores keyboard focus to second slot')
        check(not errors, f'{width}px: no browser errors')
        check(page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'),
              f'{width}px: no horizontal overflow')
        page.close()
    desktop = browser.new_page(viewport={'width':1280,'height':850})
    desktop.goto(BASE+'/#/case/NA-001',wait_until='networkidle')
    check(desktop.locator('[data-jump="board"]').is_hidden()
          and desktop.locator('[data-jump="evidence"]').is_hidden(),
          'desktop: mobile jump controls hidden')
    desktop.locator('#btn-submit').click()
    check(desktop.locator('[data-open-evidence]').count()>0,
          'desktop: evidence mismatch drill-down remains available')
    desktop.close()
    en = browser.new_page(viewport={'width':390,'height':844})
    en.goto(BASE+'/?lang=en#/case/NA-001',wait_until='networkidle')
    en.wait_for_selector('#slots .slot')
    check('arrangement' in en.locator('[data-jump="board"]').inner_text().lower(),
          'English: contextual jump translated')
    en.locator('#btn-submit').click()
    links=en.locator('[data-open-evidence]')
    check(links.count()>0 and not re.search(r'[\u4e00-\u9fff]',links.first.inner_text()),
          'English: evidence conflict action translated')
    en.close()
    for engine in (p.firefox, p.webkit):
        other = engine.launch()
        op = other.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
        op.goto(BASE+'/#/case/NA-001',wait_until='networkidle')
        op.wait_for_selector('#slots .slot')
        op.locator('[data-jump="board"]').click()
        check(op.evaluate('document.activeElement.id')=='board-heading',
              f'{engine.name}: section jump keyboard focus')
        op.locator('#btn-submit').click()
        op.locator('[data-open-evidence]').first.click()
        check(op.evaluate('document.activeElement.classList.contains("ev-card__summary")'),
              f'{engine.name}: evidence locator keyboard focus')
        other.close()
    browser.close()

print(f'V4 UX navigation: {tests}/{tests} PASS')
