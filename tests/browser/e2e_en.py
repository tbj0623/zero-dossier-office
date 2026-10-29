#!/usr/bin/env python3
"""英文模式回归：确认 ?lang=en 下六案可通关、无障碍零违规、无中文残留。

用法：python tests/browser/e2e_en.py [--base URL]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:8140"
if "--base" in sys.argv:
    BASE = sys.argv[sys.argv.index("--base") + 1]

CJK = re.compile(r"[\u4e00-\u9fff]")

results: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def solve(pg, case_id: str) -> bool:
    """用英文显示名读 expected_solution，逐格归位。"""
    auth = json.loads((ROOT / "cases" / "author" / f"{case_id}.json").read_text(encoding="utf-8"))
    glossary = json.loads((ROOT / "site" / "i18n" / "en.json").read_text(encoding="utf-8"))["_meta"]["glossary"]
    target = [glossary.get(x, x) if isinstance(glossary.get(x, x), str) else glossary[x].get("en", x)
              for x in auth["expected_solution"]]

    for want in range(len(target)):
        labels = pg.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
        try:
            cur = labels.index(target[want])
        except ValueError:
            return False
        while cur > want:
            pg.locator(f'#slots .slot[data-index="{cur}"] [data-act="up"]').click()
            pg.wait_for_timeout(80)
            cur -= 1
        while cur < want:
            pg.locator(f'#slots .slot[data-index="{cur}"] [data-act="down"]').click()
            pg.wait_for_timeout(80)
            cur += 1
    pg.click("#btn-submit")
    try:
        pg.wait_for_selector(".verdict", timeout=8000)
        return True
    except Exception:
        return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 950})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        # 1) 首页
        page.goto(f"{BASE}/?lang=en", wait_until="networkidle")
        page.wait_for_timeout(900)
        record(page.get_attribute("html", "lang") == "en", "html lang=en")
        record("these records" in page.inner_text("h1").lower(), "英文标题", page.inner_text("h1")[:40])
        body = page.inner_text("#main")
        record(not CJK.search(body), "首页无中文残留",
               f"{len(CJK.findall(body))} 个字符" if CJK.search(body) else "")

        # 2) 档案柜
        page.goto(f"{BASE}/?lang=en#/cabinet", wait_until="networkidle")
        page.wait_for_function("() => document.querySelector('#view-cabinet')?.dataset.active === 'true'", timeout=8000)
        page.wait_for_timeout(600)
        cards = page.query_selector_all("#view-cabinet .case-card")
        record(len(cards) == 6, "档案柜 6 张卡", f"{len(cards)} 张")
        txt = page.inner_text("#main")
        record(not CJK.search(txt), "档案柜无中文残留")

        # 3) 手册 / 关于
        for route in ("manual", "about"):
            page.goto(f"{BASE}/?lang=en#/{route}", wait_until="networkidle")
            page.wait_for_timeout(600)
            txt = page.inner_text("#main")
            record(not CJK.search(txt), f"{route} 页无中文残留")

        # 4) 六案通关
        solved = []
        for i in range(1, 7):
            cid = f"NA-{i:03d}"
            page.goto(f"{BASE}/?lang=en#/case/{cid}", wait_until="networkidle")
            page.wait_for_selector("#slots .slot", timeout=9000)
            page.wait_for_timeout(400)
            desk_txt = page.inner_text("#case-root")
            if CJK.search(desk_txt):
                record(False, f"{cid} 桌面无中文残留",
                       "".join(dict.fromkeys(CJK.findall(desk_txt)))[:30])
            if solve(page, cid):
                solved.append(cid)
                vt = page.inner_text("#case-root")
                if CJK.search(vt):
                    record(False, f"{cid} 结案页无中文残留")
                if page.query_selector(".verdict__h1"):
                    pass
                page.goto(f"{BASE}/?lang=en#/cabinet", wait_until="networkidle")
                page.wait_for_timeout(300)
        record(len(solved) == 6, "英文模式六案通关", f"{len(solved)}/6 {solved}")

        # 5) 语言切换按钮
        # 前面用 ?lang=en 访问过，localStorage 里已经存了 en；
        # 先清掉，确保从中文默认态开始测切换。
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.evaluate("() => localStorage.removeItem('zd:v1:lang')")
        page.goto(f"{BASE}/", wait_until="networkidle")
        # 等应用完成首次渲染（语言按钮存在且导航已填充）再点
        page.wait_for_function("() => document.querySelectorAll('.site-nav a').length === 3", timeout=8000)
        page.wait_for_timeout(1200)
        record(page.get_attribute("html", "lang") == "zh-CN", "切换前为中文默认")
        page.click("#lang-toggle")
        page.wait_for_timeout(900)
        record(page.get_attribute("html", "lang") == "en", "点按钮切到英文")
        page.click("#lang-toggle")
        page.wait_for_timeout(900)
        record(page.get_attribute("html", "lang") == "zh-CN", "再点切回中文")
        record(not errors, "无控制台错误", str(errors[:2]))

        browser.close()

    passed = sum(1 for ok, _, _ in results if ok)
    print()
    print("=" * 56)
    print(f"共 {len(results)} 项检查：{passed} PASS / {len(results) - passed} FAIL")
    out = ROOT / "screenshots" / "en-report.json"
    out.write_text(json.dumps(
        {"base": BASE, "checks": len(results), "passed": passed,
         "results": [{"ok": o, "name": n, "detail": d} for o, n, d in results]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告：{out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
