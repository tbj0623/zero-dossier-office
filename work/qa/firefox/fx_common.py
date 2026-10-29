#!/usr/bin/env python3
"""Shared helpers for the Firefox QA suite of 第零证物局 (zero-dossier-office).

Everything here is READ-ONLY with respect to the product. All output goes to
work/qa/firefox/.

Target: the LIVE site  https://tbj0623.github.io/zero-dossier-office/
Both Firefox and the Chromium control run the SAME measurement code so that
element bounding boxes are directly comparable.
"""
from __future__ import annotations

import itertools
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # zero-dossier-office/
QA = Path(__file__).resolve().parent                # work/qa/firefox
RAW = QA / "raw"
SHOTS = QA / "shots"
RAW.mkdir(parents=True, exist_ok=True)
SHOTS.mkdir(parents=True, exist_ok=True)

LIVE_BASE = "https://tbj0623.github.io/zero-dossier-office/"
CASE_PUBLIC = ROOT / "cases" / "public"
CASE_AUTHOR = ROOT / "cases" / "author"

FIREFOX_VERSION = "153.0"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_public(case_id: str) -> dict:
    return json.loads((CASE_PUBLIC / f"{case_id}.json").read_text(encoding="utf-8"))


def load_author(case_id: str) -> dict:
    return json.loads((CASE_AUTHOR / f"{case_id}.json").read_text(encoding="utf-8"))


def expected_solution(case_id: str) -> list[str]:
    """The authoritative answer, read from cases/author/*.json -> expected_solution.

    Raises if the field is missing so that a silent fallback can never mask a
    discrepancy between the author answer and the browser's accepted answer.
    """
    data = load_author(case_id)
    sol = data.get("expected_solution")
    if not sol:
        raise KeyError(f"{case_id}: cases/author has no expected_solution")
    return list(sol)


def solve(case: dict) -> list[str]:
    """Independent reference solver (constraint enumeration, mirrors e2e.py)."""
    def ok(order, r):
        a = order.index(r["a"])
        op = r["op"]
        if op == "at":
            return a == r["slot"]
        if op == "not_at":
            return a != r["slot"]
        b = order.index(r["b"])
        if op == "before":
            return a < b
        if op == "after":
            return a > b
        if op == "immediately_before":
            return a + 1 == b
        if op == "immediately_after":
            return a - 1 == b
        if op == "adjacent":
            return abs(a - b) == 1
        if op == "distance":
            return abs(a - b) == r["gap"]
        if op == "between":
            c = order.index(r["c"])
            return min(b, c) < a < max(b, c)
        raise ValueError(op)

    sols = [p for p in itertools.permutations(case["items"])
            if all(ok(list(p), r) for r in case["constraints"])]
    assert len(sols) == 1, f"{case['id']} non-unique solution: {len(sols)}"
    return list(sols[0])


def current_order(page) -> list[str]:
    return page.eval_on_selector_all("#slots .slot__item", "els => els.map(e => e.textContent)")


def fill_order(page, target: list[str]) -> None:
    """Drive the real up/down buttons until the board matches `target`."""
    for want in range(len(target)):
        labels = current_order(page)
        cur = labels.index(target[want])
        while cur > want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="up"]')
            cur -= 1
        while cur < want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="down"]')
            cur += 1


def no_horizontal_overflow(page) -> dict:
    return page.evaluate("""() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        bodyScrollWidth: document.body.scrollWidth,
        ok: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1
    })""")


def undersized_targets(page, selector=None) -> list[dict]:
    sel = selector or "#slots button, .actions button, .site-header button, .site-header a, .case-card a.btn"
    return page.evaluate("""(sel) => {
        const els = [...document.querySelectorAll(sel)];
        return els.filter(e => {
            const r = e.getBoundingClientRect();
            const cs = getComputedStyle(e);
            if (cs.display === 'none' || cs.visibility === 'hidden') return false;
            return r.width > 0 && (r.width < 44 || r.height < 44);
        }).map(e => ({
            tag: e.tagName.toLowerCase(),
            id: e.id || '',
            cls: (e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className) || '',
            w: Math.round(e.getBoundingClientRect().width * 10) / 10,
            h: Math.round(e.getBoundingClientRect().height * 10) / 10,
            text: (e.textContent || '').trim().slice(0, 24)
        }));
    }""", sel)


SETTLE = """async () => {
    if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (e) {} }
    const imgs = [...document.images];
    await Promise.all(imgs.map(i => (i.complete && i.naturalWidth > 0)
        ? Promise.resolve()
        : new Promise(r => { i.addEventListener('load', r, {once:true}); i.addEventListener('error', r, {once:true}); setTimeout(r, 4000); })));
    window.scrollTo(0, 0);
    const h = document.body.scrollHeight;
    for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 25)); }
    window.scrollTo(0, 0);
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    return {images: imgs.length, decoded: imgs.filter(i => i.complete && i.naturalWidth > 0).length};
}"""


class ConsoleCollector:
    """Collects uncaught page exceptions, console.error text and failed requests."""

    def __init__(self, page):
        self.console_errors: list[str] = []
        self.pageerrors: list[str] = []
        self.request_failures: list[str] = []
        page.on("console", self._console)
        page.on("pageerror", self._pageerror)
        page.on("requestfailed", self._reqfail)

    def _console(self, msg):
        if msg.type == "error":
            self.console_errors.append(msg.text)

    def _pageerror(self, exc):
        self.pageerrors.append(f"{type(exc).__name__}: {exc}")

    def _reqfail(self, req):
        self.request_failures.append(f"{req.url} :: {req.failure}")

    @property
    def all(self) -> list[str]:
        return [f"console: {m}" for m in self.console_errors] + \
               [f"pageerror: {m}" for m in self.pageerrors]


def collect_requests(page, base: str, sink: list[str]) -> None:
    def on_request(req):
        url = req.url
        if url.startswith(base) or url.startswith("data:") or url.startswith("blob:"):
            return
        sink.append(url)
    page.on("request", on_request)


class Results:
    def __init__(self, suite: str, engine: str):
        self.suite = suite
        self.engine = engine
        self.rows: list[dict] = []
        self.extra: dict = {}

    def add(self, check: str, ok: bool, detail: str = "", **kw) -> None:
        row = {"check": check, "ok": bool(ok), "detail": detail}
        row.update(kw)
        self.rows.append(row)
        print(f"[{'PASS' if ok else 'FAIL'}] {check}" + (f" — {detail}" if detail else ""))

    def dump(self, name: str) -> Path:
        payload = {
            "suite": self.suite,
            "engine": self.engine,
            "when": now_iso(),
            "base": LIVE_BASE,
            "results": self.rows,
            "pass": sum(1 for r in self.rows if r["ok"]),
            "fail": sum(1 for r in self.rows if not r["ok"]),
            **self.extra,
        }
        p = RAW / name
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{self.suite}/{self.engine}: {payload['pass']} PASS / {payload['fail']} FAIL -> {p}")
        return p
