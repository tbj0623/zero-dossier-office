# 红队审查报告 · 第零证物局 V2

**审查对象**：`https://tbj0623.github.io/zero-dossier-office/`（线上）＋ 仓库 `tbj0623/zero-dossier-office`
**审查时间**：2026-10-30
**审查视角**：发布前的对抗性红队（隐私 / 版权 / 营销真实性 / 安全 / 伦理 / 无障碍）
**审查者立场**：只报告，不修复。写入范围仅限 `work/redteam/`。

> 本报告所有"已实测"结论都附带可复现的探针脚本（同目录 `*.py`）与原始 JSON 输出。
> 凡我没有实际验证的，一律写"未验证"，不用推测填空。

---

## Executive summary

### 结论：**SHIP-WITH-FIXES**（若剩余 3 项在部署前处理完，则可 **SHIP**）

这个项目在**最容易被吹牛的地方反而格外诚实**——这是本次审查最意外的发现。隐私声明逐条可验证为真（我抓了 20 个请求、0 个第三方、0 个 cookie、0 个 sessionStorage、0 个 IndexedDB、0 个 Service Worker，提交错误答案时 0 个网络请求）；"唯一解 + 每条线索都必要"我用独立 Python 实现复算，6/6 全部成立；"不伪造玩家好评"这一点项目自己写在 `PLAYTEST_PROTOCOL.md` 第 6 行并在 README 第 135 行明确标注未验证。**这些都不是包装，是真的。**

它曾经有 **1 个 critical + 3 个 high**。**审查期间团队把 6 条（含全部 critical/high）真正修好了**，我逐条复验通过（§0.1）——修得对，不是掩盖症状。但修复 `build.mjs` 时引入了一个新回归（RT-026，3 个死链接），且**所有修复都还没部署**（线上仍是旧版 `41fc9520`）。

**因此最终判断：不要在修复未部署的情况下发布 itch.io 页面。** 先处理 §0.3 的 3 件事，再上线。

这些问题的共同特征是：**项目自己以为已经验证过了，但验证方法本身有漏洞**（CI 正则、e2e 选择器、链接完整性）。这也是为什么我在 §4.1 里坚持要"测试你的测试"。

| 严重度 | 数量 | 当前状态 |
|---|---|---|
| **critical** | 1 | RT-001：CI 的"无第三方远程资源"门禁正则用了 PCRE 前瞻，GNU grep 不支持 → 该门禁**永远 PASS**，我植入外部 `<script>` 仍输出"OK"。**→ 审查期间已被修复并复验通过**（见 §0） |
| **high** | 3 | RT-002：存档残留旧物件名会让案件**永久卡在"正在取阅档案…"**。**→ 已修复并复验通过**<br>RT-003：`site/tools/editor.html` 被 `build.mjs` 全量拷进 `dist/`。**→ 已修复，但修复引入新回归 RT-026**<br>RT-004："交互目标 ≥ 44px"实测不成立。**→ 已修复并复验通过（0 个不达标）** |
| **medium** | 10 | 2 条在审查期间已修复（axe 违规、heading 层级），8 条仍开放（含新回归 RT-026） |
| **low** | 12 | 全部开放，见 `FINDINGS.json` |
| **合计** | **26** | **已修复 6 / 仍开放 20；开放项中无 critical、无 high** |

### 0. 重要说明：审查期间仓库在被并发修改

本次审查期间，团队的其他成员在持续提交（HEAD 从 `41fc9520` → `ace474f` → `01be953` → `8e46506` → `0e131eb`），并且有未提交的工作树改动。因此：

- **§1–§9 的发现是相对于我审查时的快照**（线上 `BUILD = 41fc9520`，以及 HEAD `0e131eb` 的构建）。
- 我在最后一轮**用当前 HEAD 的本地构建重新验证了全部 headline 发现**，结果记录在 `work/redteam/reverify_head.json` 与本节 §0.1 表格。
- **"已修复"是我实测确认的，不是听说的。** 每一条都附了复验方法。
- 线上站点仍是 `BUILD = 41fc9520`（旧版），**上述所有修复都还没有部署**。

### 0.1 修复复验结果（当前 HEAD 构建，本地 `http://127.0.0.1:8899`）

| 发现 | 复验方法 | 结果 |
|---|---|---|
| RT-001 CI 门禁 | 植入 `<script src="https://cdn.evil.example/t.js">` 到 `dist/` 后跑 `python tools/check_no_remote.py dist` | ✅ **真的失败了**：`::error::发现第三方运行时资源引用 ... EXIT=1`。干净构建时 `OK ... EXIT=0`；正文里的普通 URL（`https://example.com/x`）不误报 → 修复**精准且有效** |
| RT-002 存档卡死 | 注入 `{"order":["红票（旧名）",…]}` 后硬刷新 `#/case/NA-001` | ✅ `slots_rendered=true`、`submit_present=true`、`stuck_loading=false`、`pageerrors=[]`。坏存档被丢弃并回退到初始排列 |
| RT-003 编辑器发布 | `node tools/build.mjs` 后检查 `dist/tools` | ✅ `dist/tools` **不存在**；`build.mjs` 新增了构建后防回归断言 |
| RT-004 44px | 全量选择器 `a[href],button,input,select,textarea,[tabindex]`，390/768px × 5 路由 | ✅ **全部 0 个不达标**（390px: 14/15/28/10/9 个目标；768px: 17/18/31/13/12 个目标） |
| RT-008 `aria-prohibited-attr` | `#hints` 现在有 `role='region'` | ✅ 已修 |
| RT-009 heading 层级 | 首页 `h3`→`h2`、页脚 `h4`→`h2`、verdict 加 `h1` | ✅ 已修 |
| RT-008/009 合计 | axe-core 全量复跑（5 路由，wcag2a/2aa/21a/21aa/best-practice） | ✅ **5/5 路由 0 violation** |
| RT-026 新回归 | `curl` 访问 dist 里 3 个导航链接 | ❌ `/tools/editor.html` → **404**、`/status.html` → **404** |

**换句话说：我提出的 4 个 headline 问题里有 3 个（外加 2 个 medium）已经被真正的修好了，而且修得对——不是掩盖症状。唯一新问题是修复 RT-003 时忘了同步删掉页面上的入口链接。**

### 0.2 关于 RT-026（新发现，medium）

- **Evidence**：`site/index.html:82`（主导航）、`:268`（页脚）都有 `<a href="./tools/editor.html">案件编辑器</a>`；`:269` 有 `<a href="./status.html">发布状态</a>`。但 `build.mjs` 现在会**主动排除** `site/tools/`，而 `status.html` 只由 `tools/build_dashboard.py` 单独生成、`build.mjs` 不产出它。用当前 HEAD 构建后实测：`/tools/editor.html` → **404**、`/status.html` → **404**。
- **Why it matters**：玩家点主导航第二个链接就吃 404。更尴尬的是，这是**修复一个发布安全问题所引入的回归**——`build.mjs` 的防回归断言保证了"文件不会进包"，但没人检查"页面还在引用它"。这类问题正好说明为什么 §4.1 建议的"负向测试"和链接完整性检查都应该进 CI。
- **Suggested fix**：
  1. 从 `site/index.html` 删掉这 3 个链接（编辑器与状态页是作者工具，本来就不该出现在玩家站点）。
  2. 在 CI 里加一步链接完整性检查：构建后扫描 `dist/**/*.html` 的所有 `href`/`src`，断言每个相对路径都能在 `dist/` 里找到对应文件。
  3. 若确实想让玩家看到"发布状态"，把 `build_dashboard.py` 接入 `build.mjs` 的构建流程（而不是单独手动跑）。

### 0.3 仍开放的问题（按优先级）

| ID | 严重度 | 状态 | 一句话 |
|---|---|---|---|
| RT-026 | medium | **新开放** | 3 个导航链接指向已移除页面，全部 404 |
| RT-005 | medium | 开放 | 229 个已跟踪文件不属任何许可；`ASSETS_LICENSE` §2/§3 缺明确授权句 |
| RT-006 | medium | 开放 | `ASSETS_LICENSE.md:26` 引用不存在的 `docs/STORY_BIBLE.md` |
| RT-007 | medium | 开放 | `work/qa/a11y/axe.min.js` 是 MPL-2.0 第三方代码入库，无许可证说明 |
| RT-010 | medium | 开放 | README "独立解题者" 未限定为 AI agent |
| RT-011 | medium | 开放 | NA-006 终章块仍无"结案后补充记录"标签 |
| RT-012 | medium | 开放 | GitHub Actions 全部用浮动 major tag，未固定 SHA |
| RT-013 | medium | 开放 | `docs/screenshots/` 缺可复现生成脚本 |
| RT-014..RT-025 | low | 开放 | 12 条低危项，见 `FINDINGS.json` |

**发布前必须做的三件事**（RT-001/002/004 已修，剩余）：
1. **删掉 `site/index.html:82/268/269` 的 3 个死链接**（RT-026），并在 CI 加链接完整性检查。
2. **补 `ASSETS_LICENSE.md` 的明确授权句**（RT-005）——这是唯一会直接影响他人合规复用的问题。
3. **确认上述修复真的部署上线**（线上仍是 `41fc9520`），然后重新跑一遍 `net_probe.py` 与 axe 复验。

其余 medium/low 可在 itch.io 上架前陆续处理。

---

## 1. 隐私声明 vs 实际行为

### 1.1 结论：**声明全部为真**，这是本项目最扎实的一块

我逐条核对了 `docs/PRIVACY.md`、`README.md:112-118`、`site/index.html:199-202` 的每一条声明。

**实测方法**（脚本：`work/redteam/net_probe.py`，原始输出：`work/redteam/net_probe.json`）：
用 Playwright 打开线上站点，依次访问首页、档案柜、全部 6 个案件（每案展开全部证物 + 揭开全部提示）、玩法说明、关于页，然后**故意提交一个错误答案**，全程记录 `page.on("request")`。

**实测结果**：

| 声明 | 实测 | 结论 |
|---|---|---|
| 无账户 | 全站无登录/注册 UI，无 `Authorization` 头 | ✅ 真 |
| 无后端 | 20 个请求全部是 `GET` 静态文件 | ✅ 真 |
| 无分析脚本 | 无 `gtag` / `analytics` / `pixel` / `sendBeacon` | ✅ 真 |
| 无第三方 CDN | **distinct hosts = `['tbj0623.github.io']`**，`third_party_requests = []` | ✅ 真 |
| 无远程字体 | CSS 中 0 个 `@font-face`、0 个 `@import`、0 个外部 `url()` | ✅ 真 |
| 不上传答案 | **提交错误答案前后请求数差 = 0** | ✅ 真 |
| 进度只在 localStorage | `localStorage` 键全部以 `zd:v1:` 开头；`cookies=[]`、`document.cookie=''`、`sessionStorage={}`、`indexedDB=[]`、`caches=[]`、`serviceWorkers=0` | ✅ 真 |
| 键名前缀 `zd:v1:` | 实测键：`zd:v1:progress`、`zd:v1:order:NA-001` … `NA-006`，与 `PRIVACY.md:20-25` 表格**逐字一致** | ✅ 真 |

**代码层交叉验证**：全仓库（限定 `.mjs/.js/.html/.css/.json`）搜索 `fetch(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|document.cookie|sessionStorage|gtag|google-analytics|analytics|pixel`，**只有 3 处命中**：
- `site/app.mjs:352` — `fetch(\`./cases/${id}.json\`)`，同源、相对路径、`id` 已被 `RELEASED` 白名单和 `/^NA-\d{3}$/` 双重约束。
- `site/app.mjs:114` — `const NS = 'http://www.w3.org/2000/svg'`，是 SVG 命名空间字符串常量，**不发起请求**。
- `site/assets/archive-emblem.svg:1` — `xmlns="http://www.w3.org/2000/svg"`，同上。

