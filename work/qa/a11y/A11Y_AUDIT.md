# 第零证物局 · 无障碍审计报告（A11Y AUDIT）

**审计对象**：线上真实部署站点 <https://tbj0623.github.io/zero-dossier-office/>
**不是源码审计**——所有结论均在真实浏览器中对线上产物测得。
**部署版本指纹**：`BUILD = 41fc9520deb643883af262b36a9c6b11fe2c918c`（`app.mjs` sha256 前缀 `711e230dd20c784e`，审计期间及收尾时两次复核均未变更）
**审计日期**：2026-10-30
**重要时效说明**：审计结束时本地工作区已有新提交（`0e131eb` 等）在改 `site/app.mjs`，但**线上 `app.mjs` 的 BUILD 指纹在收尾复核时仍是 `41fc9520…`，未被重新部署**。因此本报告针对的线上产物与审计开始时完全一致，结论有效。待本地改动重新构建并发布后，本报告需复跑——尤其是 §5 中标注 `site/app.mjs` 的条目可能已被他人在改。
**工具**：Playwright for Python (Chromium) + axe-core 4.10.2（本地缓存 `axe.min.js`，`page.add_script_tag(path=...)` 注入）
**axe 规则集**：`wcag2a`, `wcag2aa`, `wcag21aa`, `wcag22aa`, `best-practice`
**视口**：桌面 1440×900；移动 390×844（`is_mobile=True, has_touch=True, dsf=2`）；重排测试 320×900 与 720×450（≈200% 缩放）

---

## 1. Executive Summary

### 1.1 axe-core 机器判定计数

| 严重度 | 违规实例（nodes） | 独立规则数 |
|---|---|---|
| critical | 0 | 0 |
| **serious** | **5** | 1（`aria-prohibited-attr`） |
| **moderate** | **11** | 2（`heading-order` ×10、`page-has-heading-one` ×1） |
| minor | 0 | 0 |
| **合计** | **16** | **3** |

> 12 个状态 × 每状态 17–46 条通过规则。axe 另有 **4–78 个节点/页 的 `color-contrast` 为 "incomplete"**（12 状态合计 688 节点；主要原因 `Element's background color could not be determined due to a background gradient`，仅 `desk-expanded` 一页就有 63 个节点属此原因，另 5 个是 `Element content is too short to determine if it is actual text content`）。这部分**不能算通过**，我用真实像素采样逐对复测，结论见 §4.5——全部通过，最差 5.16:1。

### 1.2 去重后的真实问题计数

把 axe 的 3 条规则命中（`page-has-heading-one` 并入第 3 条 critical）与人工检查合并去重，得到**独立缺陷 11 项**。其中 8 项 axe 原理上测不到，只能人工判定：

| 严重度 | 独立问题数 | 说明 | axe 可测？ |
|---|---|---|---|
| **critical** | **3** | 跳转链接把用户带离页面；选中格位后焦点掉到 `<body>`（连带 Esc 失效）；结案页焦点丢失 + h1 消失 + 悬空 IDREF | 否 / 否 / 部分（仅 IDREF 与 h1 那部分为 incomplete） |
| **serious** | **3** | 提示内容对读屏不可达（`#hints` aria-label 非法且非 live）；从档案柜进入案件后焦点停在 `<body>`；toast 隐藏后仍留在无障碍树 | 部分（`aria-prohibited-attr` 命中其一） |
| **moderate** | **3** | 标题层级跳级；`<dialog>` 缺 `aria-describedby`；触控目标小于站点自己宣称的 44 px | 是 / 否 / 否 |
| **minor** | **2** | 移动端菜单 Esc 不关闭；状态栏文字非 live | 否 / 否 |
| **合计** | **11** | | 3 项可测 |

> 注意"数量"口径不同：§1.1 的 16 是 axe 的**违规节点数**（同一规则在 10 个页面各命中 1 次即记 10），§1.2 的 11 是**去重后的独立缺陷数**。两者不可相加。

### 1.3 一句话结论

**不可按现状发布。** 视觉设计、配色对比、焦点环、减少动效、200% 重排这五项做得比多数同类作品都好，且都有数字证明；但**键盘/读屏的主路径是断的**：第一个 Tab 按下去（跳到主要内容）会把人送回首页；选中格位后焦点丢失且文档里写的 Esc 取消选中随之失效；结案时焦点与 h1 一起消失。这三条都在主流程上，不是边角。

---

## 2. 逐页 axe 结果

图例：✔ = 0 违规；每条违规列出 rule id / impact / help / 精确选择器 / 节点数。

| # | 页面/状态 | 通过规则 | 违规 | 明细 |
|---|---|---|---|---|
| 1 | `#/` home | 39 | **1** | `heading-order` moderate — *Heading levels should only increase by one* — `.pitch__card:nth-child(1) > h3` — 1 node（h1 → h3，跳过 h2） |
| 2 | `#/cabinet` | 40 | **1** | `heading-order` moderate — `.act:nth-child(1) > .act__head > div > .act__title` — 1 node（h1 → h3） |
| 3 | `#/case/NA-001` 全部折叠 | 42 | **2** | `aria-prohibited-attr` **serious** — *Elements must only use permitted ARIA attributes* — `#hints` — 1 node；`heading-order` moderate — `div:nth-child(1) > h4` — 1 node |
| 4 | `#/case/NA-001` 全部展开 | 42 | **2** | 同上两条（`#hints` 1 node、`div:nth-child(1) > h4` 1 node） |
| 5 | `#/case/NA-001` 选中态 | 43 | **2** | 同上两条 |
| 6 | `#/case/NA-001` 错误提交 | 42 | **2** | 同上两条 |
| 7 | `#/case/NA-001` 查看提示后 | 42 | **1** | `heading-order` moderate — `div:nth-child(1) > h4` — 1 node。`aria-prohibited-attr` 降级为 **incomplete**（`#hints` 内有文本后 axe 无法判定支持度，改为需人工复核——实际仍是缺陷，见 §4.3） |
| 8 | `#/case/NA-001` 结案页 | 45 | **1** | `page-has-heading-one` moderate — *Page should contain a level-one heading* — `html` — 1 node。另有 incomplete：`aria-valid-attr-value` **critical**（`#view-case` 的 `aria-labelledby="case-title"` 目标不存在）+ `aria-prohibited-attr` serious |
| 9 | `#/manual` | 46 | **1** | `heading-order` moderate — `div:nth-child(1) > h4` — 1 node |
| 10 | `#/about` | 40 | **1** | `heading-order` moderate — `div:nth-child(1) > h4` — 1 node |
| 11 | 重置确认 `<dialog>` 打开 | 17 | **0** | ✔ 0 违规。**注意覆盖范围**：`:modal` 生效时 axe 只能看到对话框子树（`nodesChecked: 12`、`passes: 6`、`inapplicable: 24`），页面上其余 60+ 节点本轮未被检查——"0 违规"仅指对话框内部。4 个 `color-contrast` incomplete 已像素复测：`#confirm-title` 10.53:1、`#confirm-body` 7.48:1、取消按钮 7.78:1、确认按钮 7.88:1，全通过 |
| 12 | 移动端 390×844 调查桌 | 42 | **2** | 同 #3 两条 |

