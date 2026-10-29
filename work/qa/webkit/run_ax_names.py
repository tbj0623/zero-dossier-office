#!/usr/bin/env python3
"""Accessible-name reality check on the home page, as WebKit exposes it.

Playwright 1.62 removed page.accessibility.snapshot(); the supported way to read
the AX tree of a Playwright browser is page.aria_snapshot(), which serialises
what the engine's accessibility tree actually exposes (YAML-ish). We parse that
and compare it against a DOM-derived name computation:

  DOM side : aria-label -> aria-labelledby -> visible text -> title -> img alt
  AX  side : the serialised tree from WebKit

Flags: empty names, duplicated names, DOM names that never reach the AX tree,
and AX interactive nodes with no name.

Writes raw/ax-names-webkit.json.
"""
from __future__ import annotations

import json
import re
from collections import Counter

from playwright.sync_api import sync_playwright
from wk_common import BASE, RAW, Results

R = Results("ax_names", "webkit")

DOM_NAMES = r"""() => {
  const nameOf = (el) => {
    const al = el.getAttribute('aria-label');
    if (al && al.trim()) return {name: al.trim(), src: 'aria-label'};
    const lb = el.getAttribute('aria-labelledby');
    if (lb) {
      const t = lb.split(/\s+/).map(id => document.getElementById(id))
        .filter(Boolean).map(n => (n.textContent || '').trim()).join(' ').trim();
      if (t) return {name: t, src: 'aria-labelledby'};
    }
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ');
    if (t) return {name: t, src: 'text'};
    const title = el.getAttribute('title');
    if (title && title.trim()) return {name: title.trim(), src: 'title'};
    const img = el.querySelector('img[alt]');
    if (img && img.alt.trim()) return {name: img.alt.trim(), src: 'img-alt'};
    return {name: '', src: 'none'};
  };
  const isVisible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    if (el.closest('[hidden]')) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 || r.height > 0;
  };
  const view = document.body;
  const rows = [];
  let i = 0;
  const landmarkOf = (el) => {
    const n = el.closest('header, footer, nav, main, dialog, [role="banner"], [role="contentinfo"], [role="navigation"], [role="main"]');
    if (!n) return 'body';
    const tag = n.tagName.toLowerCase();
    const label = n.getAttribute('aria-label') || '';
    return label ? `${tag}[${label}]` : tag;
  };
  for (const el of view.querySelectorAll('a[href], button, input, select, textarea, [role="button"], [role="link"]')) {
    if (!isVisible(el)) continue;
    const n = nameOf(el);
    const r = el.getBoundingClientRect();
    rows.push({i: i++, tag: el.tagName.toLowerCase(), id: el.id || '',
               cls: (el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className) || '',
               name: n.name, nameSrc: n.src, href: el.getAttribute('href') || '',
               landmark: landmarkOf(el),
               w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10,
               y: Math.round(r.y)});
  }
  return {rows, total: rows.length};
}"""

INTERACTIVE_ROLES = {"link", "button", "textbox", "checkbox", "radio", "combobox",
                     "menuitem", "tab", "switch", "searchbox", "slider", "spinbutton"}

LINE_RE = re.compile(r"^(?P<indent>\s*)-\s(?P<role>[a-zA-Z]+)(?:\s\"(?P<name>(?:[^\"\\]|\\.)*)\")?\s*:?\s*(?P<rest>.*)$")


def parse_aria_snapshot(text: str) -> list[dict]:
    """Turn Playwright's aria_snapshot() YAML-ish output into flat rows."""
    rows: list[dict] = []
    stack: list[int] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = LINE_RE.match(raw)
        if not m:
            continue
        indent = len(m.group("indent"))
        depth = indent // 2
        while stack and stack[-1] >= depth:
            stack.pop()
        stack.append(depth)
        rows.append({
            "depth": depth,
            "role": m.group("role"),
            "name": (m.group("name") or "").replace('\\"', '"').strip(),
            "rest": (m.group("rest") or "").strip(),
            "path": " > ".join(f"{r['role']}[{r['name'][:20]}]" for r in rows[-0:] if False) or "",
            "line": raw.rstrip(),
        })
    # build readable paths
    by_depth: dict[int, str] = {}
    for r in rows:
        by_depth[r["depth"]] = f"{r['role']}[{r['name'][:20]}]"
        r["path"] = " > ".join(by_depth[d] for d in sorted(by_depth) if d <= r["depth"])
    return rows