**一个值得表扬的细节**：`site/app.mjs:349-353` 的 `loadCase()` 会先查 `RELEASED` 白名单再 `fetch`，所以路由 `#/case/NA-999` 不会产生任何请求。我用 `work/qa/cross-browser/shots/route-na999.png` 之外的方式也复核了：`parseHash()`（`app.mjs:252-261`）用 `/^NA-\d{3}$/` 正则过滤，非法 ID 直接落到 `home` 路由。

### 1.2 [SEVERITY: low] `PRIVACY.md:47` "不含…性内容…适合一般公众" 是一句无法被代码保证的自我评级

- **Evidence**：`docs/PRIVACY.md:45-47`。
- **Why it matters**：这不是隐私声明，是内容分级声明。它出现在隐私文档里会让读者误以为这句话经过了某种评级流程。实际上没有任何分级机构参与，也没有 age gate。
- **Suggested fix**：把这段移到独立的内容说明里，措辞改为"本作未包含血腥、性内容或真实人物；未经过任何分级机构评定"。

### 1.3 [SEVERITY: low] `PRIVACY.md` 未说明 GitHub Pages 会记录完整 URL（含 hash 之外的路径）

- **Evidence**：`docs/PRIVACY.md:37-39` 已经提到"平台自身可能按其隐私政策记录常规访问日志（如 IP、User-Agent、请求路径）"，**这一点写得很到位**。
- **Why it matters**：只差一句"案件 ID 会出现在请求路径里（如 `/cases/NA-003.json`），因此托管方日志能看出你玩到第几案"。这是玩家可能关心的元数据。
- **Suggested fix**：在 §3 补一句即可。属于锦上添花，不是缺陷。

### 1.4 明确否定：**没有发现任何隐私声明与代码不符的地方**

我没有找到"文档说了但代码没做到"的隐私项。相反，我找到两处**代码比文档更严格**：
- `store.clearAll()`（`app.mjs:156-168`）只删 `zd:v1:` 前缀的键，不会误删同域其他应用的数据 —— 比"清除本机全部进度"这个措辞更克制。
- 隐私模式下 `localStorage` 抛异常时全部 `try/catch` 静默降级（`app.mjs:136-169`）。我实测（`work/redteam/no_storage_probe.py`）：把 `localStorage` 整个替换成抛 `SecurityError` 的桩对象后，**案件仍能渲染、仍能通关到结案页**，`renders_without_localstorage: true`、`completes_without_localstorage: true`、0 报错。`PRIVACY.md:35` 那句"游戏仍可完整游玩…会静默降级"是**真的**。

---

## 2. 版权 / 许可卫生

### 2.1 [SEVERITY: high → 现已修复，但引入新回归 RT-026] `build.mjs` 曾整目录拷贝 `site/`，`site/tools/editor.html` 进入 `dist/`

> **状态更新（2026-10-30 复验）**：`build.mjs` 的 filter 现在排除 `site/tools/`，并加了构建后防回归断言（`dist/tools` 存在则 `exit 1`）。实测 `dist/tools` 不存在。**但页面上的 3 个入口链接没同步删掉，见 RT-026。**

- **Evidence**：
  - `tools/build.mjs:73-79`：`cpSync(SITE, outDir, { recursive: true, filter: ... })`，filter **只排除** `node_modules`、`.DS_Store`、`Thumbs.db`。
  - `site/tools/editor.html` 已由 commit `01be953`（"feat: 案件编辑器与发布状态仪表盘"）提交入库（`git ls-files site/tools` → 1 个文件）。
  - 我实跑 `node tools/build.mjs`，输出 `dist/tools/editor.html`（26233 字节）**确实存在**。
  - 线上目前是 `404`（curl 实测 `https://tbj0623.github.io/zero-dossier-office/tools/editor.html` → 404），因为线上部署停在 `41fc9520`，**尚未包含该 commit**。
- **Why it matters**：这是一个**定时炸弹**而非当前泄漏。下一次 `push` 到 `main` 触发 `pages.yml` 部署，这个"案件编辑器"就会公开。它虽然不直接含答案（我 grep 过：不含 `红票`/`航海图`/`空白底片` 等），但它是作者工具链的一部分，且 `editor.html:456` 明确提示"把它填进 `expected_solution`，再按作者指南导出"——等于公开告诉玩家答案字段叫什么、在哪。更严重的是：任何人往 `site/` 里丢一个 `.html`/`.json`/`.md` 都会被静默发布，这个模式本身就是发布流程的结构性缺陷。
- **Suggested fix**：
  ```js
  cpSync(SITE, outDir, {
    recursive: true,
    filter: (src) => {
      const rel = relative(SITE, src).split(sep).join('/');
      if (rel.startsWith('tools/')) return false;        // 作者工具不进发布包
      if (rel.endsWith('.html') && rel !== 'index.html') return false;
      return !['node_modules', '.DS_Store', 'Thumbs.db'].includes(basename(src));
    },
  });
  ```
  并把 `site/tools/` 移出 `site/`（例如放 `tools/editor/`），从根上消除"站点目录 = 发布目录"的耦合。同时在 `pages.yml` 的"校验发布产物"步骤里加一条：`test ! -e dist/tools`。

### 2.2 [SEVERITY: medium] 许可覆盖存在**大片空白区**：229 个已跟踪文件既不属 MIT 也不属 CC

- **Evidence**：`LICENSE:25-28` 只覆盖"程序代码（`engine/`、`site/*.mjs`、`site/styles/`、`tools/`、`tests/` 中以代码形式存在的部分）"；`ASSETS_LICENSE.md:21-26` 只覆盖"`cases/**/*.json`、构建后的 `site/cases/*.json`、`docs/STORY_BIBLE.md`、`work/lore/**`"。

  我把 `git ls-files` 的 266 个文件按这两份文档分类，**229 个文件不落在任何一类里**，包括：
  - `README.md`、`docs/*.md`（除 `STORY_BIBLE.md`）、`marketing/ITCH_PAGE_DRAFT.md`、`ops/*.md`
  - `site/index.html`（HTML 不属于"`site/*.mjs`"也不属于"`site/styles/`"）
  - `site/assets/*.webp|.png|.svg`（`ASSETS_LICENSE.md:32-43` 用表格逐一点名了这些文件，但**该节标题是"视觉资产"，正文没有写"本表所列文件以 CC BY-NC-SA 4.0 授权"**——只写了"以上图片为本项目的原创概念插画"，这是署名声明，不是授权声明）
  - `review/*.json`、`screenshots/*.json`、`work/qa/**`、`work/blind/**`
- **Why it matters**：如果真有人想合规复用（尤其 `site/assets` 的图片——这是外部最可能想用的部分），会发现**没有一条明确条款授权它们**。CC BY-NC-SA 的核心价值就是"明确允许非商业复用"，而这个项目最想被复用的资产恰好落在授权空白里。对于一个自称"把程序与创作材料分开授权"的项目，这是自相矛盾的。
- **Suggested fix**：
  1. 在 `ASSETS_LICENSE.md` §3 开头加一句明确授权句："本表所列全部视觉资产均以 CC BY-NC-SA 4.0 授权"。§2 同理加"本表所列文件均以 CC BY-NC-SA 4.0 授权"。
  2. 加一节 §6 "其它文件"，明确 `docs/*.md`、`README.md`、`marketing/**`、`ops/**`、`review/**`、`screenshots/**` 的授权（建议文档也用 CC BY-NC-SA 4.0，`screenshots/` 因为含游戏画面同样 CC）。
  3. `site/index.html` 明确划归 MIT（它是站点代码的一部分）。

### 2.3 [SEVERITY: medium] `ASSETS_LICENSE.md:26` 引用了**不存在**的 `docs/STORY_BIBLE.md`

- **Evidence**：`ASSETS_LICENSE.md:26` 写"世界观与剧情文档 | `docs/STORY_BIBLE.md`、`work/lore/**`"。实际 `docs/` 目录只有 `AUTHOR_GUIDE.md`、`EDIT_MANIFEST.md`、`GAMEPLAY.md`、`PLAYTEST_PROTOCOL.md`、`PRIVACY.md`、`screenshots/`。**`STORY_BIBLE.md` 不存在**（`ls` 实测 + 文件系统检查）。
- **Why it matters**：一个许可文档引用了不存在的文件，读者会怀疑整份文档的可靠性。而且如果 `STORY_BIBLE.md` 曾经存在过又被删了，那 `work/lore/**` 是否完整覆盖了世界观内容就存疑。
- **Suggested fix**：删掉该引用，或补上文件。如果世界观内容实际散落在 `cases/*.json` 的 `setting`/`epilogue` 里，就在 §2 明确写"世界观设定内嵌于 `cases/**/*.json` 的 `setting`/`epilogue` 字段"。

### 2.4 [SEVERITY: medium] `work/qa/a11y/axe.min.js` 是 MPL-2.0 第三方代码，被提交入库，但仓库没有保留许可证全文的独立文件

- **Evidence**：`work/qa/a11y/axe.min.js` 头部：
  ```
  /*! axe v4.10.2
   * Copyright (c) 2015 - 2024 Deque Systems, Inc.
   * Your use of this Source Code Form is subject to the terms of the Mozilla Public
   * License, v. 2.0. If a copy of the MPL was not distributed with this
   * file, You can obtain one at http://mozilla.org/MPL/2.0/.
   * This entire copyright notice must appear in every copy of this file you
   * distribute or in any file that contains substantial portions of this source code.
   */
  ```
  仓库里 `find work/qa -iname "*license*" -o -iname "*notice*"` → **0 个结果**。
- **Why it matters**：MPL-2.0 第 3.1 条要求"以源码形式分发时必须告知如何获取源码"，头部声明本身满足"保留声明"这一点（`axe.min.js` 保留了完整头部 ✅），但仓库**没有说明这个文件的第三方来源与许可证**，而 `ASSETS_LICENSE.md` §3.3 又断言"无第三方图标库；所有图标为内联 SVG path"——这句话**只对运行时资产成立**，对仓库里的 QA 工具不成立，容易让读者误以为整个仓库零第三方代码。
  另外，`work/qa/a11y/axe.min.js` 是 **553KB 的压缩源码**，MPL-2.0 对"Source Code Form"的定义下，minified 版本通常被视为需要同时提供可读源码（或用 "Exhibit B" 方式声明）。这是个灰色地带，但既然它是**测试工具、不随站点发布**，最干净的做法是不入库。
- **Suggested fix**：
  1. 从仓库删除 `work/qa/a11y/axe.min.js`，改为在 `work/qa/a11y/run_axe.py` 里从 CDN/`npm i axe-core` 获取，并在 README 的"构建与测试"里注明。
  2. 若坚持入库，加 `work/qa/a11y/THIRD_PARTY_NOTICES.md` 写明 axe-core v4.10.2 / MPL-2.0 / 上游 URL。
  3. 修正 `ASSETS_LICENSE.md:59` 的措辞为"站点运行时无第三方图标库…（仓库的开发/QA 工具除外，见 THIRD_PARTY_NOTICES）"。

### 2.5 [SEVERITY: low] `tools/*.py` 的许可归属在 `ASSETS_LICENSE.md:16` 被漏掉

- **Evidence**：`ASSETS_LICENSE.md:16` 的 MIT 表格写"构建与工具 | `tools/*.mjs`"——**只写了 `.mjs`**。但 `tools/` 下有 5 个 `.py`：`build_itch.py`、`export_case.py`、`scramble_items.py`、`write_review.py`、`build_dashboard.py`。`LICENSE:25` 写的是"`tools/`"（无扩展名限制），所以**根 LICENSE 覆盖了，但 ASSETS_LICENSE 的表格漏了**。
- **Why it matters**：两份文档在同一个问题上给出不同范围，读者会以更窄的那份为准。
- **Suggested fix**：`ASSETS_LICENSE.md:16` 改为"构建与工具 | `tools/**`"。