**`div:nth-child(1) > h4` 的实体**：`<footer>` 内三个栏目标题 `<h4>文献</h4>` / `<h4>技术</h4>` / `<h4>声明</h4>`（线上 `index.html:225` 起）。它们出现在**全部 10 个内容页**，是同一处根因。

各页实际标题序列（实测）：

```
#/         H1 这些记录，不应该同时成立。→ H3 ×3（跳过 H2）→ H2 档案柜 → H3 ×5 → H4 ×3
#/cabinet  H1 档案柜 → H3 ×10 → H4 ×3
#/case/…   H1 末班车的四张车票 → H2 已采集证物 → H2 复原格位 → H4 ×3
#/manual   H1 怎么玩 → H2 ×5 → H4 ×3
#/about    H1 第零证物局 → H2 ×5 → H4 ×3
#/case/… 结案后  （无 H1）→ H2 档案归位。→ H3 ×2 → H4 ×3
```

原始数据：`axe-home.json`、`axe-cabinet.json`、`axe-desk-collapsed.json`、`axe-desk-expanded.json`、`axe-desk-selected.json`、`axe-desk-error.json`、`axe-desk-hint.json`、`axe-verdict.json`、`axe-manual.json`、`axe-about.json`、`axe-reset-dialog.json`、`axe-desk-mobile-390.json`。

---

## 3. 键盘可达性

### 3.1 完整焦点顺序（调查桌 1440×900，25 个可聚焦元素）

`Tab` 从页面起点开始，实测 25 个停靠点后进入 `<body>` 并回到第 0 项（浏览器默认循环，非页面自建陷阱）：

| # | 元素 | 可访问名 | 尺寸 |
|---|---|---|---|
| 0 | `a.skip-link` | 跳到主要内容 | 146×52 |
| 1 | `a.brand` | 第零证物局 · 返回封面 | 227×46 |
| 2 | `a[data-nav=cabinet]` | 档案柜 | 73×44 |
| 3 | `a[data-nav=manual]` | 玩法说明 | 87×44 |
| 4 | `a[data-nav=about]` | 关于与隐私 | 101×44 |
| 5 | `a` (面包屑) | 档案柜 | 41×23 |
| 6 | `#ev-btn-E01` | E01 粘连的票根 物证 | 521×47 |
| 7 | `#ev-btn-E02` | E02 灯塔站的回执 记录 | 521×47 |
| 8 | `#ev-btn-E03` | E03 维修铃声 证词 | 521×47 |
| 9 | `.slot[0] [data-act=down]` | 将「蓝票」下移一格 | 44×44 |
| 10 | `.slot[0] [data-act=pick]` | 选中「蓝票」以交换位置 | 44×44 |
| 11 | `.slot[1] [data-act=up]` | 将「绿票」上移一格 | 44×44 |
| 12 | `.slot[1] [data-act=down]` | 将「绿票」下移一格 | 44×44 |
| 13 | `.slot[1] [data-act=pick]` | 选中「绿票」以交换位置 | 44×44 |
| 14 | `.slot[2] [data-act=up]` | 将「红票」上移一格 | 44×44 |
| 15 | `.slot[2] [data-act=down]` | 将「红票」下移一格 | 44×44 |
| 16 | `.slot[2] [data-act=pick]` | 选中「红票」以交换位置 | 44×44 |
| 17 | `.slot[3] [data-act=up]` | 将「黄票」上移一格 | 44×44 |
| 18 | `.slot[3] [data-act=pick]` | 选中「黄票」以交换位置 | 44×44 |
| 19 | `#btn-submit` | 提交复原 | 183×44 |
| 20 | `#btn-hint` | 查看提示 | 131×44 |
| 21 | `#btn-reset` | 重置此案 | 131×44 |
| 22–24 | footer 3 个链接 | 档案柜 / 玩法说明 / 关于与隐私 | 41×20 等 |

**可达性核对（逐项）**

| 目标 | 结论 | 证据 |
|---|---|---|
| 每张证物摘要 | **PASS** | 3/3 出现在 #6–#8 |
| 每个 ↑ / ↓ / 选中按钮 | **PASS** | 12 个可用按钮全部可达；第 1 格 `up`、第 4 格 `down` 因边界 `disabled` 被跳过，属正确行为 |
| submit | **PASS** | #19 |
| undo | **PASS（条件性）** | 初始 `disabled`，不在 Tab 序中；执行任意一次移动后 `disabled=false` 且进入 Tab 序（实测 `undo_after_move.inTabOrder = true`）。这是正确的可用性语义，不是缺陷 |
| hint | **PASS** | #20 |
| reset | **PASS** | #21 |

无焦点陷阱：第 25 步落到 `BODY`，第 26 步回到 skip-link。

### 3.2 焦点可见性 —— **PASS**

对上述**每一个**停靠点取 `getComputedStyle`，全部为：

```
outline: rgb(223, 185, 120) solid 3px;  outline-offset: 3px;  :focus-visible = true
```

