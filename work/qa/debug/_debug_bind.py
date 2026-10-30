from playwright.sync_api import sync_playwright

JS = r"""
() => {
  window.__calls = [];
  const orig = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, fn, opts) {
    if (type === 'click' && this.id === 'case-root') {
      window.__calls.push('bind#' + window.__calls.length);
    }
    return orig.call(this, type, fn, opts);
  };
}
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    # Install BEFORE the app loads
    pg.add_init_script(JS)
    pg.goto("http://127.0.0.1:8112/#/case/NA-001", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    print("case-root click listeners bound:", pg.evaluate("() => window.__calls.length"))
    b.close()