### 2.6 [SEVERITY: low] `ASSETS_LICENSE.md:69` 的署名模板含未替换的占位符 `<owner>/<repo>`

- **Evidence**：`ASSETS_LICENSE.md:69`：`https://github.com/<owner>/<repo>`。实际仓库是 `tbj0623/zero-dossier-office`。
- **Why it matters**：CC BY-NC-SA 要求署名，给别人一个带 `<owner>/<repo>` 占位符的模板，等于让复用者去猜。
- **Suggested fix**：填成实际 URL。

### 2.7 内容原创性：**未发现抄袭，但"原创"声明强度超出我的验证能力**

- **Evidence**：
  - 我通读了 6 案全文（`cases/public/*.json`，共 20.8KB 文本）。全部为虚构设定：雾港（Fogport）、第零室、旧环线车站、灯塔检修架、邮局分拣线、钟楼/码头/邮局底片。**未出现任何真实机构名、真实人名、真实地名、真实事件、知名 IP 角色**。
  - 专有名词检索：`雾港` 在中文语境中不是著名真实城市（我做了 web 搜索，返回的是"雾"的字词典解释，无同名城市/机构）；`证物局` 不是中国现行机构名称（中国对应机构是"公安局""检察院""法院"）；`第零证物局` 搜索无同名作品。
  - 图片：我实际查看了 `harbor-archive-background.webp`（1672×941）与 `NA-006-episode-card.webp`（1200×675）。风格是**通用"暗色维多利亚书房 + 港口夜景"AI 概念图**，元素为：拱窗、钟楼、电车、灯塔、黄铜台灯、放大镜、火漆信封、怀表、行李箱、地图。这些是**类型化的蒸汽朋克/侦探视觉母题**，不指向任何特定商业游戏的具体角色或场景。没有 EXIF、没有 C2PA、没有水印（`PIL` 读取 `getexif()` 全部为空，`info` 只有 WebP 的 `loop`/`background`）。
- **Why it matters**：我必须诚实地说：**"是否 AI 生成"我无法证明，也没必要证明**（AI 生成本身不构成版权问题）。我能确认的是：**我没有发现任何可识别的复制来源**。风格不构成版权保护对象，这一点项目自己的 `ASSETS_LICENSE.md:48` 也写对了。
- **残留风险（medium）**：`ASSETS_LICENSE.md:46` 断言"以上图片为本项目的**原创**概念插画"。如果这些图确实由生成式模型产出，"原创"在中文字面意义上可能被理解为"人类原创绘制"。建议改为"本项目自主生成/委托制作，未使用任何第三方现成素材"——这个表述更准确，且不影响授权效力。
- **未验证**：图片的生成工具链、prompt、生成日期。仓库里没有记录。**这不算缺陷，但如果将来有人主张权利，缺少生成记录会是麻烦**。

### 2.8 [SEVERITY: low] `cases/author/` 未进入站点 —— **这一点做对了，且有多重防护**

- **Evidence**：
  - `tools/build.mjs:51-63` 只从 `cases/public/` 读取并拷贝，`cases/author/` 根本不在构建路径上。
  - `tools/build.mjs:94-111` 构建后扫描 `dist/` 全部 `.json`，出现 `expected_solution`/`editorial_note`/`logic_recap_check` 就 `process.exit(1)`。
  - `ci.yml:42-49` 与 `pages.yml:51-54` 各有一道 `grep -rl '"expected_solution"' dist/` 门禁。
  - 线上实测：`/cases/author/NA-001.json` → **404**；`/cases/public/NA-001.json` → **404**；`/engine/verify_cases.py` → **404**；`/review/NA-001-formal.json` → **404**；`/work/blind-src/NA-001.json` → **404**。
  - `cases/public/*.json` 实测**不含** `expected_solution` 字段（6/6 确认）。
- **结论**：这是本次审查中**防护最完整的一处**。GitHub 仓库本身是 public，所以 `cases/author/` 在仓库里可见——但这**不是泄漏**，因为 `README.md:37` 和 `AUTHOR_GUIDE.md:9-13` 都明确说了"含答案，仅内部校验"且"静态游戏不可能防作弊"。**这个透明度是对的**。

---

## 3. 营销与文档真实性

我逐行核对了 `README.md`（135 行）与 `marketing/ITCH_PAGE_DRAFT.md`（154 行）。**绝大部分声明是可验证且为真的**。以下是我找到的问题。

### 3.1 [SEVERITY: high → 现已修复] "交互目标 ≥ 44px（360/390/768 断点实测）" 曾**实测不成立**

> **状态更新（2026-10-30 复验）**：CSS 已新增"FIX PASS 03 — 触摸目标尺寸"补丁（`.site-nav a`、`.desk-crumbs a`、`.btn--sm` 加 `min-height: var(--tap)`）。我用全量选择器在 390/768px × 5 路由复测：**0 个不达标目标**（此前 390px 首页 12 个中 3 个不足）。**这条 high 已消除。** 但 `marketing/ITCH_PAGE_DRAFT.md:36/136` 与 `docs/PLAYTEST_PROTOCOL.md:27` 的措辞仍写"已实测"，建议改成"已实测（含导航与页脚链接）"以反映修复后的真实覆盖。

- **Evidence**：
  - 声明位置：`marketing/ITCH_PAGE_DRAFT.md:136`、`docs/PLAYTEST_PROTOCOL.md:27`、`README.md` 无直接声明但 `site/index.html:180` 写"交互目标按 44 px 设计"。
  - 项目自己的测试 `tests/browser/e2e.py:268-275` **只检查了 5 类选择器**：`#slots button, .actions button, .site-header button, .site-header a`。它**没有检查**主导航链接（`<a href="#/cabinet">` 等）、面包屑、页脚链接、`#clear-progress` 按钮。
  - 我用更完整的选择器（`a[href], button, input, select, textarea, [tabindex], [draggable]`）在线上实测（`work/redteam/targets_probe.py`，结果 `work/redteam/targets.json`）：

| 视口 | 页面 | 交互目标总数 | < 44px 的数量 | 实例 |
|---|---|---|---|---|
| 390px | 首页 | 12 | **3** | 导航"档案柜" 38×19、"玩法说明" 50×19、"关于与隐私" 63×19 |
| 390px | 调查桌 | 30 | **4** | 同上 3 个 + 面包屑"档案柜" 38×21 |
| 390px | 玩法说明 | 8 | **5** | 同上 + "封面" 25×21 + **"清除本机全部进度" 127×38** |
| 768px | 玩法说明 | 10 | **5** | 同上 |
| 1440px | 玩法说明 | 10 | **5** | 同上 |

- **Why it matters**：这不是"没测"，是"**测了但测漏了**"，然后把这个漏测的结论写进了 itch.io 的 Accessibility 栏。玩家在手机上点"档案柜"导航，实际可点高度只有 19px——远低于 Apple HIG 的 44pt 和 WCAG 2.5.8 的 24×24（更不用说 44×44）。
  尤其 `#clear-progress`（127×38）——这是一个**破坏性操作**按钮，尺寸不达标比普通链接更危险：误触的代价是清空全部进度。
- **Suggested fix**：
  1. 文案立刻降级：从 itch.io 的 ✅ 列表里**删掉**"交互目标 ≥ 44px"，或改为"主要游戏内控件（格位按钮、操作按钮）≥ 44px；导航与页脚文本链接为常规尺寸"。
  2. 修 CSS：`site/styles/app.css` 中给 `.site-nav a`、`.desk-crumbs a`、`.btn--sm` 加 `min-height: 44px; display: inline-flex; align-items: center;`（导航链接可用负 margin 保持视觉密度）。
  3. 修测试：`tests/browser/e2e.py:268` 的选择器改为全量 `a[href], button`，并把阈值改成"所有可见交互元素"。

### 3.2 [SEVERITY: medium] `README.md:19` "全部为**已部署站点**在真实 Chromium 中的实拍，非概念稿、非 mockup" —— 截图确实是实拍，但 `docs/screenshots/` 与 `screenshots/` 是两套不同文件

- **Evidence**：
  - `README.md:19` 声称 `docs/screenshots/*.png` 是从已部署站点实拍。
  - 实测尺寸：`docs/screenshots/01-home.png` = 1440×900（视口截图）；`screenshots/01-home-desktop.png` = 1440×2162（`full_page=True` 全页截图）。两者不是同一张图。
  - `docs/screenshots/05-mobile-home.png` = 780×1688；`screenshots/06-mobile-390.png` = 780×4578。前者是 390×844 的 2x 视口截图，后者是 2x 全页截图。**不是同一来源**（不同 `full_page` 设置）。
  - 这本身**不构成造假**——两套都是真实浏览器产物，只是截取范围不同。但 README 说"以下全部为…实拍"，而它引用的是 `docs/screenshots/`，这套图的生成脚本在仓库里**找不到**（`tests/browser/e2e.py` 只写 `screenshots/`，不写 `docs/screenshots/`）。
- **Why it matters**：无法从仓库复现 `docs/screenshots/` 的生成过程。一个声称"质量门禁"的项目，最核心的对外展示物料缺少可复现路径。
- **Suggested fix**：在 `tests/browser/e2e.py` 里加一步，把全页截图裁成视口尺寸或直接复制到 `docs/screenshots/`；或明确在 README 注明"`docs/screenshots/` 为手工截取的视口截图，生成脚本见 X"。

### 3.3 [SEVERITY: medium] `README.md:79` "最难的 NA-006 为 6! = 720 种排列" —— 数字对，但"最难"没有依据

- **Evidence**：`README.md:79`、`docs/AUTHOR_GUIDE.md:130`。720 这个数字我独立验证为真（`6! = 720`）。但"最难"是主观判断：`GAMEPLAY.md:79` 把 NA-003 和 NA-006 都标为"挑战"，而 `work/blind/BLIND_REPORT.md:533` 的约束力分析显示 NA-006 四条齐全才收敛到 1 解（E01 单独 144 解 → +E02 10 解 → +E03 3 解 → 四条 1 解），推理链长度与 NA-003（E01 单独 24 解 → +E02 12 → +E03 6 → 四条 1）**并不构成明显更难**。
- **Why it matters**：`AGENT_GUIDE.md:24` 明确写 `play_minutes` "**是设计估计，不是实测均值**"（这个诚实标注很好），但 `README.md` 和 `GAMEPLAY.md` 里"挑战"/"最难"的标签没有同样的限定。
- **Suggested fix**：`README.md:79` 改为"物品数最多的是 NA-006（6! = 720 种排列）；难度分级为设计者自评，未经真人试玩校准"。

### 3.4 [SEVERITY: medium] `README.md:103-110` "四项独立签核" —— 其中"独立盲审"的独立性有瑕疵，但**项目自己已经披露了**

- **Evidence**：
  - `README.md:103-110` 声称"每个案件必须同时通过**四项独立签核**"，第 3 项是"**盲审**：只给剥离答案的材料，由**独立解题者**自行推导"。
  - `work/blind/BLIND_REPORT.md:3` 写明："**Reviewer:** independent blind reviewer (teammate `blind-reviewer`)"。
  - `work/blind/BLIND_REPORT.md:11` 写明隔离方法："我只读取了 `work/blind-src/` 下的六个 JSON 文件。我没有打开…`cases/`、`engine/`、`tests/`…也没有运行项目自带的求解器。"
  - `review/NA-001-blind.json` 的 `status: "PASS"`，`evidence.final_verdict: "CLEAN"`。
