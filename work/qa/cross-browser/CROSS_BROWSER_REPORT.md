# Cross-browser & performance QA — 第零证物局 (zero-dossier-office)

**Target:** live build at <https://tbj0623.github.io/zero-dossier-office/>
**Date:** 2026-10-30 (Asia/Shanghai)
**Engines tested:** Chromium **151.0.7922.34** (Playwright bundled) · Microsoft Edge **156.0.4314.50** (channel=`msedge`)
**Method:** Playwright for Python 1.62.0, headless, brand-new browser process per measurement run.
**Write scope:** everything below lives under `work/qa/cross-browser/`. No product file was modified.

Build provenance check: the live `app.mjs` differs from the local `site/app.mjs` **only** in the
`BUILD` constant (`41fc9520…` vs the `__BUILD_VERSION__` placeholder). `cases/NA-001.json` and
`styles/app.css` are byte-identical to the deployed copies. So this run tests the real deployed code,
not a stale local copy. (`raw/live-app.mjs`, diff was 1 line.)

---

## Verdict

**ship-with-fixes** — no blockers, no critical defects, no XSS.

All 34 journey checks pass identically on both engines; 21/21 deep-link checks pass on both; all 7
malformed-JSON inputs degrade to a readable error state with zero uncaught exceptions. The fixes are
two low-severity polish items (below), neither of which should hold the release.

---

## A. Edge vs Chromium

Both engines ran the **same** runner (`run_journey.py`), each in its own process. Raw data:
`raw/journey-chromium.json`, `raw/journey-msedge.json`.

| # | Check | Chromium | Edge |
|---|---|---|---|
| 1 | Browser launches | PASS 151.0.7922.34 | PASS 156.0.4314.50 |
| 2 | Home loads, correct title | PASS | PASS |
| 3 | Home has `#cta-first` entry | PASS | PASS |
| 4 | Cabinet shows 6 cards | PASS (6) | PASS (6) |
| 5 | NA-001 desk opens with title | PASS | PASS |
| 6 | NA-001 has exactly 3 evidence cards | PASS (3) | PASS (3) |
| 7 | All evidence expands (3/3) | PASS | PASS |
| 8 | Default order is not the answer | PASS | PASS |
| 9 | Wrong submit → non-spoiler feedback | PASS ("2 条关系未满足", no "→") | PASS (same text) |
| 10 | Wrong submit preserves order | PASS | PASS |
| 11 | Three hints appear one by one | PASS [1,2,3] | PASS [1,2,3] |
| 12 | Hints do not auto-fill the answer | PASS | PASS |
| 13 | Hint button disables when exhausted | PASS | PASS |
| 14 | Correct solve reaches verdict | PASS ("档案归位。") | PASS (same) |
| 15 | Logic recap and story recap are separate blocks | PASS | PASS |
| 16 | Logic recap cites E01/E02/E03 | PASS | PASS |
| 17 | Recaps are not duplicates | PASS (336 ch / 164 ch) | PASS (same) |
| 18 | Archive progress persists (1/6) | PASS | PASS |
| 19 | Refresh restores arrangement | PASS | PASS |
| 20 | Tab order reaches slot controls | PASS (skip-link→brand→nav→evidence→slot) | PASS (identical chain) |
| 21 | **Enter** on a move button reorders | PASS | PASS |
| 22 | **ArrowUp** on a slot reorders | PASS | PASS |
| 23 | **ArrowDown** reorders | PASS | PASS |
| 24 | ArrowDown reverses ArrowUp | PASS | PASS |
| 25 | ArrowUp on top row is a no-op | PASS | PASS |
| 26 | ArrowDown on last row is a no-op | PASS | PASS |
| 27 | Focus outline visible | PASS (`outline-style: solid`) | PASS |
| 28 | Focus retained after keyboard reorder | PASS (`act=down`) | PASS |
| 29 | 390×844 — no horizontal overflow | PASS (390 / 390) | PASS (390 / 390) |
| 30 | 390×844 — targets ≥44 px | PASS (0 undersized) | PASS (0 undersized) |
| 31 | 390×844 — touch tap works | PASS | PASS |
| 32 | No console errors (desktop) | PASS (0) | PASS (0) |
| 33 | No console errors (390 mobile) | PASS (0) | PASS (0) |
| 34 | No third-party requests | PASS (0) | PASS (0) |

**Divergences found: 0.** Every assertion produced the same result and the same values on both engines.

### Visual / layout parity (extra)

A controlled comparison (`run_visual_parity.py`) captured 6 settled scenes on both engines with fonts
ready and every `<img>` decoded (`raw/visual-parity.json`):

