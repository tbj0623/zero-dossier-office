#!/usr/bin/env python3
"""Red-team probe: record EVERY network request on the live site, plus
localStorage / cookie / storage-write verification and answer-leak checks.

Read-only against the live site. Writes only into work/redteam/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE = "https://tbj0623.github.io/zero-dossier-office/"
OUT = Path(__file__).resolve().parent
ORIGIN = "https://tbj0623.github.io"


def main() -> int:
    report = {"base": BASE, "pages": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()

        reqs = []
        page.on("request", lambda r: reqs.append({
            "url": r.url, "method": r.method, "type": r.resource_type,
        }))
        console = []
        page.on("console", lambda m: console.append({"type": m.type, "text": m.text}))
        page.on("pageerror", lambda e: console.append({"type": "pageerror", "text": str(e)}))

        # ---- 1. home ----
        page.goto(BASE, wait_until="networkidle")
        # ---- 2. every case, fully ----
        for i in range(1, 7):
            page.goto(f"{BASE}#/case/NA-00{i}", wait_until="networkidle")
            page.wait_for_selector("#slots .slot")
            # expand every evidence card
            for btn in page.query_selector_all(".ev-card__summary"):
                if btn.get_attribute("aria-expanded") == "false":
                    btn.click()
            # reveal all hints
            for _ in range(4):
                b = page.query_selector("#btn-hint")
                if b and not b.is_disabled():
                    b.click()
        # ---- 3. manual + about pages ----
        for r in ("#/manual", "#/about", "#/cabinet"):
            page.goto(BASE + r, wait_until="networkidle")
        # ---- 4. submit a WRONG answer on a case and watch for any network ----
        page.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        page.wait_for_selector("#slots .slot")
        before = len(reqs)
        page.click("#btn-submit")
        page.wait_for_selector("#message[data-show='true']")
        after_submit = len(reqs)

        # ---- storage / cookie inspection ----
        ls = page.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
        ss = page.evaluate("() => Object.fromEntries(Object.entries(sessionStorage))")
        cookies = ctx.cookies()
        doc_cookie = page.evaluate("() => document.cookie")
        # IndexedDB databases
        idb = page.evaluate("async () => (await indexedDB.databases()).map(d => d.name)")
        caches = page.evaluate("async () => await caches.keys()")
        # service worker registrations
        sw = page.evaluate("async () => (await navigator.serviceWorker.getRegistrations()).length")
        # performance resource entries (covers everything the page fetched)
        perf = page.evaluate("() => performance.getEntriesByType('resource').map(e => e.name)")

        third_party = []
        for r in reqs:
            host = urlparse(r["url"]).netloc
            if host and host != "tbj0623.github.io":
                third_party.append(r)

        report["pages"] = reqs
        report["request_count"] = len(reqs)
        report["distinct_hosts"] = sorted({urlparse(r["url"]).netloc for r in reqs if urlparse(r["url"]).netloc})
        report["third_party_requests"] = third_party
        report["requests_during_wrong_submit"] = reqs[before:after_submit]
        report["localStorage"] = ls
        report["sessionStorage"] = ss
        report["cookies"] = cookies
        report["document_cookie"] = doc_cookie
        report["indexedDB"] = idb
        report["cacheStorage"] = caches
        report["serviceWorkers"] = sw
        report["performance_resources"] = perf
        report["console"] = console

        # ---- direct URL probes for answer leakage ----
        anon = browser.new_context()
        ap = anon.new_page()
        probes = {}
        for path in [
            "cases/NA-001.json", "cases/author/NA-001.json", "cases/public/NA-001.json",
            "engine/verify_cases.py", "tools/editor.html", "tools/export_case.py",
            "work/blind-src/NA-001.json", "review/NA-001-formal.json",
            "app.mjs", "index.html", "sitemap.xml", "robots.txt",
        ]:
            resp = ap.request.get(ORIGIN + "/zero-dossier-office/" + path)
            body = resp.text() if resp.ok else ""
            probes[path] = {
                "status": resp.status,
                "bytes": len(body),
                "has_expected_solution": "expected_solution" in body,
                "has_constraints": '"constraints"' in body,
            }
        report["url_probes"] = probes
        anon.close()
        browser.close()

    (OUT / "net_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("requests:", report["request_count"])
    print("hosts:", report["distinct_hosts"])
    print("third-party:", len(third_party))
    print("requests during wrong submit:", len(report["requests_during_wrong_submit"]))
    print("localStorage keys:", list(ls.keys()))
    print("cookies:", cookies, "| document.cookie:", repr(doc_cookie))
    print("sessionStorage:", ss, "| idb:", idb, "| cache:", caches, "| sw:", sw)
    print("console issues:", [c for c in console if c["type"] in ("error", "warning", "pageerror")][:5])
    print("--- url probes ---")
    for k, v in probes.items():
        print(f'  {v["status"]}  {k}  bytes={v["bytes"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