- 25/25 停靠点 `outline-width = 3px`、`outline-style = solid`、`outline-offset = 3px`
- 对比度：`--brass #dfb978` on `--ink #081821` = **9.76:1**，远超 3:1（2.4.11 / 1.4.11）
- `:focus:not(:focus-visible){outline:none}` 只在鼠标聚焦时生效，键盘路径全部保留焦点环——实测 `fv = true` 无一例外
- 唯一 `outline-style: none` 的是 `BODY`（`outline-width` 仍报 3px 但样式为 none，浏览器默认焦点不渲染），BODY 不是交互控件，不计缺陷

### 3.3 重渲染后的焦点保持 —— **混合结果**

| 操作 | 焦点去向 | 结论 |
|---|---|---|
| 键盘 Enter 触发某格 **↑** | **留在同一物件上移后的那个 ↑ 按钮**。实测：操作前 `aria-label="将「红票」上移一格"` 位于 y=578，操作后同一 `aria-label` 位于 y=497，`focusVisible=true`，`inViewport=true` | **PASS** |
| 键盘 Enter 触发 **↓** | 同上，跟随物件 | **PASS** |
| 键盘 Enter 触发 **选中（pick）** | **掉到 `<body>`**。`selected` 确实变成 `"0"`（选中成功），但 `document.activeElement === BODY`，`focusVisible=false` | **FAIL** |
| 第二次 pick（完成交换） | **`<body>`** | **FAIL** |
| undo / 错误提交 | 焦点保留在 `#btn-undo` / `#btn-submit` | **PASS** |
| 结案（submit 成功 → 渲染 verdict） | **`<body>`**，且此后 2.8 秒内 14 次采样均为 BODY；`#verdict-title` 的 `tabIndex = -1`，`h2` 默认不可聚焦，`?.focus?.()` 是空操作 | **FAIL** |
| 从档案柜点进案件 | **`<body>`**。`router()` 在 `route.view === 'case'` 分支 `return`（线上 `app.mjs:328-329`）**早于** `$('#main')?.focus()`（`:343`） | **FAIL** |

**根因（三条同源）**：`drawSlots()` 用 `host.replaceChildren()` 整体重建 `#slots`（`app.mjs:662`），`onPick()` 的两个分支都调用无参 `drawSlots()`（`:788`、`:796`），没有像 `move()` 那样传 `{index, act}` 恢复焦点，于是被点按钮随 DOM 一起被销毁。

**连锁缺陷**：文档承诺的 `Esc` 取消选中失效。`Esc` 监听器挂在 `.slot` 的 keydown 上（`:1059-1075`），而 pick 之后焦点已在 `<body>`，事件永远不进该处理器。实测：

```
选中后 activeElement = BODY  →  按 Esc  →  selected 仍为 1，状态栏仍为「已选中「绿票」，请点目标格位」
手动把焦点放回格位内再按 Esc →  selected 归 0，状态栏变为「已取消选中」   ← 证明逻辑本身是对的，只是焦点不在那儿
```

`/manual` 页「键盘操作」表格明确写着 `Esc`「取消当前选中」，因此这是**文档承诺与实际行为不符**，不只是未实现。

---

## 4. 人工检查逐项结果

### 4.1 证据卡语义（静态分析）—— **PASS**

| 检查项 | 结果 |
|---|---|
| `aria-expanded` 存在且随展开切换 | **PASS**。三张卡实测序列 `true / false / false`；对 E02 连点三次得到 `true → false → true`，与 `body.hidden` 完全同步 |
| `aria-controls` 目标存在 | **PASS**。`ev-btn-E01 → ev-body-E01`、`E02 → E02`、`E03 → E03`，`document.getElementById()` 全部命中 |
| 展开按钮有可访问名 | **PASS**。三者均无 `aria-label`，但按钮内含可见文本，计算名为 `E01 粘连的票根 物证` / `E02 灯塔站的回执 记录` / `E03 维修铃声 证词`——名称来自内容，符合 4.1.2 |
| `hidden` 与 `aria-expanded` 一致 | **PASS**。折叠时 `body.hidden = true` 且 `checkVisibility() = false` |

### 4.2 格位语义 —— **PASS**

| 检查项 | 结果 |
|---|---|
| 当前物件名可程序化确定 | **PASS**。每格 `<li>` 内含 `.slot__label`（如 `22:00`）与 `.slot__item`（如 `蓝票`），均真实文本节点，无 `aria-hidden` |
| ↑/↓ 的 `aria-label` 唯一且含物件名 | **PASS**。12 个标签两两互异（`duplicateLabels: []`），形如 `将「红票」上移一格`、`将「红票」下移一格` |
| 选中按钮状态 | **PASS**。`aria-pressed` 正确：选中项 `"true"`、其余 `"false"`；选中后标签变为 `取消选中「蓝票」`，语义随状态更新 |
| 列表结构 | **PASS**。`<ol aria-label="复原格位列表">`，`<li>` 语义正确（`draggable="true"` 无 role 不影响，按钮是等价操作路径） |
| 边界按钮 | **PASS**。首格 ↑ / 末格 ↓ 同时 `disabled` + `aria-disabled="true"` |

### 4.3 提示区（`#hints`）—— **FAIL**

```html
<div class="hints" id="hints" aria-label="已揭开的提示">…</div>
```

- `aria-label` 用在**无 role 的普通 `div`** 上 → axe `aria-prohibited-attr`（**serious**）。该标签被浏览器丢弃，读屏用户不会听到"已揭开的提示"这个区域名。
- `role` 为 `null`，`aria-live` 为 `null` → **提示正文本身不是 live region**。
- 点「查看提示」后，进入 live region 的只有 `#message` 里那句通用话术 `提示只是帮你推进，不会自动完成排列。`；真正的提示内容 `档案员注 01 ／ 03 先把红票和蓝票当成一组不可分开的相邻票。` 写在 `#hints` 里，**不会被主动播报**。读屏用户必须自己用虚拟光标往下找才能读到。
- 提示按钮文本会更新为 `查看提示（1/3）`，这一点是好的。

### 4.4 实时区域 —— **部分 PASS**

