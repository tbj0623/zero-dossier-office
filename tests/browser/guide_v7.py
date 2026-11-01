#!/usr/bin/env python3
"""V7 first-case contextual guide: actions are earned, never auto-solved."""
import sys
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8140'
if '--base' in sys.argv: BASE=sys.argv[sys.argv.index('--base')+1]
n=0
def check(x,label):
 global n
 assert x,label
 n+=1
 print('[PASS]',label,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in (390,1280):
  ctx=browser.new_context(viewport={'width':width,'height':850},reduced_motion='reduce')
  page=ctx.new_page()
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/#/case/NA-001',wait_until='networkidle')
  page.wait_for_selector('#slots .slot')
  guide=page.locator('#field-guide')
  check(guide.is_visible(),f'{width}px guide initially visible')
  check(guide.locator('[data-guide-step]').count()==3,f'{width}px three actions')
  check(guide.locator('[data-done="true"]').count()==0,f'{width}px no faked progress')
  guide.locator('[data-guide-jump="read"]').click()
  check(page.evaluate('document.activeElement.id')=='ev-heading',f'{width}px evidence jump focuses')
  page.locator('.ev-card__summary').nth(1).click()
  check(guide.locator('[data-guide-step="read"]').get_attribute('data-done')=='true',
    f'{width}px reading evidence earns step')
  page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
  check(guide.locator('[data-guide-step="moved"]').get_attribute('data-done')=='true',
    f'{width}px real move earns step')
  page.locator('#btn-submit').click()
  check(guide.locator('[data-guide-step="submitted"]').get_attribute('data-done')=='true',
    f'{width}px real check earns step')
  check('3' in page.locator('#guide-progress').inner_text() or
        '操作' in page.locator('#guide-progress').inner_text(),
        f'{width}px progress complete')
  page.reload(wait_until='networkidle')
  check(page.locator('#field-guide [data-done="true"]').count()==3,
        f'{width}px guide progress survives reload')
  guide=page.locator('#field-guide')
  guide.locator('[data-guide-dismiss]').click()
  check(page.locator('#field-guide').count()==0,f'{width}px guide can be dismissed')
  page.reload(wait_until='networkidle')
  check(page.locator('#field-guide').count()==0,f'{width}px dismissal persists')
  page.goto(BASE+'/#/case/NA-002',wait_until='networkidle')
  check(page.locator('#field-guide').count()==0,f'{width}px no forced guide on later cases')
  check(not errors,f'{width}px no JS errors')
  ctx.close()
 en=browser.new_page(viewport={'width':390,'height':844})
 en.goto(BASE+'/?lang=en#/case/NA-001',wait_until='networkidle')
 check('investigator' in en.locator('#field-guide').inner_text().lower(),
   'English guide text translated')
 check(en.locator('#field-guide [data-guide-jump]').count()==3,
       'English guide actions present')
 check(en.evaluate('document.documentElement.scrollWidth <= innerWidth'),
       'English mobile no horizontal scroll')
 en.close()
 browser.close()
print('V7 first-case guide:',n,'/',n,'PASS')
