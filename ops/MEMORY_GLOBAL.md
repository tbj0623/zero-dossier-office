# MEMORY_GLOBAL · 可靠结论与已知缺陷索引

> 短索引。详细内容指向具体文件。

## 可靠结论（已验证）

1. **单一求解核心成立**：`engine/solver.mjs` 只有一份；站点通过 `tools/build.mjs` 复制到 `dist/engine/`，测试直接 import 同一文件。不存在"不同 UI 各写一套判定"。
2. **Python 与 JS 规则一致**：4508 条真值探针（全排列 × 全部约束）逐条比对，0 差异。
3. **六案都是唯一解且无冗余线索**：去掉任意一条约束，解数都 >1。
4. **每条约束都有玩家可读证据承载**：`evidence[*].constraint_ids` 的并集恰等于约束集合，无隐藏规则。
5. **发布层不含答案**：`cases/public/` 与 `dist/cases/` 均无 `expected_solution`；线上站点已用 curl 实测确认。
6. **items 顺序不泄题**：6 案均打乱且 ≠ 答案顺序；UI 侧还有 `deterministicScramble()` 二次保证。
7. **六案在真实浏览器可通关**：本地与线上 Pages 各 36/36 PASS、6/6 通关。
8. **三个真实缺陷已修复并加回归测试**（见 `docs/EDIT_MANIFEST.md`）：
   - NA-006「相距三次」单位歧义（BLOCKING，两种读法各得不同唯一解）
   - NA-003 时间轴↔格位轴映射缺失
   - NA-005「相差三格」计数歧义
9. **NA-006 hint 与正文口径已同步**（盲审复审的 caveat 命中："相隔三次"残留）。
10. **零外部运行时依赖**：无 CDN、无远程字体、无跟踪。浏览器实测第三方请求数 = 0。

## 已知缺陷 / 限制（不修或未修）

| # | 项 | 状态 | 处置 |
|---|---|---|---|
| 1 | 无 Google Chrome，仅 Chromium + Edge | 环境限制 | 记录在案，不声称"全浏览器已验证" |
| 2 | 屏幕阅读器未实机测试 | 未做 | **不声明 WCAG 等级**；只声明已实测项 |
| 3 | 真实人类试玩 | NOT_DONE | 见 `docs/PLAYTEST_PROTOCOL.md`，绝不伪造 |
| 4 | itch.io 上传 | DRAFT_READY | 需用户账户授权 |
| 5 | 仓库 Social Preview | 未设置 | 需 Settings 手动，图片上传 ≠ 已设置 |
| 6 | 静态站点可被查看源码 | 设计使然 | README 明说，不声称防作弊 |
| 7 | git push 到 github.com 间歇失败 | 环境 | 改用 REST API 提交，已验证内容一致 |

## 容易踩的坑（给后续 Agent）

- **构建脚本绝不能回写 `site/`**：早期版本把 BUILD 版本写回 `site/app.mjs`，污染源文件并触发文件版本冲突。现在只写 `dist/`。
- **`el()` 的 aria 属性**：键必须写成 `aria-<name>`，早期直接写 `label`/`disabled` 导致按钮真被禁用。
- **`tests/` 下的相对路径**：`parents[2]` 才是仓库根（`parents[1]` 是 `tests/`）。
- **修改任何证据文本后**：必须重跑 `engine/verify_cases.py` + `test_regressions.py`，并同步 `docs/EDIT_MANIFEST.md` 与 `revision`。
- **提示文案与正文必须同口径**：`TestHintBodyConsistency` 会抓这类漂移。
- **盲审包 `work/blind-src/` 改动后**：`revision` 要一起更新，否则盲审员无法确认它复审的是哪一版。

## 文件职责速查

| 路径 | 职责 |
|---|---|
| `engine/solver.mjs` | **唯一**求解核心（站点 + 测试共用） |
| `engine/verify_cases.py` | 独立 Python 校验（唯一解 + 必要性） |
| `site/app.mjs` | 全部 UI 逻辑，无 innerHTML |
| `site/index.html` | 五个视图的静态骨架 |
| `cases/author/` | 含答案，**永不发布** |
| `cases/public/` | 发布版（白名单导出） |
| `work/blind-src/` | 盲审包（无约束/答案/提示/尾声） |
| `review/` | 24 份四项门禁签核 |
| `tools/build.mjs` | 构建 dist（只写 dist） |
| `tools/scramble_items.py` | 打乱 items 顺序防泄题 |
| `tools/write_review.py` | 从真实产物生成签核 |
| `tests/browser/e2e.py` | 36 项真实浏览器检查 |
