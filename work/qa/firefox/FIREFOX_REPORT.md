# Firefox QA — 第零证物局 (zero-dossier-office)

**Target:** live build <https://tbj0623.github.io/zero-dossier-office/>
**Firefox tested:** **Mozilla Firefox 153.0** (Playwright bundled Gecko, build `firefox-1538`)
**Control engine:** Chromium 151.0.7922.34 (Playwright bundled) — same measurement code
**Harness:** Playwright for Python 1.62.0, `p.firefox.launch()`, Windows 11 x64
**When:** 2026-10-30 (Asia/Shanghai)
**Write scope:** everything below is under `work/qa/firefox/`. No product file was modified.

---

## Verdict

### **ship-with-fixes**

Firefox is **fully playable**. Every one of the ten mandated journey areas passes, all six
cases solve end-to-end in Gecko, and the layout is numerically identical to Chromium
(max box delta **1.85 px**, header/hero **0.00 px**). Nothing here blocks release.

There are **four divergences** from Chromium, and exactly one of them is a visual defect a
user can see: **`backdrop-filter` on the sticky header is not painted in Firefox**, so the
header becomes a flat tint instead of a blur. It is cosmetic, does not affect layout or
interaction, and does not fail on any other engine. Recommended: mark it **fix before the
next visual-polish pass**, not before shipping this one.

---

## Firefox version tested

| Item | Value |
|---|---|
| Browser | Firefox **153.0** |
| Build | Playwright `firefox-1538` (`%LOCALAPPDATA%\ms-playwright\firefox-1538`) |
| User agent | `Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0` |
| Install command | `python -m playwright install firefox` — succeeded first try, no `--with-deps` needed |
| Launch | `p.firefox.launch(headless=True)`; one `headed` run used for the compositor check |
| WebGL renderer inside Firefox | `ANGLE (Intel, Intel(R) HD Graphics 400 …)` — GPU raster is available |

### Build provenance (important — the live site was redeployed during this work)

The product was being edited by another agent while this QA ran. The deployed `app.mjs`
**changed hash mid-session** (`BUILD 33f9ae0c…` → `b29f5d61…`). A byte diff shows the two
deployed builds differ **only in the `BUILD` constant** — no functional change — and the
new local i18n work was **not** deployed. To keep the numbers honest, every suite was
re-run as one batch bracketed by hashes of the deployed files
(`raw/batch-provenance.json`): **`CHANGED DURING BATCH: none`**.

| Deployed file | sha256 (start = end) |
|---|---|
| `app.mjs` | `6ee1e4ef8fa316d6565fea0669c36aa942f2751a0fe148a7da84467896995932` |
| `index.html` | `061ba534e0aef203d8e7fcaa16c0df464d5fc8aea9a0061aef891c9c88afb88d` |
| `styles/app.css` | `c0df93a8a8f872f00021fedddb86a025a0d58851c58685bf3326406147eba721` |
| `styles/base.css` | `c258ba1bcb20e4532d6f7106f0e5b56830f599699f9d34c3573e808f4038b58c` |
| `styles/tokens.css` | `9bd5a66678e9711300e46a38d77f3406be3a59178869ddce0499525e8d81e4de` |

All results below are therefore from one consistent, verified build.
Raw data: `raw/journey-firefox.json`, `raw/six-cases-firefox.json`, `raw/firefox-specific.json`,
`raw/layout-parity.json`, `raw/batch-provenance.json`.

> **Note added after the batch (not part of my scope).** While I was writing this report another
> agent changed `site/styles/app.css`: the sticky header's `background` became an almost-opaque
> vertical gradient (`0.97 → 0.94`) with a comment explicitly citing this Firefox QA finding
> (“Gecko 上 backdrop-filter 有时能解析、却不上屏 … 像素差 0.0%”). That is a **product-side
> mitigation I did not ask for and did not verify**, and it was **not deployed** — the live site
> still serves the exact CSS I tested (`styles/app.css` sha256 `c0df93a8…`, re-checked after the
> batch). Everything in this report describes the **live build as tested**, not that local edit;
> the header-mitigation should get its own Firefox verification once it ships.

