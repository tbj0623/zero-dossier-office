# MASTER_STATE · 第零证物局 V2

更新时间：2026-10-30 06:45（Asia/Shanghai）

## 一句话

六案三幕的原创推理游戏已**上线可玩**，中文 + 英文双语，在 **Chromium / Firefox / WebKit
三个引擎**上实测通过；通过形式化/语义/盲审/浏览器四道案件门禁，以及无障碍、跨引擎、
性能、隐私、安全、许可六项独立审计。

## Gate 状态

| Gate | 状态 | 依据 |
|---|---|---|
| G0 环境与防误操作 | ✅ PASS | 独立目录；未触碰 decision-arena-lab 或任何既有仓库 |
| G1 核心纵切 | ✅ PASS | NA-001 全流程真实浏览器通过（本地 + 线上 + 三引擎） |
| G2 逻辑与内容 | ✅ PASS | 6 案 × 4 门禁签核全 PASS；独立盲审 3 轮后 6/6 CLEAN |
| G3 产品体验 | ✅ PASS | 五断点、键盘、触摸、降级、隐私；axe 12 状态 0 违规 |
| G4 代码与公开交付 | ✅ PASS | 仓库 + Pages 上线；CI 全绿；真实 URL 实测 |
| G5 真实价值 | ⛔ **NOT_DONE** | 需真实人类试玩，不可伪造 |

## 真实发布状态

| 项 | 值 |
|---|---|
| GitHub 仓库 | https://github.com/tbj0623/zero-dossier-office |
| 远端 HEAD | 见仓库（git 直连已恢复，不再需要 API 绕过） |
| 线上站点 | https://tbj0623.github.io/zero-dossier-office/ |
| Pages 构建 | Actions（`build_type=workflow`） |
| **itch.io（已上线）** | **https://tbj0623.itch.io/zero-dossier-office** — 公开，HTML 版，1280×800 嵌入，手机友好 + 全屏 + 滚动条 |
| 社交预览 | 图片就绪，**未在 Settings 设置** |
| 真实人类试玩 | **NOT_DONE** |
| 费用 | 零 |

### itch.io 发布实测（匿名访客视角）

`tests/browser/test_itch_live.py` 在**公开的 itch 页面**上用全新浏览器上下文（未登录）实测 **13/13**：
公开页 200 → Run game → 游戏在 `html-classic.itch.zone` 的 iframe 中加载 → 档案柜 6 张卡 →
NA-001 用真实按钮排列 → 提交 → 结案页两段复盘。零未捕获异常。

## 三引擎实测

| 引擎 | 版本 | 旅程 | 六案通关 | 布局差异 | 结论 |
|---|---|---|---|---|---|
| Chromium | 151.0.7922.34 | 38/38 | 6/6 | 基准 | ✅ |
| Firefox | 153.0（Gecko 1538） | 43/43 | 6/6 | ≤1.85 px；header/hero **0.00 px** | ✅ ship-with-fixes（4 项均已处置） |
| WebKit | 26.5（webkit-2336） | 34/34 | 6/6 | ≤1.14 px；0 项超 2 px | ✅ ship-with-fixes（1 项已修） |

**跨引擎统一回归** `tests/browser/cross_engine.py`：**42/42 PASS**（14 项 × 3 引擎）。

### 三引擎各自发现的真实问题（均已修复）

| 来源 | 问题 | 严重度 | 修复 |
|---|---|---|---|
| Firefox | `backdrop-filter` 在 Gecko 上能解析但不绘制 → 头部变成 0.84 透明灰块 | Low（视觉） | 头部改为近不透明渐变，不再依赖模糊成立 |
| WebKit | **Safari 默认把 `<a href>` 排除在 Tab 序列外** → 键盘用户 20 个链接一个都到不了 | **High（无障碍）** | 所有 `<a>` 补 `tabindex="0"`；修复后 WebKit Tab 序列与 Chromium **逐项相同** |
| WebKit | `<dialog>` 自动 focus trap 在 WebKit 不完整，Tab 会逃到 `BODY` | Medium（无障碍） | 补显式 Tab 循环；三引擎实测 escapes=0 |

## itch.io 嵌入实测（跨源 iframe）

itch.io 的 HTML5 游戏运行在 itchi.io 域名下的 **iframe** 里，与直接访问不同。
`work/qa/itch-iframe/host.html` 搭了一个同机跨源宿主来还原这个场景，
`tests/browser/test_itch_iframe.py` 实测 **10/10 通过**：渲染、导航、六案卡片、
移动按钮、键盘重排全部正常，宿主页未被劫持，零未捕获异常。

由此修掉一个诚实性缺陷：浏览器若真的拒绝 `localStorage`（隐私模式等），
应用原先会**静默不保存**，玩家刷新后进度全丢却以为是自己弄错。
现在会探测写入能力，不可用时明确提示「不允许保存进度，但游戏完全可玩」；
能正常保存时绝不显示。中英文都有。

## Lighthouse 实测（Google 官方工具，线上 URL）

| 页面 | 性能 | 无障碍 | 最佳实践 | SEO |
|---|---|---|---|---|
| 首页 | **97** | **100** | **100** | **100** |
| 案件调查桌 NA-006（最重） | **96** | **100** | **100** | **100** |

