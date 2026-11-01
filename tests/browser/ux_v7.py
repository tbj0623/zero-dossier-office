#!/usr/bin/env python3
"""V7 real local backup download, hostile-file rejection, cancel and round-trip."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8140'
if '--base' in sys.argv: BASE = sys.argv[sys.argv.index('--base')+1]
count=0
def check(cond,desc):
    global count
    assert cond,desc
    count+=1
    print('[PASS]',desc,flush=True)

with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(accept_downloads=True,viewport={'width':390,'height':850},reduced_motion='reduce')
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(BASE+'/?lang=en#/case/NA-001',wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    page.locator('#deduction-notebook summary').click()
    page.locator('[data-note-row="0"][data-note-col="0"]').click()
    page.locator('[data-note-row="1"][data-note-col="2"]').click()
    page.locator('[data-note-row="1"][data-note-col="2"]').click()
    page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
    original=page.evaluate("""() => ({
      current: JSON.parse(localStorage.getItem('zd:v1:order:NA-001')),
      lang: localStorage.getItem('zd:v1:lang')
    })""")
    check(original['current']['notes'][0][0]==1 and original['current']['notes'][1][2]==2,
          'Player notes exist in saved session')
    page.goto(BASE+'/#/manual',wait_until='networkidle')
    check('offline' in page.locator('[data-i18n="vault.heading"]').inner_text().lower(),
          'English vault UI translated')
    with TemporaryDirectory() as folder:
        with page.expect_download() as download_event:
            page.locator('#vault-export').click()
        download=download_event.value
        check(download.suggested_filename.startswith('zero-dossier-backup-')
              and download.suggested_filename.endswith('.json'),'Backup downloads as JSON')
        dest=Path(folder)/'backup.json'
        download.save_as(dest)
        backup=json.loads(dest.read_text(encoding='utf-8'))
        check(backup['format']=='zero-dossier-local-backup'
              and backup['version']==1,'Backup includes version header')
        saved=backup['cases']['NA-001']['session']
        check(saved['notes'][0][0]==1 and saved['notes'][1][2]==2,'Export retains notes')
        check(saved['order']==original['current']['order'],'Export retains arrangement')

        # Corrupt backup must be rejected before any confirmation/mutation.
        page.locator('#vault-file').set_input_files({
          'name':'invalid.json','mimeType':'application/json','buffer':b'{"fake":"backup"}'})
        page.wait_for_function("""() => document.querySelector('#vault-status')?.dataset.kind === 'bad'""")
        check(page.evaluate("""() => JSON.parse(localStorage.getItem('zd:v1:order:NA-001')).notes[0][0]""")==1,
              'Invalid upload leaves original save untouched')
        check(not page.locator('#confirm-dialog').is_visible(),
              'Invalid file never asks for replacement')

        # Validate cancel and accept paths on a clean in-browser state.
        page.locator('#clear-progress').click()
        page.locator('#confirm-dialog [data-confirm="ok"]').click()
        check(page.evaluate("""() => localStorage.getItem('zd:v1:order:NA-001') === null"""),
              'Clear progress removed current case')
        page.locator('#vault-file').set_input_files(str(dest))
        page.wait_for_selector('#confirm-dialog[open]')
        check('replace' in page.locator('#confirm-title').inner_text().lower(),
              'Valid backup explains destructive replacement')
        page.locator('#confirm-dialog [data-confirm="cancel"]').click()
        check(page.evaluate("""() => localStorage.getItem('zd:v1:order:NA-001') === null"""),
              'Cancel import does not write a save')
        page.locator('#vault-file').set_input_files(str(dest))
        page.wait_for_selector('#confirm-dialog[open]')
        page.locator('#confirm-dialog [data-confirm="ok"]').click()
        page.wait_for_function("""() => document.querySelector('#vault-status')?.dataset.kind === 'ok'""")
        restored=page.evaluate("""() => JSON.parse(localStorage.getItem('zd:v1:order:NA-001'))""")
        check(restored['order']==original['current']['order']
              and restored['notes'][0][0]==1 and restored['notes'][1][2]==2,
              'Import restores arrangement and note grid')
        check(page.evaluate("""() => localStorage.getItem('zd:v1:lang')""")==original['lang'],
              'Import preserves language setting')
        page.goto(BASE+'/#/case/NA-001',wait_until='networkidle')
        page.locator('#deduction-notebook summary').click()
        check(page.locator('[data-note-row="0"][data-note-col="0"]').get_attribute('data-mark')=='1',
              'Player can resume imported notes in actual case')
        check(not errors,'No JS page errors')
    context.close()
    browser.close()

    # Firefox / WebKit also need to support Blob-based offline export.
    for engine in (p.firefox, p.webkit):
        other = engine.launch()
        ctx = other.new_context(accept_downloads=True)
        page = ctx.new_page()
        page.goto(BASE+'/#/manual',wait_until='networkidle')
        with page.expect_download() as d:
            page.locator('#vault-export').click()
        check(d.value.suggested_filename.endswith('.json'),
              f'{engine.name} offline file export')
        check(page.locator('#vault-status').get_attribute('data-kind')=='ok',
              f'{engine.name} local export succeeds')
        ctx.close()
        other.close()
print('V7 vault:',count,'/',count,'PASS')