* **Layout metrics: 0 differences.** Header, hero, cards, slots, buttons, evidence/order columns —
  identical `x/y/width/height`, `font-size`, `line-height`, and `scrollWidth == clientWidth` at every
  viewport (`raw/layout-parity.json`).
* Raw pixel deltas exist but are text/gradient anti-aliasing: mean channel delta 0.33–1.11 / 255;
  only 0.013 %–0.78 % of pixels differ by more than 16/255 (`raw/pixel-delta-summary.json`).
  Edge and Chromium rasterize glyphs slightly differently; this is not a layout divergence.
* One transient: on the 390 px cabinet shot Edge had 5/7 images decoded vs Chromium 7/7 at that
  instant. Re-tested 3× with a scroll: **7/7 decoded every time in Edge**. This is normal
  `loading="lazy"` behaviour, not a bug.

---

## B. Performance (live site, Chromium)

**This is not a Lighthouse audit.** No Lighthouse run was performed and **no Lighthouse score is
claimed anywhere in this report.** The numbers below are Navigation Timing, Resource Timing and
Playwright CDP measurements taken in this session.

TTI definition used: `performance.now()` at the first 10 ms poll where `#slots .slot` exists **and**
the first slot's move button is enabled, visible and hit-testable (`elementFromPoint` at its centre).
It is measured from that document's navigation start via an init script installed before `goto`.
Cold runs launch a fresh browser process (empty HTTP cache). Warm runs reuse the **same** context,
which is what a returning visitor's profile actually does.

### Cold load — median of 3 runs (`raw/perf.json`)

| Metric | Normal | Slow 4G (1.6 Mbps ↓ / 750 kbps ↑ / 150 ms RTT) |
|---|---|---|
| TTFB | **387.5 ms** (255.9–424.9) | **396.9 ms** (285.4–755.7) |
| DOMContentLoaded | **1030.6 ms** | **1043.6 ms** |
| Load | **1030.6 ms** (556.2–1332.3) | **1043.7 ms** (989.7–1582.1) |
| **Time to interactive (slots clickable)** | **1327 ms** (719–1599) | **1416 ms** (1371–1984) |
| Requests incl. document | **13** | **13** |
| Transferred bytes | **45 602 B** | **45 602 B** |
| Warm-cache TTI (same context) | **143 ms** | **261 ms** |
| Warm-cache transferred | **1 800 B** (6/12 subresources from cache) | **1 800 B** |

Per-run detail (all 6 cold runs):

| Run | TTFB | DCL | Load | TTI | Warm TTI |
|---|---|---|---|---|---|
| cold-normal-1 | 387.5 | 1332.2 | 1332.3 | 1599 | 143 |
| cold-normal-2 | 424.9 | 1030.6 | 1030.6 | 1327 | 144 |
| cold-normal-3 | 255.9 | 556.1 | 556.2 | 719 | 139 |
| cold-slow4g-1 | 285.4 | 1043.6 | 1043.7 | 1416 | 270 |
| cold-slow4g-2 | 396.9 | 989.6 | 989.7 | 1371 | 261 |
| cold-slow4g-3 | 755.7 | 1582.0 | 1582.1 | 1984 | 244 |

### Byte budget — first load

* 45 602 B total transferred = 5 590 B document + 40 012 B subresources (gzip on the wire).
* Uncompressed total of the 20 assets the app can use: 497 785 B (`raw/asset-sizes.json`) — but only
  13 requests are made on a NA-001 first load; the three ~100 KB episode cards (NA-004/005/006) are
  **not** fetched.
* **Largest single resource: `app.mjs` — 14 401 B encoded / 14 701 B on the wire / 45 288 B decoded.**
  (Next: `styles/app.css` 6 615 B encoded, `styles/base.css` 2 039 B, `engine/solver.mjs` 3 012 B.)

### Render-blocking

**Yes — 3 render-blocking resources, all same-origin CSS:**
`styles/tokens.css` (1 197 B encoded), `styles/base.css` (2 039 B), `styles/app.css` (6 615 B).
The module scripts `app.mjs` and `engine/solver.mjs` report `renderBlockingStatus: non-blocking`.
The three stylesheets are small and gzipped (≈9.9 KB combined), so the cost is one extra round trip
rather than transfer volume. This is the single clearest optimisation lever: inlining the critical
CSS above the fold would remove 3 blocking requests from the critical path.

### Honest interpretation

* **Slow 4G barely moved TTI** (1327 → 1416 ms, +7 %). That is not a measurement failure: the page
  is ~45 KB over the wire, which at 1.6 Mbps is ≈230 ms of transfer — the rest of the time is
  connection setup, TLS, and main-thread work, none of which this profile throttles.
  Throttling was independently verified as active: at an extreme 50 kbps / 2000 ms profile the same
  page's load event went from ~1.0 s to **11.5 s**.