---

## Journey checks — table

Runner: `run_journey.py` (own runner; mirrors `tests/browser/e2e.py` assertions, driven on
`p.firefox.launch()`, against the live site). **43/43 PASS — all 10 mandated areas covered.**

| # | Check | Result | Notes |
|---|---|---|---|
| **1** | Home loads, correct title | **PASS** | `第零证物局｜雾港异常档案 · 原创互动推理` |
| 1 | `#cta-first` exists and is visible | **PASS** | label `打开第 001 号档案` |
| **2** | Cabinet shows exactly 6 case cards | **PASS** | 6 cards |
| **3** | NA-001 desk opens | **PASS** | `末班车的四张车票` |
| 3 | Exactly 3 evidence cards | **PASS** | 3 |
| 3 | One click moves exactly one slot (double-bind guard) | **PASS** | `['蓝票','绿票','红票','黄票'] → ['绿票','蓝票','红票','黄票']` |
| 3 | Click-to-select toggles off | **PASS** | `true → false` |
| 3 | All evidence cards expand (3/3) | **PASS** | `aria-expanded=[true,true,true]`, 3 bodies visible |
| **4** | Default arrangement is NOT the answer | **PASS** | start `['绿票','蓝票','红票','黄票']` ≠ answer `['红票','蓝票','黄票','绿票']` |
| **5** | Wrong submit → non-spoiler message | **PASS** | `档案仍有不一致：2 条关系未满足。` — no `→`, no answer leaked |
| 5 | Wrong submit preserves arrangement | **PASS** | board kept `['绿票','黄票','蓝票','红票']` |
| **6** | Three hints appear one at a time | **PASS** | counts `[1, 2, 3]` |
| 6 | Hints do not auto-arrange | **PASS** | order unchanged across all three hints |
| 6 | Hint button disables when exhausted | **PASS** | `disabled=true`, label `提示已全部解封` |
| **7** | Correct solve → verdict page | **PASS** | `档案归位。` |
| 7 | Logic recap block present | **PASS** | label `逻辑复盘 · 可由证据严格证明` |
| 7 | Story recap block present | **PASS** | label `档案后记 · 结案后补充记录` |
| 7 | Recaps are not duplicates | **PASS** | 336 ch vs 188 ch; two distinct `.recap-block` nodes |
| 7 | Logic recap cites E01/E02/E03 | **PASS** | none missing |
| 7 | Archive progress persists (1 / 6) | **PASS** | `已归档 1 / 6` |
| 7 | Arrangement restored after reload | **PASS** | `['航海图','银徽章','玻璃球','铜钥匙']` before and after reload |
| **8** | Tab reaches a focusable control | **PASS** | first stop `skip-link` |
| 8 | Tab order reaches slot controls | **PASS** | 10 stops inside `#slots`; first is slot 0 `act=down` |
| 8 | Tab order reaches action buttons | **PASS** | `btn-submit`, `btn-hint`, `btn-reset` all reached |
| 8 | **Enter** on a move button reorders | **PASS** | moved exactly one position |
| 8 | **ArrowUp** on a slot reorders | **PASS** | `['绿票','蓝票',…] → ['蓝票','绿票',…]` |
| 8 | **ArrowDown** on a slot reorders | **PASS** | reverses ArrowUp; ArrowUp on row 0 is a no-op |
| 8 | Focus ring visible on keyboard focus | **PASS** | `outline: solid 3px rgb(223,185,120)`, `:focus-visible` matches |
| 8 | Focus retained after keyboard reorder | **PASS** | focus stays on `act=pick`, slot 0 |
| **9** | 390×844 — no horizontal overflow | **PASS** | `scrollWidth 390 / clientWidth 390` |
| 9 | 390×844 — every interactive target ≥44 px | **PASS** | 0 undersized (see note below) |
| 9 | 360×800 / 768×1024 — overflow + 44 px | **PASS** | both clean |
| 9 | 390×844 touch tap reorders | **PASS** | real `tap()` on the down button |
| **10** | No third-party requests | **PASS** | 0 desktop, 0 mobile — every request same-origin |
| 10 | No console errors / page errors | **PASS** | 0 desktop, 0 mobile; 0 uncaught exceptions |

