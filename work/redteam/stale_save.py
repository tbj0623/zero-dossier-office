#!/usr/bin/env python3
"""Confirm the stale-save crash: what does the player actually see, and is
there any way out other than clearing site data?"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://tbj0623.github.io/zero-dossier-office/"
OUT = Path(__file__).resolve().parent


def main() -> int:
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE, wait_until="networkidle")
        # simulate a save written before an item was renamed
        pg.evaluate("""() => {
            localStorage.clear();
            localStorage.setItem('zd:v1:order:NA-001',
              JSON.stringify({order:['红票','蓝票','黄票','绿票'].map(x=>x+'（旧名）'),
                              hintIndex:1, at: Date.now()}));
        }""")
        pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(1500)
        out["case_root_text"] = pg.inner_text("#case-root")[:200].replace("\n", " ")
        out["case_root_html_head"] = pg.inner_html("#case-root")[:260]
        out["slots_present"] = pg.query_selector("#slots") is not None
        out["submit_button"] = pg.query_selector("#btn-submit") is not None
        out["errors"] = errs[:3]
        # can the player recover via the documented "clear progress" path?
        pg.goto(BASE + "#/manual", wait_until="networkidle")
        pg.click("#clear-progress")
        pg.wait_for_selector("#confirm-dialog[open]")
        pg.click('[data-confirm="ok"]')
        pg.wait_for_timeout(500)
        out["clear_button_reachable"] = True
        out["storage_after_clear"] = pg.evaluate(
            "() => Object.keys(localStorage)")
        # after clearing, does the case work again?
        pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        out["recovers_after_clear"] = pg.query_selector("#slots") is not None
        ctx.close()
        b.close()
    (OUT / "stale_save.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
