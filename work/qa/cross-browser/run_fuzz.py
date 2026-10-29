#!/usr/bin/env python3
"""C: robustness fuzzing of NA-001 case JSON on the LIVE site.

Uses Playwright route interception to serve malformed JSON for ./cases/NA-001.json,
then records exactly what the user sees, whether an exception escapes to the
console, whether an alert fires, whether an <img> was injected into the DOM, and
whether the app is still navigable afterwards.

Nothing here writes to the product; only work/qa/cross-browser/ is written.
"""
from __future__ import annotations

import copy
import json
import sys
import time

from playwright.sync_api import sync_playwright

from qa_common import LIVE_BASE, RAW, SHOTS, ConsoleCollector, load_case, now_iso

ERROR_HEADLINE = "这份档案尚未完整送达"
CASE_URL_PART = "/cases/NA-001.json"


def base_case() -> dict:
    return copy.deepcopy(load_case("NA-001"))


def mutation_duplicate_item() -> dict:
    c = base_case()
    # keep length 4 so only the duplicate rule can fire:
    # ['蓝票','绿票','红票','黄票'] -> ['蓝票','蓝票','红票','黄票']
    c["items"][1] = c["items"][0]
    return c


def mutation_unknown_op() -> dict:
    c = base_case()
    c["constraints"][1]["op"] = "xor"
    return c


def mutation_truncated_json() -> str:
    return "{"


def mutation_html_item() -> dict:
    """Rename one item to an HTML payload (consistently referenced, so the case
    still validates and actually RENDERS) and also inject it into prose fields.

    If the app used innerHTML anywhere on case data, this would create a real
    <img> element and fire onerror=alert(1).
    """
    c = base_case()
    payload = '<img src=x onerror=alert(1)>'
    old = c["items"][0]                      # 蓝票
    c["items"][0] = payload
    for r in c["constraints"]:
        for k in ("a", "b", "c"):
            if r.get(k) == old:
                r[k] = payload
    c["title"] = f'{c["title"]} {payload}'
    c["evidence"][0]["body"] = c["evidence"][0]["body"] + " " + payload
    c["hints"][0] = c["hints"][0] + " " + payload
    return c


def mutation_missing_item_ref() -> dict:
    c = base_case()
    c["constraints"][1]["a"] = "不存在的物件"
    return c


def mutation_not_unique() -> dict:
    """Extra case: a well-formed but under-constrained file (non-unique solution)."""
    c = base_case()
    c["constraints"] = [c["constraints"][0]]
    c["evidence"] = [{
        **c["evidence"][0],
        "constraint_ids": [c["constraints"][0]["id"]],
    }]
    return c


def mutation_missing_field() -> dict:
    c = base_case()
    del c["constraints"]
    return c


MUTATIONS = [
    ("1. items with a duplicate entry", "duplicate_item", lambda: json.dumps(mutation_duplicate_item(), ensure_ascii=False)),
    ("2. constraints with unknown op \"xor\"", "unknown_op", lambda: json.dumps(mutation_unknown_op(), ensure_ascii=False)),
    ("3. truncated / invalid JSON \"{\"", "truncated_json", mutation_truncated_json),
    ("4. items containing <img src=x onerror=alert(1)>", "html_item", lambda: json.dumps(mutation_html_item(), ensure_ascii=False)),
    ("5. constraint referencing nonexistent item", "missing_item_ref", lambda: json.dumps(mutation_missing_item_ref(), ensure_ascii=False)),
    ("6. extra: non-unique solution (under-constrained)", "not_unique", lambda: json.dumps(mutation_not_unique(), ensure_ascii=False)),
    ("7. extra: required field 'constraints' deleted", "missing_field", lambda: json.dumps(mutation_missing_field(), ensure_ascii=False)),
]


