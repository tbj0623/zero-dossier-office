#!/usr/bin/env python3
"""Red-team probe 4:
  A. touch-only (no keyboard, no mouse) playthrough at 390px
  B. WCAG 1.4.10 reflow at 320px on every route
  C. malicious case-JSON injection: serve a tampered case through Playwright
     route interception and see whether markup reaches the DOM.
"""
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

        # ---------- A. touch-only playthrough ----------
        ctx = b.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN",
                            is_mobile=True, has_touch=True, device_scale_factor=2)
        pg = ctx.new_page()
        pg.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        pg.wait_for_selector("#slots .slot")
        tap_log = []
        for want in range(len(ANSWER)):
            order = pg.eval_on_selector_all("#slots .slot__item",
                                            "els => els.map(e => e.textContent)")
            cur = order.index(ANSWER[want])
            while cur > want:
                pg.tap(f'#slots .slot[data-index="{cur}"] [data-act="up"]')
                tap_log.append("up")
                cur -= 1
            while cur < want:
                pg.tap(f'#slots .slot[data-index="{cur}"] [data-act="down"]')
                tap_log.append("down")
                cur += 1
        final = pg.eval_on_selector_all("#slots .slot__item",
                                        "els => els.map(e => e.textContent)")
        pg.tap("#btn-submit")
        try:
            pg.wait_for_selector(".verdict", timeout=8000)
            verdict = "completed"
        except Exception:  # noqa: BLE001
            verdict = "FAILED"
        out["touch_playthrough_390"] = {"taps": len(tap_log), "final": final,
                                        "verdict": verdict}

        # tap-to-swap (select then tap another slot) — the primary documented path
        pg.goto(f"{BASE}#/case/NA-002", wait_until="networkidle")
        pg.wait_for_selector("#slots .slot")
        before = pg.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
        pg.tap('#slots .slot[data-index="0"] [data-act="pick"]')
        pg.tap('#slots .slot[data-index="1"] [data-act="pick"]')
        after = pg.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
        out["tap_to_swap"] = {"before": before, "after": after, "swapped": before != after}
        ctx.close()

        # ---------- B. reflow @ 320px ----------
        reflow = {}
        for w in (320, 360):
            c = b.new_context(viewport={"width": w, "height": 800}, locale="zh-CN",
                              is_mobile=True, has_touch=True)
            q = c.new_page()
            for route in ("", "#/cabinet", "#/case/NA-004", "#/manual", "#/about"):
                q.goto(BASE + route, wait_until="networkidle")
                if "case" in route:
                    q.wait_for_selector("#slots .slot")
                over = q.evaluate(
                    "() => ({sw: document.documentElement.scrollWidth,"
                    " cw: document.documentElement.clientWidth})")
                reflow[f"{w}px{route or '/home'}"] = {
                    "overflow_px": over["sw"] - over["cw"],
                    "ok": over["sw"] <= over["cw"] + 1,
                }
            c.close()
        out["reflow"] = reflow

        # ---------- C. malicious case JSON ----------
        c = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        q = c.new_page()
        q.goto(BASE, wait_until="networkidle")
        real = q.request.get(BASE + "cases/NA-001.json").json()
        evil = json.loads(json.dumps(real))
        evil["title"] = '<img src=x onerror="window.__XSS_TITLE=1">TITLE'
        evil["evidence"][0]["body"] = '<img src=x onerror="window.__XSS_BODY=1">BODY'
        evil["evidence"][0]["title"] = '<svg onload="window.__XSS_EVT=1">'
        evil["hints"][0] = '<img src=x onerror="window.__XSS_HINT=1">'
        evil["items"] = evil["items"][:]

        q.route("**/cases/NA-001.json", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps(evil, ensure_ascii=False)))
        errs = []
        q.on("pageerror", lambda e: errs.append(str(e)))
        q.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        q.wait_for_timeout(1500)
        xss = q.evaluate("""() => ({
            title: window.__XSS_TITLE||0, body: window.__XSS_BODY||0,
            hint: window.__XSS_HINT||0, evt: window.__XSS_EVT||0,
            injectedImgs: document.querySelectorAll('#case-root img[src="x"]').length,
            injectedSvg: document.querySelectorAll('#case-root svg[onload]').length,
            titleText: (document.querySelector('#case-title')||{}).textContent||null
        })""")
        out["malicious_case_json"] = {"xss": xss, "pageerrors": errs[:3]}

        # long-string DoS
        evil2 = json.loads(json.dumps(real))
        evil2["evidence"][0]["body"] = "长" * 500_000
        q.unroute("**/cases/NA-001.json")
        q.route("**/cases/NA-001.json", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps(evil2, ensure_ascii=False)))
        import time
        t0 = time.time()
        q.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        try:
            q.wait_for_selector("#slots .slot", timeout=15000)
            state = "rendered"
        except Exception as exc:  # noqa: BLE001
            state = f"FAILED {exc}"[:120]
        out["long_string"] = {"state": state, "seconds": round(time.time()-t0, 2)}
        c.close()
        b.close()

    (OUT / "probe4.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def evial_rest(items):  # pragma: no cover - defensive placeholder
    return items[1:]


if __name__ == "__main__":
    raise SystemExit(main())
