# CHECKPOINT · 第零证物局 V2

> **给一个看不到旧聊天的 Agent**：读完本文件 + `ops/MASTER_STATE.md` + `ops/MEMORY_GLOBAL.md`
> 就能继续推进，不需要任何旧对话。

- **更新时间**：2026-10-30 12:25（Asia/Shanghai）— 验收整改同步（发行状态、素材来源、试玩协议）
- **生产仓库路径**：`C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\`
- **输入材料（只读）**：`..\第零证物局_V2_究极版_完整策划素材案件与DSH执行包.zip`
  → 已解压至 `..\_input\Zero_Dossier_V2\`
- **是否触碰 Decision Arena 或其它既有仓库**：**否**

---

## Gate 状态

| Gate | 内容 | 状态 | 证据 |
|---|---|---|---|
| **G0** 环境与防误操作 | 新目录、输入留档、工具链核验、基线测试 | ✅ **PASS** | `ops/ENV_CHECK.md` |
| **G1** 核心纵切（NA-001） | 打开→读证→移动→错误提交→三档提示→正确复原→两段式结案 | ✅ **PASS** | 真实 Chromium，本地 + 线上 |
| **G2** 逻辑与内容 | 6 案唯一解、逐条必要性、Python/JS 一致、语义、独立盲审 | ✅ **PASS** | `review/*.json` 24 份签核 |
| **G3** 产品体验 | 美术、三幕导航、响应式、44px、键盘、降级、隐私 | ✅ **PASS** | axe 12 状态 0 违规 |
| **G4** 代码与公开交付 | 测试、许可、README、截图、CI、Pages、itch 包 | ✅ **PASS** | 仓库 + Pages 已上线，CI 绿 |
| **G5** 真实价值 | 真实人类试玩 | ⛔ **NOT_DONE** | 需真人，不可伪造 |

---

## 真实发布状态（已实测，非声明）

| 项 | 值 |
|---|---|
| GitHub 仓库 | <https://github.com/tbj0623/zero-dossier-office> |
| 远端 HEAD | `7ed97bea` |
| 本地 HEAD | `cbe25f3`（内容与远端逐 blob 一致） |
| 线上站点 | <https://tbj0623.github.io/zero-dossier-office/> — HTTP 200 |
| Pages 来源 | GitHub Actions（`build_type=workflow`） |
| CI | ✅ success（含全部门禁） |
| **itch.io** | **已公开上线** — https://tbj0623.itch.io/zero-dossier-office |
| 社交预览 | 图片就绪，**未在仓库 Settings 设置** |
| 真实人类试玩 | **NOT_DONE** |
| 费用 | 零 |

---

## 本机真实执行的测试结果

```
$ python engine/verify_cases.py
PASS 6 author cases FORMALLY valid

$ python -m unittest discover -s tests/logic -p 'test_*.py'
Ran 44 tests — OK

$ node --test tests/logic/solver.test.mjs
tests 52 / pass 52 / fail 0

$ python tests/logic/cross_check.py
PASS Python/JS 规则一致：6 案 · 4508 条真值探针全部吻合
PASS 双方支持的运算符集合相同：9 个

$ python tests/browser/e2e.py --base http://127.0.0.1:8140
共 38 项检查：38 PASS / 0 FAIL
六案浏览器通关: 6/6

$ python tests/browser/a11y.py --base http://127.0.0.1:8140
共 12 个页面状态：12 无违规 / 0 有违规
违规总数：0

$ python tools/check_links.py dist
OK: 14 条站内引用全部可解析

$ python tools/check_no_remote.py dist
OK: dist 中无第三方运行时资源引用

$ python tools/check_license_coverage.py
OK: 全部文件都有明确的许可归属

$ python tools/check_cover_art.py
OK: 6 张封面的物件顺序均不等于答案顺序
```

证据文件：`screenshots/browser-report.json`、`screenshots/a11y-report.json`

---

## 六案资格

| 案件 | 形式化 | 语义 | 盲审 | 浏览器 | 上架 |
|---|---|---|---|---|---|
| NA-001 末班车的四张车票 | PASS | PASS | PASS | PASS | ✅ |
| NA-002 封存室的四格抽屉 | PASS | PASS | PASS | PASS | ✅ |
| NA-003 静默分拣线上的五个包裹 | PASS | PASS | PASS | PASS | ✅ |
| NA-004 灯塔没有亮起的第五盏灯 | PASS | PASS | PASS | PASS | ✅ |
| NA-005 寄不到的第五封回信 | PASS | PASS | PASS | PASS | ✅ |
| NA-006 第零号空白底片 | PASS | PASS | PASS | PASS | ✅ |

签核文件：`review/<id>-{formal,semantic,blind,browser}.json`（共 24 份）

---

## 尚未完成 / 阻塞项

| # | 项 | 需要谁 | 说明 |
|---|---|---|---|
| 1 | 真实人类试玩（G5） | 真人玩家 | 协议与邀请模板在 `docs/PLAYTEST_PROTOCOL.md`；**不可由 Agent 伪造**。当前 0 个样本。 |
| 2 | 仓库 Social Preview | 用户在 Settings 手动 | 图片已就绪（`site/assets/github-social-preview.png`，1280×640），**API 上传 ≠ 已设置**，仍未设置 |
| 3 | 屏幕阅读器实机测试 | 需要 NVDA/VoiceOver | 未做，因此不声明任何 WCAG 等级 |
| 4 | 真实 Safari / 真实 iOS Safari | 需要 Apple 设备 | WebKit（Playwright `webkit-2336`）**已测**；**真实 Safari 与 iOS Safari 仍未验证** |
| 5 | GitHub 侧仓库体积 GC | GitHub Support / 时间 | 强制推送后 GitHub 仍显示 68 MB；旧对象需后台 GC 才真正回收，见文末 |

> **已从本表移除**：
> - ~~itch.io 上传~~ —— 2026-10-30 已公开发布，
>   见 `marketing/ITCH_PAGE_DRAFT.md`（状态 `RELEASED`）。
> - ~~itch 后台 AI 披露取证~~ —— Graphics 已勾选并留证：
>   `screenshots/itch-ai-disclosure-before.json`（`false`）→ `-after.json`（`true`），
>   间隔 29 秒、唯一差异即 Graphics，`PENDING_OWNER-5` 关闭。

---

## 下一轮的第一条动作

```bash
cd "C:\Users\11930\Desktop\第零号证物局\zero-dossier-office"
python engine/verify_cases.py && node --test tests/logic/solver.test.mjs
node tools/build.mjs
python -m http.server 8140 --directory dist
# 打开 http://127.0.0.1:8140
```

若要继续推进剩余项：
1. **G5**：按 `docs/PLAYTEST_PROTOCOL.md` 的邀请模板找 3–5 名真人试玩，把真实结果填回该文件
2. **Social Preview**：用户在 GitHub Settings 手动设置
3. **真实设备**：NVDA/VoiceOver 实机、真实 Safari / iOS Safari（WebKit 不等于 Safari）
4. **仓库 GC**：GitHub 侧体积长期不降则联系 Support 触发回收

---

## 推送

**网络恢复后 `git push` 直连已正常**，直接用标准 git 流程即可：

```bash
git push origin main
```

此前因连接重置，曾用 REST API 绕过（`tools/push_incremental.py`，
只上传改动 blob，走增量）。该脚本仍可用作备用，但不再是必需。

注意：全局 gitconfig 里曾有一条 `url.<ghproxy>.insteadOf https://github.com/`
的改写规则（把所有 GitHub 请求转到代理）。已用 `github_mirror` 工具清除，
remote 也已改回直连 `https://github.com/tbj0623/zero-dossier-office.git`


---

## 2026-10-30 历史重写（仓库瘦身）

**做了什么**：用 `git-filter-repo` 从**全部历史**移除 `work/qa/**/*.png`（270 张审计过程截图），
然后 force push。

**为什么**：仓库 .git 达 128 MB，其中 61 MB 是这 270 张截图。它们对结论没有独立价值——
由 `work/qa/` 下 70 个仍入库的脚本可重新生成；4 份报告 + 99 份原始 JSON 才是证据本体。

**结果**：本地 .git 128 MB → **15 MB**；对象包 61.4 MiB → **13.9 MiB**；22 个提交全部保留。

**保留**：`docs/screenshots/` 12 张面向用户的真实运行截图**未动**。

**验证**：重写后逐项复跑——6 案唯一解、44 Python、52 JS、4508 真值探针全部通过；
线上 38/38 + 6/6、英文 12/12 全绿；CI/Pages 在新历史上 success。

**备份**：改写前完整 git bundle 在 `C:	mpackup\zdrepo-before-rewrite.bundle`（68 MB）。
需要恢复旧历史时：`git clone zdrepo-before-rewrite.bundle <dir>`。

**注意**：GitHub 侧「仓库大小」统计尚未下降（仍显示 68 MB）——
强制推送后旧对象要等 GitHub 后台 GC 才会真正回收，这不是本地问题。
若长期不降，可在仓库 Settings 里联系 GitHub Support 触发 gc。
