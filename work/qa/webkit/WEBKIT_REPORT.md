# WebKit QA — 第零证物局 (zero-dossier-office)

**Target:** local server build `http://127.0.0.1:8140` (the built site, so results are not
affected by GitHub Pages deployment lag)
**WebKit tested:** **WebKit 26.5** (Playwright bundled `webkit-2336`)
**Control engines:** Chromium 151.0.7922.34 · Firefox 153.0 (Playwright bundled, same machine)
**Harness:** Playwright for Python 1.62.0, `p.webkit.launch()`, Windows 11 x64
**When:** 2026-10-30 (Asia/Shanghai)
**Write scope:** everything below is under `work/qa/webkit/`. No product file was modified.

---

## Verdict

### **ship-with-fixes**

The game is **fully playable in WebKit**. All 34 core-journey assertions pass, **all six cases
solve end-to-end through the real UI**, and layout parity against Chromium is essentially exact
(max box delta **1.14 px**, zero measurements over the 2 px threshold). Nothing here prevents
shipping.

**But:** Playwright's WebKit is **not** Safari. See *What this proves* below before reading the
verdict as "Safari is fine".

**One engine-level accessibility divergence was found and is now fixed.** On the initial build,
plain `<a href>` elements were not in WebKit's Tab order (Safari's factory default), so a
keyboard-only Safari user could reach **zero of the 8 home-page links** and could not navigate
between pages at all. The product added `tabindex="0"` to its links mid-session; on the final build
Tab reaches **11 of 11** links and the WebKit Tab order is now **identical to Chromium's**. Re-verified
after the change — see Divergence 1 and the build-provenance table.

The remaining findings are one cosmetic engine difference (`text-wrap: pretty`) and three
informational notes. **Nothing outstanding is a blocker.**

### What this does and does not prove

| This report proves | This report does NOT prove |
|---|---|
| The site runs on **WebKit 26.5**, the engine core Safari ships | Anything about a specific **Safari release** on macOS or iOS |
| Behaviour of WebKit's **Playwright build on Windows** | Safari's **Compositor / Metal** paths, which do not run here |
| `<dialog>`, `100dvh`, `:focus-visible`, `aspect-ratio`, `clamp()`, `gap` behave as measured | **Real iOS Safari** (dynamic toolbar, rubber-band, safe-area, touch) |
| Layout parity vs Chromium to **≤1.14 px** | VoiceOver / real AT announcements |
| AX tree as **Playwright's WebKit** exposes it | Safari's own AX API surface, which differs |

> **Not "Safari verified".** Say: *WebKit (Playwright build `webkit-2336`, engine 26.5) verified;
> real Safari unverified.*

---

## WebKit version actually tested

| Item | Value |
|---|---|
| Browser | **WebKit 26.5** |
| Build | Playwright `webkit-2336` (`%LOCALAPPDATA%\ms-playwright\webkit-2336`) |
| User agent | `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.5 Safari/605.1.15` |
| Install | `python -m playwright install webkit` — succeeded first try, exit 0, **no `--with-deps`**, no package manager, no sandbox escalation |
| Launch | `p.webkit.launch(headless=True)`; headed run used once to confirm the blur result is not a headless artifact |
| WebGL renderer reported inside WebKit | `Apple GPU` (n/a on Windows — see divergence 4) |

### Build provenance (important — the product was fixed mid-session)

The site was being edited by another agent while this QA ran. **Two builds were tested**, and
every number in this report is labelled with which one it came from:

| Build | `app.mjs` sha256 | `index.html` sha256 | What it is |
|---|---|---|---|
| **A** (initial) | `5195a988f41db115…` | `5891d9fddb76b406…` | BUILD `8f993e8` — no `tabindex` on links |
| **B** (final) | `d0676119eb030765…` | `3f7036921052f257…` | BUILD `78b2128` — **17 `tabindex="0"` added** to links |

`styles/app.css`, `styles/base.css`, `styles/tokens.css`, `i18n.mjs` and `engine/solver.mjs` were
**byte-identical across both builds** — only `app.mjs` and `index.html` changed, and the change was
the Tab-order fix described in Divergence 1.

**What was re-run on build B after the change:** core journey (**34/34 PASS**), six-case solve
(**6/6**), all CSS risks (same 37/38 — only the engine-limited backdrop row fails), layout parity
(same **1.14 px** max, 0 over threshold), and the Tab audit (**now 7/7 PASS**).
The only results that differ between builds are the Tab-reachability ones, which are reported for
both. Raw evidence for the pre-fix run is kept in `raw/pre-fix/`.

| Build B served file | sha256 |
|---|---|
| `index.html` | `3f7036921052f25787759deb86d6cb1d0d36a8a308a79a3f32c0f38434b2bf2d` |
| `app.mjs` | `d0676119eb030765a8e2b3658c26d835d7b29e009b0f899583cc107e80262280` |
| `styles/app.css` | `2525329b941fed56c4c91fe7720d64af3174abf2610c87ba692a1bead0b4156b` |
| `styles/base.css` | `b326b196d9a965540b696f6b4e795b03480d56a6979e8afef7ecdbdcda21ef96` |
| `styles/tokens.css` | `9bd5a66678e9711300e46a38d77f3406be3a59178869ddce0499525e8d81e4de` |
| `i18n.mjs` | `19544b5bc082568d1c72bed098bfbecf0e2aaf4f84f63b4e9475287622ec326c` |
| `engine/solver.mjs` | `94e7cbb950f878987ae9c38421d6d2eac23b699682aa9e4dfb6537dd7531cedc` |

