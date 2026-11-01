#!/usr/bin/env python3
"""V3 玩家体验专项回归：存档、撤销/重做、续玩、双语错误反馈、导航安全。"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from e2e import fill_order

BASE = 'http://127.0.0.1:8140'
if '--base' in sys.argv:
    BASE = sys.argv[sys.argv.index('--base') + 1]
count = 0


def check(ok, name):
    global count
    assert ok, f'FAIL: {name}'
    count += 1
    print(f'[PASS] {name}', flush=True)


def order(page):
    return page.eval_on_selector_all('#slots .slot__item', 'xs=>xs.map(x=>x.textContent)')


def move_down(page, index=0):
    page.locator(f'#slots .slot[data-index="{index}"] [data-act="down"]').click()


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    page.goto(BASE + '/', wait_until='networkidle')
    check(page.locator('#cta-first').get_attribute('href') == '#/case/NA-001', '新访客主 CTA 保持第一案')

    page.goto(BASE + '/#/case/NA-002', wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    before = order(page)
    move_down(page)
    after = order(page)
    check(after != before and page.locator('#btn-undo').is_enabled(), '移动后生成撤销历史')
    page.locator('#btn-undo').click()
    check(order(page) == before and page.locator('#btn-redo').is_enabled(), '撤销操作与重做按钮')
    page.reload(wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    check(order(page) == before and page.locator('#btn-redo').is_enabled(), '刷新后恢复重做栈')
    page.locator('#btn-redo').click()
    check(order(page) == after, '刷新后重做成功')
    page.keyboard.press('Control+z')
    check(order(page) == before, 'Ctrl+Z 键盘撤销')
    page.keyboard.press('Control+Shift+z')
    check(order(page) == after, 'Ctrl+Shift+Z 键盘重做')
    page.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
    page.locator('#slots .slot[data-index="1"] [data-act="pick"]').click()
    check(page.locator('#slots .slot[data-selected="true"]').count() == 0, '交换后不残留选中高亮')

    page.goto(BASE + '/', wait_until='networkidle')
    check(page.locator('#cta-first').get_attribute('href') == '#/case/NA-002', '首页优先续玩最近未结案档案')
    page.goto(BASE + '/#/cabinet', wait_until='networkidle')
    check(page.locator('.case-card__status--inprogress').count() >= 1, '档案柜显示整理中状态')

    page.goto(BASE + '/?lang=en#/case/NA-003', wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    page.locator('#btn-submit').click()
    feedback = page.locator('#message').inner_text() + page.locator('#status-text').inner_text()
    check(not re.search(r'[\u4e00-\u9fff]', feedback), '英文错误反馈无中文残留')
    check(page.locator('#btn-redo').count() == 1, '英文版也有重做按钮')
    page.locator('#btn-hint').click()
    check(not re.search(r'[\u4e00-\u9fff]', page.locator('#message').inner_text()), '英文提示反馈无中文残留')

    # 损坏存档的提示数与历史必须被限制。
    page.goto(BASE + '/#/cabinet', wait_until='networkidle')
    page.evaluate('''() => localStorage.setItem('zd:v1:order:NA-004', JSON.stringify({
      order: ['铜铃','值班簿','玻璃罩','旧透镜','海图'],
      hintIndex: 999, history: [['nope']], redo: [['bad']], attempts: 999999, at: -123
    }))''')
    page.goto(BASE + '/#/case/NA-004', wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    check(page.locator('.hint-card').count() <= 3, '损坏提示计数自动裁剪到 3')
    check(page.locator('#btn-undo').is_disabled() and page.locator('#btn-redo').is_disabled(), '损坏历史被过滤而非执行')

    # 逻辑正确但主存档错误，返回安全初始状态。
    page.goto(BASE + '/#/cabinet', wait_until='networkidle')
    page.evaluate("""() => localStorage.setItem('zd:v1:order:NA-005', JSON.stringify({order:['xx','xx'],hintIndex:999}))""")
    page.goto(BASE + '/#/case/NA-005', wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    check(page.locator('#slots .slot').count() == 5 and not page.locator('#btn-undo').is_enabled(),
          '非法排列安全重建，不白屏')
    # 结案页有延迟渲染，提交后立即离开时不能把旧结案写回调查桌。
    page.goto(BASE + '/?lang=zh#/case/NA-001', wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    author = Path(__file__).resolve().parents[2] / 'cases' / 'author' / 'NA-001.json'
    target = json.loads(author.read_text(encoding='utf-8'))['expected_solution']
    fill_order(page, target)
    page.locator('#btn-submit').click()
    page.evaluate("location.hash = '#/cabinet'")
    page.wait_for_timeout(700)
    check(page.locator('#view-cabinet').get_attribute('data-active') == 'true'
          and page.locator('#case-root .verdict').count() == 0,
          '离开后延迟结案回调不能污染下一页面')

    # 重玩必须重新绑定监听器，避免多次打开/结案后单次点击移动两格。
    page.goto(BASE + '/?lang=zh#/case/NA-001', wait_until='networkidle')
    page.wait_for_selector('#slots .slot')
    fill_order(page, target)
    page.locator('#btn-submit').click()
    page.wait_for_selector('.verdict', timeout=8000)
    page.locator('#btn-replay').click()
    page.locator('#confirm-dialog [data-confirm="ok"]').click()
    page.wait_for_selector('#slots .slot')
    again = order(page)
    move_down(page)
    check(order(page) == [again[1], again[0], *again[2:]], '重玩后一次点击只移动一步')
    browser.close()

print(f'V3 UX regression: {count}/{count} PASS')
