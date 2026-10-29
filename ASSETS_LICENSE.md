# 资产与叙事许可 · ASSETS LICENSE

本项目把「程序」与「创作材料」分开授权。**代码用 MIT，叙事与美术用 CC BY-NC-SA 4.0。**
这不是法律意见；如需商业授权请另行联系。

> **一句话版本**：代码拿去用（MIT）；故事、案件文本、图片可以分享和改编，
> 但要署名、不能商用、衍生作品要用同样的许可（CC BY-NC-SA 4.0）。
> 其余一切（文档、构建脚本、测试、发布资料）也按 MIT 处理，除了明确列在下面的创作材料。

---

## 0. LICENSE 覆盖范围（为什么分成两个文件）

`LICENSE` 是**纯 MIT 全文**，只覆盖**程序代码**。
之所以不让它顺带写"本许可只用于代码"，是因为 GitHub 的许可证识别要做**精确文本匹配**，
在 MIT 全文后追加任何说明都会让仓库显示为「未识别许可证」（NOASSERTION），
反而降低可复用性。范围说明因此放在本文件。

| 文件 | 覆盖对象 |
|---|---|
| `LICENSE` | 程序代码（MIT 全文） |
| `ASSETS_LICENSE.md`（本文件） | 叙事、案件数据、视觉资产，以及全仓库的许可归属总表 |

---

## 1. 授权范围总表（覆盖仓库全部文件）

| 范围 | 典型路径 | 许可 |
|---|---|---|
| **程序代码** | `engine/**`、`site/*.mjs`、`site/engine/**`、`site/styles/**`、`tools/**`、`tests/**`、`.github/**`、`site/index.html` | **MIT**（见 `LICENSE`） |
| **文档与运营材料** | `README.md`、`docs/**`、`marketing/**`、`ops/**`、`review/**` | **MIT** |
| **叙事与案件数据** | `cases/**/*.json`、`work/lore/**`、`work/blind-src/**` | **CC BY-NC-SA 4.0** |
| **视觉资产** | `site/assets/**`（全部图片与 SVG） | **CC BY-NC-SA 4.0** |
| **第三方组件** | `work/qa/a11y/axe.min.js` | **MPL-2.0**（Deque Systems），见 §6 |

如果你不确定某个文件属于哪一类：**默认按 MIT 处理**，只有上表明确标为
CC BY-NC-SA 的创作材料例外。

### 1.1 图形资产的正式授权声明

`site/assets/` 目录下的全部文件（`harbor-archive-background.webp`、
`archive-desk-background.webp`、`evidence-case-001..003.webp`、
`NA-004..006-episode-card.webp`、`archive-emblem.svg`、`archive-emblem-512.png`、
`github-social-preview.png`、`readme-hero.png`）由本项目创作者原创，**依
CC BY-NC-SA 4.0 授权**：你可以复制、分发、改编，条件是——

1. **署名**（BY）：注明来源为本项目及下方署名格式；
2. **非商业**（NC）：不得用于商业目的；
3. **相同方式共享**（SA）：改编作品须以相同许可发布。

许可全文：<https://creativecommons.org/licenses/by-nc-sa/4.0/>

## 2. 叙事与案件数据 —— CC BY-NC-SA 4.0

案件正文、证物文本、提示、复盘、后记、世界观文档适用 CC BY-NC-SA 4.0，
理由同上（署名 + 非商业 + 相同方式共享）。

## 3. 制作声明

- 以上图片为**本项目的原创概念插画**，用于本项目世界观「雾港」，不描绘真实地点、
  真实机构或现存个人。
- 图片是**氛围层**：任何解谜所需信息都以可选中、可复制的 HTML 文本呈现，
  不存在「必须看清图片里的颜色/暗纹才能解题」的设计。
- 本项目不声称对这些图片拥有超出适用法律范围的独占权利，也不声称具备任何
  真实机构的背书。
- 图片中出现的字母、数字、印章纹样均为装饰，**不构成解题线索**。

### 3.1 字体

站点不加载任何外部字体。全部使用**访问者本机已安装的系统字体**
（Noto Sans SC / PingFang SC / Microsoft YaHei / Songti SC 等回退栈）。
因此本项目**不分发、不嵌入、不再许可**任何字体文件。

### 3.2 不包含的素材

- 无音频文件（本版本无音效）。
- 无第三方图标库；所有界面图标为内联 SVG path，随代码以 MIT 授权。
- 无广告 SDK、跟踪像素、分析脚本。

## 4. 如果你要商用

CC BY-NC-SA 的 **NC** 条款禁止商业使用。若你希望把本作的案件或美术用于商业产品，
请先取得书面许可，或仅复用 **MIT 授权的代码部分**并替换全部创作材料
（`cases/` 与 `site/assets/` 中的内容）。

## 5. 署名格式

```
第零证物局 (The Zero Dossier Office) — https://github.com/tbj0623/zero-dossier-office
© 2026 第零证物局 contributors — CC BY-NC-SA 4.0
```

## 6. 第三方组件

| 文件 | 组件 | 许可 | 用途 |
|---|---|---|---|
| `work/qa/a11y/axe.min.js` | axe-core 4.10.2（Deque Systems） | **MPL-2.0** | 仅供本地/CI 无障碍测试使用，**不进入发布产物 `dist/`，不随游戏分发** |

MPL-2.0 全文：<https://www.mozilla.org/en-US/MPL/2.0/>

axe-core 的许可是文件级的弱 copyleft：修改该文件本身才需要公开修改后的该文件，
不影响本项目其余代码的授权。因为它**不会被打包进游戏**，玩家的实际下载内容中
不含任何第三方代码。

## 7. 许可完整性自检

`tools/check_license_coverage.py` 会枚举仓库中每一个受版本控制的文件，
确认它至少落在 §1 表格的某一类里；未被覆盖的文件会让 CI 失败。
