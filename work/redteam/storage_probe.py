#!/usr/bin/env python3
"""Corrected corrupt-localStorage probe: force a real reload so the app
re-reads storage, then observe whether the case still renders."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://tbj0623.github.io/zero-dossier-office/"
OUT = Path(__file__).resolve().parent

CASES = {
    "garbage_progress": {"zd:v1:progress": "not-json{{{"},
    "progress_wrong_types": {"zd:v1:progress": '{"NA-001":{"solved":"yes","times":"x"}}'},
    "progress_is_string": {"zd:v1:progress": '"hello"'},
    "progress_is_array": {"zd:v1:progress": "[1,2,3]"},
    "order_wrong_len": {"zd:v1:order:NA-001": '{"order":["红票"],"hintIndex":99}'},
    "order_unknown_items": {"zd:v1:order:NA-001":
                            '{"order":["甲","乙","丙","丁"],"hintIndex":2}'},
    "order_correct_len_dup": {"zd:v1:order:NA-001":
                              '{"order":["红票","红票","黄票","绿票"],"hintIndex":0}'},
    "order_null": {"zd:v1:order:NA-001": "null"},
    "order_is_number": {"zd:v1:order:NA-001": "42"},
    "hintIndex_huge": {"zd:v1:order:NA-001":
                       '{"order":["蓝票","绿票","红票","黄票"],"hintIndex":100000}'},
    "hintIndex_negative": {"zd:v1:order:NA-001":
                           '{"order":["蓝票","绿票","红票","黄票"],"hintIndex":-5}'},
    "hintIndex_string": {"zd:v1:order:NA-001":
                         '{"order":["蓝票","绿票","红票","黄票"],"hintIndex":"3"}'},
}


def main() -> int:
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for name, kv in CASES.items():
            ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
            pg.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}")
                  if m.type == "error" else None)
            # go to origin first so localStorage is writable for this origin
            pg.goto(BASE, wait_until="networkidle")
            pg.evaluate("(kv) => { localStorage.clear();"
                        " for (const [k,v] of Object.entries(kv)) localStorage.setItem(k,v); }", kv)
            # full document navigation -> app boots and re-reads storage
            pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
            pg.reload(wait_until="networkidle")
            try:
                pg.wait_for_selector("#slots .slot", timeout=9000)
                slots = pg.eval_on_selector_all("#slots .slot__item",
                                                "e => e.map(x => x.textContent)")
                hints = len(pg.query_selector_all(".hint-card"))
                body = pg.inner_text("#case-root")
                state = "ok"
            except Exception:  # noqa: BLE001
                slots, hints = None, None
                body = pg.inner_text("body")[:200]
                state = "BROKEN"
            out[name] = {"state": state, "slots": slots, "hint_cards": hints,
                         "body_head": body[:180].replace("\n", " "),
                         "errors": errs[:3]}
            ctx.close()

        # empty-state / error UI for a missing case file
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        pg.route("**/cases/NA-001.json", lambda r: r.fulfill(status=500, body="boom"))
        pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        out["case_json_500"] = {"text": pg.inner_text("#case-root")[:200].replace("\n", " ")}
        ctx.close()

        # malformed JSON
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        pg.route("**/cases/NA-001.json", lambda r: r.fulfill(
            status=200, content_type="application/json", body="{not json"))
        pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        pg.wait_for_timeout(1200)
        out["case_json_malformed"] = {"text": pg.inner_text("#case-root")[:200].replace("\n", " ")}
        ctx.close()
        b.close()
    (OUT / "storage_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
