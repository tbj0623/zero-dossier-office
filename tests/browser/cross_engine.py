#!/usr/bin/env python3
"""跨引擎回归：同一套关键断言在 Chromium 与 Firefox 上各跑一遍。

为什么需要：Firefox QA 报告指出本机只有 Playwright 的 Gecko，且它不绘制
backdrop-filter；同时确认了 43/43 旅程检查与 6/6 通关在 Gecko 上通过。
这个脚本把"两引擎都必须成立"的最小核心固化成回归门禁，任何一边坏掉就失败。

用法：python tests/browser/cross_engine.py [--base URL]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:8140"
if "--base" in sys.argv:
    BASE = sys.argv[sys.argv.index("--base") + 1]

results: list[tuple[str, bool, str, str]] = []


def record(engine: str, ok: bool, name: str, detail: str = "") -> None:
    results.append((engine, ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {engine:9s} {name}" + (f" — {detail}" if detail else ""))


def run(engine_name: str, browser) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # 首页
    page.goto(f"{BASE}/", wait_until="networkidle")
    page.wait_for_timeout(800)
    record(engine_name, page.title() != "", "首页有标题", page.title()[:30])
    record(engine_name, page.is_visible("#cta-first"), "首页主 CTA 可见")

    # 头部在有背景内容滚过时仍可读（不依赖 backdrop-filter 是否上屏）
    page.goto(f"{BASE}/#/cabinet", wait_until="networkidle")
    page.wait_for_function("() => document.querySelector('#view-cabinet')?.dataset.active === 'true'", timeout=8000)
    page.wait_for_timeout(600)
    page.evaluate("() => window.scrollTo(0, 600)")
    page.wait_for_timeout(400)
    hdr = page.evaluate("""() => {
      const h = document.querySelector('.site-header');
      const cs = getComputedStyle(h);
      return { bg: cs.backgroundImage, alpha: cs.backgroundColor, pos: cs.position, top: h.getBoundingClientRect().top };
    }""")
    # 头部必须有接近不透明的底色，才能在"模糊不生效"的引擎上依然可读
    record(engine_name, "gradient" in hdr["bg"] or "rgb" in hdr["bg"], "头部有实色/渐变底", hdr["bg"][:40])
    record(engine_name, hdr["pos"] == "sticky", "头部 sticky", hdr["pos"])
    record(engine_name, abs(hdr["top"]) < 2, "滚动后头部仍吸顶", f"top={hdr['top']:.1f}")

    cards = page.query_selector_all("#view-cabinet .case-card")
    record(engine_name, len(cards) == 6, "档案柜 6 张卡", str(len(cards)))

    # NA-001：单击恰好移动一格（防重复绑定，两引擎都必须成立）
    page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle")
    page.wait_for_selector("#slots .slot", timeout=9000)
    page.wait_for_timeout(400)
    before = page.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
    page.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
    page.wait_for_timeout(300)
    after = page.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
    expected = [before[1], before[0], *before[2:]]
    record(engine_name, after == expected, "单击恰好移动一格", f"{before} -> {after}")

    # 键盘：方向键重排
    page.locator('#slots .slot[data-index="0"] [data-act="pick"]').focus()
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(300)
    kbd = page.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
    record(engine_name, kbd != after, "方向键可重排", f"{after} -> {kbd}")

    # 对话框 Tab 陷阱：三个引擎都不得把焦点放出去
    page.locator("#btn-reset").click()
    page.wait_for_timeout(400)
    if page.query_selector("dialog[open]"):
        escapes = 0
        for _ in range(6):
            page.keyboard.press("Tab")
            page.wait_for_timeout(60)
            tag = page.evaluate("() => document.activeElement.tagName")
            if tag in ("BODY", "HTML", "DIALOG"):
                escapes += 1
        record(engine_name, escapes == 0, "对话框 Tab 焦点不外逃", f"escapes={escapes}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        record(engine_name, page.query_selector("dialog[open]") is None, "Esc 关闭对话框")
        # 重新进入案件，后面还要继续测
        page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle")
        page.wait_for_selector("#slots .slot", timeout=9000)
        page.wait_for_timeout(300)

    # 提示逐条出现
    counts = []
    for _ in range(3):
        page.locator("#btn-hint").click()
        page.wait_for_timeout(300)
        counts.append(len(page.query_selector_all(".hint-card")))
    record(engine_name, counts == [1, 2, 3], "三档提示逐条出现", str(counts))

    # 通关
    auth = json.loads((ROOT / "cases" / "author" / "NA-001.json").read_text(encoding="utf-8"))
    target = auth["expected_solution"]
    for want in range(len(target)):
        labels = page.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
        cur = labels.index(target[want])
        while cur > want:
            page.locator(f'#slots .slot[data-index="{cur}"] [data-act="up"]').click()
            page.wait_for_timeout(70)
            cur -= 1
        while cur < want:
            page.locator(f'#slots .slot[data-index="{cur}"] [data-act="down"]').click()
            page.wait_for_timeout(70)
            cur += 1
    page.locator("#btn-submit").click()
    try:
        page.wait_for_selector(".verdict", timeout=9000)
        ok = True
    except Exception:
        ok = False
    record(engine_name, ok, "NA-001 通关出结案页")
    if ok:
        labels = page.eval_on_selector_all(".recap-block__label", "e=>e.map(x=>x.textContent.trim())")
        record(engine_name, len(labels) >= 2, "逻辑复盘 + 档案后记两段", str([x[:12] for x in labels]))

    record(engine_name, not errors, "无控制台异常", str(errors[:2]))
    page.close()


def main() -> int:
    with sync_playwright() as p:
        for name, launcher in (("chromium", p.chromium), ("firefox", p.firefox), ("webkit", p.webkit)):
            try:
                browser = launcher.launch()
            except Exception as exc:  # 引擎不可用要显式失败，不能静默跳过
                record(name, False, "引擎可启动", str(exc)[:120])
                continue
            try:
                run(name, browser)
            finally:
                browser.close()

    passed = sum(1 for _, ok, _, _ in results if ok)
    print()
    print("=" * 60)
    print(f"共 {len(results)} 项：{passed} PASS / {len(results) - passed} FAIL")
    out = ROOT / "screenshots" / "cross-engine-report.json"
    out.write_text(json.dumps(
        {"base": BASE, "checks": len(results), "passed": passed,
         "results": [{"engine": e, "ok": o, "name": n, "detail": d} for e, o, n, d in results]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告：{out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
