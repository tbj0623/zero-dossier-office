#!/usr/bin/env python3
"""生成自包含的发布状态仪表盘（单文件 HTML，无外部依赖）。

聚合真实产物：
  - review/<id>-{formal,semantic,blind,browser}.json   四项签核
  - screenshots/browser-report.json                    浏览器检查
  - work/blind/BLIND_REPORT.md                         盲审
  - docs/EDIT_MANIFEST.md                              内容修订
  - release/RELEASE_MANIFEST.json                      itch 包

用法：python tools/build_dashboard.py
产出：dist/status.html（进构建产物，可直接在站点访问）
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = DIST / "status.html"

CST = timezone(timedelta(hours=8))
RELEASED = ["NA-001", "NA-002", "NA-003", "NA-004", "NA-005", "NA-006"]
GATES = ["formal", "semantic", "blind", "browser"]
GATE_LABEL = {
    "formal": "形式化", "semantic": "语义", "blind": "盲审", "browser": "浏览器",
}


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def collect() -> dict:
    cases = []
    for cid in RELEASED:
        pub = read_json(ROOT / "cases/public" / f"{cid}.json", {})
        gates = {}
        for g in GATES:
            d = read_json(ROOT / "review" / f"{cid}-{g}.json", {})
            gates[g] = d.get("status", "MISSING")
        evidence_ok = all(e.get("constraint_ids") for e in pub.get("evidence", []))
        cases.append({
            "id": cid,
            "title": pub.get("title", "?"),
            "difficulty": pub.get("difficulty", "?"),
            "chapter": pub.get("chapter", 0),
            "revision": pub.get("revision", "—"),
            "gates": gates,
            "all_pass": all(v == "PASS" for v in gates.values()),
            "evidence_count": len(pub.get("evidence", [])),
            "clue_count": len(pub.get("constraints", [])),
            "item_count": len(pub.get("items", [])),
            "evidence_mapped": evidence_ok,
        })

    browser = read_json(ROOT / "screenshots/browser-report.json", {})
    results = browser.get("results", [])
    itch = read_json(ROOT / "release/RELEASE_MANIFEST.json", {})

    blind_md = ROOT / "work/blind/BLIND_REPORT.md"
    blind_text = blind_md.read_text(encoding="utf-8") if blind_md.exists() else ""
    reverify_done = "复审" in blind_text
    final_clean = blind_text.count("CLEAN")

    manifest = ROOT / "docs/EDIT_MANIFEST.md"
    edit_count = 0
    if manifest.exists():
        edit_count = sum(1 for ln in manifest.read_text(encoding="utf-8").splitlines()
                         if ln.startswith("| ") and ln.split("|")[1].strip().isdigit())

    return {
        "cases": cases,
        "browser": {
            "base": browser.get("base", "—"),
            "when": browser.get("when", "—"),
            "total": len(results),
            "passed": sum(1 for r in results if r.get("ok")),
            "failed": [r["check"] for r in results if not r.get("ok")],
            "solved": browser.get("solved_cases", []),
        },
        "itch": itch,
        "blind": {"reverify_done": reverify_done, "clean_mentions": final_clean},
        "edits": edit_count,
        "git": {
            "head": git("rev-parse", "--short", "HEAD") or "—",
            "subject": git("log", "-1", "--format=%s") or "—",
            "dirty": bool(git("status", "--porcelain")),
        },
        "generated": datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
    }


def badge(status: str) -> str:
    cls = "ok" if status == "PASS" else ("bad" if status == "FAIL" else "miss")
    return f'<span class="b {cls}">{status}</span>'


def render(d: dict) -> str:
    total = len(d["cases"])
    ok = sum(1 for c in d["cases"] if c["all_pass"])
    b = d["browser"]
    pass_rate = f"{b['passed']}/{b['total']}" if b["total"] else "—"

    rows = []
    for c in d["cases"]:
        gates = "".join(
            f'<td title="{g}">{badge(c["gates"][g])}</td>' for g in GATES
        )
        rows.append(
            f'<tr>'
            f'<td class="mono">{c["id"]}</td>'
            f'<td>{c["title"]}</td>'
            f'<td class="c">{c["difficulty"]}</td>'
            f'<td class="c mono">{c["chapter"]}</td>'
            f'{gates}'
            f'<td class="c mono">{c["evidence_count"]}/{c["clue_count"]}</td>'
            f'<td class="c">{"✓" if c["evidence_mapped"] else "✗"}</td>'
            f'<td class="c mono tiny">{c["revision"]}</td>'
            f'</tr>'
        )

    failed = ", ".join(b["failed"]) if b["failed"] else "无"

    return f"""<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>发布状态 · 第零证物局</title>
