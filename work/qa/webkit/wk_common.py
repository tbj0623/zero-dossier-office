#!/usr/bin/env python3
"""Shared helpers for the WebKit QA suite of 第零证物局 (zero-dossier-office).

Everything here is READ-ONLY with respect to the product. All output goes to
work/qa/webkit/.

Target: the LOCAL server http://127.0.0.1:8140 (built site), so results are not
affected by GitHub Pages deployment lag.
"""
from __future__ import annotations

import itertools
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # zero-dossier-office/
QA = Path(__file__).resolve().parent                # work/qa/webkit
RAW = QA / "raw"
SHOTS = QA / "shots"
CROPS = QA / "crops"
for d in (RAW, SHOTS, CROPS):
    d.mkdir(parents=True, exist_ok=True)

BASE = os.environ.get("WK_BASE", "http://127.0.0.1:8140")
CASE_PUBLIC = ROOT / "cases" / "public"
CASE_AUTHOR = ROOT / "cases" / "author"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# --------------------------------------------------------------------------
# case data
# --------------------------------------------------------------------------
def load_public(case_id: str) -> dict:
    return json.loads((CASE_PUBLIC / f"{case_id}.json").read_text(encoding="utf-8"))


def load_author(case_id: str) -> dict:
    return json.loads((CASE_AUTHOR / f"{case_id}.json").read_text(encoding="utf-8"))


def expected_solution(case_id: str) -> list[str]:
    """Authoritative answer from cases/author/*.json -> expected_solution."""
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


# --------------------------------------------------------------------------
# page helpers
# --------------------------------------------------------------------------
def current_order(page) -> list[str]:
    return page.eval_on_selector_all("#slots .slot__item", "els => els.map(e => e.textContent)")


def fill_order(page, target: list[str], pause: int = 60) -> None:
    """Drive the real up/down buttons until the board matches `target`."""
    for want in range(len(target)):
        labels = current_order(page)
        cur = labels.index(target[want])
        while cur > want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="up"]')
            page.wait_for_timeout(pause)
            cur -= 1
        while cur < want:
            page.click(f'#slots .slot[data-index="{cur}"] [data-act="down"]')
            page.wait_for_timeout(pause)
            cur += 1


def goto(page, route: str, wait_ms: int = 500) -> None:
    page.goto(f"{BASE}/{route}", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(wait_ms)


def open_case(page, case_id: str) -> None:
    goto(page, f"#/case/{case_id}", wait_ms=600)
    page.wait_for_selector("#slots .slot", timeout=15000)


def no_horizontal_overflow(page) -> dict:
    return page.evaluate("""() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        bodyScrollWidth: document.body.scrollWidth,
        ok: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1
    })""")


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
    """Collects console.error, uncaught page errors and failed requests."""

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
        return ([f"console: {m}" for m in self.console_errors]
                + [f"pageerror: {m}" for m in self.pageerrors]
                + [f"requestfailed: {m}" for m in self.request_failures])


def collect_requests(page, sink: list[str], base: str = BASE) -> None:
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
            "base": BASE,
            "results": self.rows,
            "pass": sum(1 for r in self.rows if r["ok"]),
            "fail": sum(1 for r in self.rows if not r["ok"]),
            **self.extra,
        }
        p = RAW / name
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{self.suite}/{self.engine}: {payload['pass']} PASS / {payload['fail']} FAIL -> {p}")
        return p


def file_provenance() -> dict:
    """Hash the served build so numbers can be tied to one exact build."""
    import hashlib
    from urllib.request import urlopen
    out = {}
    for rel in ("index.html", "app.mjs", "styles/app.css", "styles/base.css",
                "styles/tokens.css", "i18n.mjs", "engine/solver.mjs"):
        try:
            with urlopen(f"{BASE}/{rel}", timeout=15) as r:
                data = r.read()
            out[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        except Exception as exc:  # noqa: BLE001
            out[rel] = {"error": str(exc)[:160]}
    out["_when"] = now_iso()
    return out