* **Variance is large** (TTI 719–1599 ms normal). Most of it is GitHub Pages TTFB (256–425 ms) and
  cold-connection noise, not app work. Treat single runs as indicative and the median as the estimate.
* **Warm cache is the real story:** 143 ms TTI and 1.8 KB on the wire. Returning users get an
  effectively instant first case. GitHub Pages sends `Cache-Control: max-age=600` with ETag, so
  repeat visits within 10 minutes are cache hits; after 10 minutes the browser revalidates
  (cheap 304s) rather than re-downloading.
* Nothing here says the page is "fast" in Lighthouse terms — LCP/CLS/TBT were not measured.

---

## C. Robustness fuzzing (live site, client-side)

Method: Playwright `route` interception on `**/cases/NA-001.json`, serving a mutated body with HTTP
200 while every other request passed through. Each case starts from `about:blank` so `boot()`
re-fetches. Interception was verified per case (request count and served byte length recorded in
`raw/fuzz.json → interceptionProof`). `alert()` was wrapped so an XSS could not hang the harness,
but the wrapper still records and forwards the call.

| # | Input | What the user saw | Console errors | App still usable? |
|---|---|---|---|---|
| 1 | `items` with a duplicate entry | "这份档案尚未完整送达 / items 重复 / 返回档案柜" | none | Yes — 6 cards after recovery |
| 2 | `constraints` with unknown op `"xor"` | "这份档案尚未完整送达 / 未知约束运算符：xor" | none | Yes |
| 3 | Truncated / invalid JSON (`{`) | "这份档案尚未完整送达 / Expected property name or '}' in JSON at position 1 (line 1 column 2)" | none | Yes |
| 4 | `items` containing `<img src=x onerror=alert(1)>` | **Rendered normally as literal text.** The payload is visible in the card title, the slot label, the evidence body and the hint | none | Yes |
| 5 | Constraint referencing a nonexistent item | "这份档案尚未完整送达 / 未知物件：不存在的物件" | none | Yes |
| 6 | *(extra)* under-constrained → non-unique solution | "这份档案尚未完整送达 / 该案未通过唯一解校验，已暂停展示" | none | Yes |
| 7 | *(extra)* required field `constraints` deleted | "这份档案尚未完整送达 / 案件缺少字段：constraints" | none | Yes |

Every case ends in the same graceful `.empty-state` with a "返回档案柜" link, never a spinner and
never a blank screen. No `pageerror` reached the window in any of the 7 runs.

### Case 4 — XSS verdict: **not vulnerable**

The app builds DOM with `document.createElement` + `textContent` and never assigns case data to
`innerHTML` (verified in source: zero `innerHTML`/`insertAdjacentHTML`/`outerHTML`/`document.write`
in `app.mjs`). Runtime evidence agrees:

* `alert()` dialog: **never fired**; patched alert also never called.
* Injected `<img>` inside `#case-root` / `#slots` / `#case-title`: **`[]`** — zero.
* The payload exists as a **text node** in `span.slot__item`, and `document.body.innerText`
  contains it verbatim.
* Screenshot `shots/fuzz-html_item.png` shows `<img src=x onerror=alert(1)>` printed as literal
  characters in the card title.

The payload does reach `document.title` (case titles feed the page title). `<title>` is RCDATA, so
`<img>` there is inert text — **not** an XSS vector. Flagged here only for completeness.

**No critical issue found. No XSS.**

---

## D. Deep-link / refresh / back-button

Run on both engines: `raw/deeplink-chromium.json`, `raw/deeplink-msedge.json` — **21/21 PASS on both**.

| Check | Chromium | Edge |
|---|---|---|
| Cold tab → `#/case/NA-004` opens the desk directly | PASS ("灯塔没有亮起的第五盏灯") | PASS |
| Cold deep-link renders a real case, not an error | PASS | PASS |
| Deep-link updates document title | PASS | PASS |
| Refresh on a deep link keeps the case | PASS | PASS |
| Solve part of a case, refresh → arrangement restored | PASS (`航海图…` identical) | PASS |
| Hint progress restored after refresh | PASS (1 → 1) | PASS |
| Back from a case → cabinet | PASS (`#/cabinet`, 6 cards) | PASS |
| Cabinet fully rendered after Back | PASS | PASS |
| Forward → same case again | PASS (`NA-003`) | PASS |
| Back from a deep link returns to previous in-site page | PASS (home view visible) | PASS |
| `#/case/NA-999` graceful | PASS — "这份档案尚未完整送达 / 该案尚未通过全部门禁" | PASS |
| `#/nonsense` graceful | PASS — home view | PASS |
| `#/case/NA-00` (malformed id) graceful | PASS — home view | PASS |
| `#/case/na-001` (lowercase) graceful | PASS — home view | PASS |
| `#/case/NA-001` → `localStorage.clear()` → reload | PASS — loads, default order, 0 hints, 0/6 badge | PASS |
| No console errors / no third-party requests over the whole run | PASS | PASS |