- **Why it matters**：这里有一个真实的**认识论问题**：盲审者是一个 **AI teammate**，不是人类。`PLAYTEST_PROTOCOL.md:12-13` 自己写得很清楚："Agent 之间互相夸奖不是市场调查…**无法证明**人类玩家觉得这个谜题好玩"。也就是说，项目**已经知道** AI 盲审 ≠ 人类验证，并且在 G5 明确标了 `NOT_DONE`。
  所以严格说，**README 没撒谎**——它说的是"独立解题者"，而 `blind-reviewer` 确实在信息隔离上独立（只读 blind-src、不跑求解器）。但这个措辞在营销语境下容易被读成"人类独立测试者"。
  更值得注意的是：`work/blind/BLIND_REPORT.md` 的**首轮结论是 NA-006 BLOCKING**（第 236-265 行，明确指出"E01「相距整整三次」是两种读法各自唯一解且答案不同…这正是'不公平谜题'的典型形态"），修订后转为 CLEAN。**这个"发现问题→修订→复审"的过程是真实的，报告没有粉饰首轮失败**——这一点值得肯定。
- **Suggested fix**：把 `README.md:107` 改为"**盲审**：由信息隔离的独立复核者（AI agent，非人类玩家）只读剥离答案的材料自行推导，见 `work/blind/BLIND_REPORT.md`"。一个词的补充，消除"独立=人类"的误读。

### 3.5 [SEVERITY: low] `marketing/ITCH_PAGE_DRAFT.md:57` "Average session: A few minutes" 与 `README.md:79` 的"3–12 分钟"不自洽

- **Evidence**：`ITCH_PAGE_DRAFT.md:57` 填 `A few minutes`；同文件 `:96` 写"单案 3–12 分钟"；`docs/AUTHOR_GUIDE.md:24` 说 `play_minutes` 是"设计估计，不是实测均值"。
- **Why it matters**：itch.io 的 "Average session" 是给玩家的时间预期。填 "A few minutes" 而实际单案设计值到 12 分钟、六案全通可能 30+ 分钟，会让玩家预期错位。而且这个字段**没有实测支撑**。
- **Suggested fix**：改为"10–40 minutes (6 cases, designer estimate; not yet playtested)"，或直接留空。

### 3.6 [SEVERITY: low] `README.md:135` 承诺"本仓库的玩家反馈章节只记录真实发生的试玩" —— 但 README **没有玩家反馈章节**

- **Evidence**：`README.md` 全部二级标题为：真实运行截图 / 这是什么 / 玩法 / 六案与三幕 / 技术 / 质量门禁 / 隐私 / 许可 / 虚构声明 / 已知限制。**没有"玩家反馈"章节**。
- **Why it matters**：这句话承诺了一个不存在的章节。虽然无害（甚至显得过度谨慎），但它让"已知限制"这一节读起来像模板残留。
- **Suggested fix**：删除该条，或补一个 `## 玩家反馈` 章节写"截至 2026-10-30，尚未收集任何真实人类试玩数据（见 `docs/PLAYTEST_PROTOCOL.md`）"。**后者更好**——它把 G5 的 `NOT_DONE` 明确摆到 README 里，是最强的诚实信号。

### 3.7 [SEVERITY: low] 未发现任何虚构数据 —— 这是本次审查的**正面发现**

我专门找了以下红旗，**全部未命中**：
- ❌ 无"玩家数/下载量/好评率/评分"任何数字
- ❌ 无"players love it"/"一致好评"/"口碑爆棚"类措辞
- ❌ 无虚构评论、无虚构评测引用
- ❌ 无"平均通关时间"（`play_minutes` 明确标注为"设计估计"）
- ❌ 无"verified/tested/accessible/WCAG"越界声明 —— **恰恰相反**，`marketing/ITCH_PAGE_DRAFT.md:141-143` 主动列出"**未验证**，因此不声明：❌ 未做屏幕阅读器实机测试；❌ 未声明达到任何 WCAG 等级"
- ❌ 无"真实机构背书"暗示 —— `site/index.html:67`、`:205`、`README.md:129` 三处独立的虚构声明
- ❌ 无"假稀缺/限时/强制注册"—— 站点无注册入口，无倒计时，无弹窗

**这一块我给满分。** 在一个绝大多数独立游戏营销都会注水的领域，这个项目的自我约束是真实且一致的。

---

## 4. 安全 / 健壮性

### 4.1 [SEVERITY: critical → 现已修复] CI 的"无第三方远程资源"门禁曾**永远通过**（正则用了 GNU grep 不支持的 PCRE 前瞻）

> **状态更新（2026-10-30 复验）**：`ci.yml` 已改为调用 `tools/check_no_remote.py`。我植入 `<script src="https://cdn.evil.example/t.js">` 后该脚本正确 `exit 1`，干净构建 `exit 0`，且正文普通 URL 不误报。**这条 critical 已消除。** 以下保留原始发现过程，供团队理解为何要加"负向测试"。

- **Evidence**：
  - `ci.yml:51-59`：
    ```bash
    if grep -rEn 'https?://(?!127\.0\.0\.1|localhost)' dist/ --include='*.html' --include='*.css' --include='*.mjs' \
       | grep -vE 'github\.com|creativecommons\.org|w3\.org'; then
      echo "::error::发现外部资源引用"; exit 1
    fi
    echo "OK: 无第三方运行时资源"
    ```
  - 关键：`(?!...)` 是 **PCRE 负向前瞻**，GNU grep 的 `-E`（POSIX ERE）**不支持**。GNU grep 遇到它不会报错，而是把 `(?!` 当作普通字符序列匹配，结果**永远匹配不到任何行**。
  - 我构造了最小复现（`work/redteam/` 内的实验，命令见下）：
    ```bash
    $ printf 'https://cdn.evil.example/tracker.js\nhttp://127.0.0.1/ok\n' > t.txt
    $ grep -En 'https?://(?!127\.0\.0\.1|localhost)' t.txt ; echo "EXIT=$?"
    EXIT=1                     # ← 一条都没匹配到
    $ grep -En 'https?://' t.txt ; echo "EXIT=$?"
    1:https://cdn.evil.example/tracker.js
    2:http://127.0.0.1/ok
    EXIT=0                     # ← 对照组正常
    $ grep --version | head -1
    grep (GNU grep) 3.0
    ```
  - 我进一步**完整执行了 CI 那一步的逻辑**，对着一个故意植入 `<script src="https://cdn.evil.example/tracker.js">` 的假 `dist/`：
    ```bash
    $ set -e
    $ if grep -rEn 'https?://(?!127\.0\.0\.1|localhost)' distsim/ --include='*.html' ... \
        | grep -vE 'github\.com|creativecommons\.org|w3\.org'; then
        echo "::error::发现外部资源引用"; exit 1
      else echo "OK: 无第三方运行时资源"; fi
    OK: 无第三方运行时资源        # ← 门禁被绕过，且报告"通过"
    ```
- **Why it matters**：这是**最严重的一类问题**——不是"没做防护"，而是"**做了防护并且在 CI 绿灯里向所有人保证防护生效**"。`README.md:9` 挂的 CI badge 是绿的，`MASTER_STATE.md:13` 写"G4 代码与公开交付 ✅ PASS"，读者（包括未来的贡献者）会相信这条门禁。任何一次供应链投毒（比如有人在 `site/index.html` 里加一行 CDN 引用）都会**静默通过 CI 并直接部署到 Pages**。
  叠加 §4.2 的 `build.mjs` 全量拷贝问题，攻击面是真实的：不需要改代码，只要往 `site/` 放一个文件就能上线。
- **Suggested fix**（三选一，建议全做）：
  ```bash
  # 方案 A：用 grep -P（CI 的 ubuntu-latest 自带 GNU grep 支持 -P）
  grep -rPEn 'https?://(?!127\.0\.0\.1|localhost)' ...
  # 方案 B：不用前瞻，改成"先抓全部 URL，再白名单过滤"
  grep -rhoE 'https?://[^"'"'"' )]+' dist/ --include='*.html' --include='*.css' --include='*.mjs' \
    | grep -vE '^(https?://127\.0\.0\.1|http://localhost|https://github\.com|https://creativecommons\.org|http://www\.w3\.org)' \
    && { echo "::error::发现外部资源"; exit 1; } || echo "OK"
  # 方案 C：用 node 写一个真正的 URL 提取器（零依赖）
  ```
  **并且必须加一条负向测试**：在 CI 里先植入一个已知的坏 URL，断言门禁**会失败**（"测试你的测试"）。否则修好了也没人知道它是不是真的在工作。
- **附带问题**：同一段里的白名单 `grep -vE 'github\.com|creativecommons\.org|w3\.org'` 是**子串匹配**，所以 `https://evil.com/?x=github.com` 会被放行。应改为锚定 host 的正则。

### 4.2 [SEVERITY: high → 现已修复] 过期存档曾会让案件**永久卡在加载态**（旧物件名触发未捕获异常）

> **状态更新（2026-10-30 复验）**：`app.mjs` 现已校验 `saved.order.every(x => c.items.includes(x))`，不合法则 `progress.dropOrder(id)`。我注入含旧物件名的存档并硬刷新，`slots_rendered=true`、`stuck_loading=false`、`pageerrors=[]`。**这条 high 已消除。**

- **Evidence**：
  - `site/app.mjs:526-528`：
    ```js
    state.order = Array.isArray(saved?.order) && saved.order.length === c.items.length && new Set(saved.order).size === c.items.length
      ? [...saved.order]
      : [...c.items];
    ```
    这段校验只检查**长度**和**去重**，**不检查元素是否都属于 `c.items`**。
  - 如果存档里有旧物件名（例如作者改过 `items` 文案，或玩家从旧版本升级），`state.order` 会带着未知物件进入 `openCase()`。
  - 随后 `app.mjs:534`：`verifyOrder(state.order, c.constraints).every(...)` → `verifyOrder`（`solver.mjs:67-71`）对每条 rule 调 `checkRule` → `idx()`（`solver.mjs:22-26`）发现 `order.indexOf(item) < 0` → `throw new TypeError('未知物件：…')`。
  - 这个异常**没有被 `openCase()` 的 try/catch 捕获**（try 只包住 `loadCase(id)`，见 `app.mjs:504-514`；`state.order` 的赋值在 try 之外）。
  - 实测复现（`work/redteam/stale_save.py`，输出 `work/redteam/stale_save.json`）：写入 `zd:v1:order:NA-001` = `{"order":["红票（旧名）","蓝票（旧名）","黄票（旧名）","绿票（旧名）"],"hintIndex":1}`，然后硬刷新 `#/case/NA-001`：
    ```json
    {
      "case_root_text": "正在取阅档案…",
      "slots_present": false,
      "submit_button": false,
      "errors": ["未知物件：红票", "未知物件：红票"]
    }
    ```
    玩家看到的是**永久转圈的"正在取阅档案…"**，没有错误提示、没有返回按钮、无法操作。
  - 唯一恢复方式：去"玩法说明"页点"清除本机全部进度"（我实测 `recovers_after_clear: true`）。但**卡住的页面上没有任何指引告诉玩家这件事**。
- **Why it matters**：这是**真实的玩家级数据损坏**，不是理论风险。触发条件很现实：作者改一个 `items` 文案（这在 V2 修订中**已经发生过**——`work/blind/BLIND_REPORT.md:458-469` 记录了 6 个文件的 `items` 数组被重排）、玩家之前玩过旧版、然后访问新版 → 卡死。
  更糟的是它**不可自愈**：`progress.savedOrder()` 读到的坏数据不会被清除，每次刷新都卡在同一个地方。而 `app.mjs` 的注释（第 4 行）声称"绝不拼接 innerHTML"、`store` 层"全部包在 try/catch，隐私模式也能玩"——**防御心很强，但这个具体路径漏了**。
- **Suggested fix**：
  ```js
  // app.mjs:526 附近
  const savedOrder = Array.isArray(saved?.order) ? saved.order : null;
  const validSaved = savedOrder
    && savedOrder.length === c.items.length
    && new Set(savedOrder).size === savedOrder.length
    && savedOrder.every((x) => c.items.includes(x));   // ← 关键：元素必须都属于本案例
  if (savedOrder && !validSaved) progress.dropOrder(id);  // 静默丢弃坏存档
  state.order = validSaved ? [...savedOrder] : [...c.items];
  ```
  同时把 `openCase()` 里 `state.order` 的赋值也纳入 try/catch，把任何异常转成 `.empty-state` 的"档案损坏，请重置本案"提示 + 一个可点的"重置本案"按钮。

