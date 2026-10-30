from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()

    # Monkey-patch move/onPick indirectly: count how many times the *status text* update
    # happens for one click by observing #status-text mutations.
    pg.goto("http://127.0.0.1:8112/#/case/NA-001", wait_until="networkidle")
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="networkidle")
    pg.wait_for_selector("#slots .slot")

    pg.evaluate(
        """() => {
        window.__muts = 0;
        const t = document.querySelector('#status-text');
        new MutationObserver(() => { window.__muts++; }).observe(t, { childList: true, characterData: true, subtree: true });
    }"""
    )
    pg.locator('#slots .slot[data-index="0"] [data-act="down"]').click()
    pg.wait_for_timeout(600)
    print("status-text mutations for ONE click:", pg.evaluate("() => window.__muts"))
    print("order:", pg.eval_on_selector_all("#slots .slot__item", "e=>e.map(x=>x.textContent)"))
    b.close()