Notes:

* Unknown or malformed routes silently fall back to the **home** view with `location.hash` left
  as-is. The page is never blank, but there is no "page not found" message — see issue #2.
* `NA-999` matches the `NA-\d{3}` router pattern, so it opens the case view and then shows a
  correct, friendly error ("该案尚未通过全部门禁"). Good behaviour.
* **Cold tab + Back:** if the tab's only prior history entry is the browser's own new-tab page,
  Back leaves the site to `about:blank` (`history.length=2`). This is standard browser behaviour,
  not an app defect — the app does not blank itself. Reaching a cold deep link from any real
  previous page (e.g. home) and pressing Back correctly returns to that page.

---

## Prioritized issues

| # | Severity | Issue | Evidence | Suggested fix |
|---|---|---|---|---|
| 1 | **Low** | Three render-blocking stylesheets on the critical path (`tokens.css`, `base.css`, `app.css`, ≈9.9 KB gzipped). | `raw/perf.json → renderBlocking` | Inline above-the-fold critical CSS; defer the rest. |
| 2 | **Low** | Unknown/malformed routes (`#/nonsense`, `#/case/NA-00`, `#/case/na-001`) silently render the **home** page with no explanation, while the URL still shows the bad route. Users who mistype a deep link may not realise they were redirected. | `raw/deeplink-*.json` | Render a small "找不到这份档案，已回到首页" notice, or redirect with `location.replace('#/')`. |
| 3 | **Info** | GitHub Pages sends only `Cache-Control: max-age=600`; repeat visits after 10 min revalidate every asset. | `raw/perf.json → cacheHeaders` | Nothing to fix on the app side (hosting limitation). Immutable hashed filenames would help if a build step were added. |
| 4 | **Info** | Large lazy episode-card images (~97–100 KB each) are preloaded as `<img loading="lazy">` on the cabinet; all 7 decode once scrolled. No impact on first load of a case. | `raw/perf.json`, lazy-load retest | None required. |

Nothing at **High** or **Critical**. No crash, no XSS, no uncaught exception, no third-party request,
no horizontal overflow, no undersized touch targets, no keyboard trap.

---

## What I could not test

* **Real iOS Safari / iPadOS Safari** — not available on this Windows host. No WebKit engine was run
  on a real Apple device, so iOS-specific behaviour (safe-area insets, `100vh` quirks, momentum
  scrolling, tap highlight) is **untested**.
* **Firefox / Gecko** — not installed and not run. Playwright's Firefox build was not exercised.
* **macOS Safari, Android Chrome on real hardware** — untested.
* **Screen readers** (NVDA/JAWS/VoiceOver) — only keyboard focus, focus visibility and
  `aria-expanded` toggling were checked, not actual assistive-technology output.
* **Lighthouse / Core Web Vitals** (LCP, CLS, TBT) — deliberately **not** measured; this report makes
  no Lighthouse claim.
* **Real mobile network conditions** — only Playwright CDP emulation on this host's connection, which
  adds its own latency to GitHub Pages. Absolute numbers would differ on real 4G.
* **WebKit via Playwright** — could have been simulated but was out of scope of the assigned engines
  (Chromium + Edge); no result is claimed for it.
* Edge was driven headless through Playwright's `channel="msedge"`; headed Edge with extensions,
  hardware acceleration and GPU rasterization may paint differently from the headless runs above.

---

## Raw data index (`work/qa/cross-browser/`)

| File | Contents |
|---|---|
| `raw/journey-chromium.json` / `raw/journey-msedge.json` | 34 journey checks per engine, incl. full Tab chain |
| `raw/deeplink-chromium.json` / `raw/deeplink-msedge.json` | 21 deep-link / refresh / back checks per engine |
| `raw/fuzz.json` | 7 malformed-JSON rows, user-visible text, console errors, interception proof, XSS findings |
| `raw/perf.json` | All 6 cold runs + warm runs, per-resource timings, cache headers, throughput probe |
| `raw/visual-parity.json`, `raw/layout-parity.json`, `raw/pixel-delta-summary.json` | Edge-vs-Chromium layout and pixel comparison |
| `raw/live-app.mjs` | The deployed `app.mjs` used for source verification |
| `raw/log-*.txt` | Console output of every run |
| `shots/` | Screenshots: verdict, mobile 390, fuzz per case, perf, parity + diff images |

Runners (re-executable, all write only inside this folder):
`qa_common.py`, `run_journey.py`, `run_perf.py`, `run_fuzz.py`, `run_deeplink.py`, `run_visual_parity.py`.
