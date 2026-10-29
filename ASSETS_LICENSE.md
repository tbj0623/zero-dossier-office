# 资产与叙事许可 · ASSETS LICENSE

本项目把「程序」与「创作材料」分开授权。**代码用 MIT，创作材料用 CC BY-NC-SA 4.0。**
这不是法律意见；如需商业授权请另行联系。

---

## 1. 程序代码 —— MIT

| 范围 | 文件 |
|---|---|
| 求解核心 | `engine/solver.mjs`（构建后复制到 `site/engine/`） |
| 校验工具 | `engine/verify_cases.py` |
| 站点逻辑 | `site/app.mjs` |
| 样式 | `site/styles/*.css` |
| 构建与工具 | `tools/*.mjs` |
| 测试 | `tests/**` |

条款见仓库根目录 `LICENSE`（MIT）。

## 2. 叙事与案件数据 —— CC BY-NC-SA 4.0

| 范围 | 文件 |
|---|---|
| 案件正文、证物文本、提示、复盘、后记 | `cases/**/*.json`、构建后的 `site/cases/*.json` |
| 世界观与剧情文档 | `docs/STORY_BIBLE.md`、`work/lore/**` |

你可以自由阅读、分享、改编，**但必须署名、不得用于商业目的、衍生作品须以相同条款共享**。

许可全文：<https://creativecommons.org/licenses/by-nc-sa/4.0/>

## 3. 视觉资产 —— CC BY-NC-SA 4.0

| 文件 | 用途 | 说明 |
|---|---|---|
| `site/assets/harbor-archive-background.webp` | 首页 Hero 背景 | 架空「雾港」概念插画 |
| `site/assets/archive-desk-background.webp` | 局内档案台背景 | 同上 |
| `site/assets/evidence-case-001..003.webp` | 001–003 案氛围插画 | 非真实关卡截图 |
| `site/assets/NA-004..006-episode-card.webp` | 004–006 案封面 | 非真实关卡截图 |
| `site/assets/archive-emblem.svg` / `-512.png` | Logo / favicon | 半圈「0」章图腾 |
| `site/assets/github-social-preview.png` | GitHub 社交预览 | 需在仓库 Settings 手动设置才生效 |
| `site/assets/readme-hero.png` | README 横幅 | **不是**游戏截图 |

### 3.1 制作声明

- 以上图片为**本项目的原创概念插画**，用于本项目世界观「雾港」，不描绘真实地点、真实机构或现存个人。
- 图片是**氛围层**：任何解谜所需信息都以可选中、可复制的 HTML 文本呈现，不存在"必须看清图片里的颜色/暗纹才能解题"的设计。
- 本项目不声称对这些图片拥有超出适用法律范围的独占权利，也不声称具备任何真实机构的背书。
- 图片中出现的字母、数字、印章纹样均为装饰，**不构成解题线索**。

### 3.2 字体

站点不加载任何外部字体。全部使用**访问者本机已安装的系统字体**（Noto Sans SC / PingFang SC / Microsoft YaHei / Songti SC 等回退栈）。
因此本项目**不分发、不嵌入、不再许可**任何字体文件。

### 3.3 不包含的素材

- 无音频文件（本版本无音效）。
- 无第三方图标库；所有图标为内联 SVG path，随代码以 MIT 授权。
- 无广告 SDK、跟踪像素、分析脚本。

## 4. 如果你要商用

CC BY-NC-SA 的 **NC** 条款禁止商业使用。若你希望把本作的案件或美术用于商业产品，请先取得书面许可，或仅复用 **MIT 授权的代码部分**并替换全部创作材料。

## 5. 署名格式

```
第零证物局 (The Zero Dossier Office) — https://github.com/<owner>/<repo>
© 2026 第零证物局 contributors — CC BY-NC-SA 4.0
```
