# MASTER_STATE · 第零证物局 V2

更新时间：2026-10-30 02:20（Asia/Shanghai）

## 一句话

六案三幕的原创中文推理游戏已**上线可玩**，通过形式化/语义/盲审/浏览器四道门禁，
以及无障碍、跨引擎、性能、隐私、安全、许可六项独立审计。

## Gate 状态

| Gate | 状态 | 依据 |
|---|---|---|
| G0 环境与防误操作 | ✅ PASS | 独立目录；未触碰 decision-arena-lab 或任何既有仓库 |
| G1 核心纵切 | ✅ PASS | NA-001 全流程真实浏览器通过（本地 + 线上） |
| G2 逻辑与内容 | ✅ PASS | 6 案 × 4 门禁签核全 PASS；独立盲审 3 轮后 6/6 CLEAN |
| G3 产品体验 | ✅ PASS | 五断点、键盘、触摸、降级、隐私；axe 12 状态 0 违规 |
| G4 代码与公开交付 | ✅ PASS | 仓库 + Pages 上线；CI 全绿；真实 URL 实测 |
| G5 真实价值 | ⛔ **NOT_DONE** | 需真实人类试玩，不可伪造 |

## 真实发布状态

| 项 | 值 |
|---|---|
| GitHub 仓库 | https://github.com/tbj0623/zero-dossier-office |
| 远端 HEAD | `b4c23ddc`（273 个受版本控制文件） |
| 线上站点 | https://tbj0623.github.io/zero-dossier-office/ |
| Pages 构建 | Actions（`build_type=workflow`） |
| 最新 CI | ✅ **success**（含全部门禁） |
| 最新 Pages 部署 | ✅ success |
| itch.io | **DRAFT_READY** — `release/itch-html5-release.zip`，未上传（需账户授权） |
| 社交预览 | 图片就绪，**未在 Settings 设置** |
| 真实人类试玩 | **NOT_DONE** |
| 费用 | 零 |

## 线上实测（针对 https://tbj0623.github.io/zero-dossier-office/）

| 检查 | 结果 |
|---|---|
| 浏览器端到端 | **38/38 PASS** |
| 六案通关 | **6/6** |
| 无障碍 axe-core | **12 个页面状态 / 0 违规** |
| 渲染阻塞资源 | **0**（关键 CSS 已内联） |
| 第三方网络请求 | **0** |
| 作者工具泄漏 | `tools/editor.html` → **404**（已排除） |
| 案件答案泄漏 | `cases/*.json` 无 `expected_solution` |

## 测试矩阵

| 套件 | 结果 |
|---|---|
| `engine/verify_cases.py` | 6/6 唯一解 + 逐条约束必要性 |
| Python unittest | **44 / 44 OK** |
| Node `--test` | **52 / 52 pass** |
| Python⇄JS 真值探针 | **4508 / 4508 吻合** |
| 浏览器 E2E | **38 / 38 PASS** |
| axe 无障碍 | **12 状态 / 0 违规** |
| `tools/check_links.py` | 14 条站内引用全部可解析 |
| `tools/check_no_remote.py` | 无第三方运行时资源 |
| `tools/check_license_coverage.py` | 273 文件全覆盖 |
| `tools/check_cover_art.py` | 6 张封面均不按答案顺序 |

## 四份独立审计的结论

| 审计 | 来源 | 结论 | 处置 |
|---|---|---|---|
| 无障碍 | `work/qa/a11y/A11Y_AUDIT.md` | 首轮 3 critical（skip-link 踢出页面、选中后焦点丢失、结案页失焦） | **全部修复并加回归测试** |
| 红队 | `work/redteam/REDTEAM_REPORT.md` | 1 critical + 3 high（CI 门禁永远 PASS、存档卡死、发布作者工具、44px 不符） | **全部修复，每个修复都用"植入坏输入→门禁必须失败"验证过** |
| 跨引擎/性能 | `work/qa/cross-browser/CROSS_BROWSER_REPORT.md` | Edge 与 Chromium **0 差异**；TTI 1327ms；45 KB 首屏；无 XSS | 采纳 2 项 Low 并修复 |
| 叙事主线 | `work/lore/MAINLINE_REVIEW.md` | 首轮 with-fixes（主线不渲染、封面印答案、终章与 006 矛盾） | **must-fix 全部修复** |

## 门禁清单（每道都做过"植入坏输入必须失败"的验证）

1. `verify_cases.py` — 作者版唯一解与逐条必要性
2. Python unittest — 44 项
3. Node test — 52 项
4. `cross_check.py` — Python/JS 真值表一致
5. `build.mjs` — 构建 + 产物与源码一致性自校验
6. `check_no_remote.py` — 无第三方运行时资源
7. `check_links.py` — 站内链接全部可解析
8. `check_license_coverage.py` — 每个文件都有许可归属
9. `check_cover_art.py` — 封面不按答案顺序绘制
10. `tests/browser/a11y.py` — axe 零违规
11. `tests/browser/e2e.py` — 38 项真实浏览器检查

## 已知限制（不隐瞒）

1. 无 Google Chrome；跨引擎为 Chromium(Playwright) + Microsoft Edge。
2. **屏幕阅读器（NVDA/JAWS/VoiceOver/TalkBack）未实机测试**，因此不声明任何 WCAG 等级。
3. **真实人类试玩未进行**——见 `docs/PLAYTEST_PROTOCOL.md`，不会伪造玩家数据。
4. itch.io 未上传（需账户授权）；社交预览未设置（需 Settings 手动）。
5. 静态站点无法防作弊，README 已明说。
6. Firefox / Safari 未测试（无可用引擎）。
7. git push 到 github.com 间歇失败，改用 REST API 推送；远端内容已逐 blob 校验与本地一致。

## 回滚

```bash
git revert <sha>          # 推荐：保留历史
git reset --hard <previous-good-sha>
```
线上：GitHub Actions → 上一次成功的 Pages run → Re-run all jobs。

- 当前已验证版本：`b4c23ddc`
- 上一个良好版本：`20a5ba93`