| 检查项 | 结果 | 证据 |
|---|---|---|
| `#message` 是 `role=status` + `aria-live=polite` | **PASS** | 属性实测为 `role="status"`、`aria-live="polite"`；隐藏时 `display:none`（内容不入无障碍树，正确） |
| 错误提示"只播报一次、不是每次按键" | **PASS** | 一次错误提交在 `#message` 上共触发 **6 次**变更（`attributes` ×2 + `childList` ×4，来自一次性 `setMessage()` 的 `replaceChildren` + 4 个 append），**全部集中在点击瞬间，不存在逐键触发**。重复提交同样内容会整体重新渲染并再次播报（第二次同样 6 次），符合"重新提交应重新提示"的预期 |
| 播报是否会被拆碎 | **风险（moderate）** | `setMessage()` 先 `replaceChildren()` 再逐个 append 4 个节点（strong + p + ul + 2×li）。部分读屏器会逐节点播报，产生碎片化朗读。axe 测不出，实测变更序列见下表 |
| `#toast` 也是 live | **是**，`role="status"` + `aria-live="polite"` | 与 `#message` 同级 |
| 是否双重播报 | **本流程未发生**，但有隐患 | 选中格位时 toast 播报 `已选中「蓝票」，再点一个格位即可交换`，同时状态栏文字变为 `已选中「蓝票」，请点目标格位`——但 `#status-text` **没有** `aria-live`，所以只播一次。若日后给状态栏加 live 就会立刻双重播报 |
| toast 隐藏后是否残留 | **FAIL（serious）** | 2.6 s 后 `data-show="false"`、`opacity: 0`，但 `display` 仍为 `block`，`checkVisibility() = true`，**文本仍留在无障碍树中**。读屏用户浏览页面时会读到一条早已过期的"已选中「蓝票」…" |

实测的 live region 变更记录（一次错误提交，`#message` 上共 6 次）：

```
message       attributes ×2  →  message childList ×4        ← 会被播报
case-root     attributes ×5 / childList ×1                  ← aria-live="off"，不播报（正确）
```

页面共有 4 个 live 声明：`#progress-badge`(aria-live=polite)、`#case-root`(aria-live=off)、`#message`(status)、`#toast`(status)。`#case-root` 显式设 `off` 是好设计——整块重渲染不会淹没播报。

### 4.5 颜色对比度 —— **PASS（全部通过）**

axe 因渐变背景无法判定（60–78 节点/页 incomplete），改用**真实像素采样**：把文字色设为 `transparent` 后截取元素中段，取中位像素作为实际背景色，再按 WCAG 相对亮度公式计算。

| 采样点 | 文字色 | 实测背景 | 对比度 | 要求 | 结论 |
|---|---|---|---|---|---|
| body 正文（`.desk-head__sub`）on `--ink` | `#b9c8c5` | `#091922` | **10.33:1** | 4.5 | PASS |
| `.ev-card` 正文 `#20180d` on paper | `#20180d` | `#e6d6b3` | **12.22:1** | 4.5 | PASS |
| `.ev-card__title` | `#20180d` | `#e8d8b5` | **12.46:1** | 3.0（16px/700） | PASS |
| `.ev-card__id` 徽标 | `#6d5528` | `#ebdbbb` | **5.16:1** | 4.5 | PASS |
| `.pill` brass on panel | `#dfb978` | `#091a24` | **9.58:1** | 4.5 | PASS |
| `.pill--mist` | `#9eb7b4` | `#081922` | **8.43:1** | 4.5 | PASS |
| `.slot__label`（`--mist`）on 格位底 | `#9eb7b4` | `#173542` | **6.09:1** | 4.5 | PASS |
| `.slot__item` | `#f2ece0` | `#163340` | **11.29:1** | 3.0（16.3px/700） | PASS |
| `.slot__index` brass | `#dfb978` | `#122730` | **8.35:1** | 4.5 | PASS |
| `.board__goal` | `#d6c49f` | `#1f3339` | **7.70:1** | 4.5 | PASS |
| `.status-bar` | `#9eb7b4` | `#0a1b25` | **8.26:1** | 4.5 | PASS |
| `.message--bad` 文字 | `#ffd8cf` | `#212931` | **11.20:1** | 4.5 | PASS |
| `.message--bad strong` | `#ffd8cf` | `#212b34` | **10.94:1** | 4.5 | PASS |
| `.message--bad li` | `#ffd8cf` | `#212930` | **11.21:1** | 4.5 | PASS |
| `.message--info` | `#e7d7b7` | `#202d2e` | **10.03:1** | 4.5 | PASS |
| `.hint-card` | `#d6c49f` | `#162428` | **9.31:1** | 4.5 | PASS |
| **选中态** `.slot__label` | `#9eb7b4` | `#273f3a` | **5.32:1** | 4.5 | PASS |
| 选中态 `.slot__item` | `#f2ece0` | `#253d39` | **9.89:1** | 3.0 | PASS |
| `.btn--primary`（渐变底） | `#231906` | `#d1a965` | **7.89:1**（区间 6.74–9.08） | 4.5 | PASS |
| `.btn--ghost` | `#b9c8c5` | `#05151d` | **10.72:1** | 4.5 | PASS |
| `.btn--danger` | `#ffb0a2` | `#0b1e27` | **9.75:1** | 4.5 | PASS |
| `.icon-btn` | `#b9c8c5` | `#16313e` | **7.86:1** | 4.5 | PASS |
| `#toast` | `#f2ece0` | `#14333f` | **11.33:1** | 4.5 | PASS |
| 当前导航项（brass on 半透明底） | `#dfb978` | `#232b29` | **7.83:1** | 4.5 | PASS |
| `#clear-progress`（小号危险按钮） | `#ffb0a2` | `#14222a` | **9.28:1** | 4.5 | PASS |
| 面包屑 `--mist` | `#9eb7b4` | `#05151d` | **8.74:1** | 4.5 | PASS |
| **对话框标题** `#confirm-title` | `#f2ece0` | `#173848` | **10.53:1** | 3.0（20.8px/700） | PASS |
| **对话框正文** `#confirm-body` | `#b9c8c5` | `#153543` | **7.48:1** | 4.5 | PASS |
| 对话框「取消」 | `#b9c8c5` | `#143240` | **7.78:1** | 4.5 | PASS |
| 对话框「确认重置」 | `#ffb0a2` | `#13303e` | **7.88:1** | 4.5 | PASS |

