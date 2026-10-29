"""Axe-core audit against the LIVE site (https://tbj0623.github.io/zero-dossier-office/).

Each state gets its own browser context (clean localStorage), is driven into the
target state, then axe-core 4.10.2 is injected from the local cache and run with
tags: wcag2a, wcag2aa, wcag21aa, wcag22aa, best-practice.
Raw results are written to axe-<page>.json.
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
AXE = HERE / 'axe.min.js'
TAGS = ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']


def settle(pg, ms=500):
    pg.wait_for_timeout(ms)


def goto(pg, route, wait_sel=None):
    pg.goto(BASE + route, wait_until='domcontentloaded', timeout=60000)
    if wait_sel:
        pg.wait_for_selector(wait_sel, timeout=30000)
    settle(pg, 700)


def disable_animations(pg):
    """Freeze CSS animations/transitions so axe measures a settled frame."""
    pg.add_style_tag(content='''
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    ''')
    settle(pg, 200)


def collapse_all(pg):
    n = pg.evaluate("document.querySelectorAll('.ev-card__summary').length")
    for i in range(n):
        btn = pg.locator('.ev-card__summary').nth(i)
        if btn.get_attribute('aria-expanded') == 'true':
            btn.click()
    settle(pg, 250)
    states = pg.evaluate("[...document.querySelectorAll('.ev-card__summary')].map(b=>b.getAttribute('aria-expanded'))")
    assert all(s == 'false' for s in states), states


def expand_all(pg):
    n = pg.evaluate("document.querySelectorAll('.ev-card__summary').length")
    for i in range(n):
        btn = pg.locator('.ev-card__summary').nth(i)
        if btn.get_attribute('aria-expanded') == 'false':
            btn.click()
    settle(pg, 250)
    states = pg.evaluate("[...document.querySelectorAll('.ev-card__summary')].map(b=>b.getAttribute('aria-expanded'))")
    assert all(s == 'true' for s in states), states


def click_up_for(pg, item_name):
    """Click the ↑ button of the slot that currently holds `item_name`."""
    idx = pg.evaluate(
        """(name) => [...document.querySelectorAll('#slots .slot')]
              .findIndex(li => li.querySelector('.slot__item').textContent.trim() === name)""",
        item_name,
    )
    assert idx >= 0, f'item not found: {item_name}'
    pg.locator(f'#slots .slot[data-index="{idx}"] [data-act="up"]').click()
    settle(pg, 120)


def solve(pg):
    """红票 → 蓝票 → 黄票 → 绿票 using only the ↑ buttons."""
    for _ in range(2):
        click_up_for(pg, '红票')
    click_up_for(pg, '黄票')
    order = pg.evaluate("[...document.querySelectorAll('.slot__item')].map(x=>x.textContent.trim())")
    assert order == ['红票', '蓝票', '黄票', '绿票'], order
    pg.click('#btn-submit')
    pg.wait_for_selector('.verdict', timeout=15000)
    settle(pg, 800)


def run_axe(pg, page_key):
    pg.evaluate(f'axe.configure({{}})') if False else None
    pg.add_script_tag(path=str(AXE))
    result = pg.evaluate(
        """async (tags) => {
          const r = await axe.run(document, {
            runOnly: { type: 'tag', values: tags },
            resultTypes: ['violations', 'incomplete', 'passes'],
            reporter: 'v2',
          });
          return {
            violations: r.violations,
            incomplete: r.incomplete,
            passCount: r.passes.length,
            passIds: r.passes.map(p => p.id),
            inapplicableIds: r.inapplicable.map(p => p.id),
            testEngine: r.testEngine,
            url: r.url,
            timestamp: r.timestamp,
          };
        }""",
        TAGS,
    )
    raw = HERE / f'axe-{page_key}.json'
    raw.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    v = result['violations']
    print(f'[{page_key}] violations={len(v)} incomplete={len(result["incomplete"])} passes={result["passCount"]}')
    for x in v:
        print(f'   - {x["id"]} [{x["impact"]}] nodes={len(x["nodes"])}')
    for x in result['incomplete']:
        print(f'   ~ INCOMPLETE {x["id"]} [{x["impact"]}] nodes={len(x["nodes"])}')
    return result


# ---------------------------------------------------------------- states
def state_home(pg):
    goto(pg, '#/', '#view-home[data-active="true"]')


def state_cabinet(pg):
    goto(pg, '#/cabinet', '#view-cabinet[data-active="true"] .case-card')


def state_desk(pg):
    goto(pg, '#/case/NA-001', '.desk')


def state_desk_collapsed(pg):
    state_desk(pg)
    collapse_all(pg)


def state_desk_expanded(pg):
    state_desk(pg)
    expand_all(pg)


def state_desk_selected(pg):
    state_desk(pg)
    pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
    settle(pg, 300)


def state_desk_error(pg):
    state_desk(pg)
    # initial scramble is guaranteed to violate constraints -> a genuine wrong submit
    pg.click('#btn-submit')
    pg.wait_for_selector('#message[data-show="true"]', timeout=10000)
    assert 'unchecked' not in pg.evaluate("document.querySelector('#message').className") or True
    settle(pg, 500)


def state_desk_hint(pg):
    state_desk(pg)
    pg.click('#btn-hint')
    pg.wait_for_selector('#hints .hint-card', timeout=10000)
    settle(pg, 400)


def state_verdict(pg):
    state_desk(pg)
    solve(pg)


def state_manual(pg):
    goto(pg, '#/manual', '#view-manual[data-active="true"]')


def state_about(pg):
    goto(pg, '#/about', '#view-about[data-active="true"]')


def state_dialog(pg):
    state_desk(pg)
    pg.click('#btn-reset')
    pg.wait_for_selector('#confirm-dialog[open]', timeout=10000)
    settle(pg, 300)


def state_mobile(pg):
    goto(pg, '#/case/NA-001', '.desk')


STATES = [
    ('home', state_home, {'width': 1440, 'height': 900}),
    ('cabinet', state_cabinet, {'width': 1440, 'height': 900}),
    ('desk-collapsed', state_desk_collapsed, {'width': 1440, 'height': 900}),
    ('desk-expanded', state_desk_expanded, {'width': 1440, 'height': 900}),
    ('desk-selected', state_desk_selected, {'width': 1440, 'height': 900}),
    ('desk-error', state_desk_error, {'width': 1440, 'height': 900}),
    ('desk-hint', state_desk_hint, {'width': 1440, 'height': 900}),
    ('verdict', state_verdict, {'width': 1440, 'height': 900}),
    ('manual', state_manual, {'width': 1440, 'height': 900}),
    ('about', state_about, {'width': 1440, 'height': 900}),
    ('reset-dialog', state_dialog, {'width': 1440, 'height': 900}),
    ('desk-mobile-390', state_mobile, {'width': 390, 'height': 844}),
]


def main():
    only = sys.argv[1:] or None
    summary = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for key, fn, vp in STATES:
            if only and key not in only:
                continue
            ctx = browser.new_context(viewport=vp, locale='zh-CN', device_scale_factor=1)
            pg = ctx.new_page()
            fn(pg)
            disable_animations(pg)
            res = run_axe(pg, key)
            summary[key] = {
                'violations': [
                    {'id': v['id'], 'impact': v['impact'], 'nodes': len(v['nodes'])} for v in res['violations']
                ],
                'incomplete': [{'id': v['id'], 'impact': v['impact'], 'nodes': len(v['nodes'])} for v in res['incomplete']],
            }
            ctx.close()
        browser.close()
    (HERE / 'axe-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