核心指标（首页，移动端模拟）：FCP 1.3 s · LCP 2.0 s · **TBT 0 ms** · **CLS 0**。
修复前为 71/100/100/92，CLS 高达 0.442。详见 `work/qa/lighthouse/LIGHTHOUSE_REPORT.md`。

注意：Lighthouse 是**实验室合成指标**，不等于真实用户体验，也不是 Core Web Vitals 现场数据。
无障碍满分**不等于** WCAG 合规（本项目未做屏幕阅读器实机测试）。

## 双语言实测

| 语言 | 页面 | 六案 | axe | 中文残留 |
|---|---|---|---|---|
| 中文（默认） | 38/38 | 6/6 | 12 状态 / 0 违规 | — |
| 英文（`?lang=en`） | 12/12 | 6/6（用英文名通关） | 12 状态 / 0 违规 | **0**（五个页面 + 六个案件桌面/结案页） |

英文版还重绘了 3 张烘死中文的封面图（`-en.webp`），并保证**不按答案顺序排列**。

## 测试矩阵

| 套件 | 结果 |
|---|---|
| `engine/verify_cases.py` | 6/6 唯一解 + 逐条约束必要性 |
| Python unittest | **44 / 44 OK** |
| Node `--test` | **52 / 52 pass** |
| Python⇄JS 真值探针 | **4508 / 4508 吻合** |
| 浏览器 E2E（中文） | **38 / 38 PASS** |
| 浏览器 E2E（英文） | **12 / 12 PASS** |
| 跨引擎（3 引擎） | **42 / 42 PASS** |
| Safari 键盘可达性 | **9 / 9 PASS** |
| axe 无障碍（双语言） | **各 12 状态 / 0 违规** |
| 门禁自证：无第三方资源 | **18/18 坏输入被拦 + 7/7 合法放行** |
| 门禁自证：链接完整性 | **11/11 坏引用被拦 + 6/6 合法放行** |
| `check_license_coverage.py` | 全部文件都有许可归属 |
| `check_cover_art.py` | 6 张封面均不按答案顺序 |

## CI 门禁（每道都做过"植入坏输入必须失败"的验证）

1. `verify_cases.py` — 作者版唯一解与逐条必要性
2. Python unittest — 44 项
3. Node test — 52 项
4. `cross_check.py` — Python/JS 真值表一致
5. `build.mjs` — 构建 + 产物与源码一致性自校验
6. `check_no_remote.py` — 无第三方运行时资源（18 条向量）
7. `check_links.py` — 站内链接全部可解析（11 条向量）
8. `check_license_coverage.py` — 每个文件都有许可归属
9. `check_cover_art.py` — 封面不按答案顺序绘制
10. `add_tabindex.py --check` — Safari 键盘可达性
11. `test_gate_no_remote.py` — 门禁自证（植入即失败）
12. `test_gate_links.py` — 门禁自证（植入即失败）
13. `tests/browser/a11y.py` — axe 零违规
14. `tests/browser/e2e.py` — 38 项真实浏览器检查

## 四份独立审计的结论

| 审计 | 来源 | 结论 | 处置 |
|---|---|---|---|
| 无障碍 | `work/qa/a11y/A11Y_AUDIT.md` | 首轮 3 critical | **全部修复并加回归测试** |
| 红队 | `work/redteam/REDTEAM_REPORT.md` | 1 critical + 3 high | **全部修复，每个修复都用"植入坏输入→门禁必须失败"验证过** |
| Firefox | `work/qa/firefox/FIREFOX_REPORT.md` | 43/43；4 项分歧 | backdrop-filter 已治本 |
| WebKit | `work/qa/webkit/WEBKIT_REPORT.md` | 34/34；1 high + 4 info | Safari 键盘可达性已修复 |
| 叙事主线 | `work/lore/MAINLINE_REVIEW.md` | 首轮 with-fixes | **must-fix 全部修复** |
| 跨引擎/性能 | `work/qa/cross-browser/CROSS_BROWSER_REPORT.md` | Edge vs Chromium 0 差异 | 采纳 2 项 Low 并修复 |

## 已知限制（不隐瞒）

1. **WebKit ≠ Safari。** Playwright 的 WebKit 共享 Safari 的引擎，但不共享它的图形栈
   （WebGL 回报占位 `Apple GPU`，这几乎肯定就是 `backdrop-filter` 不绘制的原因）。
   正确表述是「**WebKit（Playwright build webkit-2336, engine 26.5）已验证；真实 Safari 未验证**」。
2. 无 Google Chrome；跨引擎为 Chromium(Playwright) + Firefox(Playwright) + WebKit(Playwright)。
3. **屏幕阅读器（NVDA/JAWS/VoiceOver/TalkBack）未实机测试**，因此不声明任何 WCAG 等级。
4. **真实人类试玩未进行**——见 `docs/PLAYTEST_PROTOCOL.md`，不会伪造玩家数据。
5. **真实 iOS Safari 未测**（动态工具栏 vs `100dvh`、橡皮筋滚动、安全区）。
6. itch.io 未上传（需账户授权）；社交预览未设置（需 Settings 手动）。
7. 静态站点无法防作弊，README 已明说。
8. git push 到 github.com 间歇失败，改用 REST API 推送；远端内容已逐 blob 校验与本地一致。

## 回滚

```bash
git revert <sha>          # 推荐：保留历史
git reset --hard <previous-good-sha>
```
线上：GitHub Actions → 上一次成功的 Pages run → Re-run all jobs。