纯 token 理论值同向复核：`--text-dim`/`--ink` 10.43、`--text`/`--ink` 15.35、`#20180d`/`#e7d7b7` 12.36、`--brass`/`--panel` 7.96、`--mist`/`--panel` 6.93、`--brass`/`--ink` 9.76。

**最低值 5.16:1**（`.ev-card__id` 小徽标），仍高于 4.5:1。共 **32 组配对**（桌面 23 + 按钮专项 4 + 对话框 4 + toast 1），**全部 ≥ 4.5:1**。配色方案无问题。

> **一处采样返工，如实记录**：第一轮批处理里 `.btn--primary` 报出 `1.07:1`，原因是该按钮当时位于视口外，裁剪区落在了页面背景上而非按钮渐变底，属**测量伪影**。用 `scrollIntoView` + 元素内缩中段采样重测，实际为 **7.89:1**（区间 6.74–9.08），见 `contrast-buttons.json`。`contrast-motion-reflow.json` 中保留的 `btn_primary_label: 1.07` 是未修正的原始值，**以 `contrast-buttons.json` 的 7.89 为准**。
>
> 表中"实测背景"是裁掉文字后取元素中段的中位像素；5% 分位暗值（如 `.ev-card__id` 的 2.82）来自边框描边像素，不是文字衬底，不作为判定依据。

### 4.6 减少动态效果 —— **PASS**

`reduced_motion="reduce"` 下实测：

| 对象 | animation-duration | transition-duration |
|---|---|---|
| `#message`（`msgIn` 动画） | `1e-06s` | `1e-06s` |
| `#view-case`（`viewIn` 动画） | `1e-06s` | `1e-06s` |
| `.slot` | none | `1e-06s` |
| `.icon-btn` | none | `1e-06s` |
| `.ev-card__chev` | none | `1e-06s` |
| `#toast` | none | `1e-06s` |

- `matchMedia('(prefers-reduced-motion: reduce)').matches = true`
- `--dur` 解析为 `0ms`；`html { scroll-behavior: auto }`
- 连续 4 帧采样 `#message`：`opacity: 1 / 1 / 1 / 1`、`transform: none / none / none / none`——**第一帧即终态，无过渡**
- 印章 `stampIn` 动画包裹在 `@media (prefers-reduced-motion: no-preference)` 内，reduce 下根本不注册

### 4.7 触控目标尺寸（390×844）—— **部分 FAIL**

页面无横向滚动（`clientWidth 390 = scrollWidth 390`）。逐个测量 26 个可见交互元素：

**≥44×44（PASS，22 个）**：skip-link 139×50、brand 227×46、`#nav-toggle` 44×44、3 张证物摘要 340×47、12 个格位按钮全为 44×44、`#btn-submit` 308×44、`#btn-undo` 150×44、`#btn-hint` 150×44、`#btn-reset` 308×44。

**<44×44（4 个）**：

| 元素 | 位置 | 实测 |
|---|---|---|
| 面包屑「档案柜」 | `.desk-crumbs a` | 37.8 × 21.4 |
| 「档案柜」 | footer | 37.8 × 19 |
| 「玩法说明」 | footer | 50.3 × 19 |
| 「关于与隐私」 | footer | 62.9 × 19 |

`/manual` 页单独统计 8 个可见交互元素，其中 **5 个** <44×44：上述 4 个（面包屑 + footer 三链接，该页同样存在）再加 `#clear-progress`（`.btn--sm`）126.6 × 38。

**WCAG 2.2 AA 2.5.8（24×24）判定**：footer 三链接**中心间距 25.4 px**（实测中心 y = 1724.2 / 1749.6 / 1775.0）> 24 px，满足"间距例外"，**按 AA 判 PASS**；面包屑「档案柜」37.8×21.4 高度 21.4 < 24，但其**最近的其他交互目标中心距 121.1 px**（远大于 24 px），满足同一例外，**按 AA 亦 PASS**。
**但**：站点 `/manual` 页白纸黑字写着「交互目标按 44 px 设计」，这 5 类元素实测为 19–38 px，**该宣称不成立**（2.5.5 AAA 级别 FAIL）。这是文档准确性问题，我按 moderate 记一条。

### 4.8 缩放／重排 —— **PASS**

| 视口 | 页面 | clientWidth | scrollWidth | 横向滚动 | 越界元素 | 被裁文本 |
|---|---|---|---|---|---|---|
| 320×900 | `#/case/NA-001` | 320 | 320 | 否 | 0 | 0 |
| 320×900 | `#/manual` | 320 | 320 | 否 | 0 | 0 |
| 320×900 | `#/` | 320 | 320 | 否 | 0 | 0 |
| 720×450（≈200%） | `#/case/NA-001` | 720 | 720 | 否 | 0 | 0 |
| 720×450（≈200%） | `#/manual` | 720 | 720 | 否 | 0 | 0 |
| 720×450（≈200%） | `#/` | 720 | 720 | 否 | 0 | 0 |

1.4.10 Reflow（320 CSS px 无双向滚动）与 1.4.4 Resize Text 均通过。截图见 `reflow-320px-*.png`、`reflow-zoom200_720px-*.png`。

### 4.9 重置对话框 —— 结构 PASS，描述 FAIL

实测：`open=true`、`matches(':modal')=true`、打开后焦点自动落在「确认重置」按钮、`Escape` 可关闭、关闭后焦点回到发起按钮 `#btn-reset`、Tab 循环被限制在对话框内（实测 `canFocusOutside=false`）、点遮罩可关闭、尺寸 440×188。

| 检查项 | 结果 |
|---|---|
| 模态语义与被困焦点 | **PASS**（`:modal`，焦点不能跑到背后页面） |
| `aria-labelledby` 指向标题 | **PASS**（`confirm-title` → 「重置此案？」） |
| **`aria-describedby` 关联后果说明** | **FAIL**，实测 `null`。读屏器不会播报「重置会清空这份档案的本地排列进度。确定吗？」——而这正是不可撤销操作的后果说明 |
| 初始焦点 | **PASS**，落在 `[data-confirm="ok"]` |
| Esc / 取消 / 遮罩关闭 | **PASS**（三种路径均可用），取消后焦点回 `#btn-reset` |
| 4 个节点的对比度 | **PASS**，7.48–10.53:1 |