### 4.3 [SEVERITY: low] `app.mjs` 的 DOM 写入**确实安全** —— 我用恶意 case JSON 实测确认（当前 HEAD 复测仍安全）

- **Evidence**：
  - 全仓库 grep `innerHTML|outerHTML|insertAdjacentHTML|document.write|eval\(|new Function|srcdoc` → `site/` 下**只有 2 处命中，且都在注释里**（`app.mjs:4`、`app.mjs:72`，都是"不使用 innerHTML"的说明）。
  - `app.mjs:77-99` 的 `el()` 工具：`text` 字段走 `node.textContent = v`；`String(v)` 只用于 `setAttribute` 的通用分支；子节点用 `document.createTextNode`。**没有 `innerHTML` 路径**。
  - **主动攻击验证**（`work/redteam/probe5.py`，输出 `work/redteam/probe5.json`）：用 Playwright 拦截 `cases/NA-001.json`，把 `title`、`evidence[0].body`、`evidence[0].title`、`hints[0]` 全部替换成带事件处理器的 HTML（`<img src=x onerror="window.__X=1">`、`<svg onload=...>`、`<b onmouseover=...>`），然后加载页面：
    ```json
    {
      "page": {
        "title": "<img src=x onerror=\"window.__X=1\">REDTEAMMARK",
        "titleHTML": "&lt;img src=x onerror=\"window.__X=1\"&gt;REDTEAMMARK",
        "marks": 3,
        "imgX": 0,
        "x": 0, "y": 0, "z": 0
      }
    }
    ```
    → 恶意标记**全部作为纯文本呈现**（`titleHTML` 里是 `&lt;` 转义），**0 个注入的 `<img>` 元素、0 个事件处理器执行**。
- **结论**：**代码层 XSS 防护是有效的**。这是本项目安全上做得最好的一点。`app.mjs:4` 那句"所有 DOM 写入使用 textContent / createElement"是**真的**，不是吹的。

### 4.4 [SEVERITY: low] 超长字符串与畸形 JSON 的降级处理**得体**

- **Evidence**（`work/redteam/probe4.py`、`work/redteam/storage_probe.py`）：
  - 把 `evidence[0].body` 改成 50 万个"长"字 → 页面 **0.09 秒渲染完成**，不卡死（`long_string.state = "rendered"`）。
  - `cases/NA-001.json` 返回 **HTTP 500** → 显示"这份档案尚未完整送达 / 案件文件不可用（HTTP 500）/ 返回档案柜"。
  - `cases/NA-001.json` 返回**非法 JSON** → 显示"这份档案尚未完整送达 / Expected property name or '}' in JSON at position 1 / 返回档案柜"。
  - **但这暴露一个小问题**：错误页把原始 `JSON.parse` 异常文本直接显示给玩家（`app.mjs:510` 的 `err.message`），既无意义又泄漏内部细节。**建议**：对玩家显示固定文案，把 `err.message` 只写 `console.error`。

### 4.5 [SEVERITY: low] `assertCaseShape()` 的校验边界（含一处真实缺口）

- **Evidence**：`solver.mjs:167-191`。
  - ✅ 校验了：必需字段、`id` 正则、`items` 与 `slots` 等长、`items` 去重、`evidence` 非空、约束 ID 去重、`constraint_ids` 引用的约束存在、**并集等于全集**（防隐藏约束，这一条设计得很好）、每条 `constraint` 都能对 `items` 跑通。
  - ❌ **未校验**：`items`/`slots`/`evidence`/`hints` 是否为数组（`c.items.length` 对字符串也成立，`new Set("abc")` 会得到字符集）；`c.items` 元素是否为字符串；`c.hints` 长度是否 ≥ 1；`c.evidence[*].constraint_ids` 是否有重复引用。

  这一处我在 4.2 的路径上**间接验证了后果**（未知物件导致 `checkRule` 抛异常而无人捕获）。但注意：**病例数据由项目自己提供**，玩家无法注入（除非中间人攻击，那时 HTTPS 已破防）。所以这是**防御纵深**问题，不是当前可利用漏洞。
- **Suggested fix**：补 `Array.isArray` 检查 + 元素类型检查 + `hints` 长度检查。成本约 15 行。

### 4.6 [SEVERITY: low] `localStorage` 读取路径的健壮性 —— **大部分正确，一处已由 4.2 覆盖**

- **Evidence**（`work/redteam/storage_probe.py`，硬刷新后测试）：
  - `zd:v1:progress` = 非法 JSON / `"hello"` / `[1,2,3]` / `{"NA-001":{"solved":"yes"}}` → **全部正常渲染，0 报错**（`store.get` 的 `try/catch` 兜住了）。
  - `zd:v1:order:NA-001` = `null` / `42` / 长度错误 / 长度对但有重复 → **全部正常回退到初始排列**。
  - `hintIndex` = `100000` → 正常，显示全部 3 条提示（`c.hints.slice(0, 100000)` 安全）。
  - `hintIndex` = `-5` / `"3"` → 正常（`Number.isInteger` 过滤）。
  - **唯一失败**：`order` 长度对、无重复、但含未知物件 → **崩溃**（= §4.2）。
- **结论**：`store` 层的防御是**系统性正确**的，只有"元素归属"这一个校验缺口。修掉 4.2 后这一整块就是干净的。

### 4.7 [SEVERITY: medium] GitHub Actions 权限与供应链

- **Evidence**：
  - `ci.yml:9-10`：`permissions: contents: read` ✅ 最小权限。
  - `pages.yml:8-11`：`contents: read` + `pages: write` + `id-token: write`。`id-token: write` 是 `actions/deploy-pages` 的 OIDC 必需权限，**合理**。
  - **无 `pull_request_target`** ✅（这是最容易出事的触发器，项目没用）。
  - `concurrency: group: pages, cancel-in-progress: false` ✅ 正确（避免半途取消部署）。
  - ❌ **所有 action 都用浮动的 major tag**：`actions/checkout@v4`、`actions/setup-python@v5`、`actions/setup-node@v4`、`actions/upload-artifact@v4`、`actions/configure-pages@v5`、`actions/upload-pages-artifact@v3`、`actions/deploy-pages@v4`。
- **Why it matters**：`@v4` 这类 tag 是**可被上游 force-push 移动**的（GitHub 官方 action 相对可信，但 2025 年 `tj-actions/changed-files` 事件证明这不是理论风险）。本项目是**部署到 GitHub Pages 的公开站点**，被投毒的 action 可以直接改写 `dist/` 内容并上线。
- **Suggested fix**：用 commit SHA 固定（`actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955 # v4.3.0`），或用 Dependabot 的 `github-actions` ecosystem 自动升级 SHA。
- **补充**：`ci.yml:54` 那条坏正则（§4.1）就在这个 workflow 里，说明这个 CI 的"绿"本身不值得信任。

### 4.8 [SEVERITY: low] 无密钥 / 无 PII 泄漏（但有一个意外的邮箱泄漏，在**提交元数据**里）

- **Evidence**：
  - 全仓库 grep `gho_|ghp_|github_pat_|sk-[A-Za-z0-9]{16}|AKIA[0-9A-Z]{16}|password\s*[:=]|api[_-]?key\s*[:=]|secret\s*[:=]|C:\\Users\\|email regex` → **0 个命中**（`work/qa/**` 的二进制截图除外）。✅
  - 但：**GitHub 远端有 3 个 commit 的作者邮箱是 `13014880645@163.com`**（`git ls-remote` + GitHub API 实测：`41fc9520`、`f2637d90`、`ba9cc749`）。本地 `git config user.email` 现在是 `tbj0623@users.noreply.github.com`（已修正），但**历史 commit 改不了**。
  - 这个邮箱前缀是一串 11 位数字，**形似中国大陆手机号**。
- **Why it matters**：仓库是 **public** 的（GitHub API 实测 `"private": false`），任何访问者都能看到这 3 个 commit 的作者邮箱。如果这确实是作者的真实手机号，属于**主动公开的个人信息**。这与 `PRIVACY.md` 的"不收集任何个人数据"不冲突（那是说玩家数据），但与项目整体的隐私敏感度不匹配。
- **Suggested fix**：
  1. 立即在 GitHub 账号设置里开启 "Keep my email addresses private" 并勾选 "Block command line pushes that expose my email"。
  2. 对已经公开的 3 个 commit，用 `git filter-repo --mailmap` 或 BFG 重写历史并 force-push（**注意**：会改写 SHA，需要同步更新 `MASTER_STATE.md` 里的回滚指令）。
  3. 如果不能重写历史（已有人 fork/clone），至少不要再在未来的 commit 里使用该邮箱。
- **注意**：这条**不是**项目的代码缺陷，是**发布卫生**问题。我把它列入是因为它符合"发布后会让人尴尬"的定义。

### 4.9 [SEVERITY: low] `MASTER_STATE.md` 里有**两个不存在的 commit SHA**

- **Evidence**：`MASTER_STATE.md:21` 写"仓库最新提交 `ba9cc749`…本地 `afd1ccd` 内容与之逐字节一致"。
  - 本地 `git cat-file -t ba9cc749` → `fatal: Not a valid object name`（本地没有这个 SHA）。
  - 远端 API `GET /commits/ba9cc749` → **200**（远端有这个 commit）✅。
  - 但 `MASTER_STATE.md:66-67` 的回滚指令写 `git revert ba9cc749` / `git reset --hard d77f40b`。`d77f40b` 本地存在 ✅，`ba9cc749` **本地不存在**——所以"本地回滚"这条指令在全新 clone 的仓库里会失败（除非先 `git fetch`，但文档没写）。
  - 当前线上部署的 commit 是 `41fc9520`（`app.mjs` 的 `BUILD` 常量实测），而 `MASTER_STATE.md:22` 说"线上站点…HTTP 200，实测可玩六案"——**没写具体是哪个 SHA**，读者无法核对线上版本。
- **Why it matters**：一个专门用来记录"真实发布状态"的文档，给出的回滚指令没有前置条件说明，且没有记录线上确切的 commit。这与该文档"不隐瞒"的自我定位不符。
- **Suggested fix**：回滚章节写明"需先 `git fetch origin`"，并记录线上 `BUILD` 值（`41fc9520…`）。

---

## 5. 伦理 / 内容

### 5.1 结论：**内容伦理是干净的**，且防护是主动的

我通读六案全文后的判断：

| 检查项 | 结果 | 证据 |
|---|---|---|
| 真实死亡 | ❌ 无 | 六案无任何死亡、尸体、伤害描写。最"重"的是 `NA-004` 的"暴风夜后"和"灯塔整夜熄灭"，但**无人员伤亡**，且原因被揭示为"把旧电路图当新图"的记录错误。 |
| 真实灾难 | ❌ 无 | 无地震/海难/火灾/疫情等真实灾难映射。`NA-004` 的"暴风夜"是虚构天气背景，不是具体历史事件。 |
| 真实机构 | ❌ 无 | "第零证物局""雾港邮政""旧环线车站""灯塔检修站"全部虚构。**没有**使用"公安局""检察院""海关""海事局"等真实机构名。 |
| 可识别的真实人物 | ❌ 无 | 六案**没有出现任何具名人物**。全部用职务指代："车站管理员""灯塔站书记员""检票员""前任保管员""维修工""投递员""局长""档案员""摄影师"。这是**刻意的匿名化设计**，且做得彻底。 |
| 真实历史文书伪造 | ❌ 无 | `README.md:129`、`site/index.html:205`、`ASSETS_LICENSE.md:47` 三处声明"不以伪造的历史文书冒充真实档案"。文本层面对应的是虚构的"手记""便笺""维修卡""投递回执"，没有伪造印章、公文格式、真实年代。 |
| 血腥/暴力/性内容 | ❌ 无 | 全文无。`PRIVACY.md:47` 的声明属实。 |
| 失败信息羞辱玩家 | ❌ 无 | 见下。 |