All runs point at the **built** site served from `127.0.0.1:8140` (`dist/`), per instructions.

Runner: `run_journey.py` — own runner, mirrors `tests/browser/cross_engine.py` and
`tests/browser/e2e.py`, launched with `p.webkit.launch()`. Raw: `raw/journey-webkit.json`.

---

## Core journey — table

**34 / 34 PASS.** Results below are from the **final build B** (`app.mjs` `d0676119…`); the same
34 checks also passed on build A before the Tab fix landed.

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | Home loads, has a title | **PASS** | `第零证物局｜雾港异常档案 · 原创互动推理` |
| 1 | `#cta-first` visible | **PASS** | label `打开第 001 号档案` |
| 1 | `#view-home` is the active view | **PASS** | `data-active="true"` |
| 2 | Header `position: sticky` | **PASS** | computed `sticky` |
| 2 | Stays at `top=0` after scrolling 600 px | **PASS** | `top=0.00`, `scrollY=600`, header h=65.0 |
| 2 | Header does not move between scroll 0 and 600 | **PASS** | before `0.00` → after `0.00` |
| 3 | Cabinet shows exactly 6 case cards | **PASS** | `#view-cabinet .case-card` → 6 |
| 3 | The six cards link to the six cases | **PASS** | `#/case/NA-001` … `#/case/NA-006` in order |
| 4 | NA-001 desk opens | **PASS** | title `末班车的四张车票` |
| 4 | 3 evidence cards | **PASS** | 3 |
| 4 | All 3 expand | **PASS** | 3/3 bodies visible, `aria-expanded` = `["true","true","true"]` |
| 5 | Default arrangement ≠ answer | **PASS** | start `['蓝票','绿票','红票','黄票']` vs answer `['红票','蓝票','黄票','绿票']` |
| **6** | **One click moves exactly one slot** | **PASS** | `['蓝票','绿票','红票','黄票']` → `['绿票','蓝票','红票','黄票']` — exactly the expected single swap |
| 6b | Reverse click also moves exactly one | **PASS** | returns to the original order |
| 6c | Pick two slots → exactly one swap | **PASS** | `['蓝票','绿票','红票','黄票']` → `['红票','绿票','蓝票','黄票']` |
| 7 | ArrowDown reorders the focused slot | **PASS** | slot 0 moves down one |
| 7b | ArrowUp returns it | **PASS** | back to original |
| 7c | ArrowUp on slot 0 does **not** wrap | **PASS** | order unchanged (no wrap-around bug) |
| 8 | Three hints appear one at a time, counts `[1,2,3]` | **PASS** | `[1, 2, 3]` |
| 8b | Hints do **not** auto-arrange | **PASS** | order identical before/after |
| 8c | Hint button disabled once exhausted | **PASS** | `disabled` present |
| 8d | Three hint texts differ | **PASS** | 3 distinct strings |
| 9 | Correct solve → verdict page | **PASS** | `.verdict` appears, title `档案归位。` |
| 9b | Verdict title correct | **PASS** | `档案归位。` |
| 9c | Two **distinct** recap blocks | **PASS** | `逻辑复盘 · 可由证据严格证明` + `档案后记 · 结案后补充记录` |
| 9d | Logic and story are separated | **PASS** | different headings, `336` vs `188` chars |
| 9e | Logic recap covers every evidence item | **PASS** | `E01 E02 E03` all present |
| 10 | No console errors | **PASS** | 0 |
| 10b | No uncaught page errors | **PASS** | 0 |
| 10c | No failed requests | **PASS** | 0 |
| 10d | No third-party requests | **PASS** | 0 — every request stayed on `127.0.0.1:8140` |

Third-party check repeated on **six scenes** (`home`, `cabinet`, `NA-001`, `NA-006`, `manual`,
`about`): 93 resources total, **0 external requests, 0 third-party resources, 0 failed requests,
0 console errors** (`raw/network-all-scenes.json`).

---

## Six-case solve — table

**6 / 6 solved** through the real UI (`run_six_cases.py`, `raw/six-cases-webkit.json`).
Each case's `expected_solution` from `cases/author/*.json` was also cross-checked against an
independent constraint solver over `cases/public/*.json` — **all six agree** (`author == solver`).

| Case | Slots | Evidence | Start ≠ answer | One click = one slot | Solved in WebKit | Recap blocks | Winning order |
|---|---|---|---|---|---|---|---|
| NA-001 | 4 | 3 | PASS | PASS | **PASS** | 2 | 红票 → 蓝票 → 黄票 → 绿票 |
| NA-002 | 4 | 3 | PASS | PASS | **PASS** | 2 | 航海图 → 银徽章 → 铜钥匙 → 玻璃球 |
| NA-003 | 5 | 4 | PASS | PASS | **PASS** | 2 | 红盒 → 纸鹤 → 铜铃 → 星图 → 蓝灯 |
| NA-004 | 5 | 4 | PASS | PASS | **PASS** | 2 | 铜铃 → 值班簿 → 玻璃罩 → 旧透镜 → 海图 |
| NA-005 | 5 | 4 | PASS | PASS | **PASS** | 2 | 晨雾邮笺 → 港口便条 → 红蜡封信 → 夜航申请 → 空白回邮 |
| NA-006 | 6 | 4 | PASS | PASS | **PASS** | 3 | 钟楼影 → 纸船影 → 玻璃影 → 雨幕影 → 灯塔影 → 空白底片 |