### 4.10 其他通过的检查

| 检查项 | 结果 |
|---|---|
| `lang="zh-CN"` | **PASS** |
| 重复 `id` | **PASS**，5 个路由（`#/`、`#/cabinet`、`#/manual`、`#/about`、`#/case/NA-001`）各实测 0 处 |
| 图片缺 `alt` | **PASS**，5 个路由实测 0 处缺 `alt` |
| 装饰图 `alt=""` | **PASS**。首页 4 张（品牌徽标 + 3 张案件缩略图）、其余路由 10 张（DOM 中保留全部 6 案卡片，仅当前视图可见）——全部 `alt=""`，无冗余朗读。需注意案件卡图片的标题在紧邻的 `<h3>` 中重复给出，`alt=""` 是正确选择 |
| iframe | 无 |
| 按钮/链接无可访问名 | **PASS**，5 个路由各 0 处 |
| 正数 `tabindex` | **PASS**，5 个路由各 0 处（无 tabindex 劫持） |
| `aria-hidden` 内藏可聚焦元素 | **PASS**，0 处 |
| 地标 | header / nav[aria-label=主导航] / main / footer 齐备 |
| 跳转链接焦点可见性 | **PASS**：Tab 到 `.skip-link` 后 300 ms 内 `top` 由 −144 px 过渡到 +16 px，可完整看到 |

---

## 5. 优先级修复清单

> 每条给出：严重度 → 问题 → 精确元素/选择器 → 建议修法 → 最可能涉及的文件

### [critical] 1. 跳转链接把用户带离当前页面

- **问题**：`<a class="skip-link" href="#main">` 触发 `hashchange`，而路由把 `#main` 解析成非 `#/` 开头的非法路由 → 回退 `{view:'home'}`。实测在 `#/case/NA-001`、`#/cabinet`、`#/manual`、`#/about` 四个页面按 Enter 后：`location.hash` 变为 `#main`、激活视图变为 `view-home`。用户第一个 Tab 按下去就被踢回首页，调查桌、档案柜全部卸载。这同时使 2.4.1 (A) "绕过区块" 完全失效。
- **元素**：`site/index.html:26` `<a class="skip-link" href="#main">跳到主要内容</a>`；`site/app.mjs:252-261` `parseHash()` 的兜底分支。
- **修法**：二选一。
  - 推荐：skip-link 改成 `<a class="skip-link" href="#main" data-skip>`，在 `bindGlobal()` 里 `preventDefault()` 后直接 `$('#main').focus()` + `scrollIntoView()`，完全不改 `location.hash`；
  - 或：`parseHash()` 中把 `main`（及任何不以 `/` 开头的片段）识别为"页内锚点"，返回 `null` 并让 `router()` 直接 return，不做视图切换。
- **文件**：`site/index.html`、`site/app.mjs`

### [critical] 2. 选中格位后焦点掉到 `<body>`，且文档承诺的 Esc 取消选中随之失效

- **问题**：`onPick()` 两个分支都调用无参 `drawSlots()`，`replaceChildren()` 把被点的按钮连同焦点一起销毁。实测 pick 后 `activeElement === BODY`、`aria-pressed="true"` 已生效但 `focusVisible=false`。因为 `Esc` 监听器绑在 `.slot` 的 keydown 上，焦点在 `<body>` 时事件永远进不来——`/manual` 页"键盘操作"表格承诺的 `Esc 取消当前选中` 在真实键盘路径下**不可用**（实测选中后按 Esc，`selected` 仍为 1）。
- **元素**：`site/app.mjs:788`、`:796`（`onPick` 内的 `drawSlots();`）；`:662`（`host.replaceChildren()`）；`:1059-1075`（`.slot` 上的 keydown/Escape）。
- **修法**：
  1. `onPick(i)` 改为 `drawSlots({ index: i, act: 'pick' })`，复用 `move()` 已有的焦点恢复逻辑（`:714-721`）；
  2. 把 `Escape` 监听从 `.slot` 提升到 `document` 或 `#case-root`（`$('#case-root').addEventListener('keydown', …)`），判断 `state.selected != null` 即取消，使焦点不在格位内也能生效；
  3. 取消选中后把焦点显式送回该格的 pick 按钮。
- **文件**：`site/app.mjs`

### [critical] 3. 结案页：焦点丢失 + h1 消失 + 悬空 `aria-labelledby`

- **问题**：`submit()` 成功后 `setTimeout(renderVerdict, 420)`，`renderVerdict()` 用 `root.replaceChildren(box)` 替换整个 `#case-root`，焦点随之落到 `<body>`；随后 `$('#verdict-title')?.focus?.()` 是**空操作**，因为目标元素是 `<h2>` 且无 `tabindex="-1"`（实测 `tabIndex = -1` 表示不可编程聚焦）。同时 desk 的 `<h1 id="case-title">` 被删除，结案页进入**无 h1** 状态（axe `page-has-heading-one`），而外层 `<section id="view-case" aria-labelledby="case-title">` 仍指向这个已不存在的 ID（axe `aria-valid-attr-value` critical）。实测 14 次采样（2.8 s 内）焦点始终为 `BODY`。
- **元素**：`site/app.mjs:921`（`section.verdict` 的 `labelledby`）、`:924`（`h2#verdict-title`）、`:1003`（`root.replaceChildren(box)`）、`:1005`（空操作 focus）；`site/index.html:130`（`#view-case` 的 `aria-labelledby="case-title"`）。
- **修法**：
  1. 把 `#verdict-title` 改为 `<h1>`（`el('h1', { id: 'verdict-title', tabindex: '-1', … })`），既补回 h1 又让 `.focus()` 真正生效；
  2. `#view-case` 的 `aria-labelledby` 改为动态设置：desk 态指向 `case-title`，verdict 态指向 `verdict-title`；或在 `renderVerdict()` 里 `section.setAttribute('aria-labelledby','verdict-title')`；
  3. 渲染完成后 `$('#verdict-title').focus()` 并把焦点环保留（`:focus-visible` 已全局定义）。