### 5.2 "第零证物局"这个虚构机构名 —— **被误认为真实执法机构的风险很低，但有一个可改进点**

- **Evidence**：
  - 中文语境里"证物局"**不是**任何现存机构名（中国对应的是公安局/检察院/法院的"证据"科室，没有独立"证物局"）。我的 web 搜索也没有找到同名真实机构。
  - 更关键的是**视觉与文案的双重消歧**：
    - `site/index.html:67`（首页 hero，首屏可见）："本作人物、地点与事件均为虚构；不对真实人物或事件作任何调查判断。"
    - `site/index.html:205`（关于页）："全部人物、地点、机构与事件均为虚构的架空世界「雾港」…"
    - `README.md:127-129`（虚构声明独立成节）
    - `marketing/ITCH_PAGE_DRAFT.md:107-109`（itch 页面正文里的"声明"小节）
  - 这四处声明**彼此独立、措辞一致**，不是一句免责糊弄。
- **残留风险（low）**：`site/index.html:13-14` 的 OG 标题是"**第零证物局 · 第零号档案正在解封**"，`og:description` 是"一张票据可以说真话，六张记录也可能让人误会。**你能还原雾港的真相吗？**"——这段是**社交分享卡片文案**，会脱离站点上下文单独传播。它没有虚构声明，且"真相""档案解封"的措辞在没有上下文时更像真事。
- **Suggested fix**：`og:description` 末尾加一句"（虚构作品）"，例如："…你能还原雾港的真相吗？（本作为虚构互动小说）"。成本一个括号。

### 5.3 [SEVERITY: low] 失败反馈的语气是**克制且不羞辱**的 —— 这一点做得比多数商业游戏好

- **Evidence**：
  - `app.mjs:875`：`档案仍有不一致：${bad.length} 条关系未满足。`
  - `app.mjs:876`：`你的排列已保留，可以继续核对先后、距离或「夹在中间」的描述。`
  - `app.mjs:872`：`${e.id}「${e.title}」中描述的关系与你的排列不一致。`（**只说哪张证据冲突，不说正确答案**）
  - `app.mjs:855`：`提示只是帮你推进，不会自动完成排列。`
  - 全仓库 grep 羞辱性用语（"你居然""这很明显""太简单""怎么连这都不会""失败"）→ **0 命中**。
  - `docs/AUTHOR_GUIDE.md:97` 明确把"你居然没发现""这很明显"列为**禁止用语**。
  - `site/index.html:169`："提示不会自动替你排列，也不会扣分或**羞辱你**。"
- **结论**：**没有发现任何羞辱玩家的文案**。这是主动设计的结果，不是巧合。

### 5.4 [SEVERITY: low] 未发现任何 dark pattern

我专门检查了以下模式，**全部未命中**：

| Dark pattern | 结果 | 证据 |
|---|---|---|
| 假倒计时 / 限时 | ❌ 无 | 无任何 `setInterval` 倒计时 UI，无"仅剩 X 分钟" |
| 假稀缺 | ❌ 无 | 无"限量""最后 X 份" |
| 强制注册 | ❌ 无 | `README.md:43` "免注册"；站点**没有登录/注册入口**；`PRIVACY.md:13` "没有注册、登录或用户档案" |
| 退出挽留弹窗 | ❌ 无 | 唯一的 `<dialog>`（`index.html:258-265`）是"确认重置"和"清除进度"，都是**破坏性操作的确认**，方向正确 |
| 诱导分享 | ❌ 无 | `PRIVACY.md:41-43` 明确"本版本不调用系统分享 API，也不生成带玩家答案的分享链接"——我 grep `navigator.share` → 0 命中 ✅ |
| 暗色模式强制 / 无障碍反模式 | ❌ 无 | 支持 `prefers-reduced-motion`（`base.css:11-18`、`app.css:675`）、`forced-colors`（`tokens.css:72`）、skip-link（`index.html:26`）、焦点可见（`manual-raw.json` 实测 `outlineWidth: 3px, outlineStyle: solid`） |

### 5.5 [SEVERITY: medium] `NA-006` 的"终章"文案有一处**逻辑与叙事的越界**

- **Evidence**：`app.mjs:995-1001` 在 NA-006 结案后追加一段"终章"，其中：
  > "局长把半圈「0」章盖在每一份分类不确定的档案上，从来不是为了隐藏真相，而是为了提醒下一位读档者：先问「它是什么」，再问「它发生了什么」。"

  但 `docs/AUTHOR_GUIDE.md:102` 明确规定："`epilogue` 可以讲故事…但 UI 上必须标为「结案后补充记录」，且**不得声称是刚才排序的结论**。"
  这段"终章"**没有** "结案后补充记录" 的标签（它是独立的 `finale` 块，`recap-block__label` 只写"终章 · 第零号"），且它陈述了一个**关于局长动机的事实性断言**（"从来不是为了隐藏真相"），这个断言**无法从任何证据推出**。
- **Why it matters**：项目的核心卖点就是"逻辑与叙事分家"（`README.md:59`、`GAMEPLAY.md:85-90`、`AUTHOR_GUIDE.md:99-104`）。这段终章直接违反了自己的规则，而且是**整个游戏的最后一段话**——玩家印象最深的位置。
- **Suggested fix**：把 `finale` 的 `recap-block__label` 改为"终章 · 结案后补充记录（叙事，不构成推理结论）"，或把"从来不是为了隐藏真相"改为"档案员们相信…"（明确是角色信念而非事实）。

---

## 6. 无障碍（并入攻击面 3，但单独成节，因为它是本项目自称最弱的一环）

**先说结论：项目在无障碍上的自我约束是诚实的，但"实测"覆盖不足，导致三条对外声明超出证据。**

### 6.1 [SEVERITY: medium → 现已修复] 项目自己的 axe 扫描结果曾为 **6 类违规 + 大量 contrast 待查**

> **状态更新（2026-10-30 复验）**：当前 HEAD 构建上 axe-core 全量复跑（5 路由 × wcag2a/2aa/21a/21aa/best-practice）→ **5/5 路由 0 violation**。`#hints` 已加 `role="region"`，heading 层级已修。**这条已消除。** 以下保留原始发现与推理，因为它解释了"为什么当时需要修"。

- **Evidence**（`work/qa/a11y/axe-summary.json`，这是**项目自己跑的**）：
  | 页面 | 确定违规 | incomplete（需人工确认） |
  |---|---|---|
  | home | `heading-order` (moderate) ×1 | `color-contrast` **67 个节点** |
  | cabinet | `heading-order` ×1 | `color-contrast` 78 |
  | desk-collapsed | **`aria-prohibited-attr` (serious) ×1** + `heading-order` ×1 | `color-contrast` 59 |
  | desk-expanded | `aria-prohibited-attr` (serious) + `heading-order` | `color-contrast` 68 |
  | desk-selected | `aria-prohibited-attr` (serious) + `heading-order` | `color-contrast` 62 |
  | desk-error | `aria-prohibited-attr` (serious) + `heading-order` | `color-contrast` 66 |
  | verdict | `page-has-heading-one` (moderate) + **`aria-valid-attr-value` (critical, incomplete)** | `color-contrast` 60 |
  | manual / about | `heading-order` ×1 each | `color-contrast` 58 / 42 |

  我独立复跑 axe（`work/redteam/probe2.py`，`axe_total = 6`），**结果与项目自己的一致**：`aria-prohibited-attr` on `#hints`（`app.mjs:642` 给 `<div>` 加了 `aria-label`，而 `<div>` 是 generic role，`aria-label` 被 ARIA 规范禁止）、`heading-order`、`page-has-heading-one`（verdict 页从 `<h2>` 开始，没有 `<h1>`）。

  **但 `marketing/ITCH_PAGE_DRAFT.md:131-143` 的"可访问性声明"里完全没有提到这些。** 它列了 6 条 ✅，然后说"未声明达到任何 WCAG 等级"——这句话是诚实的，但**不足以抵消**"键盘可完成全部操作 / 所有拖放都有等价按钮 / 交互目标 ≥44px / 尊重 reduced-motion / 解谜信息全为文本 / 无自动播放音频"这 6 个 ✅ 给人的"这个游戏做过无障碍审计"的印象。
- **Why it matters**：`aria-prohibited-attr` 是 **serious** 级违规，且出现在**每一个案件页**上。`#hints` 那个 `aria-label` 是给"已揭开的提示"容器加的，本意是好的（想让屏幕阅读器知道这个区域是什么），但因为 `<div>` 没有 role，这个 label 会被**多数屏幕阅读器忽略**——等于做了无效功。
- **Suggested fix**：
  1. `app.mjs:642` 改为 `el('section', { class: 'hints', id: 'hints', aria: { label: '已揭开的提示' } })`（`<section>` 有 `region` role，`aria-label` 合法且会被朗读），或加 `role="region"`。
  2. 修 heading 层级：首页 `<h1>` 后直接 `<h3>`（`index.html:78/83/88`）应改为 `<h2>`；页脚 `<h4>` 应改为 `<h2>`（或加可视隐藏的层级桥接）。
  3. verdict 页加一个可视隐藏的 `<h1>`（或把"档案归位"从 `<h2>` 提到 `<h1>`）。
  4. 在 itch 页面的 Accessibility 栏**如实补充**："axe-core 扫描发现 6 项结构性问题（heading 层级、1 处 ARIA 属性误用），已记录待修；未做屏幕阅读器实机测试。"

### 6.2 [SEVERITY: medium → 现已修复] "标题层级"曾影响屏幕阅读器的**导航效率**

> **状态更新**：首页 `h3`→`h2`、页脚 `h4`→`h2`、verdict 补 `h1`。axe 复跑 0 violation。

- **Evidence**：`index.html:57`（h1）→ `:78`（h3）跳级；`:226/236/244` 页脚用 `<h4>` 但前面没有 `<h3>`；`app.mjs:924` verdict 用 `<h2 id="verdict-title">` 但没有 `<h1>`。
- **Why it matters**：屏幕阅读器用户靠 heading 快速跳转（`H` 键）。跳级会让"文档大纲"错乱，用户按 `H` 跳转时听到的顺序不符合内容结构。这**不阻断**操作，但会让长页面（玩法说明页有 6 个 `<h2>`）的导航体验显著变差。
- **Suggested fix**：见 6.1 第 2-3 点。

### 6.3 [SEVERITY: low] `color-contrast` 的 59-78 个 "incomplete" 我**独立核算后认为是误报为主**，但项目没有做这个核算

- **Evidence**：
  - axe 报 `incomplete`（不是 violation）通常是因为**无法从计算样式确定背景**——这个项目大量使用 CSS `linear-gradient` 做背景（如 `.ev-card` 用 `linear-gradient(165deg, #f0e2c4, #e2d0ab 70%, #d8c49b)`），axe 无法自动求值。
  - 我手工核算了 `.ev-card` 的对比度（`work/redteam/contrast.json` + 手算）：
    - 正文 `#20180d` on `#f0e2c4` → **13.67:1** ✅
    - 正文 `#20180d` on `#e2d0ab` → **11.56:1** ✅
    - 正文 `#20180d` on `#d8c49b` → **10.26:1** ✅（最差情况也远超 4.5:1）
    - 次要文字 `#5a4520` on `#d8c49b` → **5.33:1** ✅
    - `#6d5528` on `#e2d0ab` → **4.65:1** ✅（勉强过线）
  - 深色区域：`#9eb7b4` on `#142f3b` → **6.59:1** ✅；`#dfb978` on `#0d2532` → **8.55:1** ✅；正文 `#f2ece0` on `#081821` → **15.35:1** ✅
  - **结论：主色对比度实际上很好。** axe 的 59-78 个 incomplete 主要来自渐变背景无法自动求值，**不是真实缺陷**。
