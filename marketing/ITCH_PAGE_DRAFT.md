# itch.io 发布资料 · RELEASED

**当前状态：`RELEASED`** —— 已于 **2026-10-30** 在 itch.io 公开发布并通过匿名访客实测。
历史阶段 `DRAFT_READY`（发行包已构建、尚未上传）**保留在 §9 变更记录中，不删除**，
以免审计时看不出发布前后的差别。

---

## 0. 已发布信息（实测值，非声明）

| 项 | 值 | 证据 |
|---|---|---|
| **公开 URL** | **<https://tbj0623.itch.io/zero-dossier-office>** | `tests/browser/test_itch_live.py` 实测公开页 HTTP 200 |
| 上线日期 | **2026-10-30**（提交 `6e07efc`） | `git log -1 6e07efc` |
| 发行包 | `release/itch-html5-release.zip` | `release/RELEASE_MANIFEST.json` |
| 包大小 | **710 KB**（ZIP 726 680 B）/ 911 KB（解压 932 608 B） | 实测 ZIP 与清单一致 |
| 文件数 | **27**（itch 限制 1000） | `RELEASE_MANIFEST.json` `"files": 27` |
| `index.html` 位置 | **ZIP 根目录** ✅ | 同上 `"index_at_root": true` |
| 嵌入尺寸 | **1280 × 800**，含全屏按钮、手机友好、显示滚动条 | 发布配置（提交 `6e07efc` 说明） |
| Visibility | **Public** | 匿名访客可访问（未登录上下文实测） |
| 定价 | **Free**（No payments） | 发布配置 |
| 分类 / 标签 | Puzzle；3 个标签 | 发布配置 |
| 上传前置 | 邮箱验证（已完成） | 提交 `6e07efc` 说明 |
| **Generative AI disclosure** | **Yes + Text & Dialog + Code + Graphics** | 后台前后对比见 §0.1 |
| 匿名访客校验 | **20 / 20 PASS**（六案全通） | `screenshots/itch-live-report.json` |

### 0.1 生成式 AI 披露（本次整改重点）

itch.io 的 Generative AI Disclosure 最终选择：

| 勾选项 | 状态 | 依据 |
|---|---|---|
| Generative AI = **Yes** | ✅ 已勾 | 素材与文本确实含生成式 AI 产出 |
| **Text & Dialog** | ✅ 已勾 | 叙事与说明文本经过生成式工具参与 |
| **Code** | ✅ 已勾 | 代码开发过程使用 AI 辅助 |
| **Graphics** | ✅ **由本次整改补勾** | 美术至少部分是生成式 AI 输出（见 `docs/PROVENANCE.md`），原发布时因"来源无法从仓库验证"未勾，该判断已被验收报告 `P0-01` 否定 |
| Sound | ⬜ 不勾 | 本版**无任何音频**，如实不声明 |

> **后台证据（已取证，`PENDING_OWNER-5` 关闭）**：验收报告"补验门槛"第 1 条要求实际编辑后台
> 状态可核对。已留存 itch 编辑页字段抓取的前后对比：
>
> | 证据文件 | `ai_generated` | Graphics | Text | Code | 抓取时间（UTC） |
> |---|---|---|---|---|---|
> | `screenshots/itch-ai-disclosure-before.json` | `yes` | **`false`** | `true` | `true` | 2026-10-30T04:22:23Z |
> | `screenshots/itch-ai-disclosure-after.json` | `yes` | **`true`** | `true` | `true` | 2026-10-30T04:22:52Z |
>
> 两次抓取间隔 29 秒，唯一变化是 `ai_graphics.checked: false → true`；
> 编辑页为 `https://itch.io/game/edit/5261339`，`published: "published"`。
> 因此"Graphics 已勾选"有后台记录支撑，不再只是整改要求。

itch 官方说明：<https://itch.io/docs/creators/quality-guidelines#ai-disclosure>

---

## 1. 发行包

| 项 | 值 |
|---|---|
| 文件 | `release/itch-html5-release.zip` |
| 大小 | **710 KB**（ZIP 726 680 B）/ 911 KB（解压 932 608 B） |
| 文件数 | **27**（限制 1000） |
| `index.html` 位置 | **ZIP 根目录** ✅（itch.io 硬性要求） |
| 路径 | 全部相对路径，无绝对 `/` 开头 ✅ |
| 单文件最大 | 179 KB（`assets/harbor-archive-background.webp`，限制 200 MB） |
| 解压自测 | 通过：另存到临时目录独立启动静态服务器，36 项浏览器检查全 PASS，六案全部通关 |
| 不含 | `axe-core`（测试专用，MPL-2.0，未打进包）；无音频；无字体文件 |