Final progress badge after all six: **`已归档 6 / 6`**. No console errors or page errors during
the whole six-case run. NA-006 shows 3 recap blocks because it additionally renders the
`终章 · 第零号` finale block — expected.

---

## WebKit-specific risks — each PASS/FAIL with the measured evidence

Runner `run_css_risks.py` → **37 PASS / 1 FAIL** (`raw/css-risks-webkit.json`).
The single FAIL is the backdrop-filter row, and it is a genuine engine limitation, not a
product defect — explained below.

### 1. `backdrop-filter` on the sticky header — **FAIL (engine), product unaffected**

| Probe | Result |
|---|---|
| `CSS.supports('backdrop-filter','blur(1px)')` | **true** |
| computed `backdrop-filter` on `.site-header` | `blur(12px) saturate(1.2)` |
| **Does WebKit paint it?** | **NO** |
| Pixel A/B (translucent overlay, blur on vs off) | **mean abs diff `0.000` px**, HF energy `23.543` → `23.543` |

Methodology is validated on the same page and same CSS with all three engines
(`raw/backdrop-methodology-cross-engine.json`):

| Engine | mean abs diff (blur on vs off) | HF energy | Painted? |
|---|---|---|---|
| Chromium 151.0.7922.34 | **114.495** | `33.37` → `0.22` | **yes** |
| WebKit 26.5 | **0.000** | `33.37` → `33.37` | **no** |
| Firefox 153.0 | **0.000** | `33.37` → `33.37` | **no** |

A control test proves WebKit *can* blur — `filter: blur(8px)` on a child changed pixels by
`104.89` — so this is specific to the **backdrop** path, not to blurring in general. Headed and
headless runs give the identical result, so it is not a headless-compositor artifact.

**Product impact: none, and this is by design.** The header carries a near-opaque gradient
fallback (`linear-gradient(rgba(8,26,36,0.97), rgba(5,17,24,0.94))`), so with or without the
blur it is a solid, readable bar:

| Header text | Colour | Contrast vs darkest header stop |
|---|---|---|
| brand name | `rgb(242,236,224)` | **16.23 : 1** |
| brand sub-line | `rgb(223,185,120)` | **10.32 : 1** |
| nav link | `rgb(223,185,120)` | **10.32 : 1** |
| language button | `rgb(185,200,197)` | **11.03 : 1** |

All far above WCAG AA 4.5:1. **Readability requirement: PASS.** Header stays `sticky` with
`top: 0` and keeps its gradient background. → *Divergence 3.*

### 2. `<dialog>` + `showModal()` — **PASS**

| Check | Result |
|---|---|
| `HTMLDialogElement` exists | **PASS** (`true`) |
| `showModal` is a function | **PASS** (`true`) |
| Dialog opens and is `:modal` | **PASS** — `open=true`, `:modal=true`, rect `{x:500, y:356, w:440, h:188}` |
| `::backdrop` rendered | **PASS** — `rgba(2, 8, 12, 0.72)` |
| Initial focus lands in the dialog | **PASS** — `activeElement` = the confirm button (`data-confirm="ok"`) |
| Focus **trap** — never reaches page content outside the modal | **PASS** — 0 escapes across 10 Tabs + 4 Shift+Tabs |
| Page behind is inert | **PASS** — programmatic `#btn-submit.focus()` is **stolen back** into the dialog (`focusStolen=true`) |
| **Esc closes** | **PASS** — `open=false`, `display:none` |
| Cancel path leaves the arrangement untouched | **PASS** — order identical, dialog closed |
| Dialog fits a 390 px viewport | **PASS** — `{x:38, y:339, w:314, h:166}`, both buttons 44 px tall |

> Note on method: every engine parks focus on `<body>` or on the `<dialog>` element itself at the
> wrap point (Chromium does exactly the same). The meaningful assertion is therefore "focus never
> lands on page content outside the dialog", which is what is measured here — asserting "focus is
> always inside the dialog element" would fail on Chromium too and would be a false positive.

### 3. `100dvh` — **PASS**

`hero { min-height: min(88dvh, 780px) }`:

| Viewport | computed `min-height` | hero height | expected `min(0.88·vh, 780)` |
|---|---|---|---|
| 1440×900 | `780px` | 780.00 | 780.00 |
| 768×1024 | `780px` | 780.00 | 780.00 |
| 390×844 | `742.72px` | 742.72 | 742.72 |
| 390×500 | `440px` | 528.63 (content exceeds min) | 440.00 |

Not 0, not huge, tracks `vh` correctly. `body { min-height: 100dvh }` also resolves to exactly the
viewport height (`900px`, `1024px`, `844px`, `500px`). → PASS.

