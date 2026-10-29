"""Contrast (measured from painted pixels), reduced-motion and reflow checks."""
import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = 'https://tbj0623.github.io/zero-dossier-office/'
HERE = Path(__file__).parent
OUT = {}


def srgb(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = (srgb(x) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_rgb(s):
    nums = [x for x in s.replace('rgba(', '').replace('rgb(', '').replace(')', '').replace('/', ',').split(',')]
    return tuple(float(x.strip()) for x in nums if x.strip() != '')


def measure(pg, selector, sample='text', nth=0):
    """Painted-background measurement: hide glyph colour, screenshot the box, median colour.

    Returns dict with text colour, bg samples (median/min/max luminance), ratio.
    Uses a clipped page screenshot (not element screenshot) so zero-size / inline
    elements and position:fixed elements still work.
    """
    info = pg.evaluate(
        """([sel, nth]) => {
            const el = document.querySelectorAll(sel)[nth];
            if (!el) return null;
            const cs = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return {color: cs.color, bg: cs.backgroundColor, fontSize: cs.fontSize,
                    fontWeight: cs.fontWeight, rect: [r.x, r.y, r.width, r.height],
                    display: cs.display, visibility: cs.visibility, opacity: cs.opacity};
        }""",
        [selector, nth],
    )
    if not info:
        return {'selector': selector, 'error': 'not found'}
    if info['display'] == 'none' or info['visibility'] == 'hidden':
        return {'selector': selector, 'error': f"not rendered ({info['display']}/{info['visibility']})"}
    # bring into view first so the clip rect is inside the viewport
    pg.evaluate(
        """([sel, nth]) => { const el = document.querySelectorAll(sel)[nth];
             el.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'}); }""",
        [selector, nth],
    )
    pg.wait_for_timeout(120)
    # paint text transparent, screenshot the element only
    pg.evaluate(
        """([sel, nth]) => {
            const el = document.querySelectorAll(sel)[nth];
            el.dataset.__prevColor = el.style.color;
            el.style.setProperty('color', 'transparent', 'important');
            for (const c of el.querySelectorAll('*')) {
              c.dataset.__prevColor = c.style.color;
              c.style.setProperty('color', 'transparent', 'important');
            }
        }""",
        [selector, nth],
    )
    pg.wait_for_timeout(60)
    box = pg.evaluate(
        """([sel, nth]) => { const r = document.querySelectorAll(sel)[nth].getBoundingClientRect();
             const x = Math.max(0, r.x), y = Math.max(0, r.y);
             const width = Math.min(Math.max(1, r.width), innerWidth - x);
             const height = Math.min(Math.max(1, r.height), innerHeight - y);
             return {x, y, width, height}; }""",
        [selector, nth],
    )
    png = pg.screenshot(clip=box)
    pg.evaluate(
        """([sel, nth]) => {
            const el = document.querySelectorAll(sel)[nth];
            el.style.color = el.dataset.__prevColor || '';
            for (const c of el.querySelectorAll('*')) c.style.color = c.dataset.__prevColor || '';
        }""",
        [selector, nth],
    )
    img = Image.open(io.BytesIO(png)).convert('RGB')
    pixels = list(img.getdata())
    # median per channel = painted background (text area is the bulk of the box)
    pixels.sort(key=lambda p: sum(p))
    med = pixels[len(pixels) // 2]
    darkest = pixels[int(len(pixels) * 0.05)]
    lightest = pixels[int(len(pixels) * 0.95)]
    text = parse_rgb(info['color'])
    return {
        'selector': selector, 'nth': nth,
        'text_color': info['color'], 'font_size': info['fontSize'], 'font_weight': info['fontWeight'],
        'painted_bg_median': '#%02x%02x%02x' % med,
        'bg_dark_5pct': '#%02x%02x%02x' % darkest,
        'bg_light_95pct': '#%02x%02x%02x' % lightest,
        'ratio_median': round(ratio(text, med), 2),
        'ratio_worst_dark': round(ratio(text, darkest), 2),
        'ratio_worst_light': round(ratio(text, lightest), 2),
        'requires': 3.0 if float(info['fontSize'].replace('px', '')) >= 18.66 or
        (float(info['fontSize'].replace('px', '')) >= 14 and int(info['fontWeight']) >= 700) else 4.5,
    }


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()

        # ---------- contrast on the desk ----------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        pg = ctx.new_page()
        pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
        pg.wait_for_selector('.desk')
        pg.wait_for_timeout(800)
        targets = {
            'body_text_on_ink': ('.desk-head__sub', 0),
            'ev_card_body_text': ('.ev-card__body p', 0),
            'ev_card_title': ('.ev-card__title', 0),
            'ev_card_id_chip': ('.ev-card__id', 0),
            'pill_brass_on_panel': ('.desk-head .pill', 0),
            'pill_mist': ('.desk-head .pill--mist', 0),
            'slot_label_mist': ('.slot__label', 0),
            'slot_item_text': ('.slot__item', 0),
            'slot_index_brass': ('.slot__index', 0),
            'board_goal': ('.board__goal', 0),
            'status_bar': ('.status-bar', 0),
            'hint_text': ('.col-head .hint', 0),
            'crumbs': ('.desk-crumbs', 0),
        }
        contrast = {}
        for name, (sel, nth) in targets.items():
            try:
                contrast[name] = measure(pg, sel, nth=nth)
            except Exception as e:
                contrast[name] = {'error': f'{type(e).__name__}: {e}', 'selector': sel}
        # error message: trigger a wrong submit
        pg.click('#btn-submit')
        pg.wait_for_selector('#message[data-show="true"]')
        pg.wait_for_timeout(400)
        contrast['message_bad_text'] = measure(pg, '.message--bad')
        contrast['message_bad_strong'] = measure(pg, '.message--bad strong')
        contrast['message_bad_list'] = measure(pg, '.message--bad li')
        # hint message + hint card
        pg.click('#btn-hint')
        pg.wait_for_timeout(500)
        contrast['hint_card'] = measure(pg, '.hint-card')
        contrast['message_info'] = measure(pg, '.message--info')
        # selected slot background
        pg.locator('#slots .slot[data-index="1"] [data-act="pick"]').click()
        pg.wait_for_timeout(300)
        contrast['slot_selected_label'] = measure(pg, '.slot[data-selected="true"] .slot__label')
        contrast['slot_selected_item'] = measure(pg, '.slot[data-selected="true"] .slot__item')
        # buttons
        contrast['btn_primary_label'] = measure(pg, '.btn--primary')
        contrast['btn_ghost_label'] = measure(pg, '.btn--ghost')
        contrast['btn_danger_label'] = measure(pg, '.btn--danger')
        contrast['icon_btn'] = measure(pg, '.icon-btn')
        OUT['contrast_desk'] = contrast
        ctx.close()

        # ---------- toast contrast (fixed bg #14333f) ----------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        pg = ctx.new_page()
        pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
        pg.wait_for_selector('.desk')
        pg.wait_for_timeout(600)
        pg.locator('#slots .slot[data-index="0"] [data-act="pick"]').click()
        pg.wait_for_timeout(400)
        OUT['contrast_toast'] = measure(pg, '.toast')
        ctx.close()

        # ---------- reduced motion ----------
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='zh-CN', reduced_motion='reduce')
        pg = ctx.new_page()
        pg.goto(BASE + '#/case/NA-001', wait_until='domcontentloaded')
        pg.wait_for_selector('.desk')
        pg.wait_for_timeout(600)
        pg.click('#btn-submit')
        pg.wait_for_selector('#message[data-show="true"]')
        pg.wait_for_timeout(100)
        rm = pg.evaluate("""() => {
          const pick = (sel) => { const e = document.querySelector(sel); if (!e) return null;
            const cs = getComputedStyle(e);
            return {sel, animationDuration: cs.animationDuration, animationName: cs.animationName,
                    transitionDuration: cs.transitionDuration, transitionProperty: cs.transitionProperty}; };
          return {
            mediaMatches: matchMedia('(prefers-reduced-motion: reduce)').matches,
            msg: pick('#message'),
            view: pick('#view-case'),
            slot: pick('.slot'),
            iconBtn: pick('.icon-btn'),
            evChev: pick('.ev-card__chev'),
            toast: pick('#toast'),
            spinner: pick('.spinner'),
            heroScroll: pick('.hero__scroll::after'),
            stamp: pick('.stamp'),
            htmlScrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
            rootDur: getComputedStyle(document.documentElement).getPropertyValue('--dur'),
          };
        }""")
        # measure actual frames: is the message instantly at full opacity?
        pg.evaluate("document.querySelector('#message').dataset.show='false'")
        pg.wait_for_timeout(150)
        pg.click('#btn-submit')
        frames = pg.evaluate("""async () => {
          const m = document.querySelector('#message');
          const out = [];
          for (let i = 0; i < 4; i++) {
            await new Promise(r => requestAnimationFrame(r));
            out.push({opacity: getComputedStyle(m).opacity, transform: getComputedStyle(m).transform});
          }
          return out;
        }""")
        rm['message_frames'] = frames
        # transitions on hover over a slot: does the border change instantly?
        rm['slot_transition_ms'] = pg.evaluate("getComputedStyle(document.querySelector('.slot')).transitionDuration")
        OUT['reduced_motion'] = rm
        ctx.close()

        # ---------- reflow: 320px and 200%-zoom equivalents ----------
        reflow = {}
        for label, w, h, dsf in [('320px', 320, 900, 1), ('zoom200_720px', 720, 450, 1)]:
            ctx = b.new_context(viewport={'width': w, 'height': h}, locale='zh-CN',
                                device_scale_factor=dsf, is_mobile=False)
            pg = ctx.new_page()
            for route, sel in [('#/case/NA-001', '.desk'), ('#/manual', '#view-manual[data-active="true"]'),
                               ('#/', '#view-home[data-active="true"]')]:
                pg.goto(BASE + route, wait_until='domcontentloaded')
                pg.wait_for_selector(sel, timeout=30000)
                pg.wait_for_timeout(600)
                info = pg.evaluate("""() => {
                  const de = document.documentElement;
                  const over = [];
                  for (const el of document.querySelectorAll('body *')) {
                    const cs = getComputedStyle(el);
                    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.position === 'fixed') continue;
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && (r.right > de.clientWidth + 1 || r.left < -1)) {
                      over.push({tag: el.tagName, id: el.id || null,
                                 cls: typeof el.className === 'string' ? el.className : null,
                                 left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width)});
                    }
                  }
                  return {clientWidth: de.clientWidth, scrollWidth: de.scrollWidth,
                          bodyScrollWidth: document.body.scrollWidth,
                          hasHScroll: de.scrollWidth > de.clientWidth + 1,
                          overflowing: over.slice(0, 15), overflowCount: over.length};
                }""")
                # is any text clipped (scrollWidth > clientWidth on text containers)?
                clip = pg.evaluate("""() => {
                  const bad = [];
                  for (const el of document.querySelectorAll('p,h1,h2,h3,h4,li,td,th,span')) {
                    if (el.children.length) continue;
                    if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflow === 'hidden') {
                      bad.push({tag: el.tagName, cls: typeof el.className === 'string' ? el.className : null,
                                text: el.textContent.trim().slice(0, 30)});
                    }
                  }
                  return bad.slice(0, 10);
                }""")
                reflow[f'{label}:{route}'] = {**info, 'clippedText': clip}
                pg.screenshot(path=str(HERE / f'reflow-{label.replace("%", "pct")}-{route.strip("#/").replace("/", "-") or "home"}.png'),
                              full_page=False)
            ctx.close()
        OUT['reflow'] = reflow
        b.close()

    (HERE / 'contrast-motion-reflow.json').write_text(json.dumps(OUT, ensure_ascii=False, indent=2), encoding='utf-8')

    print('== CONTRAST ==')
    for k, v in OUT['contrast_desk'].items():
        if 'error' in v:
            print(f'{k:28s} ERROR {v["error"][:80]}')
        else:
            print(f'{k:28s} text={v["text_color"]:22s} bg={v["painted_bg_median"]} '
                  f'ratio={v["ratio_median"]:5.2f} (needs {v["requires"]}) worst {v["ratio_worst_dark"]}/{v["ratio_worst_light"]} {v["font_size"]}')
    print('toast:', OUT['contrast_toast'])
    print('\n== REDUCED MOTION ==')
    print(json.dumps(OUT['reduced_motion'], ensure_ascii=False, indent=1)[:2500])
    print('\n== REFLOW ==')
    for k, v in OUT['reflow'].items():
        print(k, 'client', v['clientWidth'], 'scroll', v['scrollWidth'],
              'hscroll', v['hasHScroll'], 'overflowNodes', v['overflowCount'], 'clipped', len(v['clippedText']))


if __name__ == '__main__':
    main()