**Touch-target note (measured, broader than the inherited test).** `tests/browser/e2e.py` only
checks `#slots button, .actions button, .site-header button, .site-header a`. I re-audited
**every** interactive element (`a[href], button, input, select, textarea, summary,
[role=button], [tabindex]:not([tabindex="-1"])`) at 390×844 across **home, cabinet, desk,
manual, about, verdict, and the opened mobile nav** — 15/13/26/8/7/10 (+3 per nav-open) elements.
Result: **0 undersized, minimum 44×44 in every view** (`raw/dialog-and-targets.json`).

---

## Six-case solve — table

Runner: `run_six_cases.py`. Oracle = `expected_solution` from `cases/author/*.json`
(which I independently verified equals the constraint solver's unique solution for all six,
`raw/oracle-crosscheck.json`). Each case: fresh deep-link → default order checked ≠ answer →
all evidence expanded → board driven to the oracle through the real UI buttons → submit.

| Case | Items | Title | Default ≠ answer | Reached oracle | Verdict | Logic / story recap | Result |
|---|---|---|---|---|---|---|---|
| NA-001 | 4 | 末班车的四张车票 | PASS | PASS | `档案归位。` | 336 / 188 ch | **PASS** |
| NA-002 | 4 | 封存室的四格抽屉 | PASS | PASS | `档案归位。` | 345 / 166 ch | **PASS** |
| NA-003 | 5 | 静默分拣线上的五个包裹 | PASS | PASS | `档案归位。` | 412 / 176 ch | **PASS** |
| NA-004 | 5 | 灯塔没有亮起的第五盏灯 | PASS | PASS | `档案归位。` | 428 / 211 ch | **PASS** |
| NA-005 | 5 | 寄不到的第五封回信 | PASS | PASS | `档案归位。` | 454 / 183 ch | **PASS** |
| NA-006 | 6 | 第零号空白底片 | PASS | PASS | `档案归位。` | 445 / 192 ch | **PASS** |

**6 / 6 solved in Firefox.** After the sixth: progress badge `已归档 6 / 6`, and all six
cabinet cards show the `已归档` status. Zero console errors, zero third-party requests across
the whole run.

---

## Chromium vs Firefox numeric layout deltas — table

Runner: `run_layout_parity.py`. Identical code path in both engines: same route, same viewport,
`document.fonts.ready` + every `<img>` decoded + scroll-through-settle + 2×rAF, then measure.
DPR = 1. Delta = **Firefox − Chromium** in CSS px.

### Aggregate

| Viewport | Scene | Max abs delta (any element) | Worst element | Pixel diff >2/255 |
|---|---|---|---|---|
| 1440×900 | home | **0.35 px** | heroLede | 6.16 % |
| 1440×900 | cabinet | **0.09 px** | brand | 5.51 % |
| 1440×900 | case NA-001 | **0.35 px** | slots | 3.90 % |
| 768×1024 | home | **0.38 px** | heroLede | 7.16 % |
| 768×1024 | case NA-004 | **1.85 px** | slots | n/a (see below) |
| 390×844 | home | **0.23 px** | caseGrid | 10.22 % |
| 390×844 | case NA-004 | **0.29 px** | board | 6.54 % |
| 390×844 | cabinet | **0.09 px** | brand | n/a (see below) |

### The five elements the assignment asked about (Δ = Firefox − Chromium, px)