### 4. `:focus-visible` — **PASS**

| Path | Result |
|---|---|
| Keyboard **Tab** → focused element matches `:focus-visible` | **PASS** — `outline: solid 3px`, matches `true` |
| Keyboard focus on a button (`#btn-undo`) | **PASS** — `outline: solid 3px`, matches `true` |
| **Mouse click** on a button | **PASS** — matches `false`, `outline-style: none` |

The selector behaves exactly as intended: rings on keyboard, none on pointer.
(The skip-link also gets `outline: solid` when focused — see risk 9.)

### 5. `text-wrap: balance` / `pretty` — **PASS (with a real divergence in `pretty`)**

| Engine | `balance` | `pretty` | computed on `h1` | computed on `p` |
|---|---|---|---|---|
| WebKit 26.5 | supported | **supported** | `balance` | `pretty` |
| Chromium 151 | supported | supported | `balance` | `pretty` |
| Firefox 153 | supported | **NOT** supported | `balance` | `wrap` |

Heading layout stays sane in every case: **no** zero-height boxes, **no** horizontal overflow,
**no** heading shorter than one line, and the hero `h1` renders exactly **2 visual lines**
(155 px box ÷ 77.44 px line-height) — *identical* in WebKit and Chromium, including the exact
same line widths `[362.4, 362.4, 720, 579.8]`.

The divergence is in `pretty` on body copy — see **Divergence 2**.

### 6. `aspect-ratio` on `.case-card__thumb` — **PASS**

| Viewport | cards measured | expected ratio | measured | max error | `<img>` fill delta |
|---|---|---|---|---|---|
| 390×844 | 6 | 1.7778 | **1.778** (340 × 191.25) | **0.000** | 0 px |
| 768×1024 | 6 | 1.7778 | **1.778** (350 × 196.88) | **0.000** | 0 px |
| 1440×900 | 6 | 1.7778 | **1.778** (380.66 × 214.11) | **0.000** | 0 px |

Every card is exactly 16:9; the cover image fills its box with **0 px** overflow at all three
widths.

### 7. `clamp()` font sizes — **PASS, exact match to Chromium**

| Viewport | body (WebKit) | body (Chromium ref) | Δ | h1 (WebKit) | h1 (Chromium ref) | Δ |
|---|---|---|---|---|---|---|
| 390×844 | **15.180** | 15.180 | **0.000** | **40.380** | 40.380 | **0.000** |
| 768×1024 | **15.936** | 15.936 | **0.000** | **56.256** | 56.256 | **0.000** |
| 1440×900 | **16.320** | 16.320 | **0.000** | **70.400** | 70.400 | **0.000** |

Zero deviation at all three widths (tolerance was ±0.75 px). Raw values:
`raw/css-risks-webkit.json` → `clamp.measured`.

### 8. `gap` (flexbox), `inset`, `place-items` — **PASS**

| Check | Measured | Verdict |
|---|---|---|
| flex `gap` — `.slot__actions` (3 buttons, `gap: 4px`) | measured gaps **`[4, 4]`** | **PASS** |
| flex/grid `gap` — `.actions` (4 buttons, `gap: 8px`) | measured gaps **`[8, 8, 8]`** | **PASS** |
| grid `gap` — `#slots` (`gap: 8px`) | measured pitch **16 px** = `gap 8` + `li { margin-bottom: 8px }` from base.css; matches `expectedPitch` **exactly** | **PASS** |
| every slot row has non-zero height | `[65.2, 65.2, 65.2, 65.2]` | **PASS** |
| `place-items: center` — `.slot__index` | 34 × 34, perfectly square | **PASS** |
| no layout collapse in `.desk/.evidence-col/.order-col/.board/#slots/.actions` | 0 zero-sized containers | **PASS** |

`inset` is supported (`CSS.supports('inset','0')` → true) and the `inset:0` pseudo-element
overlays (`.hero::before/::after`, `.case-card__thumb::after`) render — the hero background image
and gradient are visibly present in the screenshots and are what the crops compare.

> The `#slots` 16 px pitch is **not** a gap bug: `base.css` gives every `li` `margin-bottom: 8px`,
> which stacks on top of the 8 px grid gap. Chromium produces the identical 16 px. Recorded
> because a naive "gap should equal the declared 8 px" assertion would flag it falsely.

### 9. `overscroll-behavior` / `scroll-padding-top` — **PASS**

| Check | Result |
|---|---|
| `CSS.supports('overscroll-behavior','contain')` | **false** — WebKit does not support it |
| Does the site use it anywhere? | **No** — 0 occurrences in `site/` (grep) |
| `scroll-padding-top` supported | **true** |
| computed `scroll-padding-top` on `<html>` | `80px` |
| `scrollIntoView({block:'start'})` on `.board` clears the sticky header | **PASS** — `board.top = 284.97` vs `header.bottom = 65` |
| skip-link: CSS reveal works when focused | **PASS** — `top` goes `-200` → `16`, visible, `outline: solid` |
| skip-link: Enter jumps to `#main` and is not hidden by the header | **PASS** — `main.top = 65` = `header.bottom = 65` |
| skip-link: reachable by Tab | **PASS on build B** (`FAIL on build A` — it is an `<a href>`; fixed by `tabindex="0"`, see Divergence 1) |