- **文件**：`site/app.mjs`、`site/index.html`

### [serious] 4. 提示内容对读屏不可达

- **问题**：`<div class="hints" id="hints" aria-label="已揭开的提示">` 是**无 role 的普通 div**，`aria-label` 被丢弃（axe `aria-prohibited-attr` serious，5 个页面状态各 1 node）。且该容器无 `aria-live`，点「查看提示」后真正进入 live region 的只有通用话术「提示只是帮你推进，不会自动完成排列。」，提示正文（`档案员注 01 ／ 03 先把红票和蓝票当成一组不可分开的相邻票。`）不会被播报。
- **元素**：`site/app.mjs:642`（`el('div', { class:'hints', id:'hints', aria:{ label:'已揭开的提示' } })`）。
- **修法**：改为 `el('section', { class:'hints', id:'hints', aria:{ label:'已揭开的提示', live:'polite' } })`（`section` + `aria-label` 合法，等价于 `role="region"`），并让 `revealHint()` 只播报新增那一条（把 `#hints` 设为 polite，或复制一条到 `#message`）。若担心整块重渲染重复播报，可给最新 `.hint-card` 加 `role="status"`。
- **文件**：`site/app.mjs`

### [serious] 5. 从档案柜进入案件，焦点停在 `<body>`

- **问题**：`router()` 在 `route.view === 'case'` 分支里 `await openCase(...)` 后 `return`（`app.mjs:328-329`），**早于** 末尾的 `$('#main')?.focus({preventScroll:true})`（`:343`）。实测从档案柜点「立即调查」进入 `#/case/NA-001` 后 `activeElement === BODY`，键盘/读屏用户丢失位置，必须从头 Tab 过整条导航。
- **元素**：`site/app.mjs:324-330`。
- **修法**：在 case 分支 `return` 之前补 `$('#main')?.focus({ preventScroll: true });`（或 `openCase` 完成后聚焦 `#case-title` 并给其 `tabindex="-1"`）。
- **文件**：`site/app.mjs`

### [serious] 6. toast 隐藏后仍留在无障碍树中

- **问题**：`#toast` 是 `role="status"` + `aria-live="polite"`。2.6 s 后只把 `data-show` 设为 `false`，CSS 只改 `opacity: 0`（`site/styles/app.css:887-903`），`display` 仍为 `block`。实测隐藏后 `checkVisibility() = true`、`innerText` 仍是「已选中「蓝票」，再点一个格位即可交换」。读屏用户浏览页面时会读到这条早已过期的状态，且每次新消息前旧文本一直可被虚拟光标命中。
- **元素**：`.toast`（`site/index.html:259`）、`site/styles/app.css:887-903`、`site/app.mjs:205-212` `toast()`。
- **修法**：`.toast[data-show="false"] { visibility: hidden; }`（配合 `opacity` 过渡仍可动画），或在 `toast()` 的 `setTimeout` 里同时 `t.textContent = ''`。推荐前者，避免空 live region 反复被读。
- **文件**：`site/styles/app.css`、`site/app.mjs`

### [moderate] 7. 标题层级跳级（全站 10 处）

- **问题**：`<footer>` 三个栏目标题用 `<h4>`，但其前一个标题是 `<h2>` 或 `<h3>`，跳级；首页 `.pitch__card` 用 `<h3>` 紧跟 `<h1>`，跳过 `<h2>`；档案柜 `.act__title` 用 `<h3>` 紧跟 `<h1>`。axe `heading-order` 在 10 个页面状态各报 1 node。
- **元素**：`site/index.html:225` 起 `<h4>文献</h4>` / `<h4>技术</h4>` / `<h4>声明</h4>`；`site/index.html:76/81/86` `.pitch__card > h3`；`site/app.mjs` `renderActBlocks` 的 `h3.act__title`。
- **修法**：footer 三处降为 `<h2 class="site-footer__h">` 并加 `visually-hidden` 样式（或改 `<p>` + 视觉样式，因为它们并非真正的文档层级）；首页 pitch 三卡改 `<h2>`；档案柜幕标题改 `<h2>` 并让卡片标题降为 `<h3>`。
- **文件**：`site/index.html`、`site/app.mjs`

### [moderate] 8. `<dialog>` 缺 `aria-describedby`

- **问题**：`<dialog id="confirm-dialog" aria-labelledby="confirm-title">` 有标题关联，但正文 `<p id="confirm-body">重置会清空这份档案的本地排列进度。确定吗？</p>` **没有**被关联（`aria-describedby` 实测为 `null`）。读屏器只会读出「重置此案？ dialog」和两个按钮，不会读出"会清空什么"这一关键后果说明——而这个对话框是不可撤销操作的最后一道确认。
- **元素**：`site/index.html:261-268`。
- **修法**：`<dialog ... aria-labelledby="confirm-title" aria-describedby="confirm-body">`。
- **文件**：`site/index.html`

### [moderate] 9. 触控目标小于站点自己宣称的 44 px

- **问题**：`/manual` 页写着「交互目标按 44 px 设计」，实测 5 处不符：面包屑「档案柜」37.8×21.4、footer 三链接 37.8/50.3/62.9 × 19、`#clear-progress` 126.6×38。WCAG 2.2 AA 2.5.8（24×24）因中心间距 25.4 px 可适用"间距例外"而通过，但 2.5.5 AAA 与站点自身承诺不达标。
- **元素**：`.desk-crumbs a`、`.site-footer a`、`.btn--sm`。
- **修法**：给这三类加 `min-height: 44px; display:inline-flex; align-items:center;`（footer 可加 `padding-block: 12px; margin-block: -12px` 保持视觉节奏）；或把 `/manual` 的文案改成「主要操作目标按 44 px 设计」。
- **文件**：`site/styles/app.css`、`site/index.html`

### [minor] 10. 移动端菜单 Esc 不关闭

