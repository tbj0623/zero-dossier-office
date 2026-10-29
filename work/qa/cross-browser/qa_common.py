#!/usr/bin/env python3
"""Shared helpers for the cross-browser / performance / fuzz QA suite.

Everything here is READ-ONLY with respect to the product; all output goes to
work/qa/cross-browser/.
"""
from __future__ import annotations

import itertools
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # zero-dossier-office/
QA = Path(__file__).resolve().parent
RAW = QA / "raw"
SHOTS = QA / "shots"
RAW.mkdir(parents=True, exist_ok=True)
SHOTS.mkdir(parents=True, exist_ok=True)

LIVE_BASE = "https://tbj0623.github.io/zero-dossier-office/"
CASE_DIR = ROOT / "cases" / "public"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_case(case_id: str) -> dict:
    return json.loads((CASE_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def solve(case: dict) -> list[str]:
    """Reference solver independent of the site code (mirrors tests/browser/e2e.py)."""
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


def no_horizontal_overflow(page) -> bool:
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )


class ConsoleCollector:
    """Collects uncaught page exceptions and console.error text."""

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
