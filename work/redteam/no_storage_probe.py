#!/usr/bin/env python3
"""Verify PRIVACY.md claim: 'If the browser disables localStorage ... the game
is still fully playable and silently degrades.'"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://tbj0623.github.io/zero-dossier-office/"
OUT = Path(__file__).resolve().parent
ANSWER = ["红票", "蓝票", "黄票", "绿票"]


def main() -> int:
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        # make every localStorage access throw, like a locked-down privacy mode
        pg.add_init_script("""() => {
            const boom = () => { throw new DOMException('denied', 'SecurityError'); };
            Object.defineProperty(window, 'localStorage', {
              get() { return { getItem: boom, setItem: boom, removeItem: boom,
                               clear: boom, key: boom, length: 0 }; }
            });
        }""")
        pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        try:
            pg.wait_for_selector("#slots .slot", timeout=9000)
            rendered = True
        except Exception:  # noqa: BLE001
            rendered = False
        out["renders_without_localstorage"] = rendered
        out["errors"] = errs[:4]
        if rendered:
            for want in range(len(ANSWER)):
                order = pg.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
                cur = order.index(ANSWER[want])
                while cur > want:
                    pg.click(f'#slots .slot[data-index="{cur}"] [data-act="up"]'); cur -= 1
                while cur < want:
                    pg.click(f'#slots .slot[data-index="{cur}"] [data-act="down"]'); cur += 1
            pg.click("#btn-submit")
            try:
                pg.wait_for_selector(".verdict", timeout=8000)
                out["completes_without_localstorage"] = True
            except Exception:  # noqa: BLE001
                out["completes_without_localstorage"] = False
        ctx.close()
        b.close()
    (OUT / "no_storage.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
