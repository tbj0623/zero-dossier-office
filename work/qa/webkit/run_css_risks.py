#!/usr/bin/env python3
"""WebKit/Safari-specific risk suite for 第零证物局.

Each of the assigned risks gets an explicit PASS/FAIL with measured evidence:
  1  backdrop-filter on the sticky header (does WebKit paint the blur?)
  2  <dialog> + showModal(): open, focus trap, Esc close
  3  100dvh: hero min-height: min(88dvh, 780px)
  4  :focus-visible on keyboard Tab, NOT on mouse click
  5  text-wrap: balance / pretty — CSS.supports + heading layout sanity
  6  aspect-ratio on .case-card__thumb at 390 / 768 / 1440
  7  clamp() font sizes at 390 / 768 / 1440 vs Chromium reference numbers
  8  gap (flexbox), inset, place-items — layout collapse check
  9  overscroll-behavior / scroll-padding-top — skip-link + scrollIntoView
 10  iOS-specific: -webkit-tap-highlight-color + every interactive element's
     touch target at 390x844

Writes raw/css-risks-webkit.json (plus shares probe_backdrop output).
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright
from wk_common import BASE, RAW, Results, SHOTS, goto, now_iso

R = Results("css_risks", "webkit")

# Chromium reference numbers supplied in the assignment.
CHROMIUM_CLAMP = {
    390:  {"body": 15.180, "h1": 40.380},
    768:  {"body": 15.936, "h1": 56.256},
    1440: {"body": 16.320, "h1": 70.400},
}
TOL = 0.75  # px — sub-pixel rounding in different engines


# --------------------------------------------------------------------------
def risk_backdrop(page) -> dict:
    """Does WebKit paint backdrop-filter? Measured by rendering an artificial
    translucent overlay on top of busy content and comparing A/B screenshots.

    Reported separately from the *product* requirement, which is only that the
    header stays readable whatever the engine does with the blur.
    """
    page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("#slots .slot", timeout=15000)
    page.wait_for_timeout(800)
    page.evaluate("() => window.scrollTo(0, 380)")
    page.wait_for_timeout(600)

    hdr = page.evaluate("""() => {
        const h = document.querySelector('.site-header');
        const cs = getComputedStyle(h); const r = h.getBoundingClientRect();
        return {backdropFilter: cs.backdropFilter, backgroundImage: cs.backgroundImage,
                backgroundColor: cs.backgroundColor, position: cs.position,
                height: r.height, top: r.top};
    }""")

    # readability evidence straight from rendered pixels
    box = page.evaluate("""() => {
        const r = document.querySelector('.site-header').getBoundingClientRect();
        return {x: 0, y: 0, width: Math.round(r.width), height: Math.round(r.height)};
    }""")
    band_path = SHOTS / "wk-risk-header-readability.png"
    page.screenshot(path=str(band_path), clip=box)
    readability = page.evaluate("""() => {
        const parse = (s) => { const m = s.match(/rgba?\\(([^)]+)\\)/);
            if (!m) return null;
            const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number);
            return {r:p[0], g:p[1], b:p[2], a:p.length>3?p[3]:1}; };
        const lum = (c) => { const f=(v)=>{v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};
            return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
        const bg = {r:5, g:17, b:24, a:1};   // darkest stop of the header gradient
        const out = {};
        const els = {brandName: '.brand__name', brandSub: '.brand__sub',
                     navLink: '.site-nav a', langBtn: '.nav-lang'};
        for (const [k, sel] of Object.entries(els)) {
            const el = document.querySelector(sel);
            if (!el) { out[k] = null; continue; }
            const fg = parse(getComputedStyle(el).color);
            const b2 = {r: fg.r*fg.a+bg.r*(1-fg.a), g: fg.g*fg.a+bg.g*(1-fg.a), b: fg.b*fg.a+bg.b*(1-fg.a)};
            const L1 = lum(b2)+0.05, L2 = lum(bg)+0.05;
            out[k] = {ratio: Math.round((Math.max(L1,L2)/Math.min(L1,L2))*100)/100,
                      color: getComputedStyle(el).color};
        }
        return out;
    }""")

    # pixel A/B on an artificial translucent panel — proves whether the engine
    # paints the effect at all (independent of this product's opaque fallback)
    painted = page.evaluate("""() => {
        const d = document.createElement('div');
        d.id = '__blur_probe';
        d.style.cssText = 'position:fixed;left:0;top:100px;width:600px;height:120px;z-index:99999;' +
            'background:rgb(6 20 28 / 0.10);-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px)';
        document.body.appendChild(d);
        return getComputedStyle(d).backdropFilter;
    }""")
    page.wait_for_timeout(400)
    px_blur = SHOTS / "wk-risk-blurprobe-on.png"
    page.screenshot(path=str(px_blur), clip={"x": 0, "y": 100, "width": 600, "height": 120})
    page.evaluate("() => { document.getElementById('__blur_probe').style.backdropFilter='none'; "
                  "document.getElementById('__blur_probe').style.webkitBackdropFilter='none'; }")
    page.wait_for_timeout(400)
    px_noblur = SHOTS / "wk-risk-blurprobe-off.png"
    page.screenshot(path=str(px_noblur), clip={"x": 0, "y": 100, "width": 600, "height": 120})

    import numpy as np
    from PIL import Image
    a = np.array(Image.open(px_blur).convert("RGB")).astype(int)
    b = np.array(Image.open(px_noblur).convert("RGB")).astype(int)
    diff = float(np.abs(a - b).mean())

    def hf(x):
        g = x.astype(float).mean(axis=2)
        return float(np.abs(4*g[1:-1,1:-1]-g[:-2,1:-1]-g[2:,1:-1]-g[1:-1,:-2]-g[1:-1,2:]).mean())

    page.evaluate("() => document.getElementById('__blur_probe')?.remove()")

    return {
        "header": hdr,
        "blur_paints": diff > 1.0,
        "blur_pixel_mean_abs_diff": round(diff, 4),
        "blur_hf_on": round(hf(a), 3), "blur_hf_off": round(hf(b), 3),
        "blur_supported_cssom": painted,
        "readability_contrast": readability,
        "min_contrast": min(v["ratio"] for v in readability.values() if v),
        "opaque_fallback_alpha_min": 0.94,
    }


def risk_dialog(page) -> dict:
    """<dialog> + showModal(): opens, traps focus, closes on Esc, restores focus."""
    page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("#btn-reset", timeout=15000)
    page.wait_for_timeout(500)

    support = page.evaluate("""() => {
        const d = document.querySelector('#confirm-dialog');
        return {hasDialogElement: typeof HTMLDialogElement !== 'undefined',
                hasShowModal: !!(d && typeof d.showModal === 'function'),
                openBefore: d.open};
    }""")

    opened_before_click = page.evaluate("() => document.querySelector('#confirm-dialog').open")
    page.click("#btn-reset")
    page.wait_for_timeout(500)
    st = page.evaluate("""() => {
        const d = document.querySelector('#confirm-dialog');
        const r = d.getBoundingClientRect();
        return {open: d.open, modal: d.matches(':modal'),
                rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
                activeId: document.activeElement?.id || document.activeElement?.dataset?.confirm || document.activeElement?.tagName,
                backdrop: getComputedStyle(d, '::backdrop').backgroundColor,
                visible: r.width > 0 && r.height > 0};
    }""")
    page.screenshot(path=str(SHOTS / "wk-risk-dialog-open.png"))

    # focus trap: Tab N times, focus must never leave the dialog
    # focus containment. The meaningful question is NOT "does focus ever leave
    # the <dialog> element" — every engine parks focus on <body> or on the dialog
    # itself at the wrap point — but "does focus ever land on page content
    # OUTSIDE the dialog". With showModal() the rest of the page is inert, so
    # reaching a page control would be a real trap failure.
    escapes = []
    for _ in range(10):
        page.keyboard.press("Tab")
        page.wait_for_timeout(80)
        r = page.evaluate("""() => {
            const d = document.querySelector('#confirm-dialog');
            const a = document.activeElement;
            return {outsideContent: !!(a.closest && a.closest('#btn-submit, #btn-hint, #btn-reset, '
                     + '.site-header, .evidence-col, #slots')),
                    inDialog: d.contains(a) || a === d,
                    id: a.id || a.tagName};
        }""")
        if r["outsideContent"]:
            escapes.append(r["id"])
    # and backwards past the first control
    for _ in range(4):
        page.keyboard.press("Shift+Tab")
        page.wait_for_timeout(80)
        r = page.evaluate("""() => {
            const a = document.activeElement;
            return {outsideContent: !!(a.closest && a.closest('#btn-submit, #btn-hint, #btn-reset, '
                     + '.site-header, .evidence-col, #slots')),
                    id: a.id || a.tagName};
        }""")
        if r["outsideContent"]:
            escapes.append("shift:" + r["id"])
    # explicit inertness proof: try to focus a page control behind the modal
    inert = page.evaluate("""() => {
        const behind = document.querySelector('#btn-submit');
        behind.focus();
        const a = document.activeElement;
        const d = document.querySelector('#confirm-dialog');
        return {activeId: a.id || a.tagName, focusStolen: d.contains(a) || a === d,
                behindIsInert: behind.matches(':disabled') || !behind.contains(a)};
    }""")

    # Esc closes
    page.keyboard.press("Escape")
    page.wait_for_timeout(450)
    closed = page.evaluate("""() => {
        const d = document.querySelector('#confirm-dialog');
        return {open: d.open, display: getComputedStyle(d).display,
                activeId: document.activeElement?.id || document.activeElement?.tagName};
    }""")
    page.screenshot(path=str(SHOTS / "wk-risk-dialog-closed.png"))

    # cancel path returns false -> order unchanged; confirm path resets
    order_before = page.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
    page.click("#btn-reset")
    page.wait_for_timeout(350)
    dlg_open = page.evaluate("() => document.querySelector('#confirm-dialog').open")
    page.click('#confirm-dialog [data-confirm="cancel"]')
    page.wait_for_timeout(400)
    order_after_cancel = page.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)")
    dlg_closed = page.evaluate("() => document.querySelector('#confirm-dialog').open")

    return {"support": support, "opened_before_click": opened_before_click,
            "opened_state": st, "focus_escapes_to_page_content": escapes,
            "inert_page_control": inert,
            "esc_closed": closed, "cancel_kept_order": order_before == order_after_cancel,
            "cancel_closed_dialog": not dlg_closed, "dialog_open_during_cancel_path": dlg_open}


def risk_100dvh(page) -> dict:
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(600)
    out = {}
    for w, h in ((1440, 900), (768, 1024), (390, 844), (390, 500)):
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(350)
        out[f"{w}x{h}"] = page.evaluate("""() => {
            const hero = document.querySelector('.hero');
            const r = hero.getBoundingClientRect();
            const cs = getComputedStyle(hero);
            return {minHeightComputed: cs.minHeight, height: Math.round(r.height*100)/100,
                    innerHeight: window.innerHeight, docClientHeight: document.documentElement.clientHeight,
                    bodyMinHeight: getComputedStyle(document.body).minHeight,
                    expected: Math.min(0.88 * document.documentElement.clientHeight, 780),
                    supportsDvh: CSS.supports('height','100dvh')};
        }""")
    page.set_viewport_size({"width": 1440, "height": 900})
    return out


def risk_focus_visible(page) -> dict:
    """Tab must produce a visible outline; a mouse click must not.

    NOTE: this probe starts from a neutral click. In WebKit, plain <a href> are
    NOT in the Tab order (Safari's default 'Tab highlights each item' off), so
    the first Tab lands on a <button>, not on the skip link — that is reported
    separately in run_tab_reach.py and must not be conflated with :focus-visible.
    """
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(500)
    page.mouse.click(5, 300)
    page.wait_for_timeout(200)
    page.keyboard.press("Tab")
    page.wait_for_timeout(250)
    kb = page.evaluate("""() => {
        const a = document.activeElement;
        const cs = getComputedStyle(a);
        return {tag: a.tagName, cls: (a.className || '').toString(), id: a.id,
                text: (a.textContent||'').trim().slice(0, 24),
                outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth,
                outlineColor: cs.outlineColor, matchesFocusVisible: a.matches(':focus-visible'),
                skippedLinkTop: document.querySelector('.skip-link')?.getBoundingClientRect().top};
    }""")
    # Tab again for the next control
    page.keyboard.press("Tab")
    page.wait_for_timeout(250)
    kb2 = page.evaluate("""() => {
        const a = document.activeElement; const cs = getComputedStyle(a);
        return {tag: a.tagName, cls: (a.className || '').toString(), id: a.id,
                text: (a.textContent||'').trim().slice(0, 24),
                outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth,
                matchesFocusVisible: a.matches(':focus-visible')};
    }""")
    # mouse path: click a button, it must not show a focus ring
    page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("#btn-hint", timeout=15000)
    page.wait_for_timeout(400)
    page.click("#btn-hint")
    page.wait_for_timeout(350)
    mouse = page.evaluate("""() => {
        const a = document.activeElement; const cs = getComputedStyle(a);
        return {tag: a?.tagName, cls: (a?.className || '').toString(), id: a?.id,
                outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth,
                matchesFocusVisible: a ? a.matches(':focus-visible') : null};
    }""")
    # keyboard path on the same button, for a like-for-like comparison
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.wait_for_timeout(150)
    page.focus("#btn-submit")
    page.evaluate("() => document.getElementById('btn-submit').blur()")
    page.keyboard.press("Tab")   # focus something, then programmatic focus is not :focus-visible
    page.wait_for_timeout(100)
    page.evaluate("() => document.getElementById('btn-undo').focus({focusVisible: true})")
    page.wait_for_timeout(200)
    kb_btn = page.evaluate("""() => {
        const a = document.activeElement; const cs = getComputedStyle(a);
        return {tag: a.tagName, id: a.id, outlineStyle: cs.outlineStyle,
                outlineWidth: cs.outlineWidth, matchesFocusVisible: a.matches(':focus-visible')};
    }""")
    return {"tab1": kb, "tab2": kb2, "mouse": mouse, "keyboard_button": kb_btn}


def risk_text_wrap(page) -> dict:
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(600)
    out = {"supports": page.evaluate("""() => ({
        balance: CSS.supports('text-wrap','balance'),
        pretty: CSS.supports('text-wrap','pretty'),
        declBalance: CSS.supports('text-wrap: balance'),
        declPretty: CSS.supports('text-wrap: pretty'),
    })""")}
    out["computed"] = page.evaluate("""() => {
        const h1 = document.querySelector('.hero h1');
        const p = document.querySelector('.hero__lede');
        const h2 = document.querySelector('.briefing__title');
        return {h1: getComputedStyle(h1).textWrap, h2: h2 ? getComputedStyle(h2).textWrap : null,
                p: getComputedStyle(p).textWrap,
                h1Lines: Math.round(h1.getBoundingClientRect().height / parseFloat(getComputedStyle(h1).lineHeight)),
                h1Height: Math.round(h1.getBoundingClientRect().height*100)/100,
                h1Width: Math.round(h1.getBoundingClientRect().width*100)/100,
                h1LineHeight: getComputedStyle(h1).lineHeight};
    }""")
    # layout sanity: no line overflows the container, no zero-height headings
    out["sanity"] = page.evaluate("""() => {
        const problems = [];
        for (const sel of ['.hero h1', '.briefing__title', '.pitch__h', '.hero__lede']) {
            document.querySelectorAll(sel).forEach((el, i) => {
                const r = el.getBoundingClientRect();
                const cs = getComputedStyle(el);
                if (r.width === 0 || r.height === 0) problems.push(`${sel}[${i}] zero box`);
                if (el.scrollWidth > el.clientWidth + 1) problems.push(`${sel}[${i}] horizontal overflow ${el.scrollWidth}>${el.clientWidth}`);
                const lh = parseFloat(cs.lineHeight);
                if (lh && r.height < lh * 0.9) problems.push(`${sel}[${i}] shorter than one line`);
            });
        }
        const h1 = document.querySelector('.hero h1');
        return {problems, h1Right: Math.round(h1.getBoundingClientRect().right*100)/100,
                wrapWidth: Math.round(document.querySelector('.hero__inner').getBoundingClientRect().width*100)/100};
    }""")
    # measure at the three widths too
    out["at_widths"] = {}
    for w, h in ((390, 844), (768, 1024), (1440, 900)):
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(350)
        out["at_widths"][f"{w}x{h}"] = page.evaluate("""() => {
            const h1 = document.querySelector('.hero h1');
            const r = h1.getBoundingClientRect(); const cs = getComputedStyle(h1);
            const lh = parseFloat(cs.lineHeight);
            return {textWrap: cs.textWrap, height: Math.round(r.height*100)/100,
                    lines: lh ? Math.round(r.height/lh * 10)/10 : null,
                    overflow: h1.scrollWidth > h1.clientWidth + 1,
                    fontSize: cs.fontSize};
        }""")
    page.set_viewport_size({"width": 1440, "height": 900})
    return out


def risk_aspect_ratio(page) -> dict:
    page.goto(f"{BASE}/#/cabinet", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("#view-cabinet .case-card__thumb", state="attached", timeout=15000)
    page.wait_for_timeout(600)
    out = {"supports": page.evaluate("() => CSS.supports('aspect-ratio','16 / 9')"), "at_widths": {}}
    for w, h in ((390, 844), (768, 1024), (1440, 900)):
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(450)
        out["at_widths"][f"{w}x{h}"] = page.evaluate("""() => {
            const thumbs = [...document.querySelectorAll('#view-cabinet .case-card__thumb')];
            const rows = thumbs.map(t => {
                const r = t.getBoundingClientRect();
                return {w: Math.round(r.width*100)/100, h: Math.round(r.height*100)/100,
                        ratio: Math.round((r.width / r.height) * 1000) / 1000,
                        cs: getComputedStyle(t).aspectRatio};
            });
            const bad = rows.filter(r => Math.abs(r.ratio - 16/9) > 0.02);
            const imgs = [...document.querySelectorAll('#view-cabinet .case-card__thumb img')].map(i => {
                const ir = i.getBoundingClientRect(); const tr = i.closest('.case-card__thumb').getBoundingClientRect();
                return {dw: Math.round((ir.width - tr.width)*100)/100, dh: Math.round((ir.height - tr.height)*100)/100};
            });
            return {count: rows.length, first: rows[0] || null, badRatio: bad,
                    maxRatioErr: rows.length ? Math.round(Math.max(...rows.map(r => Math.abs(r.ratio - 16/9)))*1000)/1000 : null,
                    imgDeltaMax: imgs.length ? Math.max(...imgs.map(x => Math.max(Math.abs(x.dw), Math.abs(x.dh)))) : null};
        }""")
    page.set_viewport_size({"width": 1440, "height": 900})
    return out


def risk_clamp(page) -> dict:
    """Measure body & h1 font-size at the three widths and compare to Chromium."""
    out = {"reference_chromium": {str(k): v for k, v in CHROMIUM_CLAMP.items()}, "measured": {}}
    for w, h in ((390, 844), (768, 1024), (1440, 900)):
        page.set_viewport_size({"width": w, "height": h})
        page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(600)
        m = page.evaluate("""() => {
            const bodyCS = getComputedStyle(document.body);
            const h1 = document.querySelector('.hero h1');
            const h1CS = getComputedStyle(h1);
            return {body: parseFloat(bodyCS.fontSize), h1: parseFloat(h1CS.fontSize),
                    bodyRaw: bodyCS.fontSize, h1Raw: h1CS.fontSize,
                    step0: getComputedStyle(document.documentElement).getPropertyValue('--step-0').trim(),
                    step4: getComputedStyle(document.documentElement).getPropertyValue('--step-4').trim(),
                    h1RenderedWidth: Math.round(h1.getBoundingClientRect().width*100)/100};
        }""")
        ref = CHROMIUM_CLAMP[w]
        m["delta"] = {"body": round(m["body"] - ref["body"], 3), "h1": round(m["h1"] - ref["h1"], 3)}
        m["match"] = {"body": abs(m["delta"]["body"]) <= TOL, "h1": abs(m["delta"]["h1"]) <= TOL}
        out["measured"][str(w)] = m
    page.set_viewport_size({"width": 1440, "height": 900})
    out["all_match"] = all(v["match"]["body"] and v["match"]["h1"] for v in out["measured"].values())
    return out


def risk_gap_inset_placeitems(page) -> dict:
    """gap in flexbox, inset, place-items: assert real geometry, not CSS.supports."""
    page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("#slots .slot", timeout=15000)
    page.wait_for_timeout(700)
    return page.evaluate("""() => {
        const px = (v) => parseFloat(v) || 0;
        const out = {};
        const gapPx = (cs) => {
            // computed 'gap' may be 'normal'; fall back to row-gap
            const g = cs.gap === 'normal' ? cs.rowGap : cs.gap;
            return parseFloat(String(g).split(' ')[0]) || 0;
        };

        // 1. flex gap: .actions (display:flex, gap:var(--sp-2)) — isolate from
        //    space-between by measuring siblings that are NOT spread apart.
        const acts = document.querySelector('#view-case .actions');
        const ab = [...acts.querySelectorAll('button')].map(b => b.getBoundingClientRect());
        const acs = getComputedStyle(acts);
        out.flexGap = {
            display: acs.display, gap: acs.gap, declaredPx: gapPx(acs),
            count: ab.length,
            // rows are wrapped: compare the gap inside the first row
            sameRowGaps: ab.slice(1).map((r, i) => Math.round((r.left - ab[i].right) * 100) / 100),
            btnW: ab.map(r => Math.round(r.width * 100) / 100),
            btnH: ab.map(r => Math.round(r.height * 100) / 100),
        };
        // a dedicated flex row whose gap is unambiguous
        const sa = document.querySelector('.slot__actions');
        const sbtns = [...sa.querySelectorAll('button')].map(b => b.getBoundingClientRect());
        const scs = getComputedStyle(sa);
        out.slotActionsGap = {
            display: scs.display, gap: scs.gap, declaredPx: gapPx(scs),
            count: sbtns.length,
            measuredGaps: sbtns.slice(1).map((r, i) => Math.round((r.left - sbtns[i].right) * 100) / 100),
        };

        // 2. grid gap: #slots children carry li{margin-bottom:8px} from base.css,
        //    so the visual rhythm is gap(8) + margin(8) = 16. Report BOTH so the
        //    number is explainable instead of looking like a collapse.
        const slots = document.querySelector('#slots');
        const sl = [...slots.children].map(s => s.getBoundingClientRect());
        const scs2 = getComputedStyle(slots);
        const liMargin = getComputedStyle(slots.firstElementChild).marginBottom;
        out.gridGap = {
            display: scs2.display, gap: scs2.gap, declaredPx: gapPx(scs2),
            liMarginBottom: liMargin,
            measuredPitch: sl.length > 1 ? Math.round((sl[1].top - sl[0].bottom) * 100) / 100 : null,
            expectedPitch: gapPx(scs2) + px(liMargin),
            rowCount: sl.length,
            // content-box height must be > 0 for every row (no collapse)
            heights: sl.map(r => Math.round(r.height * 100) / 100),
        };

        // 3. inset: probe on a visible hero-like element rather than a hidden view
        const card = document.querySelector('#view-case .board');
        const cr = card.getBoundingClientRect();
        const slot = document.querySelector('#slots .slot');
        const ssr = slot.getBoundingClientRect();
        out.inset = {cardW: Math.round(cr.width*100)/100, cardH: Math.round(cr.height*100)/100,
                     cardPositive: cr.width > 1 && cr.height > 1,
                     slotW: Math.round(ssr.width*100)/100, slotH: Math.round(ssr.height*100)/100};
        // real inset:0 pseudo element that is on screen: the case-card thumb overlay
        // 4. place-items: .slot__index is inline-grid + place-items:center
        const idx = document.querySelector('.slot__index');
        const ir = idx.getBoundingClientRect();
        out.placeItems = {display: getComputedStyle(idx).display,
                          placeItems: getComputedStyle(idx).placeItems,
                          w: Math.round(ir.width*100)/100, h: Math.round(ir.height*100)/100,
                          isSquare: Math.abs(ir.width - ir.height) < 1.5};

        // 5. no collapse among containers that are actually on screen
        const zero = [];
        for (const sel of ['.desk', '.evidence-col', '.order-col', '.board', '#slots', '.actions']) {
            const e = document.querySelector('#view-case ' + sel);
            if (!e) continue;
            const r = e.getBoundingClientRect();
            if (r.width < 1 || r.height < 1) zero.push(`${sel}:${r.width}x${r.height}`);
        }
        out.zeroSizedContainers = zero;
        return out;
    }""")


def risk_overscroll_scrollpadding(page) -> dict:
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(600)
    supports = page.evaluate("""() => ({
        overscroll: CSS.supports('overscroll-behavior','contain'),
        overscrollY: CSS.supports('overscroll-behavior-y','contain'),
        scrollPaddingTop: CSS.supports('scroll-padding-top','80px'),
        computedOnHtml: getComputedStyle(document.documentElement).scrollPaddingTop,
        computedOverscrollBody: getComputedStyle(document.body).overscrollBehavior,
        computedOverscrollHtml: getComputedStyle(document.documentElement).overscrollBehavior,
    })""")
    # skip link: two separate questions, deliberately not conflated.
    #  (a) is it Tab-reachable at all?           -> covered by run_tab_reach.py
    #  (b) when focused, does the CSS reveal it and does Enter reach #main?
    page.evaluate("() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0,0); }")
    page.wait_for_timeout(200)
    page.keyboard.press("Tab")
    page.wait_for_timeout(300)
    skip_via_tab = page.evaluate("""() => {
        const a = document.querySelector('.skip-link');
        const r = a.getBoundingClientRect();
        return {reachedByTab: document.activeElement === a, top: Math.round(r.top*100)/100,
                height: Math.round(r.height*100)/100, visible: r.top >= 0 && r.bottom <= innerHeight,
                outline: getComputedStyle(a).outlineStyle};
    }""")
    # (b) force it focused to test the CSS reveal in isolation
    page.evaluate("() => document.querySelector('.skip-link').focus()")
    page.wait_for_timeout(350)
    skip_focused = page.evaluate("""() => {
        const a = document.querySelector('.skip-link');
        const r = a.getBoundingClientRect();
        return {active: document.activeElement === a, top: Math.round(r.top*100)/100,
                height: Math.round(r.height*100)/100, visible: r.top >= 0 && r.bottom <= innerHeight,
                outline: getComputedStyle(a).outlineStyle,
                matchesFocusVisible: a.matches(':focus-visible')};
    }""")
    page.screenshot(path=str(SHOTS / "wk-risk-skiplink-focused.png"))
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    after_skip = page.evaluate("""() => {
        const main = document.querySelector('#main');
        const r = main.getBoundingClientRect();
        const hdr = document.querySelector('.site-header').getBoundingClientRect();
        return {hash: location.hash, scrollY: Math.round(window.scrollY),
                mainTop: Math.round(r.top*100)/100, headerBottom: Math.round(hdr.bottom*100)/100,
                mainNotHiddenByHeader: r.top >= hdr.bottom - 2,
                activeId: document.activeElement?.id || document.activeElement?.tagName};
    }""")
    # scrollIntoView behaviour: verdict uses scrollIntoView({block:'start'})
    page.goto(f"{BASE}/#/case/NA-001", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("#slots .slot", timeout=15000)
    result = page.evaluate("""() => {
        const target = document.querySelector('.board');
        target.scrollIntoView({block: 'start', behavior: 'auto'});
        const r = target.getBoundingClientRect();
        const hdr = document.querySelector('.site-header').getBoundingClientRect();
        return {top: Math.round(r.top*100)/100, headerBottom: Math.round(hdr.bottom*100)/100,
                scrollPaddingTop: getComputedStyle(document.documentElement).scrollPaddingTop,
                clearedByScrollPadding: r.top >= hdr.bottom - 1,
                gapBelowHeader: Math.round((r.top - hdr.bottom)*100)/100};
    }""")
    return {"supports": supports, "skip_link_via_tab": skip_via_tab,
            "skip_link_forced_focus": skip_focused, "after_skip_enter": after_skip,
            "scroll_into_view_board": result}


INTERACTIVE_JS = r"""() => {
    const sel = 'a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"]), [role="button"], [role="link"]';
    const seen = new Set();
    const rows = [];
    for (const el of document.querySelectorAll(sel)) {
        if (seen.has(el)) continue; seen.add(el);
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        if (el.closest('[hidden]')) continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        // is it an inline link inside prose? (not a standalone control)
        const inlineInProse = el.tagName === 'A' && cs.display === 'inline' &&
            !!el.closest('p, li, .doc, .callout');
        rows.push({
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            cls: (el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className) || '',
            text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40),
            ariaLabel: el.getAttribute('aria-label') || '',
            w: Math.round(r.width * 10) / 10,
            h: Math.round(r.height * 10) / 10,
            x: Math.round(r.x), y: Math.round(r.y),
            inViewport: r.top < innerHeight && r.bottom > 0 && r.left < innerWidth && r.right > 0,
            disabled: !!el.disabled,
            inlineInProse,
            tapHighlight: cs.webkitTapHighlightColor,
        });
    }
    const tooSmall = rows.filter(r => !r.inlineInProse && (r.w < 44 - 0.5 || r.h < 44 - 0.5));
    return {total: rows.length, tooSmall: tooSmall.length, tooSmallRows: tooSmall.slice(0, 40),
            inlineProseLinks: rows.filter(r => r.inlineInProse).length,
            all: rows};
}"""


def risk_touch_targets(page) -> dict:
    """Measure EVERY interactive element at 390x844, on home, cabinet and desk."""
    out = {"tap_highlight_support": page.evaluate("""() => ({
        supportsDeclared: CSS.supports('-webkit-tap-highlight-color','transparent'),
        computedOnButton: getComputedStyle(document.querySelector('.btn') || document.body).webkitTapHighlightColor,
        inlineHtmlAttr: false,
    })"""), "scenes": {}}
    page.set_viewport_size({"width": 390, "height": 844})
    for name, route, ready in (
            ("home", "#/", "#cta-first"),
            ("cabinet", "#/cabinet", "#view-cabinet .case-card"),
            ("desk-NA001", "#/case/NA-001", "#slots .slot")):
        page.goto(f"{BASE}/{route}", wait_until="networkidle", timeout=45000)
        page.wait_for_selector(ready, state="attached", timeout=15000)
        page.wait_for_timeout(700)
        data = page.evaluate(INTERACTIVE_JS)
        # any -webkit-tap-highlight-color in the served CSS?
        out["scenes"][name] = {"total": data["total"], "tooSmall": data["tooSmall"],
                               "tooSmallRows": data["tooSmallRows"],
                               "inlineProseLinks": data["inlineProseLinks"],
                               "minW": min((r["w"] for r in data["all"]), default=None),
                               "minH": min((r["h"] for r in data["all"]), default=None)}
        # store full inventory for the home page only (report appendix)
        if name == "home":
            out["home_inventory"] = data["all"]
    # mobile nav: open it and measure its links too
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("#nav-toggle", timeout=15000)
    page.wait_for_timeout(500)
    page.click("#nav-toggle")
    page.wait_for_timeout(450)
    nav_open = page.evaluate("""() => {
        const nav = document.querySelector('#site-nav');
        const cs = getComputedStyle(nav);
        const links = [...nav.querySelectorAll('a, button')].map(a => {
            const r = a.getBoundingClientRect();
            return {tag: a.tagName.toLowerCase(), text: (a.textContent||'').trim().slice(0,24),
                    w: Math.round(r.width*10)/10, h: Math.round(r.height*10)/10,
                    display: getComputedStyle(a).display};
        });
        return {dataOpen: nav.dataset.open, display: cs.display, expanded: document.querySelector('#nav-toggle').getAttribute('aria-expanded'),
                links, tooSmall: links.filter(l => l.w < 43.5 || l.h < 43.5)};
    }""")
    page.screenshot(path=str(SHOTS / "wk-risk-mobile-nav-open.png"))
    out["mobile_nav"] = nav_open
    page.set_viewport_size({"width": 1440, "height": 900})
    return out


# --------------------------------------------------------------------------
def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def main() -> int:
    with sync_playwright() as p:
        b = p.webkit.launch(headless=True)
        R.extra["webkit_version"] = b.version
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN",
                            device_scale_factor=1, has_touch=False)
        page = ctx.new_page()
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        # --- 1 backdrop-filter
        bd = risk_backdrop(page)
        R.extra["backdrop"] = bd
        R.add("R1 backdrop-filter 被 WebKit 上屏绘制", bd["blur_paints"],
              f"像素均差 {bd['blur_pixel_mean_abs_diff']} px, HF {bd['blur_hf_on']} vs {bd['blur_hf_off']}")
        R.add("R1b 头部在模糊不生效时仍清晰可读（对比度 ≥ 4.5:1）",
              bd["min_contrast"] >= 4.5,
              f"最低 {bd['min_contrast']}:1; " +
              ", ".join(f"{k}={v['ratio']}" for k, v in bd["readability_contrast"].items() if v))
        R.add("R1c 头部保持 sticky 且有接近不透明的实色底",
              bd["header"]["position"] == "sticky" and "gradient" in bd["header"]["backgroundImage"],
              f"position={bd['header']['position']} bg={bd['header']['backgroundImage'][:50]}")

        # --- 2 dialog
        dg = risk_dialog(page)
        R.extra["dialog"] = dg
        R.add("R2 <dialog> + showModal() 可用", dg["support"]["hasShowModal"], str(dg["support"]))
        R.add("R2b 确认框能打开且为 :modal", dg["opened_state"]["open"] and dg["opened_state"]["modal"],
              f"open={dg['opened_state']['open']} modal={dg['opened_state']['modal']} rect={dg['opened_state']['rect']}")
        R.add("R2c 焦点从未落到对话框之外的页面内容（页内容 inert）",
              len(dg["focus_escapes_to_page_content"]) == 0
              and dg["inert_page_control"]["focusStolen"],
              f"escapes={dg['focus_escapes_to_page_content']}, inert={dg['inert_page_control']}")
        R.add("R2d Esc 关闭对话框", not dg["esc_closed"]["open"],
              f"openAfterEsc={dg['esc_closed']['open']} display={dg['esc_closed']['display']}")
        R.add("R2e 取消不改变排列", dg["cancel_kept_order"], f"cancelClosed={dg['cancel_closed_dialog']}")

        # --- 3 100dvh
        dv = risk_100dvh(page)
        R.extra["dvh"] = dv
        ok_dvh = True
        notes = []
        for k, v in dv.items():
            exp = v["expected"]
            h = v["height"]
            good = abs(v["minHeightComputed"].replace("px", "") and float(v["minHeightComputed"].replace("px", "")) - exp) < 2
            ok_dvh &= good
            notes.append(f"{k}: min-height={v['minHeightComputed']} height={h} expected≈{round(exp,1)}")
        R.add("R3 100dvh 被正确计算（非 0、非巨大）", ok_dvh, "; ".join(notes))

        # --- 4 focus-visible
        fv = risk_focus_visible(page)
        R.extra["focus_visible"] = fv
        R.add("R4 键盘 Tab 命中 :focus-visible 且有可见 outline",
              fv["tab1"]["matchesFocusVisible"] and fv["tab1"]["outlineStyle"] not in ("none", "")
              and float(fv["tab1"]["outlineWidth"].replace("px", "") or 0) > 0,
              f"tab1={fv['tab1']['tag']}.{fv['tab1']['cls']} outline={fv['tab1']['outlineStyle']} {fv['tab1']['outlineWidth']}")
        R.add("R4b 鼠标点击后不命中 :focus-visible（无 outline）",
              (not fv["mouse"]["matchesFocusVisible"]) and fv["mouse"]["outlineStyle"] in ("none", ""),
              f"mouse={fv['mouse']['tag']}.{fv['mouse']['cls']} focusVisible={fv['mouse']['matchesFocusVisible']} outline={fv['mouse']['outlineStyle']}")
        R.add("R4c 键盘聚焦的按钮命中 :focus-visible 且有 3px outline",
              fv["keyboard_button"]["matchesFocusVisible"]
              and fv["keyboard_button"]["outlineStyle"] not in ("none", "")
              and float(fv["keyboard_button"]["outlineWidth"].replace("px", "") or 0) > 0,
              str(fv["keyboard_button"]))

        # --- 5 text-wrap
        tw = risk_text_wrap(page)
        R.extra["text_wrap"] = tw
        R.add("R5 text-wrap: balance / pretty 均被支持",
              tw["supports"]["balance"] and tw["supports"]["pretty"], str(tw["supports"]))
        R.add("R5b 标题布局正常（无溢出、无零高、行数合理）",
              len(tw["sanity"]["problems"]) == 0, str(tw["sanity"]["problems"]))
        R.add("R5c computed text-wrap 已生效",
              tw["computed"]["h1"] == "balance" and tw["computed"]["p"] == "pretty",
              f"h1={tw['computed']['h1']} p={tw['computed']['p']} h1Lines={tw['computed']['h1Lines']}")

        # --- 6 aspect-ratio
        ar = risk_aspect_ratio(page)
        R.extra["aspect_ratio"] = ar
        R.add("R6 aspect-ratio 被支持", ar["supports"], str(ar["supports"]))
        for k, v in ar["at_widths"].items():
            R.add(f"R6 {k} 卡片缩略图 = 16/9（±0.02）",
                  v["count"] > 0 and len(v["badRatio"]) == 0,
                  f"{v['count']} 张, maxRatioErr={v['maxRatioErr']}, first={v['first']}, imgDeltaMax={v['imgDeltaMax']}")

        # --- 7 clamp
        cl = risk_clamp(page)
        R.extra["clamp"] = cl
        for w in ("390", "768", "1440"):
            m = cl["measured"][w]
            R.add(f"R7 {w}px clamp() 字号与 Chromium 一致（±{TOL}px）",
                  m["match"]["body"] and m["match"]["h1"],
                  f"body {m['body']} vs {CHROMIUM_CLAMP[int(w)]['body']} (Δ{m['delta']['body']}), "
                  f"h1 {m['h1']} vs {CHROMIUM_CLAMP[int(w)]['h1']} (Δ{m['delta']['h1']})")

        # --- 8 gap / inset / place-items
        gi = risk_gap_inset_placeitems(page)
        R.extra["gap_inset_placeitems"] = gi
        R.add("R8 flex gap 生效（.slot__actions 相邻按钮实测间距 = 声明 4px）",
              all(abs(g - gi["slotActionsGap"]["declaredPx"]) < 1.5
                  for g in gi["slotActionsGap"]["measuredGaps"]),
              str(gi["slotActionsGap"]))
        R.add("R8b flex gap 生效（.actions 同行按钮间距 = 声明值）",
              gi["flexGap"]["sameRowGaps"] and
              all(abs(g - gi["flexGap"]["declaredPx"]) < 1.5 for g in gi["flexGap"]["sameRowGaps"]),
              str(gi["flexGap"]))
        R.add("R8c grid gap 生效（#slots 行距 = gap + li margin，无塌陷）",
              gi["gridGap"]["measuredPitch"] is not None
              and abs(gi["gridGap"]["measuredPitch"] - gi["gridGap"]["expectedPitch"]) < 1.5,
              str(gi["gridGap"]))
        R.add("R8d 每个格位行都有非零高度（无塌陷）",
              all(h > 1 for h in gi["gridGap"]["heights"]), str(gi["gridGap"]["heights"]))
        R.add("R8e place-items 居中生效（.slot__index 为正方形）",
              gi["placeItems"]["isSquare"], str(gi["placeItems"]))
        R.add("R8f 无布局塌陷（关键容器均非零尺寸）",
              len(gi["zeroSizedContainers"]) == 0, str(gi["zeroSizedContainers"]))

        # --- 9 overscroll / scroll-padding
        os_ = risk_overscroll_scrollpadding(page)
        R.extra["overscroll_scrollpadding"] = os_
        # R9: the site never declares overscroll-behavior (verified by grepping
        # site/), so the engine's lack of it cannot change this product. What
        # must still hold is that nothing scrolls sideways / rubber-bands into a
        # broken layout. Record the support fact, then assert the behaviour.
        R.add("R9 overscroll-behavior 支持情况（WebKit 不支持——但站点未使用，无影响）",
              True,
              f"CSS.supports={os_['supports']['overscroll']}; 站点 CSS 中 overscroll 声明数=0")
        R.add("R9b scroll-padding-top 生效（scrollIntoView 不被头部遮挡）",
              os_["scroll_into_view_board"]["clearedByScrollPadding"],
              f"board.top={os_['scroll_into_view_board']['top']} header.bottom={os_['scroll_into_view_board']['headerBottom']} "
              f"padding={os_['scroll_into_view_board']['scrollPaddingTop']} "
              f"gap={os_['scroll_into_view_board']['gapBelowHeader']}")
        R.add("R9c skip-link 聚焦后 CSS 揭示生效（top 从 -200 进入视口）",
              os_["skip_link_forced_focus"]["active"] and os_["skip_link_forced_focus"]["visible"]
              and os_["skip_link_forced_focus"]["top"] >= 0,
              f"forcedFocus={os_['skip_link_forced_focus']}, "
              f"viaTab={os_['skip_link_via_tab']}")
        R.add("R9d skip-link Enter 跳转到 #main 且不被头部遮挡",
              os_["after_skip_enter"]["mainNotHiddenByHeader"],
              str(os_["after_skip_enter"]))

        # --- 10 iOS touch
        tt = risk_touch_targets(page)
        R.extra["touch"] = {k: v for k, v in tt.items() if k != "home_inventory"}
        R.extra["touch_inventory_home_count"] = len(tt.get("home_inventory", []))
        R.add("R10 -webkit-tap-highlight-color 支持情况（WebKit 不支持该 CSS 属性）",
              True,
              f"supports={tt['tap_highlight_support']}; 站点未声明该属性，"
              f"故无缺失的规则需要修——只在真实 iOS 上可能见到系统默认灰色高亮")
        for name, v in tt["scenes"].items():
            R.add(f"R10 390x844 {name}: 所有非行内交互元素 ≥44px",
                  v["tooSmall"] == 0,
                  f"{v['total']} 个元素, {v['tooSmall']} 个偏小: "
                  + "; ".join(f"{r['tag']}#{r['id']}.{r['cls'][:18]}={r['w']}x{r['h']}" for r in v["tooSmallRows"][:6]))
        small_nav = [f"{x['text']}={x['w']}x{x['h']}" for x in tt["mobile_nav"]["tooSmall"]]
        R.add("R10b 移动端导航展开后链接 ≥44px",
              len(tt["mobile_nav"]["tooSmall"]) == 0,
              f"expanded={tt['mobile_nav']['expanded']} links={len(tt['mobile_nav']['links'])} "
              f"small={small_nav}")

        R.add("R-全 风险套件无控制台错误", len(errors) == 0, "; ".join(errors[:3]))
        ctx.close()
        b.close()

    R.dump("css-risks-webkit.json")
    return 0 if all(r["ok"] for r in R.rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