重新构建：

```bash
node tools/build.mjs
python tools/build_itch.py
```

> 注意：`assets/archive-desk-background.webp` 仍在打包清单里，但**当前版本没有任何代码引用它**
> （`tools/build_itch.py` L33 已注明）。是否从下个版本移除，见 `docs/PROVENANCE.md` §3.1。

## 2. 上传步骤（**历史操作记录，已完成**）

以下为 2026-10-30 实际执行的上传流程，保留原文以便复核当时的选择：

1. itch.io → **Create new project** ✅ 已完成
2. Kind of project：**HTML** ✅ 已完成
3. 上传 `release/itch-html5-release.zip` ✅ 已完成
4. **勾选** "This file will be played in the browser" ✅ 已完成
5. Embed options：
   - Viewport：`1280 × 800`（站点自适应，也可用 `Fullscreen button`）✅ 已设置
   - 勾选 **Fullscreen button** ✅ 已设置
   - 勾选 **Mobile friendly**（已实测 360/390/768 无溢出、目标 ≥44px）✅ 已设置
6. 按下文填写页面字段 ✅ 已完成
7. Visibility：先选 **Draft** → 自己预览确认 → 再 **Public** ✅ 已完成（当前为 Public）

> ⚠️ 原文提醒"首次预览时请在 itch 的 iframe 里实际点开第 001 案走一遍"——
> 这一步后来被 `tests/browser/test_itch_live.py` 以**匿名访客**方式覆盖，
> 结果见 §2.1。

### 2.1 上传后实测结果

`tests/browser/test_itch_live.py` 在**公开的 itch 页面**上、用**全新浏览器上下文（未登录 = 真实访客）**
跑完整流程，**20 / 20 PASS（六案全部在 itch 托管实例上通关）**，
原始结果见 `screenshots/itch-live-report.json`（该 JSON 由测试脚本生成，重跑后会覆盖，
数字以 JSON 当前内容为准）：

| # | 检查项 | 结果 | 实测细节 |
|---|---|---|---|
| 1 | 公开页面 HTTP 200 | ✅ | `status=200` |
| 2 | 页面标题正确 | ✅ | `第零证物局 · The Zero Dossier Office by tbj0623` |
| 3 | Run game 可点击 | ✅ | — |
| 4 | 游戏在 itch iframe 中加载 | ✅ | `https://html-classic.itch.zone/html/20141202/index.html?v=17` |
| 5 | 首页视图存在 | ✅ | — |
| 6 | 默认中文 | ✅ | — |
| 7 | 档案柜 6 张卡 | ✅ | 6 张（证明 case JSON 在 itch 环境可达） |
| 8 | NA-001 四个格位 | ✅ | 4 个 |
| 9 | 排列到答案顺序 | ✅ | `红票 → 蓝票 → 黄票 → 绿票` |
| 10 | 提交后出现结案页 | ✅ | — |
| 11 | 结案标题正确 | ✅ | `档案归位。` |
| 12 | 逻辑复盘 + 档案后记两段 | ✅ | `['逻辑复盘 · 可由证据严', '档案后记 · 结案后补充']` |
| 13 | NA-002 在 itch 实例上通关 | ✅ | `航海图 → 银徽章 → 铜钥匙 → 玻璃球` |
| 14 | NA-003 在 itch 实例上通关 | ✅ | `红盒 → 纸鹤 → 铜铃 → 星图 → 蓝灯` |
| 15 | NA-004 在 itch 实例上通关 | ✅ | `铜铃 → 值班簿 → 玻璃罩 → 旧透镜 → 海图` |
| 16 | NA-005 在 itch 实例上通关 | ✅ | `晨雾邮笺 → 港口便条 → 红蜡封信 → 夜航申请 → 空白回邮` |
| 17 | NA-006 在 itch 实例上通关 | ✅ | `钟楼影 → 纸船影 → 玻璃影 → 雨幕影 → 灯塔影 → 空白底片` |
| 18 | 六案全部在 itch 托管实例通关 | ✅ | 6/6（NA-001 … NA-006） |
| 19 | 归档进度显示 6 / 6 | ✅ | `已归档 6 / 6` |
| 20 | 无未捕获异常 | ✅ | `[]` |

> 第 13–17 项在 JSON 原文里写作「在 itch 实例上**天**通关」——测试脚本的笔误，
> 不影响结果。此处按原意表述，未改动测试文件（`tests/` 不在本次整改范围）。