- **问题**：390 px 下打开 `#nav-toggle` 后按 `Esc`，实测 `navOpen` 仍为 `"true"`、`aria-expanded` 仍为 `"true"`、`display` 仍为 `flex`。菜单内链接可 Tab 到达（`after_tab → inNav: true`），所以不是键盘陷阱，但 Esc 关闭是平台惯例。
- **元素**：`site/app.mjs:1144-1151`（`nav-toggle` 点击处理），`site/app.mjs:1059` 附近已有的 keydown 监听未覆盖菜单。
- **修法**：在 `bindGlobal()` 加 `document.addEventListener('keydown', e => { if (e.key === 'Escape' && nav.dataset.open === 'true') { nav.dataset.open='false'; toggle.setAttribute('aria-expanded','false'); toggle.focus(); } })`。
- **文件**：`site/app.mjs`

### [minor] 11. 状态栏文字变化不播报

- **问题**：`#status-text`（`准备核对` / `已调整排列，等待核对` / `已选中「X」，请点目标格位` / `存在 N 处与证据不符的关系`）无 `role` 无 `aria-live`，读屏用户感知不到排列已被修改。目前靠 `#toast` 兜底，但 `#toast` 只覆盖"选中"一种，移动/交换/撤销没有等价播报。
- **元素**：`site/app.mjs:634-637`。
- **修法**：`<span id="status-text" role="status" aria-live="polite">`。**注意**：加之前必须先解决 toast 与状态栏的双重播报——建议只在 `#toast` 不存在显示内容时才让状态栏参与播报，或把二者合并为单一 live region。
- **文件**：`site/app.mjs`

---

## 6. 我无法验证的部分（诚实边界）

1. **真实读屏器**：本环境无法运行 NVDA / JAWS / VoiceOver / TalkBack。所有语义结论来自 DOM/ARIA 静态分析与 `MutationObserver` 变更序列，**"是否真的播报、播报几次、语速与打断行为"未经真人验证**。§4.4 中"碎片化播报风险"尤其需要 NVDA 实测确认。
2. **浏览器/读屏组合矩阵**：仅测 Chromium。Firefox + NVDA、Safari + VoiceOver、iOS VoiceOver 对 `<dialog>`、`aria-describedby`、live region 的处理差异未覆盖。
3. **语音控制 / 眼动 / 开关控制**：未测。2.5.3 Label in Name 已通过静态检查（所有 `aria-label` 均以可见文本开头或完全一致），但未做真实语音控制验证。
4. **高对比模式**：`@media (forced-colors: active)` 有 token 映射（`--brass: Highlight` 等），但我只在 CSS 层确认规则存在，**未在 Windows 高对比主题下实际渲染验证**。
5. **200% 缩放**：用 720×450 视口等效模拟，非真实浏览器 zoom。真实 zoom 下可能出现不同的亚像素/字体回退行为。
6. **触摸手势**：只测量了尺寸与间距，未做真实手指点击的误触率测试（44 px 只是经验阈值，非实测命中率）。
7. **性能对可访问性的影响**：未测首屏加载、字体回退（`Noto Sans SC` / `Songti SC` 在无该字体的系统上会回退到 `Microsoft YaHei` / `SimSun`），字体回退可能改变文字尺寸进而影响对比度与断行。
8. **动态内容的完整时序**：`submit()` 成功后有 420 ms `setTimeout` 才渲染结案页。我只在 200 ms 间隔采样，未做逐帧追踪；若读屏器在该窗口期内有其他播报，可能与结案播报竞争。
9. **`#progress-badge`（`aria-live="polite"`）**：仅确认属性存在，未在"归档数从 0/6 变为 1/6"时验证播报（该变化只在档案柜页发生，且需先解一案）。
10. **CMS/构建差异**：本次针对线上 `BUILD=41fc9520…` 实测；本地 `site/app.mjs` 与该构建的差异仅为 `BUILD` 常量（已 diff 确认），但若后续重新构建发布，本报告结论需重跑。

---

## 7. 复现方式

```bash
cd work/qa/a11y
python run_axe.py            # 12 个状态 × axe-core 4.10.2 → axe-<page>.json
python manual_checks.py      # 焦点序/焦点保持/语义/live/dialog/触控 → manual-raw.json
python contrast_motion_reflow.py  # 像素级对比 + reduce + 重排 → contrast-motion-reflow.json
python contrast_buttons.py   # 渐变按钮专项重测 → contrast-buttons.json
python dialog_detail.py      # 对话框模态覆盖范围 + 对比 → dialog-detail.json
python followups.py          # 标题/live 细节/键盘通关 → followups.json
python headings_tokens.py    # 标题序列 + token 对比 → headings-tokens-geometry.json
python final_checks.py       # skip-link/Esc/移动菜单/小目标 → final-checks.json
python last_round.py         # 方向键/toast 残留/几何 → last-round.json
python undo_tabdist.py       # undo 可达性/Tab 距离 → undo-tabdist.json
python verdict_focus.py      # 结案焦点交接 → verdict-focus.json
python semantics_global.py   # 全局语义 → semantics-global.json
python skip_link_routing.py  # skip-link 路由冲突 → skip-link-routing.json
```

`axe.min.js`（553,290 bytes）已缓存在本目录，重复运行无需联网。

### 产物清单

| 文件 | 内容 |
|---|---|
| `A11Y_AUDIT.md` | 本报告 |
| `SUMMARY.txt` | 10 行摘要 |
| `axe-<page>.json` × 12 | axe 原始结果（violations / incomplete / passes / inapplicable） |
| `axe-summary.json` | 12 状态违规索引 |
| `manual-raw.json` | 焦点序、焦点保持、语义、live、dialog、触控原始数据 |
| `contrast-motion-reflow.json` | 像素对比度、reduce、重排 |
| `contrast-buttons.json` | 渐变按钮专项采样（`btn--primary` 修正值 7.89:1 的出处） |
| `dialog-detail.json` | 对话框模态范围、axe 覆盖节点数、4 节点对比度 |
| `followups.json` / `last-round.json` / `undo-tabdist.json` / `verdict-focus.json` / `final-checks.json` / `semantics-global.json` / `skip-link-routing.json` / `headings-tokens-geometry.json` | 各专项原始数据 |
| `reflow-*.png` | 320 px 与 200% 重排截图 |
| `_live/` | 审计时抓取的线上产物快照（用于核对结论对应版本） |
