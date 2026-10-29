#!/usr/bin/env python3
"""WebKit keyboard reachability audit.

Safari's factory default is "Press Tab to highlight each item on a webpage" OFF,
which means plain <a href> elements are NOT in the sequential focus order.
Playwright's WebKit build reproduces that default. This runner measures it
directly, on the real site and on a 5-element minimal page, and compares with
Chromium and Firefox.

It also records WHAT A KEYBOARD USER CAN ACTUALLY REACH on each page, because
"the game is fully playable by keyboard" is a product claim that depends on
this default.
Writes raw/tab-reach-webkit.json.
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright
from wk_common import BASE, RAW, Results, now_iso

R = Results("tab_reach", "webkit")

MINIMAL = """<!doctype html><html><head><meta charset=utf-8></head><body>
<a id="plain" href="#x">plain link</a>
<a id="tabidx" href="#y" tabindex="0">link tabindex=0</a>
<button id="btn">button</button>
<a id="rolebtn" href="#z" role="button">link role=button</a>
<input id="inp">
</body></html>"""

TAB_PROBE = """() => {
    const a = document.activeElement;
    return {tag: a.tagName, id: a.id || '',
            cls: (a.className || '').toString().slice(0, 40),
            text: (a.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 28),
            href: a.getAttribute ? a.getAttribute('href') : null,
            focusVisible: a.matches(':focus-visible')};
}"""


def tab_walk(page, n: int, neutral_click=(5, 300)) -> list[dict]:
    """Walk the Tab order from a neutral click. Repeat-safe: stops when it loops."""
    if neutral_click:
        page.mouse.click(*neutral_click)
        page.wait_for_timeout(150)
    seq: list[dict] = []
    seen_sig: set[str] = set()
    for _ in range(n):
        page.keyboard.press("Tab")
        page.wait_for_timeout(90)
        row = page.evaluate(TAB_PROBE)
        sig = f"{row['tag']}|{row['id']}|{row['cls']}|{row['text']}"
        row["sig"] = sig
        row["repeat"] = sig in seen_sig
        seen_sig.add(sig)
        seq.append(row)
    return seq


def main() -> int:
    out: dict = {"when": now_iso(), "base": BASE, "scenes": {}, "minimal": {}}
    with sync_playwright() as p:
        # ---------- minimal page, all three engines ----------
        for engine, launcher in (("webkit", p.webkit), ("chromium", p.chromium), ("firefox", p.firefox)):
            b = launcher.launch()
            pg = b.new_page()
            pg.set_content(MINIMAL)
            pg.wait_for_timeout(300)
            seq = tab_walk(pg, 6, neutral_click=None)
            out["minimal"][engine] = {"version": b.version,
                                      "order": [s["id"] or s["tag"] for s in seq],
                                      "plain_link_reachable": any(s["id"] == "plain" for s in seq),
                                      "role_button_link_reachable": any(s["id"] == "rolebtn" for s in seq),
                                      "tabindex_link_reachable": any(s["id"] == "tabidx" for s in seq)}
            b.close()

        # ---------- the real site, WebKit ----------
        b = p.webkit.launch(headless=True)
        R.extra["webkit_version"] = b.version
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()

        for scene, route, ready in (
                ("home", "#/", "#cta-first"),
                ("cabinet", "#/cabinet", "#view-cabinet .case-card"),
                ("desk-NA001", "#/case/NA-001", "#slots .slot"),
                ("verdict-NA001", "#/case/NA-001", "#slots .slot")):
            page.goto(f"{BASE}/{route}", wait_until="networkidle", timeout=45000)
            page.wait_for_selector(ready, timeout=15000)
            page.wait_for_timeout(700)

            if scene == "verdict-NA001":
                # drive to the verdict page with the keyboard-accessible path
                from wk_common import expected_solution, fill_order
                # solve via buttons (mouse) just to reach the verdict DOM
                sol = expected_solution("NA-001")
                fill_order(page, sol, pause=40)
                page.locator("#btn-submit").click()
                page.wait_for_selector(".verdict", timeout=12000)
                page.wait_for_timeout(600)

            seq = tab_walk(page, 14)
            reachable = [s for s in seq if not s["repeat"]]
            counts = page.evaluate("""() => {
                const all = [...document.querySelectorAll(
                    '#view-home, #view-cabinet, #view-case, #view-manual, #view-about')]
                    .filter(v => v.dataset.active === 'true');
                const scope = all[0] || document.body;
                const isVisible = (el) => {
                    const cs = getComputedStyle(el);
                    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
                    if (el.closest('[hidden]')) return false;
                    const r = el.getBoundingClientRect();
                    return r.width > 0 || r.height > 0;
                };
                const links = [...scope.querySelectorAll('a[href]')].filter(isVisible);
                const buttons = [...scope.querySelectorAll('button, input, select, textarea')].filter(isVisible);
                return {links: links.length, buttons: buttons.length,
                        explicitTabindexLinks: links.filter(a => a.hasAttribute('tabindex')).length,
                        totalControls: links.length + buttons.length,
                        scope: scope.id || 'body'};
            }""")
            out["scenes"][scene] = {
                "sequence": seq, "distinct_reachable": len(reachable),
                "distinct_tags": sorted({s["tag"] for s in reachable}),
                "never_reached_link": counts["links"] > 0 and not any(s["tag"] == "A" for s in reachable),
                "counts": counts,
            }
            page.screenshot(path=str(RAW.parent / "shots" / f"wk-tab-{scene}.png"))

        ctx.close()
        b.close()

    (RAW / "tab-reach-webkit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    mn = out["minimal"]
    print("minimal page Tab order:")
    for eng, v in mn.items():
        print(f"  {eng:9s} {v['order']}  plain_link={v['plain_link_reachable']} "
              f"role=button_link={v['role_button_link_reachable']} tabindex_link={v['tabindex_link_reachable']}")
    print()
    for scene, v in out["scenes"].items():
        print(f"{scene}: distinct reachable={v['distinct_reachable']}, tags={v['distinct_tags']}, "
              f"controls on page={v['counts']}, no-link-reached={v['never_reached_link']}")

    # ---- assertions ----
    R.add("T1 WebKit 的最小页里，无 tabindex 的 <a href> 不可 Tab 到达",
          mn["webkit"]["plain_link_reachable"] is False,
          f"order={mn['webkit']['order']}")
    R.add("T1b 加 tabindex=0 后同一链接可到达（根因确认）",
          mn["webkit"]["tabindex_link_reachable"] is True,
          f"order={mn['webkit']['order']}")
    R.add("T1c Chromium/Firefox 上同一链接默认可到达（引擎差异，不是标记问题）",
          mn["chromium"]["plain_link_reachable"] and mn["firefox"]["plain_link_reachable"],
          f"chromium={mn['chromium']['order']} firefox={mn['firefox']['order']}")
    for scene, v in out["scenes"].items():
        links = v["counts"]["links"]
        R.add(f"T2 {scene}: Tab 序列能到达页面上的链接（共 {links} 个）",
              not v["never_reached_link"],
              f"reachable tags={v['distinct_tags']}, distinct={v['distinct_reachable']}")
    R.dump("tab-reach-summary.json")
    return 0 if all(r["ok"] for r in R.rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