**这次实测覆盖了什么**：itch 托管环境下 iframe 能加载、静态资源能取到、存档可用性探测正常、
**六案全部可通关**、归档进度正确累计、零 JS 异常。

**没覆盖什么**（不夸大）：
- 不是登录态后台预览，是公开页访客视角；
- 没做 itch 页面的手机实机测试（手机断点只在 Pages 站点验证过）；
- 未逐文件枚举 27 个产物是否 404，只证明"已走通路径"无 404。

## 3. 页面文案（可直接粘贴）

### Title
```
第零证物局 · The Zero Dossier Office
```

### Short description / tagline（≤ 160 字符）
```
在雾港的异常档案局里，你不是找凶手，而是把互相错位的真实记录重新归位。六份档案，三幕，一次分类错误。
```

### Classification
- **Genre**：Puzzle
- **Tags**：`puzzle` `mystery` `detective` `narrative` `point-and-click` `story-rich` `chinese` `short` `free` `browser`
- **Made with**：HTML5, JavaScript
- **Average session**：A few minutes
- **Languages**：中文 (Simplified)
- **Inputs**：Mouse, Keyboard, Touchscreen
- **Accessibility**：见第 5 节

### Description（正文）

```markdown
**这些记录，不应该同时成立。**

一张车票，一封从未寄出的回信，一张什么都没拍下的底片。
你是雾港第零室的记录修复员——你的工作不是判断谁在撒谎，而是把互相错位的真实记录排回它本来的秩序。

每一案解决的都不是"魔法"，而是**对事实的误读**：一次错误的分类、一份错版的图纸、一个被当成事件的校准动作。

---

### 怎么玩

1. **读证物** —— 每张证物都写明了一种可核实的关系：先后、相邻、间距、夹在中间、固定格位。
2. **排格位** —— 点击卡片选中，再点目标格位交换；也可以用 ↑↓ 按钮。三种操作等价。
3. **提交复原** —— 系统逐条核对，只告诉你"哪些关系不符"，绝不替你排好。

卡住了？每案有三档提示：先给方法，再点出关键组合，最后给较直接的推导。**提示不会自动完成排列，也不扣分。**

### 六案 · 三幕

| 幕 | 档案 |
|---|---|
| I · 错位的开端 | 末班车的四张车票 / 封存室的四格抽屉 / 静默分拣线上的五个包裹 |
| II · 灯塔与回信 | 灯塔没有亮起的第五盏灯 / 寄不到的第五封回信 |
| III · 第零张底片 | 第零号空白底片 |

六案之间藏着一条隐形主线：反复出现的半枚「0」章。漏看不会卡关，但看完整季，你会明白它到底是什么。

### 特点

- **免费、免注册**，打开就能玩
- 单案 3–12 分钟，随时可以停下
- **手机与键盘都能完整游玩**：所有拖放操作都有等价的按钮
- **不需要联网推理**：所有判定都在你的浏览器里完成，不上传你的答案
- **结案页把"逻辑"和"故事"分开**：哪些是能从证据严格推出来的，哪些是事后补写的叙述，一目了然

### 关于公平性

这不是"作者藏了一个答案让你猜"的游戏。每一案的证据都写明了自己是哪一种关系，程序可以验证这些关系只允许一种排列。我们还请了独立解题者只看剥离答案的证物、自己推导一遍，确认文字没有第二种读法。

发现某条证物有两种理解方式？欢迎告诉我们具体编号——这会直接帮助我们修复档案。

### 声明

所有人物、地点、机构与事件均为虚构的架空世界「雾港」。本作不影射真实死者、真实机构或现存个人。

**语言**：简体中文
```

### Credits
```
设计、编程、文本与美术：第零证物局 contributors
代码许可：MIT
叙事与美术许可：CC BY-NC-SA 4.0
```

> **[整改建议，尚未生效]** 建议在 itch 后台把 Credits 追加一行：
> `美术：含生成式 AI 输出，经人工裁切/调色/重排（详见仓库 docs/PROVENANCE.md）`。
> 本文件不改动**已在线上生效**的文案；是否追加由账号持有人决定（`PENDING_OWNER-5`）。

## 4. 需要的图片

| 用途 | 素材 | 尺寸建议 |
|---|---|---|
| Cover image | `site/assets/github-social-preview.png`（或另做 630×500） | itch 建议 630×500 |
| Screenshots | `docs/screenshots/01..06*.png` | 上传 5–6 张 |
| Thumbnail | `site/assets/archive-emblem-512.png` | 512×512 |

