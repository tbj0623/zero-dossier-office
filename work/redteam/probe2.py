#!/usr/bin/env python3
"""Red-team probe 2: robustness of localStorage restore, keyboard-only
completion, and an axe-core accessibility scan of the live site."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://tbj0623.github.io/zero-dossier-office/"
OUT = Path(__file__).resolve().parent
AXE = Path(r"C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\work\qa\a11y\axe.min.js")


def main() -> int:
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)

        # ---------- A. corrupt / hostile localStorage ----------
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        pg.on("console", lambda m: errors.append(f"console[{m.type}]: {m.text}")
              if m.type == "error" else None)
        pg.goto(BASE, wait_until="networkidle")

        cases = {
            "garbage_progress": {"zd:v1:progress": "not-json{{{"},
            "wrong_types_progress": {"zd:v1:progress": '{"NA-001":{"solved":"yes","times":"x"}}'},
            "order_wrong_len": {"zd:v1:order:NA-001": '{"order":["红票"],"hintIndex":99}'},
            "order_unknown_items": {"zd:v1:order:NA-001":
                                    '{"order":["甲","乙","丙","丁"],"hintIndex":2}'},
            "order_null": {"zd:v1:order:NA-001": "null"},
            "hintIndex_huge": {"zd:v1:order:NA-001": '{"order":["蓝票","绿票","红票","黄票"],'
                                                    '"hintIndex":100000}'},
        }
        for name, kv in cases.items():
            pg.evaluate("() => localStorage.clear()")
            pg.evaluate("""(kv) => { for (const [k,v] of Object.entries(kv)) localStorage.setItem(k,v); }""", kv)
            pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
            try:
                pg.wait_for_selector("#slots .slot", timeout=8000)
                state = "rendered"
                slots = pg.eval_on_selector_all("#slots .slot__item",
                                                "els => els.map(e => e.textContent)")
                hint_count = len(pg.query_selector_all(".hint-card"))
                msg = pg.inner_text("#case-root")[:140].replace("\n", " ")
            except Exception as exc:  # noqa: BLE001
                state = f"BROKEN: {exc}"[:160]
                slots, hint_count, msg = None, None, None
            out[name] = {"state": state, "slots": slots,
                         "hint_cards": hint_count, "text": msg}
            out[name]["page_errors"] = errors[-4:]
            errors.clear()

        # corrupt progress on the cabinet (does the badge explode?)
        pg.evaluate("() => localStorage.clear()")
        pg.evaluate("""() => localStorage.setItem('zd:v1:progress','{"NA-001":"str","NA-002":null,"NA-003":{"solved":true}}')""")
        pg.goto(f"{BASE}#/cabinet", wait_until="networkidle")
        pg.wait_for_selector("#cabinet .case-card")
        out["badge_with_mixed_progress"] = pg.inner_text("#progress-badge")

        # ---------- B. keyboard-only completion of NA-001 ----------
        pg.evaluate("() => localStorage.clear()")
        pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        pg.wait_for_selector("#slots .slot")
        answer = ["红票", "蓝票", "黄票", "绿票"]
        kb_errors = []
        # read the current order, then use ONLY keyboard (focus a slot's up/down
        # button and press Enter) to reach the answer.
        for want in range(len(answer)):
            order = pg.eval_on_selector_all("#slots .slot__item",
                                            "els => els.map(e => e.textContent)")
            cur = order.index(answer[want])
            while cur > want:
                pg.focus(f'#slots .slot[data-index="{cur}"] [data-act="up"]')
                pg.keyboard.press("Enter")
                cur -= 1
                order = pg.eval_on_selector_all("#slots .slot__item",
                                                "els => els.map(e => e.textContent)")
            while cur < want:
                pg.focus(f'#slots .slot[data-index="{cur}"] [data-act="down"]')
                pg.keyboard.press("Enter")
                cur += 1
                order = pg.eval_on_selector_all("#slots .slot__item",
                                                "els => els.map(e => e.textContent)")
        final = pg.eval_on_selector_all("#slots .slot__item",
                                        "els => els.map(e => e.textContent)")
        # submit with keyboard: focus the button, press Enter
        pg.focus("#btn-submit")
        pg.keyboard.press("Enter")
        try:
            pg.wait_for_selector(".verdict", timeout=8000)
            kb = "completed"
        except Exception:  # noqa: BLE001
            kb = "FAILED to reach verdict"
        out["keyboard_only_playthrough"] = {"final_order": final, "result": kb}

        # ---------- C. axe-core scan ----------
        if AXE.exists():
            axe_results = {}
            for route, label in [("", "home"), ("#/cabinet", "cabinet"),
                                 ("#/case/NA-001", "case"), ("#/manual", "manual"),
                                 ("#/about", "about")]:
                pg.goto(BASE + route, wait_until="networkidle")
                if "case" in route:
                    pg.wait_for_selector("#slots .slot")
                pg.add_script_tag(path=str(AXE))
                res = pg.evaluate("""async () => {
                    const r = await axe.run(document, {
                      runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}
                    });
                    return r.violations.map(v => ({
                      id: v.id, impact: v.impact, help: v.help,
                      nodes: v.nodes.length,
                      targets: v.nodes.slice(0,4).map(n => n.target.join(' '))
                    }));
                }""")
                axe_results[label] = res
            out["axe_violations"] = axe_results
            out["axe_total"] = sum(len(v) for v in axe_results.values())
        else:
            out["axe_violations"] = "axe.min.js not found"

        b.close()
    (OUT / "probe2.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
