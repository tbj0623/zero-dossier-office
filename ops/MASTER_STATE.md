# MASTER_STATE · 第零证物局 V2

更新时间：2026-10-30（Asia/Shanghai）

## 当前 Gate

| Gate | 状态 | 说明 |
|---|---|---|
| G0 环境与防误操作 | ✅ PASS | 独立新目录；未触碰 decision-arena-lab 或任何既有仓库 |
| G1 核心纵切 | ✅ PASS | NA-001 全流程真实浏览器通过 |
| G2 逻辑与内容 | ✅ PASS | 6 案 × 4 门禁签核全部 PASS |
| G3 产品体验 | ✅ PASS | 五断点、键盘、降级、隐私 |
| G4 代码与公开交付 | ✅ PASS | 仓库 + Pages 已上线，CI 绿，真实 URL 实测 |
| G5 真实价值 | ⛔ NOT_DONE | 需真实人类试玩，不可伪造 |

## 真实发布状态

| 项 | 值 |
|---|---|
| GitHub 仓库 | https://github.com/tbj0623/zero-dossier-office |
| 仓库最新提交 | `ba9cc749`（docs: itch 资料）；本地 `afd1ccd` 内容与之逐字节一致 |
| 线上站点 | https://tbj0623.github.io/zero-dossier-office/ — **HTTP 200，实测可玩六案** |
| GitHub Pages 来源 | Actions（`build_type=workflow`） |
| CI 状态 | ✅ `逻辑与内容门禁` success；✅ `真实浏览器端到端` success |
| Pages 状态 | ✅ success |
| itch.io | **DRAFT_READY** — `release/itch-html5-release.zip`（0.57 MB，21 文件，index.html 在根目录）。未上传：需用户账户授权 |
| 仓库社交预览图 | 图片已就绪（`site/assets/github-social-preview.png`），**未在 Settings 手动设置** |
| 真实人类试玩 | **NOT_DONE** |
| 费用 | 零。无付费 API、无域名、无服务器、无广告 |

## 网络异常记录

本机到 `github.com:443` 的 git push 间歇性失败（schannel / 连接重置），
改用 **GitHub REST API**（`api.github.com`，可正常访问）分 blob/tree/commit/ref 提交成功。
已逐文件比对 blob SHA：远端 116 个文件与本地工作区**内容完全一致**（差异数 0）。

## 六案资格

全部 `formal / semantic / blind / browser = PASS`，签核文件 24 份在 `review/`。

## 关键质量证据

| 测试 | 结果 | 证据路径 |
|---|---|---|
| 作者版唯一解 + 逐条必要性 | 6/6 PASS | `engine/verify_cases.py` 输出 |
| Python 单测 | 44/44 OK | `tests/logic/` |
| JS 单测 | 52/52 pass | `tests/logic/solver.test.mjs` |
| Python⇄JS 真值探针 | 4508/4508 吻合 | `tests/logic/cross_check.py` |
| 浏览器端到端（本地） | 36/36 PASS，6/6 通关 | `screenshots/browser-report.json` |
| 浏览器端到端（**线上 Pages**） | 36/36 PASS，6/6 通关 | 同上（base 已切换为线上 URL） |
| 独立盲审 | 6/6 CLEAN（经 3 轮修订） | `work/blind/BLIND_REPORT.md` |

## 已知限制（不隐瞒）

1. 无 Google Chrome；跨引擎为 Chromium(Playwright) + Microsoft Edge。
2. 屏幕阅读器（NVDA/VoiceOver）**未实机测试**，因此不声明任何 WCAG 等级。
3. 真实人类试玩 **未进行**。
4. itch.io **未上传**（需账户授权）。
5. 社交预览 **未设置**（需仓库 Settings 手动操作，API 图片上传 ≠ 已设置）。
6. 静态站点无法防作弊；已在 README 明说。

## 回滚

```bash
# 回退到上一个已验证版本
git revert ba9cc749          # 或
git reset --hard d77f40b     # 本地
```
线上回滚：GitHub Actions 里对上一次成功的 Pages run 点 "Re-run all jobs"，或 revert 后推送触发重新部署。
