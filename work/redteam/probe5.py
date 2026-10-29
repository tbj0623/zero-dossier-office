#!/usr/bin/env python3
"""Confirm whether case JSON is interpolated as markup, by patching the served
payload and asserting the ACTUAL page shows the tampered title."""
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
        c = b.new_context(viewport={"width": 1280, "height": 900}, locale="zh-CN")
        q = c.new_page()
        real = q.request.get(BASE + "cases/NA-001.json").json()

        evil = json.loads(json.dumps(real))
        MARK = "REDTEAMMARK"
        evil["title"] = f'<img src=x onerror="window.__X=1">{MARK}'
        evil["evidence"][0]["body"] = f'<img src=x onerror="window.__Y=1">{MARK}'
        evil["hints"][0] = f'<b onmouseover="window.__Z=1">{MARK}</b>'

        hits = []
        q.on("request", lambda r: hits.append(r.url) if "NA-001.json" in r.url else None)
        q.route("**/cases/NA-001.json*", lambda route: route.fulfill(
            status=200, content_type="application/json; charset=utf-8",
            body=json.dumps(evil, ensure_ascii=False)))

        q.goto(f"{BASE}#/case/NA-001", wait_until="networkidle")
        q.wait_for_timeout(1200)
        out["requests_seen"] = hits
        out["page"] = q.evaluate("""() => ({
          title: (document.querySelector('#case-title')||{}).textContent || null,
          titleHTML: (document.querySelector('#case-title')||{}).innerHTML || null,
          marks: document.body.innerText.split('REDTEAMMARK').length - 1,
          imgX: document.querySelectorAll('#case-root img[src="x"]').length,
          x: window.__X||0, y: window.__Y||0, z: window.__Z||0
        })""")

        # check whether the altered body text is visible as TEXT (safe) or markup
        out["evidence_first_body"] = q.evaluate(
            "() => (document.querySelector('.ev-card__body p')||{}).textContent || null")
        out["evidence_first_html"] = q.evaluate(
            "() => (document.querySelector('.ev-card__body p')||{}).innerHTML || null")

        c.close()
        b.close()
    (OUT / "probe5.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
