#!/usr/bin/env python3
"""Re-verify the 5 headline findings against the CURRENT repo HEAD build
(local http://127.0.0.1:8899), because teammates have been committing fixes."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8899/"
OUT = Path(__file__).resolve().parent
ANSWER = ["红票", "蓝票", "黄票", "绿票"]

JS_TARGETS = r"""
() => {
  const sel = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
  const bad = [];
  for (const e of document.querySelectorAll(sel)) {
    const r = e.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (r.width < 44 || r.height < 44) {
      bad.push({tag: e.tagName, cls: (e.className.baseVal ?? e.className) || '',
                text: (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0,26),
                w: Math.round(r.width), h: Math.round(r.height)});
    }
  }
  return bad;
}
"""


def main() -> int:
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)

        # 1. stale save crash (RT-002)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE, wait_until="networkidle")
        pg.evaluate("""() => {
            localStorage.clear();
            localStorage.setItem('zd:v1:order:NA-001', JSON.stringify({
              order: ['红票（旧名）','蓝票（旧名）','黄票（旧名）','绿票（旧名）'],
              hintIndex: 1, at: Date.now()}));
        }""")
        pg.goto(BASE + "#/case/NA-001", wait_until="networkidle")
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(1200)
        out["RT-002_stale_save"] = {
            "slots_rendered": pg.query_selector("#slots") is not None,
            "submit_present": pg.query_selector("#btn-submit") is not None,
            "stuck_loading": "正在取阅档案" in pg.inner_text("#case-root"),
            "pageerrors": errs[:2],
        }
        ctx.close()

        # 2. 44px targets (RT-004)
        ctx = b.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN",
                            is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        t = {}
        for route, label in [("", "home"), ("#/case/NA-001", "case"), ("#/manual", "manual")]:
            pg.goto(BASE + route, wait_until="networkidle")
            if "case" in route:
                pg.wait_for_selector("#slots .slot")
            t[label] = pg.evaluate(JS_TARGETS)
        out["RT-004_44px_390"] = t
        ctx.close()

        # 3. axe (RT-008, RT-009) on current build
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        axe = Path(r"C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\work\qa\a11y\axe.min.js")
        axe_res = {}
        if axe.exists():
            for route, label in [("", "home"), ("#/cabinet", "cabinet"),
                                 ("#/case/NA-001", "case"), ("#/manual", "manual")]:
                pg.goto(BASE + route, wait_until="networkidle")
                if "case" in route:
                    pg.wait_for_selector("#slots .slot")
                pg.add_script_tag(path=str(axe))
                axe_res[label] = pg.evaluate("""async () => {
                    const r = await axe.run(document, {runOnly:
                      {type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}});
                    return r.violations.map(v => ({id:v.id, impact:v.impact, nodes:v.nodes.length}));
                }""")
        out["RT-008_009_axe"] = axe_res
        ctx.close()

        # 4. XSS re-check
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        real = pg.request.get(BASE + "cases/NA-001.json").json()
        evil = json.loads(json.dumps(real))
        evil["title"] = '<img src=x onerror="window.__X=1">MARK'
        pg.route("**/cases/NA-001.json*", lambda r: r.fulfill(
            status=200, content_type="application/json", body=json.dumps(evil, ensure_ascii=False)))
        pg.goto(BASE + "#/case/NA-001", wait_until="networkidle")
        pg.wait_for_timeout(1000)
        out["RT_003_xss"] = pg.evaluate("""() => ({
            x: window.__X||0,
            injected: document.querySelectorAll('#case-root img[src=\"x\"]').length})""")
        ctx.close()
        b.close()

    (OUT / "reverify_head.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