`overscroll-behavior` is unsupported, but since the product never declares it, no behaviour
changes. → recorded as *Divergence 4 (informational)*.

### 10. iOS-specific: `-webkit-tap-highlight-color` + every touch target at 390×844 — **PASS**

`-webkit-tap-highlight-color` is **not** a supported CSS property in this WebKit build
(`CSS.supports` → false; assigning it yields an empty computed value), and the product never
declares it — so there is no missing rule to fix. On a real iPhone the system default grey flash
may appear; that is cosmetic and cannot be observed here. → *Divergence 5 (informational)*.

**Touch targets — every interactive element measured, not a sample**
(`raw/touch-target-audit.json`, viewport 390×844, mobile + touch emulation):

| Scene | interactive elements | under 44 px | min W × H |
|---|---|---|---|
| home | 15 | **0** | 44 × 44 |
| cabinet | 13 | **0** | 44 × 44 |
| desk (NA-001) | 30 | **0** | 44 × 44 |
| manual | 8 | **0** | 44 × 44 |
| about | 7 | **0** | 44 × 44 |
| mobile nav (opened) | 4 | **0** | 44 × 44 |
| confirm dialog | 2 | **0** | 80.4 × 44 and 110.7 × 44 |

**73 / 73 interactive elements are ≥44×44 px.** No undersized target at all.

**Bonus, tested while probing the media-query paths:** with `reduced_motion="reduce"` the
`--dur` token resolves to `0ms` and `.slot` transitions become `0.000001s` (Chromium:
`1e-06s`) — identical behaviour; with `color_scheme="dark"` the page background resolves to
`rgb(8, 24, 33)` and `color-scheme: dark` applies. **PASS** (`raw/reduced-motion-dark.json`).

---

## Layout parity vs Chromium — numeric table

Same runner, same viewports, same scenes, same settle routine, identical selectors
(`run_layout_parity.py`, `raw/layout-parity.json`). Deltas are **WebKit − Chromium**, in px.

**Across 9 scenes × 22 element selectors (198 measurement slots, 108 of which resolve to a real
element in their scene): max |delta| = 1.14 px, 0 measurements over 2 px.**

### Mandated elements

| Scene | Element | WebKit (x, y, w, h) | Chromium (x, y, w, h) | Δx | Δy | Δw | Δh | >2 px? |
|---|---|---|---|---|---|---|---|---|
| home-1440 | header | 0, 0, 1440, 65 | 0, 0, 1440, 65 | 0.00 | 0.00 | 0.00 | 0.00 | no |
| home-1440 | hero h1 | 130, 253.59, 720, 154.84 | 130, 253.53, 720, 154.88 | 0.00 | **+0.06** | 0.00 | −0.04 | no |
| home-768 | header | 0, 0, 768, 65 | 0, 0, 768, 65 | 0.00 | 0.00 | 0.00 | 0.00 | no |
| home-768 | hero h1 | 24, 268.30, 720, 123.75 | 24, 268.23, 720, 123.75 | 0.00 | **+0.07** | 0.00 | 0.00 | no |
| home-390 | header | 0, 0, 390, 65 | 0, 0, 390, 65 | 0.00 | 0.00 | 0.00 | 0.00 | no |
| home-390 | hero h1 | 24, 253.42, 342, 88.81 | 24, 253.39, 342, 88.81 | 0.00 | **+0.03** | 0.00 | 0.00 | no |
| case-1440 | evidence column | 130, 281.73, 522.94, 600.39 | 130, 281.78, 522.94, 600.56 | 0.00 | **−0.05** | 0.00 | −0.17 | no |
| case-1440 | board | 676.94, 281.73, 633.06, 595.73 | 676.94, 281.78, 633.06, 595.98 | 0.00 | **−0.05** | 0.00 | −0.25 | no |
| case-1440 | action buttons | 693.94, 758.47, 599.06, 44 | 693.94, 758.77, 599.06, 44 | 0.00 | **−0.30** | 0.00 | 0.00 | no |
| case-768 | evidence column | 24, 276.36, 720, 544.02 | 24, 276.44, 720, 544.53 | 0.00 | **−0.08** | 0.00 | −0.51 | no |
| case-768 | board | 24, 844.38, 720, 621.98 | 24, 844.97, 720, 622.53 | 0.00 | **−0.59** | 0.00 | −0.55 | no |
| case-768 | action buttons | 41, 1295.36, 686, 96 | 41, 1296.50, 686, 96 | 0.00 | **−1.14** | 0.00 | 0.00 | no |
| case-390 | evidence column | 24, 308.52, 342, 676.92 | 24, 308.55, 342, 677.03 | 0.00 | **−0.03** | 0.00 | −0.11 | no |
| case-390 | board | 24, 1009.44, 342, 713.97 | 24, 1009.58, 342, 713.64 | 0.00 | **−0.14** | 0.00 | +0.33 | no |
| case-390 | action buttons | 41, 1500.41, 308, 148 | 41, 1500.22, 308, 148 | 0.00 | **+0.19** | 0.00 | 0.00 | no |