**全部使用真实运行截图**（`docs/screenshots/` 目录，从已部署站点实拍），不使用概念稿冒充游戏画面。
但这些截图里呈现的插画本身**含生成式 AI 输出**，复用受 CC BY-NC-SA 4.0 约束，见 `docs/PROVENANCE.md` §3.3。

## 5. 可访问性声明（填写 itch 的 Accessibility 栏）

已实测：
- ✅ 键盘可完成全部操作（Tab / Enter / ↑↓ / Esc）
- ✅ 所有拖放操作都有等价按钮替代
- ✅ 交互目标 ≥ 44px（360/390/768 断点实测）
- ✅ 尊重 `prefers-reduced-motion`
- ✅ 解谜信息全部为可复制文本，不依赖图片细节
- ✅ 无自动播放音频

**未验证**，因此不声明：
- ❌ 未做屏幕阅读器（NVDA / VoiceOver）实机测试
- ❌ 未声明达到任何 WCAG 等级

## 6. 定价

**Free**。**已发布**：No payments / In browser = 是 / Downloadable = 否。

## 7. 上传后必须做的验证

逐项按**真实情况**打勾。未做的保持未勾，并写明原因——不为了让表格好看而勾。

- [x] **在 itch 的 iframe 里走通第 001 案**
      —— 由 `tests/browser/test_itch_live.py` 以匿名访客身份完成（非登录预览）：
      公开页 200 → Run game → 游戏在 `html-classic.itch.zone` iframe 加载 →
      排到答案顺序 → 提交 → 结案页两段复盘齐全，零异常。
      后续扩展为**六案全通**，20/20 PASS（§2.1）。
- [ ] **手机浏览器打开 itch 页面 → 启动游戏 → 无横向滚动**
      —— **未做**。手机断点（360/390/768）是在 **GitHub Pages 站点**上实测的，
      **没有**在 itch 的嵌入页或 itch 的移动版本上实机验证。itch 侧只勾了 "Mobile friendly" 选项。
- [x] **确认无 404（图片、case JSON、solver.mjs）**
      —— 已走通路径无 404：档案柜读出 6 张卡（case JSON 可取）、NA-001 调查桌渲染
      （solver 与样式可取）、图片正常显示、提交判定正确返回。
      **未逐文件枚举**全部 27 个文件，故这是"已覆盖路径"而非"全量证明"。
- [x] **记录真实的 itch 游戏 URL 到 `ops/CHECKPOINT.md`**
      —— 已记录：`https://tbj0623.itch.io/zero-dossier-office`。
- [x] **在 itch 编辑后台核对 Generative AI 披露已勾选 Graphics，并留存证据**
      —— **已取证**。`screenshots/itch-ai-disclosure-before.json`（Graphics `false`）
      与 `screenshots/itch-ai-disclosure-after.json`（Graphics `true`）为同一次编辑的
      前后抓取，间隔 29 秒，唯一差异就是 Graphics 勾选（详见 §0.1）。

## 8. 许可证与来源

- 代码：MIT（`LICENSE` 为纯 MIT 全文，不可追加说明）
- 叙事、案件文本、视觉资产：CC BY-NC-SA 4.0（`ASSETS_LICENSE.md`）
- **素材来源、生成式 AI 参与程度、6 项 `PENDING_OWNER`**：`docs/PROVENANCE.md`
- axe-core（MPL-2.0）仅测试用，不随包分发

## 9. 变更记录

| 日期 | 阶段 | 变更 |
|---|---|---|
| 2026-10-30（早） | **`DRAFT_READY`** | 发行包构建完成（当时 21 文件 / 0.57 MB）、解压自测通过，**尚未上传**。上传需账号授权，Agent 不代建账号。 |
| 2026-10-30（晚） | **`RELEASED`** | 实际上传并公开发布（27 文件 / 710 KB）；Visibility=Public；`tests/browser/test_itch_live.py` 匿名访客 13/13 通过；补记真实 URL 与发布配置。 |
| 2026-10-30（整改） | **`RELEASED`（整改后）** | 状态从 `DRAFT_READY` 更正为 `RELEASED`（`DRAFT_READY` 作为历史阶段保留在上两行）；新增 §0 已发布信息块与 §2.1 上传后实测；Generative AI 披露补勾 **Graphics** 并留存后台前后对比；§7 逐项按真实情况勾选；§1 文件数与大小更正为 27 / 710 KB；§2.1 校验数由 13 更新为 **20（六案全通）**。 |