def main() -> int:
    out: dict = {}
    with sync_playwright() as p:
        b = p.webkit.launch(headless=True)
        out["webkit_version"] = b.version
        page = b.new_page(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page.goto(f"{BASE}/", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(900)
        page.evaluate("() => document.querySelector('#main')?.focus()")
        page.wait_for_timeout(400)

        dom = page.evaluate(DOM_NAMES)
        snap_text = page.aria_snapshot()
        ax_all = parse_aria_snapshot(snap_text)
        ax_rows = [r for r in ax_all if r["role"] in INTERACTIVE_ROLES]

        out.update({"dom_rows": dom["rows"], "dom_total": dom["total"],
                    "ax_interactive_rows": ax_rows, "ax_interactive_total": len(ax_rows),
                    "ax_all_nodes": len(ax_all), "aria_snapshot_text": snap_text})

        names = [r["name"] for r in dom["rows"]]
        empty = [r for r in dom["rows"] if not r["name"]]
        dupes = {n: c for n, c in Counter(names).items() if n and c > 1}
        # duplicates that live in DIFFERENT landmarks are expected (header nav vs
        # footer nav); duplicates INSIDE one landmark are the real problem.
        dupes_same_landmark = {}
        for n, c in dupes.items():
            landmarks = {r["landmark"] for r in dom["rows"] if r["name"] == n}
            if len(landmarks) < c:
                dupes_same_landmark[n] = {"count": c, "landmarks": sorted(landmarks)}
        ax_names = [r["name"] for r in ax_rows]
        ax_name_set = set(ax_names)

        # DOM names not represented anywhere in the AX tree
        all_ax_names = {r["name"] for r in ax_all if r["name"]}
        missing_in_ax = [r for r in dom["rows"] if r["name"] and r["name"] not in all_ax_names]
        ax_empty = [r for r in ax_rows if not r["name"]]

        # duplicates as WebKit itself presents them
        ax_dupes = {n: c for n, c in Counter(ax_names).items() if n and c > 1}

        out["summary"] = {
            "dom_total": dom["total"],
            "ax_interactive_total": len(ax_rows),
            "empty_names": [{"tag": r["tag"], "id": r["id"], "cls": r["cls"], "y": r["y"]} for r in empty],
            "empty_count": len(empty),
            "duplicate_names_dom": dupes,
            "duplicate_names_same_landmark": dupes_same_landmark,
            "duplicate_names_ax": ax_dupes,
            "missing_in_ax": [{"tag": r["tag"], "id": r["id"], "name": r["name"]} for r in missing_in_ax],
            "missing_in_ax_count": len(missing_in_ax),
            "ax_interactive_unnamed": [{"role": r["role"], "path": r["path"]} for r in ax_empty],
            "ax_interactive_unnamed_count": len(ax_empty),
        }
        (RAW / "ax-names-webkit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"DOM interactive elements on home : {dom['total']}")
        print(f"AX interactive nodes (WebKit)    : {len(ax_rows)}")
        print(f"empty DOM names                  : {len(empty)}")
        print(f"duplicate DOM names              : {dupes}")
        print(f"  (same-landmark duplicates)     : {dupes_same_landmark}")
        print(f"duplicate AX names               : {ax_dupes}")
        print(f"DOM names missing from AX        : {len(missing_in_ax)}")
        print(f"AX interactive with no name      : {len(ax_empty)}")
        print("\n-- every home link/button and its accessible name --")
        for r in dom["rows"]:
            print(f"  [{r['i']:2d}] {r['tag']:6s} {r['id'] or '-':16s} {r['name'][:46]:46s} "
                  f"({r['nameSrc']}, {r['landmark']})")
        print("\n-- AX interactive nodes as WebKit exposes them --")
        for r in ax_rows:
            print(f"  {r['role']:9s} {r['name'][:60]!r}")

        b.close()

    R.add("A1 首页每个 link/button 都有可访问名（无空名）", len(empty) == 0,
          f"{len(empty)} 空名: {[r['id'] or r['cls'][:18] for r in empty][:6]}")
    R.add("A2 DOM 侧重复名（观察项：跨 header/footer 导航属正常，不作失败）", True,
          f"{dupes} —— 同 landmark 内重复={dupes_same_landmark or '无'}")
    R.add("A2b 同一个 landmark 内没有重复的可访问名（跨 header/footer 导航重复属正常）",
          len(dupes_same_landmark) == 0,
          f"同 landmark 重复={dupes_same_landmark}; 跨 landmark 重复={dupes}")
    R.add("A2c WebKit AX 侧重复名均可由 landmark 解释（header nav vs footer nav）",
          all(n in dupes for n in ax_dupes),
          f"AX 重复={ax_dupes}")
    R.add("A3 DOM 里的可访问名都出现在 WebKit AX 树中", len(missing_in_ax) == 0,
          f"{len(missing_in_ax)} 个缺失: {[r['name'][:26] for r in missing_in_ax][:6]}")
    R.add("A4 AX 交互节点没有空名", len(ax_empty) == 0,
          f"{len(ax_empty)} 个: {[r['path'][:60] for r in ax_empty][:4]}")
    R.add("A5 AX 树暴露了首页主要控件（≥10 个交互节点）", len(ax_rows) >= 10, f"{len(ax_rows)} 个")
    R.dump("ax-names-summary.json")
    return 0 if all(r["ok"] for r in R.rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