def probe_page_state(page) -> dict:
    return page.evaluate("""() => {
        const root = document.querySelector('#case-root');
        const txt = (root ? root.innerText : '').trim();
        const payload = '<img src=x onerror=alert(1)>';
        const allNodes = [...document.querySelectorAll('body *')];
        // element whose ownText is literally the payload
        const literalNode = allNodes.find(e => e.children.length === 0 &&
            (e.textContent || '').trim() === payload);
        return {
            caseRootText: txt.slice(0, 500),
            hasErrorHeadline: document.body.innerText.includes('这份档案尚未完整送达'),
            hasEmptyState: !!document.querySelector('.empty-state'),
            hasSpinner: !!document.querySelector('.loading, .spinner'),
            hasSlots: !!document.querySelector('#slots .slot'),
            caseRootChildCount: root ? root.children.length : null,
            injectedImgs: [...document.querySelectorAll('#case-root img, #slots img, #case-title img')].map(i => i.outerHTML.slice(0, 200)),
            literalTextNode: literalNode ? {tag: literalNode.tagName, cls: String(literalNode.className||'').slice(0,50)} : null,
            payloadVisibleAsText: (document.body.innerText || '').includes(payload),
            countOfImgTagsAnywhere: document.querySelectorAll('img').length,
            bodyTextLen: document.body.innerText.trim().length,
            title: document.title,
            titleHasPayload: (document.title || '').includes('<img'),
        };
    }""")


def probe_rendered_payload(page) -> dict:
    """While NA-001 with the HTML-ish payload is rendered, check expand/hint paths too."""
    detail = {}
    try:
        btns = page.query_selector_all(".ev-card__summary")
        for b in btns:
            if b.get_attribute("aria-expanded") == "false":
                b.click()
        page.click("#btn-hint")
        page.wait_for_timeout(200)
        detail["hintCards"] = len(page.query_selector_all(".hint-card"))
        detail["slotTexts"] = page.eval_on_selector_all(
            "#slots .slot__item", "els => els.map(e => e.textContent)")
        detail["evidenceText"] = page.inner_text(".evidence-col")[:400]
    except Exception as exc:  # noqa: BLE001
        detail["error"] = f"{type(exc).__name__}: {exc}"
    return detail


def run_mutation(page, label: str, key: str, body_text: str, dialogs: list, cc: ConsoleCollector,
                 intercept_log: list) -> dict:
    cc.console_errors.clear()
    cc.pageerrors.clear()
    dialogs.clear()
    alert_fired = {"fired": False}
    served = {"count": 0, "bytes": 0, "status": None}

    def handler(route):
        # serve the malformed body for NA-001 case JSON, pass everything else through
        if CASE_URL_PART in route.request.url:
            route.fulfill(status=200, content_type="application/json; charset=utf-8", body=body_text)
            served["count"] += 1
            served["bytes"] = len(body_text.encode("utf-8"))
            served["status"] = 200
        else:
            route.continue_()

    page.unroute("**/cases/NA-001.json")
    page.route("**/cases/NA-001.json", handler)

    # Defensive: neutralise alert() so an XSS cannot hang the harness, but record it.
    page.evaluate("""() => {
        window.__qaAlerts = [];
        if (!window.__qaPatched) {
            window.__qaPatched = true;
            const orig = window.alert;
            window.alert = (m) => { window.__qaAlerts.push(String(m)); try { orig.call(window, m); } catch (e) {} };
        }
    }""")

    # fresh navigation so boot() re-fetches every case (cache-busting the SPA state)
    page.goto("about:blank")
    page.goto(f"{LIVE_BASE}#/case/NA-001", wait_until="networkidle", timeout=60000)
    try:
        page.wait_for_selector("#case-root .empty-state, #slots .slot", timeout=15000)
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.4)

    intercept_log.append({"key": key, **served})
    state = probe_page_state(page)
    rendered = probe_rendered_payload(page) if state["hasSlots"] else {}
    qa_alerts = page.evaluate("() => window.__qaAlerts || []")
    if qa_alerts:
        alert_fired["fired"] = True

    row = {
        "input": label,
        "key": key,
        "httpServed": 200,
        "payloadBytes": len(body_text.encode("utf-8")),
        "intercepted": dict(served),
        "userSees": state["caseRootText"][:300],
        "errorHeadline": state["hasErrorHeadline"],
        "emptyState": state["hasEmptyState"],
        "spinnerStuck": state["hasSpinner"] and not state["hasSlots"],
        "slotsRendered": state["hasSlots"],
        "consoleErrors": list(cc.console_errors),
        "pageErrors": list(cc.pageerrors),
        "alertDialogs": list(dialogs),
        "alertPatched": qa_alerts,
        "injectedImgs": state["injectedImgs"],
        "literalTextNode": state["literalTextNode"],
        "payloadVisibleAsText": state["payloadVisibleAsText"],
        "titleHasPayload": state["titleHasPayload"],
        "renderedDetail": rendered,
        "bodyTextLen": state["bodyTextLen"],
        "title": state["title"],
    }

    # Is the app still navigable? go to cabinet and count cards.
    nav_ok = False
    nav_detail = ""
    try:
        page.click('a[data-nav="cabinet"]', timeout=5000)
        page.wait_for_selector("#cabinet .case-card", timeout=10000)
        n = len(page.query_selector_all("#cabinet .case-card"))
        nav_ok = n > 0
        nav_detail = f"{n} cabinet cards after recovery"
    except Exception as exc:  # noqa: BLE001
        nav_detail = f"{type(exc).__name__}: {exc}"[:200]
    row["navigableAfter"] = nav_ok
    row["navigableDetail"] = nav_detail
    row["consoleErrorsAfterNav"] = list(cc.pageerrors)
    return row


