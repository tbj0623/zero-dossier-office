#!/usr/bin/env python3
"""V6 real-browser verification of user-owned deduction notes. No author answers in UI."""
from playwright.sync_api import sync_playwright
import sys

BASE = 'http://127.0.0.1:8140'
if '--base' in sys.argv: BASE = sys.argv[sys.argv.index('--base')+1]
checks=0
def check(x, description):
    global checks
    assert x, 'FAIL '+description
    checks+=1
    print('[PASS]',description,flush=True)

def open_case(page,case_id):
    page.goto(BASE+'/#/case/'+case_id,wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    page.locator('#deduction-notebook summary').click()

with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in (320,390,1280):
        ctx=browser.new_context(viewport={'width':width,'height':850},reduced_motion='reduce')
        page=ctx.new_page()
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        open_case(page,'NA-001')
        check(page.locator('#deduction-notebook').is_visible(),f'{width}px notebook available')
        check(page.locator('.deduction-notebook__cell').count()==16,f'{width}px 4x4 grid')
        cell=page.locator('[data-note-row="0"][data-note-col="0"]')
        check(cell.inner_text()=='·',f'{width}px starts unknown')
        cell.click()
        check(cell.get_attribute('data-mark')=='1' and cell.inner_text()=='?',f'{width}px possible note')
        cell.click()
        check(cell.get_attribute('data-mark')=='2' and cell.inner_text()=='×',f'{width}px exclude note')
        cell.click()
        check(cell.get_attribute('data-mark')=='0',f'{width}px tri-state cycles')
        cell.click()
        page.locator('[data-note-row="0"][data-note-col="1"]').click()
        page.locator('[data-note-row="0"][data-note-col="1"]').click()
        check('1' in page.locator('#notes-stats').inner_text(),f'{width}px notebook stats')
        check(page.locator('#btn-submit').is_enabled(),f'{width}px notes do not block grading')
        page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
        check(page.locator('[data-note-row="0"][data-note-col="0"]').get_attribute('data-mark')=='1',
              f'{width}px grid independent of arrangement')
        page.reload(wait_until='networkidle')
        page.locator('#deduction-notebook summary').click()
        check(page.locator('[data-note-row="0"][data-note-col="0"]').get_attribute('data-mark')=='1'
              and page.locator('[data-note-row="0"][data-note-col="1"]').get_attribute('data-mark')=='2',
              f'{width}px notebook saved across reload')
        check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),
              f'{width}px no horizontal viewport overflow')
        check(not errors,f'{width}px no JavaScript errors: {errors}')
        if width==390:
            page.locator('[data-notes-clear]').click()
            dlg=page.locator('#confirm-dialog')
            check(dlg.is_visible(), 'Clear-notes confirmation shown')
            dlg.locator('[data-confirm="cancel"]').click()
            check(page.locator('[data-note-row="0"][data-note-col="0"]').get_attribute('data-mark')=='1',
                  'Cancel retains notebook')
            page.locator('[data-notes-clear]').click()
            dlg.locator('[data-confirm="ok"]').click()
            check(page.locator('[data-note-row="0"][data-note-col="0"]').get_attribute('data-mark')=='0',
                  'Clear only note marks')
            check(page.locator('#slots .slot').count()==4,'Note clearing preserves arrangement')
            page.locator('[data-note-row="0"][data-note-col="0"]').click()
            page.locator('#btn-reset').click()
            page.locator('#confirm-dialog [data-confirm="ok"]').click()
            check(page.locator('[data-note-row="0"][data-note-col="0"]').get_attribute('data-mark')=='0',
                  'Reset case clears notebook alongside arrangement')
            open_case(page,'NA-006')
            check(page.locator('.deduction-notebook__cell').count()==36,'Six-item chapter 6x6 matrix')
            check(page.locator('#deduction-notebook summary').is_visible(),'Notebook works on final case')
            # Corrupt note data must be dropped without damaging the case or rendering.
            page.evaluate("""() => localStorage.setItem('zd:v1:order:NA-006', JSON.stringify({
               order: ['钟楼影','纸船影','玻璃影','雨幕影','灯塔影','空白底片'],
               notes: [['malicious']], hintIndex: 2
            }))""")
            page.reload(wait_until='networkidle')
            page.locator('#deduction-notebook summary').click()
            check(page.locator('.deduction-notebook__cell[data-mark="0"]').count()==36,
                  'Corrupt notebook safely discarded')
            check(page.locator('#slots .slot').count()==6,'Corrupt notebook does not break case')
        ctx.close()
    en=browser.new_page(viewport={'width':390,'height':844})
    en.goto(BASE+'/?lang=en#/case/NA-002',wait_until='networkidle')
    en.locator('#deduction-notebook summary').click()
    check('deduction' in en.locator('#deduction-notebook summary').inner_text().lower(),
          'English notebook heading')
    check(en.locator('.deduction-notebook__cell').count()==16,'English notebook grid size')
    en.locator('[data-note-row="0"][data-note-col="0"]').click()
    check('possible' in en.locator('[data-note-row="0"][data-note-col="0"]').get_attribute('aria-label').lower(),
          'English accessible tri-state label')
    en.locator('[data-notes-clear]').click()
    check('clear' in en.locator('#confirm-title').inner_text().lower(),'English clear dialog')
    en.locator('#confirm-dialog [data-confirm="cancel"]').click()
    en.close()
    browser.close()
print('V6 deduction notebook:',checks,'/',checks,'PASS')