<style>
:root{{--ink:#081821;--panel:#132b36;--brass:#dfb978;--mist:#9eb7b4;--text:#f2ece0;--ok:#87e1c1;--bad:#ffb0a2}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ink);color:var(--text);font:14px/1.6 "Noto Sans SC","Microsoft YaHei",system-ui,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:36px 20px 60px}}
h1{{font-size:24px;margin:0 0 4px;font-weight:700}}
.sub{{color:var(--mist);font-size:12px;letter-spacing:.06em;margin-bottom:28px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:30px}}
.stat{{background:var(--panel);border:1px solid rgba(158,183,180,.2);border-radius:12px;padding:16px}}
.stat b{{display:block;font-size:26px;font-family:ui-monospace,monospace;color:var(--brass);line-height:1.2}}
.stat span{{font-size:11px;color:var(--mist);letter-spacing:.08em;text-transform:uppercase}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border-radius:12px;overflow:hidden;font-size:13px}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid rgba(158,183,180,.12)}}
th{{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--brass);font-weight:700;white-space:nowrap}}
tr:last-child td{{border-bottom:0}}
.c{{text-align:center}} .mono{{font-family:ui-monospace,monospace}} .tiny{{font-size:11px;color:var(--mist)}}
.b{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:700;font-family:ui-monospace,monospace}}
.b.ok{{background:rgba(135,225,193,.14);color:var(--ok);border:1px solid rgba(135,225,193,.4)}}
.b.bad{{background:rgba(255,176,162,.14);color:var(--bad);border:1px solid rgba(255,176,162,.4)}}
.b.miss{{background:rgba(158,183,180,.12);color:var(--mist);border:1px solid rgba(158,183,180,.3)}}
.sec{{margin-top:34px}}
.sec h2{{font-size:15px;color:var(--brass);letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px}}
.kv{{display:grid;grid-template-columns:170px 1fr;gap:6px 16px;font-size:13px;background:var(--panel);
    border:1px solid rgba(158,183,180,.2);border-radius:12px;padding:16px}}
.kv dt{{color:var(--mist);font-size:12px}} .kv dd{{margin:0;font-family:ui-monospace,monospace;font-size:12px;word-break:break-all}}
a{{color:var(--brass)}}
.note{{font-size:11px;color:var(--mist);margin-top:10px;line-height:1.7}}
</style></head><body><div class="wrap">
<h1>发布状态</h1>
<div class="sub">第零证物局 · ZERO DOSSIER OFFICE · 生成于 {d['generated']} (UTC+8)</div>

<div class="stats">
  <div class="stat"><b>{ok}/{total}</b><span>四门禁全通过</span></div>
  <div class="stat"><b>{pass_rate}</b><span>浏览器检查</span></div>
  <div class="stat"><b>{len(b['solved'])}/6</b><span>浏览器实玩通关</span></div>
  <div class="stat"><b>{d['edits']}</b><span>已留档内容修订</span></div>
  <div class="stat"><b>{d['itch'].get('files','—')}</b><span>itch 包文件数</span></div>
</div>

<div class="sec"><h2>六案 × 四门禁</h2>
<table>
<thead><tr>
<th>编号</th><th>标题</th><th class="c">难度</th><th class="c">幕</th>
<th class="c">形式化</th><th class="c">语义</th><th class="c">盲审</th><th class="c">浏览器</th>
<th class="c">证据/约束</th><th class="c">全映射</th><th class="c">revision</th>
</tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<div class="note">
「证据/约束」= 玩家可读证据条数 / 形式化约束条数。两者必须相等才能保证没有隐藏规则。
「全映射」= 每条约束都有证据承载（✓）。
</div>
</div>

<div class="sec"><h2>浏览器实测</h2>
<dl class="kv">
<dt>测试目标</dt><dd>{b['base']}</dd>
<dt>测试时间</dt><dd>{b['when']}</dd>
<dt>通过率</dt><dd>{pass_rate}</dd>
<dt>失败项</dt><dd>{failed}</dd>
<dt>通关案件</dt><dd>{', '.join(b['solved']) if b['solved'] else '—'}</dd>
</dl></div>

<div class="sec"><h2>发行包</h2>
<dl class="kv">
<dt>itch.io ZIP</dt><dd>{d['itch'].get('itch_zip','—')}</dd>
<dt>文件数 / 解压体积</dt>
<dd>{d['itch'].get('files','—')} 个 · {(d['itch'].get('uncompressed_bytes',0)/1024/1024):.2f} MB</dd>
<dt>index.html 在根目录</dt><dd>{'✓' if d['itch'].get('index_at_root') else '—'}</dd>
</dl></div>

<div class="sec"><h2>质量门禁说明</h2>
<dl class="kv">
<dt>形式化 formal</dt><dd>唯一解 + 去掉任一约束则多解（无冗余线索）+ 每条约束都有证据承载</dd>
<dt>语义 semantic</dt><dd>每条证据正文的中文读法与算子参数严格同义，逐条核对并留档</dd>
<dt>盲审 blind</dt><dd>只给剥离答案的材料，独立解题者自行推导并报告歧义</dd>
<dt>浏览器 browser</dt><dd>真实 Chromium 完成通关，含键盘、断点、降级、无第三方请求</dd>
</dl>
<div class="note">
任一门禁未 PASS 的案件不应出现在正式档案柜。本页数据直接读取 <code>review/*.json</code>，
不是手工填写的宣传数字。
</div></div>

<div class="sec"><h2>仓库</h2>
<dl class="kv">
<dt>HEAD</dt><dd>{d['git']['head']}</dd>
<dt>最近提交</dt><dd>{d['git']['subject']}</dd>
<dt>工作区</dt><dd>{'有未提交改动' if d['git']['dirty'] else '干净'}</dd>
</dl></div>

<div class="note" style="margin-top:34px">
本页由 <code>tools/build_dashboard.py</code> 自动生成，数据来自真实签核文件与测试报告。
</div>
</div></body></html>"""


def main() -> int:
    if not DIST.exists():
        print("先运行 node tools/build.mjs", file=sys.stderr)
        return 1
    data = collect()
    OUT.write_text(render(data), encoding="utf-8")
    print(f"OK  仪表盘：{OUT}")
    print(f"    {sum(1 for c in data['cases'] if c['all_pass'])}/{len(data['cases'])} 案四门禁全通过 · "
          f"浏览器 {data['browser']['passed']}/{data['browser']['total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