Cabinet header rows are identical (Δ 0.00) in all three viewports. `document.scrollWidth` matched
`clientWidth` in **every** scene on **both** engines — **no horizontal overflow** anywhere.

The worst delta in the whole run (1.14 px) is a vertical offset of the action-button block at
768 px; it comes from the `text-wrap: pretty` line-break difference above the board (see
Divergence 2) shifting content by ~1 px, and is far below the 2 px threshold.

### Side-by-side crops

| Scene | Side-by-side (WebKit top / Chromium bottom) | Diff heatmap |
|---|---|---|
| home 1440 | `crops/side-home-1440.png` | `crops/diff-home-1440.png` |
| home 768 | `crops/side-home-768.png` | `crops/diff-home-768.png` |
| home 390 | `crops/side-home-390.png` | `crops/diff-home-390.png` |
| cabinet 1440 | `crops/side-cabinet-1440.png` | `crops/diff-cabinet-1440.png` |
| cabinet 390 | `crops/side-cabinet-390.png` | `crops/diff-cabinet-390.png` |
| desk 1440 | `crops/side-desk-1440.png` | `crops/diff-desk-1440.png` |
| desk 390 | `crops/side-desk-390.png` | `crops/diff-desk-390.png` |

Pixel statistics: `raw/crop-manifest.json`. Mean absolute difference ranges from **2.5** (cabinet
1440) to **8.0** (desk 390) out of 255 — i.e. **1–3%** — and, as Divergence 2 shows, it is
entirely explained by one paragraph's line-break position, not by any box moving.

---

## Accessible-name reality check

`run_ax_names.py` — reads WebKit's own AX serialisation (`page.aria_snapshot()`, which replaced
`page.accessibility.snapshot()` in Playwright 1.62) and compares it with a DOM-side name
computation. **7 / 7 PASS** (`raw/ax-names-webkit.json`, full tree in `aria_snapshot_text`).

**DOM interactive elements on home: 18 · AX interactive nodes: 18 · empty names: 0 ·
DOM names missing from the AX tree: 0 · unnamed AX nodes: 0.**

| # | Element | Accessible name | Name source |
|---|---|---|---|
| 1 | link | `跳到主要内容` | text |
| 2 | link | `第零证物局 · 返回封面` | aria-label |
| 3 | link | `档案柜` | text |
| 4 | link | `玩法说明` | text |
| 5 | link | `关于与隐私` | text |
| 6 | button | `Switch to English` | aria-label |
| 7 | link | `打开第 001 号档案` | text |
| 8 | link | `查看全部档案` | text |
| 9 | link | `开始整理` | text |
| 10 | button | `我知道了` | text |
| 11 | link | `随时查看局内手册` | text |
| 12 | link | `进入档案柜` | text |
| 13 | link | `调查档案 001：末班车的四张车票` | aria-label |
| 14 | link | `调查档案 002：封存室的四格抽屉` | aria-label |
| 15 | link | `调查档案 003：静默分拣线上的五个包裹` | aria-label |
| 16 | link | `档案柜` | text (footer) |
| 17 | link | `玩法说明` | text (footer) |
| 18 | link | `关于与隐私` | text (footer) |

**No empty names. No duplicates inside a single landmark.** Three names repeat —
`档案柜`, `玩法说明`, `关于与隐私` — but each pair is one link in the header `<nav>` and one in the
footer `<nav>`, which is normal and correctly disambiguated by their landmark. **Nothing to fix.**

One WebKit-specific note: `aria-label="这些记录，不应该同时成立。"` is present on the `<h1>` and
WebKit correctly exposes it as the accessible name of the `region`/heading, so the visually split
h1 (`这些记录，` + block `不应该同时成立。`) is announced as one coherent sentence.

---

## Divergences

Numbered, each with severity. **5 total: 1 high (now RESOLVED in the final build), 1 low, 3 informational.**

### 1. Plain `<a href>` elements are not in WebKit's Tab order — **RESOLVED IN BUILD B (was HIGH)**

**Root cause (engine).** On a 5-element minimal page, WebKit's Tab sequence is
`['tabidx', 'btn', 'inp', ...]` — the plain `<a href>` and the `<a role="button">` are **never
reached**, while adding `tabindex="0"` makes the same link reachable. Chromium and Firefox both
reach it. This is Safari's factory default ("Press Tab to highlight each item on a webpage" =
off); it reproduces identically in Playwright's WebKit 26.5. **This engine fact did not change.**

**On build A** (`app.mjs` `5195a988…`, no `tabindex` on links) the consequence was severe:

| Scene | links on page | buttons on page | Tab could reach |
|---|---|---|---|
| home | **8** | 1 | 2 buttons + body — **0 of 8 links** |
| cabinet | **7** | 0 | **0 of 7 links** |
| desk NA-001 | 1 | 19 | all 19 buttons, **not** the 1 link |
| verdict | 3 | 1 | **0 of 3 links** |

A keyboard-only Safari user **could not navigate between pages at all** — although once on a desk
the puzzle itself was fully operable, since every desk control is a `<button>`.

**On build B** (`app.mjs` `d0676119…`) this is **fixed**. The build adds **17 `tabindex="0"`**
attributes to the links. Re-measured with the same runner
(`raw/tab-reach-after-fix.json`), Tab now reaches every link:

| Scene | distinct stops | links reached | buttons reached | every stop `:focus-visible` |
|---|---|---|---|---|
| home | 14 | **11** | 2 | **yes** |
| cabinet | 9 | **7** | 1 | **yes** |
| desk NA-001 | 14 | **5** | 8 | **yes** |
| manual | 9 | **6** | 2 | **yes** |
| about | 8 | **6** | 1 | **yes** |

Including the skip link (`跳到主要内容`) and the brand/home link, which are now reachable too.
The tab-reach suite went from **3/7** on build A to **7/7 PASS** on build B.

**Residual note — verified, not assumed.** Does `tabindex="0"` on already-focusable links change
Chromium/Firefox order? Measured on build B (`raw/tab-order-buildB-all-engines.json`): **no.**

| Engine | distinct Tab stops on home | links reached |
|---|---|---|
| WebKit 26.5 | **14** | **11** |
| Chromium 151 | **14** | **11** |
| Firefox 153 | 10 | 9 |

WebKit and Chromium produce the **identical** 14-stop sequence, in the same order
(`打开第 001 号档案 → 查看全部档案 → 开始整理 → 我知道了 → 随时查看局内手册 → 进入档案柜 →
立即调查 → 档案柜 → 玩法说明 → 关于与隐私 → skip-link → brand → EN`). Firefox reaches 9 links
and stops there because it has no body stop in this walk. **The fix normalises WebKit to match
Chromium rather than introducing a new order.**

**Status: RESOLVED in build B. Severity was HIGH; now none.**

### 2. `text-wrap: pretty` is implemented in WebKit but a no-op in Chromium — **LOW (cosmetic)**

**Evidence** (`probe_textwrap_pretty.py`, `raw/textwrap-pretty.json`). Same element
(`.hero__lede`, 618 px wide), same text, three engines, with the wrap mode forced as a control:

| Mode | WebKit 26.5 line widths | Chromium 151 line widths | Firefox 153 line widths |
|---|---|---|---|
| **as authored** (`pretty`) | **`[537.6, 422.4]`** | **`[614.41, 345.61]`** | `[614.4, 345.6]` (→ `wrap`) |
| forced `wrap` | `[614.4, 345.6]` | `[614.41, 345.61]` | `[614.4, 345.6]` |
| forced `balance` | `[480, 480]` | `[480, 480]` | `[480, 480]` |

Under any **shared** mode the engines agree to within 0.01 px. The divergence exists **only**
because WebKit actually implements `pretty` (balancing the last line) while Chromium treats it as
`wrap`. This is WebKit behaving *better*, not worse — but it is why the screenshots are not
pixel-identical.

**Impact.** Purely cosmetic: one paragraph breaks at a different character, shifting content
below it by ≤1.14 px (the largest layout delta in the entire parity run). Text is fully readable,
no overflow, no clipping, identical line count (2) and identical block height (65.2 vs 65.3 px).
**No action needed** — this is the desired behaviour of the property.

### 3. `backdrop-filter` is not painted by WebKit — **INFORMATIONAL (no product impact)**

**Evidence.** See risk 1. Blur on vs off is pixel-identical (`0.000` mean abs diff) in WebKit and
Firefox, while Chromium blurs strongly (`114.495`). The methodology is validated by that
cross-engine control, and WebKit's `filter: blur()` works fine (`104.89` px change), so this is
specific to the backdrop path (most likely because there is no real compositor behind Playwright's
WebKit on Windows — see the "could not test" section).

**Impact: none.** The header's near-opaque gradient fallback means the blur was never load-bearing;
header text measures **10.32–16.23 : 1** contrast with the blur absent. The product note in
`app.css` ("头部不能依赖毛玻璃才能成立") is exactly the right mitigation and it works. This
divergence would be **invisible to a user** unless they compared side by side with a
blur-capable engine.

### 4. `overscroll-behavior` is unsupported by WebKit — **INFORMATIONAL**

`CSS.supports('overscroll-behavior','contain')` → **false** in WebKit 26.5 (true in Chromium and
Firefox). **The site never uses it** (0 declarations in `site/`), so no behaviour differs. Recorded
because it was on the risk list; there is nothing to fix.

### 5. `-webkit-tap-highlight-color` is not a supported CSS property here — **INFORMATIONAL**

`CSS.supports` → **false**; assigning it produces no computed value. The site never declares it.
On a real iPhone the default grey tap flash may be visible on buttons; it cannot be observed in
this environment and is cosmetic only. **73/73 interactive elements already meet the 44×44 px
target size**, which is the substantive iOS requirement.

---

## What I could not test

Being explicit, because Playwright's WebKit is **not** Safari:

1. **Real Safari on macOS.** Playwright ships its own WebKit build; it is not the system Safari
   and does not use Apple's full graphics stack. Anything about Safari's actual rendering,
   extensions, Reader mode, or OS integration is **unverified**.
2. **Real iOS Safari.** No iPhone/iPad was involved. Untested: the dynamic toolbar collapsing and
   how it interacts with `100dvh` on a *real* device (my `dvh` numbers come from an emulated
   viewport whose height is static), rubber-band overscroll, `env(safe-area-inset-*)` with a real
   notch, the real touch tap-highlight, momentum scrolling, and pinch-zoom behaviour.