- **Why it matters**：这是我**主动为项目澄清**的一点。一个红队报告如果只列问题，会让人误以为这个项目的可读性很差；实际上它的配色对比度是我这次审查里见过的**较好水平**。
- **Suggested fix**：把这个手算结果写进 `work/qa/a11y/` 的文档，把 59-78 个 incomplete 降级为"已人工复核，渐变背景导致工具无法求值，实测对比度 5.33–15.35:1，达标"。**这是唯一一处项目"少做了验证"但结论实际上没问题的地方。**

### 6.4 我实测确认的无障碍项（正面）

| 项目 | 实测 | 证据 |
|---|---|---|
| 键盘可完成全流程 | ✅ 我用**纯键盘**（`Tab` + `Enter`，零鼠标）完成 NA-001 通关到结案页 | `work/redteam/probe2.py` → `keyboard_only_playthrough: {"result": "completed"}` |
| 纯触摸可完成全流程 | ✅ 390px 视口、`has_touch=True`，用 `tap()` 完成 NA-001 通关（3 次 tap） | `work/redteam/probe4.py` → `touch_playthrough_390: {"verdict": "completed"}` |
| 点击交换（主路径） | ✅ `tap` 两个 slot 的 pick 按钮可交换 | `tap_to_swap: {"swapped": true}` |
| 320px 无横向溢出（WCAG 1.4.10 Reflow） | ✅ 5 个路由 × 2 个视口（320/360px）**全部 overflow = 0** | `work/redteam/probe4.py` → `reflow` 全部 `"ok": true` |
| 焦点可见 | ✅ `outlineWidth: 3px, outlineStyle: solid, outlineColor: rgb(223,185,120)` | `work/qa/a11y/manual-raw.json` + 我的 `probe2` |
| 尊重 reduced-motion | ✅ `base.css:11-18` 全局 `animation-duration: 0.001ms`；实测 `transitionDuration = 1e-06s` | `browser-report.json` 第 166-169 行 |
| 图片失败降级 | ✅ 全部 `.webp/.png` abort 后，证据区仍有 225 字符文本 | `browser-report.json` 第 170-174 行 |
| 无自动播放音频 | ✅ 仓库 0 个音频文件，无 `<audio>` | `ASSETS_LICENSE.md:58` 声明 + 我 grep 确认 |

**这几项是真的，而且是硬核实测。** 项目的无障碍**基础**是扎实的，问题出在**边缘控件尺寸**与**ARIA/heading 细节**。

---

## 7. Claims audit table

| # | 声明 | 位置 | 属实？ | 证据 | 修正建议 |
|---|---|---|---|---|---|
| 1 | 无账户 | README:43, PRIVACY:13, index:200 | ✅ **真** | 全站无登录 UI；0 个 `Authorization` 头 | — |
| 2 | 无后端 | README:48, PRIVACY:14 | ✅ **真** | 20 个请求全是静态 GET；无 `POST`/`PUT` | — |
| 3 | 无分析脚本 | README:114, PRIVACY:15 | ✅ **真** | grep `gtag/analytics/pixel/sendBeacon` → 0 命中 | — |
| 4 | 无第三方 CDN | README:114, PRIVACY:16, index:202 | ✅ **真** | `distinct_hosts = ['tbj0623.github.io']`；`third_party_requests = []` | — |
| 5 | 无远程字体 | README:125, ASSETS:53 | ✅ **真** | CSS 0 个 `@font-face`/`@import`/外部 `url()` | — |
| 6 | 不上传答案 | README:48, PRIVACY:7, index:200 | ✅ **真** | **提交错误答案前后网络请求数差 = 0** | — |
| 7 | 进度只在 localStorage，前缀 `zd:v1:` | README:115, PRIVACY:20 | ✅ **真** | 实测键名 `zd:v1:progress`、`zd:v1:order:NA-00X`，与文档表格逐字一致；`cookies=[]`、`sessionStorage={}`、`idb=[]`、`caches=[]`、`sw=0` | — |
| 8 | localStorage 禁用时仍可完整游玩、静默降级 | PRIVACY:35 | ✅ **真** | 桩掉 `localStorage` 使其抛 `SecurityError` → `renders=true`、`completes=true`、0 报错 | — |
| 9 | 一键清除进度（玩法说明页） | GAMEPLAY:67, index:174 | ✅ **真** | 实测按钮可达，清除后 `localStorage` 为空，案件恢复正常 | — |
| 10 | "手机与键盘均可完整游玩" | README:49, index:7 | ✅ **真**（但见 #11） | 纯键盘通关 ✅；390px 纯触摸通关 ✅；320px 无溢出 ✅ | — |
| 11 | "交互目标 ≥ 44px（360/390/768 实测）" | ITCH:136, PLAYTEST:27, index:180 | ❌ **假** | 390px 首页 12 个目标中 **3 个 <44px**（导航 38×19 等）；玩法说明页 8 个中 **5 个 <44px**，含破坏性按钮"清除进度"127×38 | 删掉此条或改为"主要游戏内控件 ≥44px"；修 CSS `min-height:44px` |
| 12 | 唯一解 | README:105, AUTHOR:10 | ✅ **真** | 我独立 Python 复算 6/6 `sols=1`；`engine/verify_cases.py` 也 PASS | — |
| 13 | 每条约束都必要（无冗余线索） | README:105, AUTHOR:57 | ✅ **真** | 独立复算：删任一条后解数变为 2–10 个，6/6 全部 `all>1: True` | — |
| 14 | Python⇄JS 一致 | MASTER_STATE:48 | ✅ **真** | `engine/verify_cases.py` 与我的独立实现答案完全一致（6/6） | — |
| 15 | 六案浏览器通关 | MASTER_STATE:49, browser-report | ✅ **真** | `browser-report.json`：36 项全 PASS、`solved_cases` 6/6；我复跑关键路径也通过 | — |
| 16 | 无第三方网络请求（e2e 检查） | browser-report:176-179 | ✅ **真**（但测试有盲区） | 报告 `0 个: []`；我独立抓包也确认 0 个 | 测试的 `external` 列表只在特定上下文收集，建议用 CDP 级拦截 |
| 17 | "四项独立签核" | README:103 | ⚠️ **措辞需限定** | 24/24 `review/*.json` 全 PASS ✅；但"独立解题者"是 **AI teammate**（`BLIND_REPORT.md:3`），非人类 | 改为"独立复核者（AI agent，信息隔离）" |
| 18 | "CI 绿" | README:9 badge, MASTER_STATE:24 | ⚠️ **技术上真，实质可疑** | GitHub API 实测 8 次 run 全 `success` ✅；但 `ci.yml:54` 的门禁正则**永远不匹配**（§4.1） | **先修 §4.1**，再谈 CI 绿的含义 |
| 19 | 部署包不含作者答案 | README:37, MASTER_STATE | ✅ **真** | `build.mjs` 双重扫描 + CI 双重 grep；线上 `cases/author/**` → **404**；`cases/public/*.json` 无 `expected_solution`（6/6） | — |
| 20 | "文字全部可复制、不依赖图片" | ASSETS:47, ITCH:138 | ✅ **真** | 断图测试后证据区仍有 225 字符文本；`ALT` 全部 `alt=""`（装饰性），信息全在 DOM 文本 | — |
| 21 | "尊重 prefers-reduced-motion" | ITCH:137, index:182 | ✅ **真** | `base.css:11-18` 全局降级；实测 `1e-06s` | — |
| 22 | "未做屏幕阅读器实机测试 / 未声明 WCAG" | ITCH:141-143 | ✅ **真**（且是**加分项**） | 文档确实这么写；`MASTER_STATE.md:56` 同样声明 | — |
| 23 | "无自动播放音频" | ITCH:139, index:183 | ✅ **真** | 0 个音频文件，0 个 `<audio>` | — |
| 24 | "六案三幕、单案 3–12 分钟" | ITCH:96, README:79 | ⚠️ **设计估计，非实测** | `AUTHOR_GUIDE.md:24` 自己标注"设计估计，不是实测均值"；`PLAYTEST_PROTOCOL.md:6` 明确"尚未收集任何真实人类试玩数据" | 在 itch 页面同步标注"designer estimate, not playtested" |
| 25 | "Average session: A few minutes" | ITCH:57 | ⚠️ **无依据** | 六案设计值合计 29–53 分钟；"A few minutes" 只符合单案下限 | 改为 "10–40 min (6 cases, estimate)" 或留空 |
| 26 | "内容适合一般公众" | PRIVACY:47 | ✅ **真**（内容上） | 六案全文无血腥/暴力/性内容；无具名真人 | 但应注明"未经过任何分级机构评定" |
| 27 | "全部人物、地点、机构、事件均为虚构" | README:129, index:205, ITCH:109 | ✅ **真** | 六案 0 个真实机构名、0 个具名人物、0 个真实地名；`雾港` 非真实城市 | — |
| 28 | 图片为"本项目原创概念插画" | ASSETS:46 | ⚠️ **无法验证** | 我实看了 2 张主图：通用暗色书房/港口母题，**未发现可识别复制来源**；EXIF 全空（无生成记录） | 改为"本项目自主生成/委托制作，未使用第三方现成素材" |
| 29 | 无第三方图标库 | ASSETS:59 | ⚠️ **对运行时为真，对仓库为假** | 运行时确实全是内联 SVG ✅；但仓库 `work/qa/a11y/axe.min.js` 是 Deque 的 MPL-2.0 代码 | 加 "（开发/QA 工具除外，见 THIRD_PARTY_NOTICES）" |
| 30 | 代码 MIT / 素材 CC BY-NC-SA 分开授权 | README:122-123 | ❌ **有空白区** | **229 个已跟踪文件不属任何一类**；`ASSETS_LICENSE` §3 未写明确授权句 | 见 §2.2 |
| 31 | "不需要在线大模型" | README:47 | ✅ **真** | 求解器 `solver.mjs` 是纯穷举（191 行，0 依赖）；无任何 API 调用 | — |
| 32 | "零依赖、零构建必需" | README:76 | ✅ **真** | `package.json` 无 dependencies（我检查过 imports）；`build.mjs` 只用 `node:fs/path/url/child_process` 内置模块 | — |
| 33 | 3–8 件物品穷举，NA-006 为 720 排列 | README:79 | ✅ **真**（数字）；"最难"⚠️ | 720 数学正确；实测 `countSolutions` NA-006 = 3.7ms，`necessity` = 10.1ms，性能无虞 | "最难"改为"物品数最多" |
| 34 | 静态站点无法防作弊 | README:133, AUTHOR:13 | ✅ **真**（且诚实） | 客户端可读 `cases/*.json` 的 `constraints`，可枚举出解——这是设计使然，已明说 | — |
| 35 | itch 包 21 个文件 / 0.57MB / index 在根 | ITCH:13-17 | ✅ **真** | 实测 zip：**21 个文件**、598668 字节（0.57MB）、`index.html` 在根、无路径穿越、全部相对路径、无 404 引用 | — |

**统计：35 条声明中，27 条完全为真 ✅，6 条需要措辞限定 ⚠️（#17 #18 #24 #25 #28 #33），2 条为假/有缺陷 ❌（#11 交互目标 44px、#30 许可覆盖空白）。** 这个比例在独立游戏里属于**优秀**。

关于 ⚠️ 的判读：这 6 条并非同一性质。#17（独立解题者是 AI）、#18（CI 绿但门禁失效）、#25（Average session 无依据）、#33（"最难"无依据）是**措辞超出了证据**；#24（时长是设计估计）是**声明本身已诚实，只是对面渠道没同步**；#28（图片原创性）是**我无法验证**——我没有找到反证，但也不能确认，所以标 ⚠️ 而非 ❌。

---

## 8. What I verified as ACTUALLY correct