| Viewport | header (x/y/w/h) | hero h1 | evidence column | board | action buttons |
|---|---|---|---|---|---|
| **1440** home | `0 / 0 / 0 / 0` | `0 / 0 / 0 / −0.01` | — (no desk) | — | — |
| **1440** desk | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / +0.02 / +0.01 / −0.08` | `+0.01 / +0.02 / −0.01 / −0.18` | `+0.01 / −0.17 / −0.01 / 0` |
| **768** home | `0 / 0 / 0 / 0` | `0 / +0.02 / 0 / +0.02` | — | — | — |
| **768** desk | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / −0.02 / 0 / −0.81` | `0 / −0.83 / 0 / −0.78` | `0 / −1.61 / 0 / 0` |
| **390** home | `0 / 0 / 0 / 0` | `0 / −0.01 / 0 / −0.01` | — | — | — |
| **390** desk | `0 / 0 / 0 / 0` | `0 / 0 / 0 / 0` | `0 / +0.05 / 0 / −0.15` | `0 / −0.10 / 0 / +0.29` | `0 / +0.19 / 0 / 0` |

**The header is pixel-identical at every viewport (0.00 px).** Document `scrollWidth`,
`clientWidth` and `scrollHeight` are equal between engines at 1440 and 390; at 768 the desk
differs by 2 px of total document height and the cabinet at 390 by 1 px — i.e. sub-line rounding,
not a layout break (nothing overflows: `scrollWidth == clientWidth` in both engines everywhere).

### Why the pixel percentages look large — measured, not assumed

A raw pixel count is misleading here, so I characterised it three ways
(`raw/raster-vs-layout.json`):

| Measure | Measured value across scenes | What it means |
|---|---|---|
| Best integer translation of the whole image | `(0, −1)` is the *best* shift, and it makes the diff **worse** (−10 % to −64 % “gain”) | there is **no systematic block offset** — it is not a layout shift |
| 1 px Gaussian blur applied to both, then diff | mean delta drops **39–51 %** | the energy is concentrated at **glyph edges** |
| Share of differing pixels lying within 2 px of an image edge | **70.9 – 97.1 %** | differences hug glyph outlines = **font rasterisation** |

Visual crops (`shots/cmp-*.png`) confirm it: identical glyph positions and identical line breaks;
Chromium simply antialiases and hinting-adjusts CJK text differently from Gecko. This is the
same *class* of difference the earlier Edge-vs-Chromium report recorded (0.013–0.78 %), just
much larger in magnitude because Gecko and Blink rasterise CJK serif text very differently —
the delta is dominated by text, not by boxes.

Footnote: the two “n/a” rows are the scenes whose full-page screenshots differ in height by
1–2 px (768 desk: 2014 vs 2012; 390 cabinet: 3923 vs 3924), so a like-for-like pixel diff is
not defined; the box deltas for those scenes are in the table above.

### `text-wrap: balance` / heading layout

Measured by **ink**, not by element rects (`raw/h1-ink.json`): the hero `<h1>` renders with the
**same box height and the same two ink lines of the same width** in both engines.

| Viewport | Chromium box / ink lines | Firefox box / ink lines |
|---|---|---|
| 390 | 342×89 / 2 lines, widths `[178, 305]` | 342×89 / 2 lines, widths `[178, 304]` |
| 768 | 720×124 / 2 lines, widths `[248, 425]` | 720×124 / 2 lines, widths `[248, 425]` |
| 1440 | 720×155 / 2 lines, widths `[309, 531]` | 720×155 / 2 lines, widths `[309, 531]` |

No explosion, no overflow (`scrollWidth == clientWidth` at all three widths).

---

## Firefox-specific risks — each PASS/FAIL with evidence

### A. `<dialog>` + `showModal()` — **PASS**