3. **The GPU compositor / Metal path.** This is almost certainly why `backdrop-filter` does not
   paint here: the WebGL renderer string is the placeholder `Apple GPU`, i.e. there is no real
   Apple GPU behind this build on Windows. **A real Mac might well paint the blur** — so
   divergence 3 should be read as "not proven to work in this build", not "broken in Safari".
   You can verify this cheaply on any Mac with the same runner.
4. **VoiceOver / real assistive technology.** I read WebKit's AX serialisation
   (`aria_snapshot()`), which is *a* view of the accessibility tree, but not what VoiceOver
   actually announces, and not Safari's native AX API. Announcement ordering, live-region
   behaviour and verbosity are **unverified**.
5. **`forced-colors`.** `(forced-colors: active)` reported `false` and Playwright has no
   forced-colors emulation for WebKit, so the forced-colors branch of `tokens.css` is
   **unverified**. — `prefers-reduced-motion` and `prefers-color-scheme` *were* testable via
   Playwright emulation and **both work correctly** in WebKit: with `reduced_motion="reduce"` the
   `--dur` token resolves to `0ms` and `.slot` transitions become `0.000001s` (identical to
   Chromium's `1e-06s`); with `color_scheme="dark"` the page background resolves to `rgb(8, 24, 33)`
   and `color-scheme: dark` applies. Raw: `raw/reduced-motion-dark.json`.
6. **Fonts.** No `@font-face` is used (0 loaded web fonts); the page relies on system fonts. WebKit
   resolved the Chinese serif stack differently from Chromium (`Songti SC` fell back to a
   different face than Chromium's), which is the residual source of the non-zero pixel diff beyond
   `text-wrap: pretty`. **This is a font-availability artifact of the test machine, not a site
   bug** — on macOS, `Songti SC` and `PingFang SC` are real system fonts and will resolve
   differently again.
7. **Deployment.** All numbers are from the **local** build at `127.0.0.1:8140` as instructed. The
   live GitHub Pages deployment was not tested in this pass.
8. **`site/` concurrent edits.** Another agent was editing and deploying while I ran, and the
   served `app.mjs` + `index.html` changed once mid-session (adding `tabindex="0"`). Both builds are
   identified by hash in the provenance table above, and **every suite was re-run on the final
   build B** — journey 34/34, six-case 6/6, CSS risks 37/38, layout parity 1.14 px, Tab audit 7/7.
   The pre-fix evidence is preserved under `raw/pre-fix/`. Nothing in this report describes a build
   I did not measure.

---

## Raw data index

| File | Contents |
|---|---|
| `raw/journey-webkit.json` | 34 core-journey checks |
| `raw/six-cases-webkit.json` | 6-case solve, answers, recap blocks |
| `raw/css-risks-webkit.json` | 38 WebKit-specific risk checks |
| `raw/capabilities-probe.json` | `CSS.supports` matrix + computed values |
| `raw/backdrop-probe.json` | 4-cell backdrop pixel isolation |
| `raw/backdrop-methodology-cross-engine.json` | same probe on all 3 engines |
| `raw/textwrap-pretty.json` | line-break divergence, with forced-mode controls |
| `raw/tab-reach-webkit.json` | Tab-order audit **build A** (pre-fix) + minimal-page proof |
| `raw/tab-reach-summary.json` | Tab-order assertions, build A |
| `raw/tab-reach-after-fix.json` | Tab reachability re-measured on **build B** (fixed) |
| `raw/tab-order-buildB-all-engines.json` | Tab order on build B, WebKit vs Chromium vs Firefox |
| `raw/pre-fix/` | archived pre-fix run evidence |
| `raw/ax-names-webkit.json` | full AX tree + DOM names |
| `raw/ax-names-summary.json` | accessible-name assertions |
| `raw/layout-parity.json` | 9 scenes × 22 element selectors, all deltas |
| `raw/crop-manifest.json` | pixel stats per side-by-side |
| `raw/touch-target-audit.json` | every interactive element at 390×844 |
| `raw/pixel-diff-analysis.json` | blur/antialiasing analysis of the diffs |
| `raw/reduced-motion-dark.json` | reduced-motion + dark-scheme parity, all engines |
| `raw/network-all-scenes.json` | third-party / failed-request audit across 6 scenes |
| `raw/h1-ink-measurement.txt` | proof the h1 is 2 visual lines in both engines |
| `raw/provenance.json` | served-file hashes before/after |
| `raw/final-summary.json` | consolidated pass/fail per suite |
| `shots/` | 100 screenshots (per-engine scenes, risks, crops) |
| `crops/` | 7 side-by-sides + 7 diff heatmaps + worst-block crops |

Runners: `run_journey.py`, `run_six_cases.py`, `run_css_risks.py`, `run_tab_reach.py`,
`run_ax_names.py`, `run_layout_parity.py`, `make_crops.py`, `run_all.py`, plus probes
`probe_capabilities.py`, `probe_backdrop.py`, `probe_textwrap_pretty.py`.

Reproduce everything: `cd work/qa/webkit && python run_all.py`