这一节是给团队的"这些不用再担心了"清单。**每一条都有实测证据，不是客套。**

### 隐私（最强项）
1. **零第三方请求**：我在线上完整走完 6 案（含展开全部证物、揭开全部提示、提交错误答案）后，抓到的 **20 个请求全部指向 `tbj0623.github.io`**，`third_party_requests` 为**空数组**。
2. **零持久化痕迹**：`cookies=[]`、`document.cookie=''`、`sessionStorage={}`、`indexedDB=[]`、`caches=[]`、`serviceWorkers=0`。
3. **零答案外传**：提交错误答案**前后网络请求数差 = 0**。
4. **storage 前缀与文档逐字一致**：实测 `zd:v1:progress`、`zd:v1:order:NA-001..006`，与 `PRIVACY.md:24-25` 表格完全对应。
5. **localStorage 被禁仍可通关**：桩掉整个 `localStorage` 后 `renders=true`、`completes=true`、0 报错。

### 逻辑与内容
6. **唯一解 6/6**：我用**独立于项目代码**的 Python 全排列实现复算，6 个案子全部 `sols=1`。
7. **线索必要性 6/6**：删任一条约束后解数变为 `[6,4,3]`、`[3,3,2]`、`[9,4,3,6]`、`[2,4,2,2]`、`[2,10,10,2]`、`[8,8,4,6]`，**每案每条都 `>1`**（无冗余线索）。
8. **答案与公开数据分离**：`cases/public/*.json` 6/6 **不含** `expected_solution`；线上 `cases/author/**` **404**。
9. **items 顺序不泄题**：6/6 的 `items` 数组顺序 **≠** 答案顺序（这是 `BLIND_REPORT.md:458-469` 修订过的）。
10. **求解器性能**：NA-006（720 排列）`countSolutions` **3.7ms**、`necessityReport` **10.1ms**，本地加载无感知延迟。
11. **纯静态零依赖**：无 npm 依赖，`build.mjs` 只用 Node 内置模块。

### 安全
12. **XSS 防护有效**：我用恶意 case JSON（`<img onerror>`、`<svg onload>`、`<b onmouseover>` 注入 `title`/`body`/`evidence.title`/`hints`）实测，全部**渲染为转义文本**，`imgX=0`、`x=y=z=0`，无任何脚本执行。
13. **无 `eval`/`new Function`/`innerHTML`**：全仓库 0 处真实使用（2 处命中在注释里）。
14. **API 密钥/PII 零泄漏**（代码内）：grep `gho_|ghp_|sk-|AKIA|password|api_key|C:\Users\` → **0 命中**。
15. **无 `pull_request_target`**：两个 workflow 都没用这个危险触发器。
16. **`permissions` 最小化**：`ci.yml` 只有 `contents: read`；`pages.yml` 的 `pages: write` + `id-token: write` 是部署必需。
17. **畸形输入降级得体**：HTTP 500 / 非法 JSON / 超长字符串（50 万字）→ 全部给出可读错误页或正常渲染，**不白屏、不卡死**。

### 无障碍
18. **纯键盘通关**：我用 `Tab` + `Enter`（零鼠标）从打开案件走到结案页，`result: "completed"`。
19. **纯触摸通关**：390px + `has_touch`，用 `tap()` 完成 NA-001，3 次 tap 到结案。
20. **320px 零横向溢出**：5 个路由 × 2 视口（320/360）= 10 项检查，**全部 `overflow_px = 0`**（这是 WCAG 1.4.10 Reflow 的硬指标，项目自己做的是 360/390/768，我补测了更严格的 320）。
21. **焦点轮廓**：`outlineWidth: 3px`、`outlineStyle: solid`、对比较强（`rgb(223,185,120)` on 深色）。
22. **reduced-motion 真实生效**：`transitionDuration = 1e-06s`（不是只写了 media query）。
23. **图片失败可玩**：断掉全部 `.webp/.png` 后，证据文字仍有 225 字符可读。
24. **主色对比度优秀**：手算渐变卡片最差情况 **10.26:1**、深色背景正文 **15.35:1**、次要文字 **5.33:1**——全部远超 WCAG AA 的 4.5:1。

### 伦理与营销
25. **零虚构玩家数据**：无玩家数、无评分、无"好评"、无虚构评论、无平均用时（`play_minutes` 明确标为设计估计）。
26. **主动披露未验证项**：`ITCH_PAGE_DRAFT.md:141-143` 主动写"未做屏幕阅读器实机测试 / 未声明 WCAG 等级"；`PLAYTEST_PROTOCOL.md:6` 写"尚未收集任何真实人类试玩数据 `NOT_DONE`"；`MASTER_STATE.md:14` 写 G5 `⛔ NOT_DONE`。**三处独立披露，措辞一致。**
27. **无真实机构/人物/事件映射**：六案 0 个具名人物（全部用职务指代）、0 个真实机构名、0 个真实地名。
28. **无羞辱性失败文案**：`app.mjs:875-876` 的失败反馈是"仍有 N 条关系未满足 / 排列已保留 / 可以继续核对"，且 `AUTHOR_GUIDE.md:97` 明令禁止"你居然没发现""这很明显"。
29. **无 dark pattern**：无倒计时、无假稀缺、无强制注册、无退出挽留、无诱导分享（`navigator.share` 0 命中）。
30. **虚构声明四处独立且一致**：`index.html:67`（首屏）、`index.html:205`（关于页）、`README.md:127-129`、`ITCH:107-109`。

---

## 9. What I could not check

诚实列出我**没有能力验证**的项。这些不应被读作"没问题"，只应被读作"我不知道"。

| # | 无法验证的项 | 原因 | 建议由谁验证 |
|---|---|---|---|
| 1 | **真人试玩体验**（趣味性、难度曲线、手机可读性、提示梯度是否有效） | 我是 AI，无法代表人类玩家。项目自己也把这项标为 `NOT_DONE` | 按 `PLAYTEST_PROTOCOL.md` 招 3–5 名真人 |
| 2 | **屏幕阅读器实机表现**（NVDA / VoiceOver / TalkBack） | 需要真实 AT 软件 + 人工听读 | 无障碍专家用 NVDA + Firefox / VoiceOver + Safari 实测 |
| 3 | **图片的生成来源与版权链** | 图片无 EXIF、无 C2PA、无生成记录；我无法反查 AI 模型的训练数据 | 项目方提供生成工具、prompt、日期的记录；或做一次反向图片搜索（我做了文字搜索，未做以图搜图） |
| 4 | **`docs/screenshots/` 的生成脚本** | 仓库里找不到产出这套视口截图的脚本（`e2e.py` 只写 `screenshots/`） | 项目方补充脚本或说明 |
| 5 | **itch.io iframe 内的真实行为** | 包还没上传（`MASTER_STATE.md:26` 明确 `DRAFT_READY`，未上传） | 上传后在 itch iframe 里走一遍 `ITCH:151` 的检查清单 |
| 6 | **Safari / Firefox 引擎兼容性** | `MASTER_STATE.md:55` 自己披露"无 Google Chrome；跨引擎为 Chromium + Edge"。我只测了 Chromium | 用 Safari（WebKit）和 Firefox 各跑一次 `e2e.py` |
| 7 | **GitHub Pages 的实际日志策略** | 我无法读取托管方日志 | 查阅 GitHub 官方隐私声明；在 `PRIVACY.md:37-39` 已经写了"平台自身可能记录"，措辞足够 |
| 8 | **`git` 历史里是否曾有密钥被提交后又删除** | 我只扫了**当前工作树**，没扫全部历史 blob | `git log -p --all | grep -iE 'ghp_|sk-|password'` 或 `gitleaks detect --log-opts=--all` |
| 9 | **`13014880645@163.com` 是否为真实手机号** | 我无法也不应验证 | 项目方自查 |
| 10 | **六案的"语义无歧义"是否真的成立** | 我读了全文，**主观上**认为措辞清晰（尤其 NA-004/NA-005 主动写了"没有记下谁高谁低""不要求居中"）；但"语义歧义"的最终判据是母语读者的直觉，不是我的分析 | 已在 `BLIND_REPORT.md` 做过三轮，但那是 AI；建议真人再读一遍 |
| 11 | **CC BY-NC-SA 的"NC"在实际分发中的边界** | 法律问题，需律师 | 若要商用，咨询版权律师（`ASSETS_LICENSE.md:5` 已写"这不是法律意见"，措辞正确） |
| 12 | **`work/qa/a11y/axe.min.js` 的 MPL-2.0 合规细节** | 我不是律师；minified 源码是否满足 MPL "Source Code Form" 有争议 | 法律顾问，或直接从仓库移除（最省事） |

---

## 10. 修复优先级清单（给 Lead 的可执行版本）

### 发布前必须（blocker）
1. **修 `ci.yml:54` 的坏正则**（critical）—— 并加"负向测试"证明门禁真的会失败。
2. **修 `app.mjs:526` 的存档校验**（high）—— 元素必须属于 `c.items`，否则 `dropOrder` 并回退。
3. **修 `build.mjs:73` 的 `cpSync` filter**（high）—— 排除 `site/tools/` 与非 `index.html` 的 HTML；`pages.yml` 加 `test ! -e dist/tools`。

### itch.io 上架前必须（因为会被玩家看到）
4. **删掉/降级"交互目标 ≥ 44px"**（high）—— 或修 CSS 让它是真的。
5. **修 `#hints` 的 `aria-label`**（medium）—— 改 `<section>` 或加 `role="region"`，1 行。
6. **修 heading 层级**（medium）—— 首页 h1→h3 跳级、页脚 h4、verdict 无 h1。
7. **改 `README.md:107` "独立解题者" → "独立复核者（AI agent，信息隔离）"**（medium）—— 1 个词。
8. **`og:description` 加"（虚构作品）"**（low）—— 1 个括号。

### 发布后 1 周内（技术债）
9. 补 `ASSETS_LICENSE.md` 的明确授权句与 229 个空白文件的分类（medium）。
10. 删 `docs/STORY_BIBLE.md` 的死引用 / 补文件（medium）。
11. 处理 `work/qa/a11y/axe.min.js` 的 MPL-2.0 合规或移除（medium）。
12. 用 commit SHA 固定 GitHub Actions（medium）。
13. 修 `NA-006` 终章的标签使其符合 `AUTHOR_GUIDE.md:102` 的自定规则（medium）。
14. 历史 commit 的邮箱泄漏处理（low，但涉及个人信息，建议尽快）。
15. `MASTER_STATE.md` 补 `git fetch` 前置条件 + 记录线上 `BUILD` SHA（low）。
16. `TEST`：把 `e2e.py` 的 44px 选择器改为全量、把 `external` 请求检测改为 CDP 级（low）。

---

## 附录：复现方法

所有探针脚本位于 `work/redteam/`，均为只读（除自身输出 JSON 外不写任何文件）：

| 脚本 | 作用 | 输出 |
|---|---|---|
| `net_probe.py` | 抓全部网络请求、cookie、storage、URL 探测 | `net_probe.json` |
| `probe2.py` | localStorage 容错 + 纯键盘通关 + axe 扫描 | `probe2.json` |
| `probe4.py` | 纯触摸通关、320px reflow、恶意 JSON 注入 | `probe4.json` |
| `probe5.py` | XSS 确认（patch 响应体） | `probe5.json` |
| `storage_probe.py` | 12 种畸形 localStorage 值 | `storage_probe.json` |
| `stale_save.py` | 过期存档崩溃复现 | `stale_save.json` |
| `no_storage_probe.py` | localStorage 禁用仍可玩 | `no_storage.json` |
| `targets_probe.py` | 全量交互目标尺寸 | `targets.json` |
| `contrast_probe.py` | 计算样式对比度 | `contrast.json` |

运行环境：Python 3.12 + Playwright 1.62.0 + Chromium（headless）、Node v24.20.0、GNU grep 3.0（Windows Git Bash）。
