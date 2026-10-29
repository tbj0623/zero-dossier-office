# Lighthouse 审计 · 第零证物局

工具：**Lighthouse 12.8.2**（Google 官方，`npx lighthouse`）
浏览器：Microsoft Edge（Lighthouse 通过 `CHROME_PATH` 驱动 headless Edge）
被测：线上站点 <https://tbj0623.github.io/zero-dossier-office/>
时间：2026-10-30（Asia/Shanghai）

原始数据：`live-home.json`（修复前）、`live-home-after.json`（第一轮修复后）、
`live-home-final.report.json` / `.report.html`（最终）、`live-desk.report.json`（核心玩法页）

---

## 结论

| 页面 | 性能 | 无障碍 | 最佳实践 | SEO |
|---|---|---|---|---|
| 首页（修复前） | **71** | 100 | 100 | 92 |
| 首页（修复后） | **97** | **100** | **100** | **100** |
| 案件调查桌 NA-006（最重的案子） | **96** | **100** | **100** | **100** |

四项全部 ≥ 96，无障碍与最佳实践满分。

### 核心指标（首页，移动端模拟）

| 指标 | 修复前 | 修复后 | 良好线 |
|---|---|---|---|
| First Contentful Paint | 1.2 s | 1.3 s | ≤ 1.8 s |
| Largest Contentful Paint | 2.2 s | **2.0 s** | ≤ 2.5 s |
| Total Blocking Time | 300 ms | **0 ms** | ≤ 200 ms |
| **Cumulative Layout Shift** | **0.442** | **0** | ≤ 0.1 |
| Speed Index | 3.2 s | 4.1 s | ≤ 3.4 s |

Speed Index 略高于良好线是本轮唯一的未达标项，原因见下文「权衡」。

---

## 修复了什么

### 1. CLS 0.442 → 0（最重要）

**现象**：Lighthouse 报 2 次布局位移，累计 0.442。良好线是 0.1，这是严重超标。

**根因**：三张样式表用 `<link rel="preload" onload="this.rel='stylesheet'">` 异步加载。
异步 CSS 换来了"不阻塞首屏"，代价是**样式晚到、整页重排**——这正是 CLS 的经典成因。
当时只内联了 4.2 KB 关键 CSS，而外部 CSS 有 44.6 KB，覆盖范围差得太远。

**修复**：`tools/build.mjs` 新增 4c 步，把 tokens / base / app 三张表**全部内联**进
`dist/index.html`。只改 dist 副本，`site/` 源文件保持外链以便开发时热改。
内联数量不足 3 张会直接构建失败，不会静默丢样式。

**效果**：CLS = 0；TBT 300 ms → 0 ms；LCP 2.2 s → 2.0 s。

### 2. 内联引入的回归：`url(../assets/)` 基准失效（已修）

内联后 Lighthouse 的 `errors-in-console` 抓到 404：
`https://tbj0623.github.io/assets/harbor-archive-background.webp`（**少了 /zero-dossier-office/ 前缀**）。

原因：`app.css` 里写的是 `url("../assets/harbor-archive-background.webp")`，
作为外部样式表时基准是 `/styles/app.css`，解析正确；一旦内联进 `index.html`，
基准变成文档本身，`../` 就跳出了项目站点根目录 → 404，首屏背景丢失。

修复：内联时把 `url(../assets/` 重写为 `url(./assets/`。
这是我自己引入又自己抓到的回归，记录在此以免重犯。

### 3. SEO 92 → 100

| 问题 | 说明 | 修复 |
|---|---|---|
| `rel=canonical` 无效 | 原为 `href="./"`，不是绝对 URL | 改为绝对地址 |
| `og:image` 是相对路径 | Open Graph 要求绝对 URL，否则**分享卡片取不到图** | 改为绝对地址 |
| 缺字段 | 无 `og:url` / `og:site_name` / 图片宽高 / twitter 标题描述图 | 全部补齐 |

`og:image` 这一条不是"刷分"，是**真 bug**：相对路径在任何社交平台都不能用。

---

## 权衡：为什么 Speed Index 从 3.2 s 变成 4.1 s

内联把 HTML 从 19.5 KB 撑到 61.4 KB（gzip 后仍很小）。浏览器要多解析约 45 KB 的
内联样式才能完成首帧，所以"视觉完成"这个累计指标变慢了一点。

这是个明确的取舍：
- 异步 CSS：FCP 略快，但 **CLS 0.442**（用户会看到整页跳动）
- 内联 CSS：FCP 慢 0.1 s，但 **CLS 0**（页面一次成型，不再跳动）

对一个**以阅读文字为主**的推理游戏，页面跳动比首帧晚 0.1 秒难受得多。
而且 TBT 也从 300 ms 降到 0 ms，交互响应性明显更好。综合分 71 → 97。

---

## 这个审计证明了什么、没证明什么

**证明了**：Google 官方工具在真实线上 URL 上，四项分类均 ≥ 96；
移动端模拟下 CLS 为 0、TBT 为 0。

**没证明**：
- Lighthouse 的性能分数是**实验室合成指标**（固定 CPU/网络节流模型），
  不等于真实用户体感，也不是 Core Web Vitals 的现场数据（本作没有真实流量，
  也不可能采集真实用户数据——这与隐私承诺一致）。
- 只测了首页与一个案件页，不是全部路由。
- 未测低速 3G / 弱设备等极端条件。
- 无障碍 100 分**不等于** WCAG 合规：Lighthouse 只覆盖可自动检测的子集，
  且本项目**未做任何屏幕阅读器实机测试**。全项目不声明任何 WCAG 等级。

---

## 复现方式

```bash
export CHROME_PATH="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
npx --yes lighthouse@12 https://tbj0623.github.io/zero-dossier-office/ \
  --output=json --output=html --output-path=work/qa/lighthouse/live-final \
  --only-categories=performance,accessibility,best-practices,seo \
  --chrome-flags="--headless=new --no-sandbox" --quiet
```

`live-final.report.html` 可读性更好，含每项扣分的具体元素。
