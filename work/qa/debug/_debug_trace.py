from playwright.sync_api import sync_playwright

JS = r"""
() => {
  window.__trace = [];
  const orig = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (k.includes('order:')) {
      const st = new Error().stack.split('\n').slice(1, 7).join(' | ');
      window.__trace.push({ v: v, stack: st });
    }
    return orig.call(this, k, v);
  };
}
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto("http://127.0.0.1:8112/#/case/NA-001", wait_until="networkidle")
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="networkidle")
    pg.wait_for_selector("#slots .slot")
    pg.evaluate(JS)
    pg.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
    pg.wait_for_timeout(500)
    for t in pg.evaluate("() => window.__trace"):
        print("WRITE:", t["v"][:80])
        print("  STACK:", t["stack"][:500])
        print()
    b.close()