| Check | Evidence |
|---|---|
| Dialog element exists, closed initially | `open=false` before use |
| `showModal()` really shows it | `open=true`, `display:block`, **440×188 px @ (500, 356)**, hit-testable at its centre |
| Modal is on the top layer | `elementFromPoint` outside the box returns the dialog/backdrop; the page header behind is **not** clickable (`headerClickable=false`) |
| Focus moves into the dialog | focus lands on `[data-confirm="ok"]` |
| Focus cannot escape | 10 × Tab + 6 × Shift+Tab: **every** stop stayed inside the dialog |
| Esc closes it | `open=false` |
| Esc = cancel | board **not** reset |
| Confirm resets | board changed; dialog closed |
| Cancel keeps the board | dialog closed, order unchanged |
| Console errors around dialog use | **0** |

Evidence: `shots/evidence-dialog-firefox.png`, `raw/firefox-specific.json`.
Caveat (see divergence #2): Tab **advances** correctly between the two dialog buttons, but
**does not wrap** from the last back to the first in Firefox.

### B. `prefers-reduced-motion` — **PASS**

Launched with `reduced_motion="reduce"` and with `"no-preference"` as a control.

| Check | Firefox (reduce) | Chromium (control) |
|---|---|---|
| Media query reports reduce | `true` | `true` |
| `.slot` transition duration | **`0.000001 s`** | `0.000001 s` |
| Max transition duration (slot/btn/header) | **`1e-06 s`** | `1e-06 s` |
| `--dur` token | **`0ms`** | `0ms` |
| `html` scroll-behavior | **`auto`** | `auto` |
| Control (no-preference) `.slot` duration | `0.22 s` | `0.22 s` |

The control run proves the measurement is live: without the preference the same property
reports 0.22 s. Transitions collapse to effectively zero under reduce.

### C. `localStorage` persistence — **PASS**

Router: same context, real reloads, plus a second tab and a fresh profile.

| Check | Evidence |
|---|---|
| App writes keys | `zd:v1:order:NA-003`, `zd:v1:progress` |
| Arrangement survives a real reload | `['纸鹤','星图','红盒','铜铃','蓝灯']` before and after; ≠ first-run order |
| Hint progress survives a reload | `1 → 1` |
| Shared with a second tab in the same context | same order |
| Fresh profile does **not** inherit | fresh context order == first-run order |
| Total keys leaked | only the two `zd:v1:*` keys |

### D. `@media (hover:hover)` drag-grip — **PASS**

| Context | `hover`/`pointer` | `.slot__grip` display | Size |
|---|---|---|---|
| 1440×900 desktop, mouse | `hover:hover`, `pointer:fine` | **`block`** | 20×44 |
| 390×844 touch | `hover:none`, `pointer:coarse` | **`none`** | **0×0** (no layout space) |
| 1440×900 **with touch** (coarse pointer) | `hover:none`, `pointer:coarse` | **`none`** | — |
| 900×900 narrow desktop (fine pointer) | `hover:hover` | **`none`** (min-width rule) | — |

Firefox exposes `(hover:none)`/`(pointer:coarse)` correctly under a touch context, and the
`(max-width: 980px), (hover: none)` media rule hides the grip exactly as intended on touch.

### E. `backdrop-filter` on the sticky header — **FAIL** (cosmetic; see divergence #1)

| Test | Chromium | Firefox 153.0 |
|---|---|---|
| `CSS.supports('backdrop-filter','blur(12px)')` | `true` | **`true`** |
| Computed value | `blur(12px) saturate(1.2)` | `blur(12px) saturate(1.2)` |
| **Does it actually paint a blur?** (synthetic checkerboard) | **yes** — pane ink energy `0.128` vs `6224` unblurred | **no** — pane energy `6224.065`, *identical* to no-filter (`ratio 1.0000`) |
| Real sticky header, content scrolled under it | blur visible (41.6 % of header pixels change when the property is removed) | **0.0 % of pixels change when the property is removed** |
| Headed vs headless | blurred in both | **not blurred in either** |

Visual proof: `shots/evidence-backdrop-filter.png` — in Chromium the checkerboard behind the
pane is visibly blurred; in Firefox the pane is a flat dark tint and the checkerboard is sharp
through it. WebGL reports a real GPU renderer in this Firefox, so it is not a “no compositor”
fallback.

**Scope, stated honestly:** MDN classifies `backdrop-filter` as **Baseline 2024 — “newly
available”, i.e. only reliably cross-browser since September 2024**, so this is genuinely a
recent feature and a gap is more plausible than for an old property. In *this*
Playwright-driven Firefox 153 build the declaration **parses and computes** correctly but is
**not painted**, in both headless and headed mode. Because I had no independent Mozilla build on
this host (no system Firefox is installed — verified), I cannot prove whether this is
harness-specific or would also happen on a user's Firefox. What is certain and measured: **in
the Firefox build under test, the header does not blur.** Flagged for a manual check on a real
Firefox before it is filed as a site bug.

### F. `text-wrap: balance` — **PASS** (identical rendering)
See the ink measurement above — same line breaks and widths at 390/768/1440.

### G. `aspect-ratio` on `.case-card__thumb` — **PASS**

| Viewport | Chromium w×h / ratio | Firefox w×h / ratio | Target 16/9 |
|---|---|---|---|
| 390 | 340×191.25 / **1.7778** | 340×191.25 / **1.7778** | 1.7778 |
| 768 | 350×196.88 / **1.7778** | 350×196.88 / **1.7777** | 1.7778 |
| 1440 | 380.66×214.11 / **1.7779** | 380.67×214.13 / **1.7777** | 1.7778 |

### H. `clamp()` font sizes — **PASS**

| Viewport | body | h1 | lede | card title | nav link |
|---|---|---|---|---|---|
| 390 — Chromium | 15.180 | 40.380 | 16.155 | 18.165 | 12.585 |
| 390 — **Firefox** | 15.167 | 40.367 | 16.150 | 18.150 | 12.583 |
| 768 — Chromium | 15.936 | 56.256 | 17.856 | 19.488 | 13.152 |
| 768 — **Firefox** | 15.933 | 56.250 | 17.850 | 19.483 | 13.150 |
| 1440 — Chromium | 16.320 | 70.400 | 19.200 | 20.800 | 13.760 |
| 1440 — **Firefox** | 16.320 | 70.400 | 19.200 | 20.800 | 13.760 |

Monotonic with viewport, inside the declared bounds, max difference **0.013 px**.

### I. `:focus-visible` — **PASS**

| Input modality | Chromium | Firefox |
|---|---|---|
| Keyboard Tab | `:focus-visible` matches, `outline: solid 3px rgb(223,185,120)` | **identical** |
| Mouse click | `:focus-visible` does **not** match, `outline-style: none` | **identical** |

Firefox correctly shows the ring for keyboard and suppresses it for pointer input.

### J. `scroll-padding-top` + `scrollIntoView` — **PASS for every in-app call; one divergence on a manual call**

* `scroll-padding-top` computes to `80px`; `scroll-margin-top: 80px` on `main`/`.view`; both engines agree.
* **Skip link → `#main`:** both engines land `mainTop = 65 = headerBottom`, gap `0` → **clear of the header**. PASS.
* **The app's own hint scroll** (`.scrollIntoView({block:'nearest'})` at 390): hint card fully in
  viewport in both engines (`[652.8, 740.3]` vs `[652.6, 740.1]`). PASS.
* **The app's own verdict scroll** (`#case-root.scrollIntoView({block:'start'})`): both engines end
  at `scrollY 77`, title at `167.34` / `167.37`, comfortably below the 65 px header. PASS.
* **Manual `#slots.scrollIntoView({block:'start'})` after scrolling to the bottom:** Chromium
  lands `#slots` at `79.5` (gap +14.5 below the header); **Firefox lands it at `43.3` (21.7 px
  underneath the header)**. Reproduced 3/3 runs. In isolation Firefox honours
  `scroll-padding-top` perfectly (synthetic page: target top exactly `80` in both engines), and
  the same call on a fresh page agrees (`84.5` vs `84.3`) — the divergence appears only for this
  target combined with a prior scroll. See divergence #3.

### K. `text-wrap: pretty` — **cosmetic divergence, no layout effect**

Firefox reports `CSS.supports('text-wrap','pretty') = false` and computes `text-wrap: wrap`
where Chromium computes `pretty`. Verified across **33 paragraphs** on 4 routes: **0 height or
line-count mismatches**, worst last-line-width share difference **0.039**
(`raw/textwrap-pretty.json`). Graceful degradation, no visible consequence.

---

## Divergences from Chromium

| # | Severity | Divergence | Evidence | User impact |
|---|---|---|---|---|
| 1 | **Low** (cosmetic) | **`backdrop-filter` is not painted on the sticky header** — Firefox renders a flat 84 %-opaque tint instead of a blur. Parses and computes correctly; simply no blur on screen. (MDN: this property is only Baseline-2024 “newly available”.) | `raw/firefox-specific.json`, `raw/backdrop-and-dialog-final.json`, `shots/evidence-backdrop-filter.png`. Synthetic pane: ink energy `6224` (= no filter) in Firefox vs `0.128` in Chromium. Real header: removing the property changes **0.0 %** of pixels in Firefox vs **41.6 %** in Chromium. Same in headless and headed. | The header looks slightly flatter/less “frosted” over scrolling content. No readability, layout or interaction change; the 0.84 alpha keeps text legible. |
| 2 | **Info** (accessibility nuance) | **Dialog Tab does not wrap around.** Tab advances correctly `cancel → ok`, but a further Tab keeps focus on `ok` instead of cycling back to `cancel`. Chromium wraps (via a `body` stop and back in). Focus never escapes the modal in either engine. | `raw/backdrop-and-dialog-final.json`, `raw/dialog-minimal-repro.json` (reproduced with a **minimal `<dialog>` and no site code**, so the tab-cycle behaviour is Gecko/Playwright's, not the site's). | A keyboard user pressing Tab repeatedly stays on the confirm button — they cannot reach “cancel” with Tab alone (Shift+Tab still works, and Esc closes). Minor; worth knowing for a11y sign-off. |
| 3 | **Low** | **`scrollIntoView({block:'start'})` on `#slots` lands 36 px higher in Firefox** when the page was already scrolled to the bottom: `#slots` top `43.28` vs `79.53`, i.e. **21.7 px of the board sits under the 64 px sticky header** (Chromium: 14.5 px clear). Reproduced 3/3. Firefox honours `scroll-padding-top` correctly in isolation and on a fresh page, and every **in-app** scroll call (verdict, hint, skip link) is correct in both engines. | `raw/scroll-into-view-isolated.json`, `raw/scroll-anomaly.json`, `raw/app-scroll-calls.json` | Only reachable by a manual `scrollIntoView` on that specific target after a prior scroll; no shipped UI path does this. Cosmetic if it ever occurs (the first control still hit-tests to the real button). |
| 4 | **Info** (cosmetic) | **`text-wrap: pretty` unsupported** — Firefox falls back to `wrap`. | `raw/textwrap-pretty.json`, `raw/paint-probe.json` | None measured: 0 line/height mismatches across 33 paragraphs; worst last-line difference 0.039 of the column width. |

**Not a divergence:** the 4–10 % raw pixel difference in full-page screenshots. Measured to be
font rasterisation, not layout — no systematic shift (best integer translation makes it worse),
39–51 % of the delta disappears under a 1 px blur, and 71–97 % of differing pixels sit on glyph
edges. Box geometry agrees to ≤1.85 px and the header/hero to 0.00 px.

**Count: 4 divergences** (1 Low cosmetic, 1 Low conditional, 1 Info a11y, 1 Info cosmetic).
**Blocking: none.**

---

## What I could not test

* **A real Mozilla-branded Firefox build.** No system Firefox exists on this host (checked the
  three standard install paths and the HKLM registry key — absent), and I was not permitted to
  install outside my write scope. Everything here is Playwright's bundled Gecko 153.0. This
  matters most for divergence #1 (`backdrop-filter`): I cannot tell whether the missing blur is
  specific to this build or would also affect a user's Firefox, so it should be re-checked
  manually on a real Firefox before being filed as a site bug.
* **Screen readers** (NVDA/JAWS) — only keyboard focus, focus-visible and dialog focus
  containment were checked, not assistive-technology output.
* **Real mobile hardware / iOS / Android Firefox** — the 390×844 run is a Playwright touch
  context on a desktop Gecko build, not a phone. `hover:none`/`pointer:coarse` are emulated
  correctly, but real mobile Gecko may differ in scrolling and font fallback.
* **Firefox extension / hardened configurations** (e.g. `privacy.resistFingerprinting`, which
  changes media-query and canvas behaviour) — not exercised.
* **Zoom / reflow at 200 %** and **`forced-colors: active`** in Firefox — out of scope for this
  pass (the CSS has a forced-colors block; it was not exercised in Gecko).
* **Screen-reader announcement of the three progressive hints** — the hint cards are plain
  `div`s in a `role="region"`; no live-region announcement was verified in Firefox.
* **Long-run stability** — each suite is a single session; no multi-hour soak.

---

## Raw data index (`work/qa/firefox/`)

| File | Contents |
|---|---|
| `raw/journey-firefox.json` | 43 journey checks across the 10 mandated areas, incl. full Tab chain |
| `raw/six-cases-firefox.json` | per-case oracle/reached order, default-vs-answer, verdict, recap lengths |
| `raw/firefox-specific.json` | dialog, reduced-motion, localStorage, hover-grip (30 checks) |
| `raw/layout-parity.json` | per-element bounding boxes + computed fonts, Chromium vs Firefox, 8 scenes |
| `raw/pixel-analysis.json`, `raw/raster-vs-layout.json` | pixel diff statistics; rasterisation-vs-layout tests |
| `raw/paint-probe.json`, `raw/text-probe.json`, `raw/h1-ink.json` | CSS support matrix, fonts, heading ink extents |
| `raw/css-risks.json`, `raw/css-risks-confirm.json`, `raw/css-risks-final.json` | the six named CSS risks, incl. the corrected re-measurements |
| `raw/backdrop-and-dialog-final.json`, `raw/dialog-minimal-repro.json` | backdrop headless/headed matrix; minimal `<dialog>` repro |
| `raw/scroll-into-view-isolated.json`, `raw/scroll-anomaly.json`, `raw/app-scroll-calls.json` | scroll-padding isolation, 3× repeat, and the app's own scroll calls |
| `raw/dialog-and-targets.json` | comprehensive 44 px touch-target audit at 390 across 6 views |
| `raw/oracle-crosscheck.json` | `cases/author/expected_solution` == independent solver, all six |
| `raw/batch-provenance.json`, `raw/live-provenance.json`, `raw/live-app.mjs` | deployed-build hashes before/after the batch; the two deployed builds |
| `raw/log-*.txt` | full stdout/stderr of every suite |
| `shots/` | 92 images: per-view engine screenshots, per-case verdicts, dialog, mobile, `cmp-*` crops, `evidence-*` |

Runners (re-executable, write only inside this folder):
`run_all.py` (batch + provenance gate), `run_journey.py`, `run_six_cases.py`,
`run_firefox_specific.py`, `run_layout_parity.py`, plus the `probe_*` / `analyse_*` scripts.
