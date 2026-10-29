#!/usr/bin/env python3
"""无障碍回归测试：axe-core 零违规门禁。

复用 work/qa/a11y/axe.min.js（本地缓存，不联网）。
覆盖：首页、档案柜、调查桌（折叠/展开/选中/报错/提示）、结案页、手册、关于、重置对话框、390px 手机。

用法：
  python -m http.server 8080 --directory dist &
  python tests/browser/a11y.py --base http://127.0.0.1:8080

退出码 0 = 全部页面 0 violations；1 = 有违规或有页面加载失败。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
AXE_PATH = ROOT / "work" / "qa" / "a11y" / "axe.min.js"
SHOTS = ROOT / "screenshots"
TAGS = ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa", "best-practice"]

SOLUTION = ["红票", "蓝票", "黄票", "绿票"]


def run_axe(page) -> list[dict]:
    page.wait_for_timeout(350)
    page.add_script_tag(content=AXE_PATH.read_text(encoding="utf-8"))
    return page.evaluate(
        """async (tags) => {
            const r = await axe.run(document, { runOnly: { type: 'tag', values: tags } });
            return r.violations.map(v => ({
                id: v.id, impact: v.impact, help: v.help,
                nodes: v.nodes.map(n => ({ target: n.target, html: (n.html || '').slice(0, 200) })),
            }));
        }""",
        TAGS,
    )


def arrange(page, target: list[str]) -> None:
    for want in range(len(target)):
        labels = page.eval_on_selector_all("#slots .slot__item", "e => e.map(x => x.textContent)")
        cur = labels.index(target[want])
        while cur > want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="up"]')
            cur -= 1
        while cur < want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="down"]')
            cur += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    args = ap.parse_args()

    if not AXE_PATH.exists():
        print(f"缺少 axe-core：{AXE_PATH}\n请先下载 axe.min.js 到该路径。", file=sys.stderr)
        return 1

    results: list[dict] = []
    failures = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()
        console_errors: list[str] = []
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        def check(label: str, path: str, prep=None, expect: str | None = None,
                  reset: bool = True) -> None:
            nonlocal failures
            page.goto(f"{args.base}{path}", wait_until="networkidle")
            if reset:
                # 清掉本机进度，确保每个检查都从「未归档」状态开始
                page.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
                page.reload(wait_until="networkidle")
            if prep:
                prep(page)
            if expect:
                page.wait_for_selector(expect, timeout=10000)
            violations = run_axe(page)
            ok = len(violations) == 0
            if not ok:
                failures += 1
            results.append({"page": label, "path": path, "violations": violations, "ok": ok})
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {label} — {len(violations)} violations")
            for v in violations:
                print(f"    [{v['impact']}] {v['id']}: {v['help']}")
                for n in v["nodes"][:3]:
                    print(f"        {n['target']}  {n['html'][:120]}")

        check("首页", "/", expect=".hero")
        check("档案柜", "/#/cabinet", expect="#cabinet .case-card")
        check("调查桌·折叠", "/#/case/NA-001", expect="#slots .slot")

        def expand(page):
            for b in page.query_selector_all(".ev-card__summary"):
                if b.get_attribute("aria-expanded") == "false":
                    b.click()
        check("调查桌·展开证据", "/#/case/NA-001", prep=expand, expect="#slots .slot")

        def select_slot(page):
            page.click('#slots .slot[data-index="0"] [data-act="pick"]')
        check("调查桌·选中格位", "/#/case/NA-001", prep=select_slot, expect="#slots .slot")

        def wrong_submit(page):
            page.click("#btn-submit")
            page.wait_for_selector("#message[data-show='true']")
        check("调查桌·提交报错", "/#/case/NA-001", prep=wrong_submit, expect="#slots .slot")

        def show_hint(page):
            page.click("#btn-hint")
            page.wait_for_selector(".hint-card")
        check("调查桌·显示提示", "/#/case/NA-001", prep=show_hint, expect="#slots .slot")

        def solve(page):
            arrange(page, SOLUTION)
            page.click("#btn-submit")
            page.wait_for_selector(".verdict", timeout=10000)
        check("结案页", "/#/case/NA-001", prep=solve, expect=".verdict")

        def open_dialog(page):
            # 上一检查已把 NA-001 归档，重进时显示结案页而非调查桌；
            # 先点「重新调查此案」回到可操作状态再开对话框。
            if page.query_selector(".verdict"):
                page.click("#btn-replay")
                page.wait_for_selector("dialog.confirm[open]", timeout=5000)
                page.click('[data-confirm="ok"]')
                page.wait_for_selector("#slots .slot", timeout=5000)
            page.click("#btn-reset")
            page.wait_for_selector("dialog.confirm[open]", timeout=5000)
        check("重置确认对话框", "/#/case/NA-001", prep=open_dialog, expect="dialog.confirm[open]")

        check("玩法说明", "/#/manual", expect="#manual-title")
        check("关于与隐私", "/#/about", expect="#about-title")

        # 手机视口
        m = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                has_touch=True, device_scale_factor=2, locale="zh-CN")
        mp = m.new_page()
        mp.goto(f"{args.base}/#/case/NA-004", wait_until="networkidle")
        mp.wait_for_selector("#slots .slot")
        v = run_axe(mp)
        ok = len(v) == 0
        if not ok:
            failures += 1
        results.append({"page": "调查桌·手机390", "path": "/#/case/NA-004", "violations": v, "ok": ok})
        print(f"[{'PASS' if ok else 'FAIL'}] 调查桌·手机390 — {len(v)} violations")
        for x in v:
            print(f"    [{x['impact']}] {x['id']}: {x['help']}")
        m.close()

        if console_errors:
            print("\n页面异常：")
            for e in console_errors[:5]:
                print("   ", e)

        browser.close()

    out = SHOTS / "a11y-report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "base": args.base,
        "when": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tags": TAGS,
        "results": results,
        "total_violations": sum(len(r["violations"]) for r in results),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(r["violations"]) for r in results)
    print(f"\n{'='*60}")
    print(f"共 {len(results)} 个页面状态：{len(results)-failures} 无违规 / {failures} 有违规")
    print(f"违规总数：{total}")
    print(f"报告：{out}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