def main() -> int:
    rows = []
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()
        cc = ConsoleCollector(page)
        dialogs: list[str] = []
        page.on("dialog", lambda d: (dialogs.append(f"{d.type}:{d.message}"), d.dismiss()))

        intercept_log: list = []
        for label, key, make_body in MUTATIONS:
            body_text = make_body()
            row = run_mutation(page, label, key, body_text, dialogs, cc, intercept_log)
            rows.append(row)
            shot = SHOTS / f"fuzz-{key}.png"
            try:
                page.screenshot(path=str(shot), full_page=True)
                shots.append(str(shot.relative_to(RAW.parent)))
            except Exception:  # noqa: BLE001
                pass
            print(f"\n### {label}")
            print(f"  userSees: {row['userSees'][:120]!r}")
            print(f"  errorHeadline={row['errorHeadline']} emptyState={row['emptyState']} "
                  f"slots={row['slotsRendered']} spinnerStuck={row['spinnerStuck']}")
            print(f"  consoleErrors={row['consoleErrors']} pageErrors={row['pageErrors']}")
            print(f"  alerts={row['alertDialogs']} patched={row['alertPatched']} imgs={row['injectedImgs']}")
            print(f"  navigableAfter={row['navigableAfter']} ({row['navigableDetail']})")

        browser.close()

    # A real XSS is declared only if code actually executed or markup was injected.
    # NOTE: case text also reaches document.title. <title> is RCDATA, so "<img>"
    # there is inert text and is NOT an XSS vector — recorded separately, not flagged.
    xss = []
    for r in rows:
        injected = [i for i in r["injectedImgs"] if "<img" in i.lower()]
        if r["alertDialogs"] or r["alertPatched"] or injected:
            xss.append({"input": r["input"], "alerts": r["alertDialogs"],
                        "patchedAlerts": r["alertPatched"], "imgs": r["injectedImgs"]})

    payload = {
        "suite": "fuzz",
        "engine": "chromium",
        "when": now_iso(),
        "base": LIVE_BASE,
        "target": "cases/NA-001.json",
        "rows": rows,
        "xssFindings": xss,
        "screenshots": shots,
        "interceptionProof": intercept_log,
    }
    (RAW / "fuzz.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nXSS findings: {len(xss)}")
    print("-> raw/fuzz.json")
    return 1 if xss else 0


if __name__ == "__main__":
    sys.exit(main())
