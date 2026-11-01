#!/usr/bin/env python3
"""V5 language + destructive-action regression: real Chromium, no private services."""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from e2e import fill_order

BASE = 'http://127.0.0.1:8140'
if '--base' in sys.argv:
    BASE = sys.argv[sys.argv.index('--base') + 1]
n = 0

def check(value, label):
    global n
    assert value, label
    n += 1
    print(f'[PASS] {label}', flush=True)

def english(*texts):
    return all(not re.search(r'[\u4e00-\u9fff]',s) for s in texts)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':390,'height':844}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE+'/?lang=en#/case/NA-001',wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    check(page.locator('html').get_attribute('lang') == 'en', 'English case ready')
    nav = page.locator('#nav-toggle')
    check(nav.get_attribute('aria-label') == 'Open navigation menu', 'Initial mobile menu aria in English')
    nav.click()
    check(nav.get_attribute('aria-label') == 'Close navigation menu', 'Expanded mobile menu aria in English')
    nav.click()

    page.locator('#btn-reset').click()
    dialog = page.locator('#confirm-dialog')
    check(dialog.is_visible(), 'Reset dialog opens')
    def check_dialog(prefix):
        title=page.locator('#confirm-title').inner_text()
        body=page.locator('#confirm-body').inner_text()
        ok=dialog.locator('[data-confirm="ok"]').inner_text()
        cancel=dialog.locator('[data-confirm="cancel"]').inner_text()
        check(english(title,body,ok,cancel), f'{prefix}: all modal texts in English')
    check_dialog('Reset')
    dialog.locator('[data-confirm="cancel"]').click()
    check(not dialog.is_visible(), 'Cancel closes modal without mutation')
    page.locator('#btn-reset').click()
    dialog.locator('[data-confirm="ok"]').click()
    check('reset' in page.locator('#toast').inner_text().lower(), 'Reset confirmation has English toast')

    author=Path(__file__).resolve().parents[2] / 'cases' / 'author' / 'NA-001.json'
    pack=__import__('json').loads((author.parents[2] / 'site' / 'i18n' / 'en.json').read_text(encoding='utf-8'))
    glossary=pack['_meta']['glossary']
    correct_ids=__import__('json').loads(author.read_text(encoding='utf-8'))['expected_solution']
    correct=[glossary[item] if isinstance(glossary[item],str) else glossary[item]['en'] for item in correct_ids]
    fill_order(page,correct)
    page.locator('#btn-submit').click()
    page.wait_for_selector('.verdict',timeout=12000)
    page.locator('#btn-replay').click()
    check_dialog('Replay')
    dialog.locator('[data-confirm="cancel"]').click()

    page.goto(BASE+'/?lang=en#/manual',wait_until='networkidle')
    page.evaluate("""() => {
      localStorage.setItem('zd:v1:briefing_dismissed','true');
      localStorage.setItem('other-site-setting','retain');
    }""")
    page.locator('#clear-progress').click()
    check_dialog('Clear progress')
    dialog.locator('[data-confirm="cancel"]').click()
    check(page.locator('#clear-progress').is_visible(),'Cancel clear keeps current page')
    page.locator('#clear-progress').click()
    dialog.locator('[data-confirm="ok"]').click()
    check('cleared' in page.locator('#toast').inner_text().lower(),
          'Clear progress message in English')
    check(page.evaluate("""() => localStorage.getItem('zd:v1:progress') === null
      && !Object.keys(localStorage).some(k=>k.startsWith('zd:v1:order:'))"""),
      'All game progress keys removed')
    check(page.evaluate("""() => localStorage.getItem('zd:v1:lang') === 'en'
      && localStorage.getItem('zd:v1:briefing_dismissed') === 'true'
      && localStorage.getItem('other-site-setting') === 'retain'"""),
      'Language, presentation preference and unrelated storage preserved')
    page.goto(BASE+'/#/',wait_until='networkidle')
    check(page.locator('html').get_attribute('lang') == 'en',
          'After reload English preference survives clearing progress')
    check(page.locator('#cta-first').get_attribute('href') == '#/case/NA-001',
          'Clearing all progress also resets home resume target')
    page.goto(BASE+'/?lang=en#/case/does-not-exist',wait_until='networkidle')
    check(english(page.locator('#toast').inner_text()), 'Invalid route toast translated')
    check(not errors, f'No browser page errors: {errors}')
    page.close()

    # Controlled 404 for an approved case tests customer-facing failure path
    broken=browser.new_page()
    broken.route('**/cases/NA-004.json',lambda route: route.fulfill(status=404,body='Missing'))
    broken.goto(BASE+'/?lang=en#/case/NA-004',wait_until='networkidle')
    check(broken.locator('.empty-state').count()==1, 'Missing approved case renders recovery state')
    check(english(broken.locator('.empty-state').inner_text()), 'English error recovery state has no Chinese')
    check(broken.locator('.empty-state a[href="#/cabinet"]').is_visible(), 'Recovery includes case cabinet link')
    broken.close()
    browser.close()

print(f'V5 language & recovery: {n}/{n} PASS')
