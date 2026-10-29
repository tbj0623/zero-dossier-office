#!/usr/bin/env python3
"""B: performance measurement on the LIVE site (Chromium), cold + warm + Slow 4G.

Honest-method notes
-------------------
* TTI is measured by an init script installed before navigation. It starts a
  poll loop at document start and stamps `performance.now()` the first moment
  `#slots .slot` exists AND its first move button is visible, enabled, and the
  top-most element at its centre (i.e. actually clickable). This is "time from
  navigation start until the first case's slots are interactive".
* Cold runs use a brand-new browser process (fresh profile => empty HTTP cache).
* The warm run reuses the SAME context as the cold run (a real returning visitor
  reuses the same browser profile); a new Playwright context would start with an
  isolated empty cache and would NOT be a warm measurement.
* This is NOT a Lighthouse audit and no Lighthouse score is produced.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

from qa_common import LIVE_BASE, RAW, SHOTS, ConsoleCollector, now_iso

SLOW4G = {
    "offline": False,
    "downloadThroughput": int(1.6 * 1024 * 1024 / 8),   # 1.6 Mbps
    "uploadThroughput": int(750 * 1024 / 8),            # 750 kbps
    "latency": 150,                                     # ms
}

INIT_TTI = r"""
(() => {
  window.__qaTTI = null;
  const started = performance.now();
  const check = () => {
    if (window.__qaTTI) return;
    try {
      const slots = document.querySelectorAll('#slots .slot');
      if (slots.length) {
        const btn = document.querySelector('#slots .slot[data-index="0"] [data-act="down"]');
        if (btn && !btn.disabled) {
          const r = btn.getBoundingClientRect();
          const st = getComputedStyle(btn);
          if (r.width > 1 && r.height > 1 && st.visibility !== 'hidden' && st.pointerEvents !== 'none') {
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            if (hit && (hit === btn || btn.contains(hit))) {
              window.__qaTTI = {
                ttiMs: Math.round(performance.now()),
                slots: slots.length,
                order: [...document.querySelectorAll('#slots .slot__item')].map(e => e.textContent),
                readyState: document.readyState
              };
              return;
            }
          }
        }
      }
    } catch (e) { window.__qaTTI = { error: String(e) }; return; }
    if (performance.now() - started > 90000) {
      window.__qaTTI = { error: 'timeout', slots: document.querySelectorAll('#slots .slot').length };
      return;
    }
    setTimeout(check, 10);
  };
  check();
})();
"""

READ_TTI = "() => window.__qaTTI"


def resource_timing(page) -> list[dict]:
    return page.evaluate("""() => performance.getEntriesByType('resource').map(e => ({
        name: e.name,
        initiatorType: e.initiatorType,
        startTime: Math.round(e.startTime * 10) / 10,
        duration: Math.round(e.duration * 10) / 10,
        transferSize: e.transferSize,
        encodedBodySize: e.encodedBodySize,
        decodedBodySize: e.decodedBodySize,
        renderBlockingStatus: e.renderBlockingStatus || null,
        nextHopProtocol: e.nextHopProtocol || null,
    }))""")


def nav_timing(page) -> dict:
    return page.evaluate("""() => {
        const n = performance.getEntriesByType('navigation')[0];
        if (!n) return null;
        return {
            type: n.type,
            ttfb: Math.round((n.responseStart - n.startTime) * 10) / 10,
            domInteractive: Math.round((n.domInteractive - n.startTime) * 10) / 10,
            domContentLoaded: Math.round((n.domContentLoadedEventEnd - n.startTime) * 10) / 10,
            loadEvent: Math.round((n.loadEventEnd - n.startTime) * 10) / 10,
            responseEnd: Math.round((n.responseEnd - n.startTime) * 10) / 10,
            transferSize: n.transferSize,
            encodedBodySize: n.encodedBodySize,
            decodedBodySize: n.decodedBodySize,
            nextHopProtocol: n.nextHopProtocol,
            redirectCount: n.redirectCount,
        };
    }""")


def wait_tti(page, timeout_ms=90000) -> dict:
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        v = page.evaluate(READ_TTI)
        if v:
            return v
        page.wait_for_timeout(50)
    return {"error": "harness timeout waiting for __qaTTI"}


def measure_cold(p, label: str, slow4g: bool) -> dict:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN",
                              device_scale_factor=1)
    ctx.add_init_script(INIT_TTI)
    page = ctx.new_page()
    cc = ConsoleCollector(page)
    cdp = ctx.new_cdp_session(page)
    cdp.send("Network.enable")
    if slow4g:
        cdp.send("Network.emulateNetworkConditions", SLOW4G)

    url = f"{LIVE_BASE}#/case/NA-001"
    t0 = time.time()
    page.goto(url, wait_until="commit", timeout=90000)
    tti = wait_tti(page)
    wall_ms = round((time.time() - t0) * 1000)
    try:
        page.wait_for_load_state("load", timeout=90000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(300)

    nt = nav_timing(page)
    resources = resource_timing(page)
    painting = page.evaluate(
        "() => performance.getEntriesByType('paint').map(e => ({name: e.name, startTime: Math.round(e.startTime*10)/10}))")
    headers = page.evaluate("""async () => {
        const out = {};
        for (const u of ['./', './app.mjs', './styles/app.css', './cases/NA-001.json']) {
            try {
                const r = await fetch(u, {method: 'HEAD', cache: 'no-store'});
                out[u] = {
                    cacheControl: r.headers.get('cache-control'),
                    etag: r.headers.get('etag'),
                    lastModified: r.headers.get('last-modified'),
                    contentEncoding: r.headers.get('content-encoding'),
                    age: r.headers.get('age'),
                };
            } catch (e) { out[u] = {error: String(e)}; }
        }
        return out;
    }""")

    result = {
        "label": label, "slow4g": slow4g, "emulation": SLOW4G if slow4g else None,
        "navigation": nt, "tti": tti, "ttiWallMs": wall_ms, "paint": painting,
        "resources": resources,
        "requestCount": len(resources),
        "requestCountIncludingDocument": len(resources) + 1,
        "subresourceTransferBytes": sum(r["transferSize"] for r in resources),
        "documentTransferBytes": (nt or {}).get("transferSize"),
        "totalTransferBytes": sum(r["transferSize"] for r in resources) + ((nt or {}).get("transferSize") or 0),
        "console": cc.all,
        "cacheHeaders": headers,
        "measuredAt": now_iso(),
    }

    # ---- warm repeat view in the SAME context (real returning-visitor cache) ----
    page.goto("about:blank")
    page.goto(url, wait_until="commit", timeout=90000)
    warm_tti = wait_tti(page)
    try:
        page.wait_for_load_state("load", timeout=90000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(300)
    warm_nav = nav_timing(page)
    warm_res = resource_timing(page)
    result["warm"] = {
        "navigation": warm_nav,
        "tti": warm_tti,
        "requestCount": len(warm_res),
        "fromCacheCount": sum(1 for r in warm_res if r["transferSize"] == 0),
        "subresourceTransferBytes": sum(r["transferSize"] for r in warm_res),
        "documentTransferBytes": (warm_nav or {}).get("transferSize"),
        "totalTransferBytes": sum(r["transferSize"] for r in warm_res) + ((warm_nav or {}).get("transferSize") or 0),
        "console": cc.all,
    }

    # ---- emulation sanity check: fetch a known-size asset and infer throughput ----
    probe = page.evaluate("""async () => {
        const u = './assets/NA-004-episode-card.webp?qa=' + Date.now();
        const t = performance.now();
        const r = await fetch(u, {cache: 'no-store'});
        const b = await r.blob();
        return {ms: Math.round(performance.now() - t), bytes: b.size};
    }""")
    probe["impliedKbps"] = round((probe["bytes"] * 8 / 1000) / (probe["ms"] / 1000), 1) if probe["ms"] else None
    result["throughputProbe"] = probe

    page.screenshot(path=str(SHOTS / f"perf-{label}.png"), full_page=False)
    browser.close()
    return result


def main() -> int:
    out: dict = {
        "base": LIVE_BASE, "when": now_iso(), "tool": "Playwright Python (Chromium)",
        "note": "Raw measurements only. This is NOT a Lighthouse audit and no Lighthouse score is reported.",
        "ttiDefinition": "performance.now() at the first 10ms poll where #slots .slot exists and the "
                         "first slot's move button is enabled, visible and hit-testable, measured from "
                         "navigation start of that document.",
    }
    runs = []
    with sync_playwright() as p:
        for i in range(3):
            r = measure_cold(p, f"cold-normal-{i+1}", slow4g=False)
            runs.append(r)
            n = r["navigation"]
            print(f"cold-normal-{i+1}: TTFB={n['ttfb']} DCL={n['domContentLoaded']} load={n['loadEvent']} "
                  f"TTI={r['tti'].get('ttiMs')} reqs={r['requestCountIncludingDocument']} bytes={r['totalTransferBytes']} "
                  f"warmTTI={r['warm']['tti'].get('ttiMs')} warmBytes={r['warm']['totalTransferBytes']}")
        for i in range(3):
            r = measure_cold(p, f"cold-slow4g-{i+1}", slow4g=True)
            runs.append(r)
            n = r["navigation"]
            print(f"cold-slow4g-{i+1}: TTFB={n['ttfb']} DCL={n['domContentLoaded']} load={n['loadEvent']} "
                  f"TTI={r['tti'].get('ttiMs')} reqs={r['requestCountIncludingDocument']} bytes={r['totalTransferBytes']} "
                  f"probe={r['throughputProbe']}")

    out["runs"] = runs

    def med(vals):
        vals = [v for v in vals if isinstance(v, (int, float))]
        return round(statistics.median(vals), 1) if vals else None

    def pack(rs):
        return {
            "ttfb_ms": med([r["navigation"]["ttfb"] for r in rs]),
            "dcl_ms": med([r["navigation"]["domContentLoaded"] for r in rs]),
            "load_ms": med([r["navigation"]["loadEvent"] for r in rs]),
            "tti_ms": med([r["tti"].get("ttiMs") for r in rs]),
            "requests_including_document": rs[0]["requestCountIncludingDocument"],
            "total_transfer_bytes": med([r["totalTransferBytes"] for r in rs]),
            "warm_tti_ms": med([r["warm"]["tti"].get("ttiMs") for r in rs]),
            "warm_total_transfer_bytes": med([r["warm"]["totalTransferBytes"] for r in rs]),
            "ranges": {
                "ttfb": [min(r["navigation"]["ttfb"] for r in rs), max(r["navigation"]["ttfb"] for r in rs)],
                "load": [min(r["navigation"]["loadEvent"] for r in rs), max(r["navigation"]["loadEvent"] for r in rs)],
                "tti": [min(r["tti"].get("ttiMs") for r in rs), max(r["tti"].get("ttiMs") for r in rs)],
            },
        }

    normal = [r for r in runs if not r["slow4g"]]
    slow = [r for r in runs if r["slow4g"]]
    out["summary"] = {"normal": pack(normal), "slow4g": pack(slow)}

    first = normal[0]
    res_sorted = sorted(first["resources"], key=lambda r: r["encodedBodySize"], reverse=True)
    out["largestResource"] = res_sorted[0] if res_sorted else None
    out["topResources"] = res_sorted[:8]
    out["renderBlocking"] = [r for r in first["resources"] if r.get("renderBlockingStatus") == "blocking"]
    out["firstLoadDetails"] = {
        "requestCountIncludingDocument": first["requestCountIncludingDocument"],
        "subresourceTransferBytes": first["subresourceTransferBytes"],
        "documentTransferBytes": first["documentTransferBytes"],
        "totalTransferBytes": first["totalTransferBytes"],
        "perResource": [{k: r[k] for k in ("name", "initiatorType", "transferSize", "encodedBodySize",
                                          "decodedBodySize", "renderBlockingStatus", "duration")}
                        for r in first["resources"]],
    }

    (RAW / "perf.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nsummary:", json.dumps(out["summary"], ensure_ascii=False, indent=1))
    print("largest:", out["largestResource"])
    print("render-blocking:", len(out["renderBlocking"]))
    print("-> raw/perf.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
