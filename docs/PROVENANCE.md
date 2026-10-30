# 素材来源与生成方式说明 · PROVENANCE

> **本文件由上线后验收整改任务新增，回应验收报告 `P0-01` / `P1-3`**
> （`P1-3` = 验收报告 P1 列表第 3 项"素材许可和来源进一步透明"）。
> 建立日期：2026-10-30。文件性质：**事实梳理 + 未决事项登记**。
> 它**不是**权利声明，也不代替项目方作出任何法律主张——见 §3。

本文件只处理**图片类素材**（`site/assets/` 与 `docs/screenshots/`）。
案件文本、证物正文、叙事的来源与许可见 [`ASSETS_LICENSE.md`](../ASSETS_LICENSE.md) §2。

---

## 1. 结论先行（可直接引用）

1. **本项目的美术素材至少部分是生成式 AI 输出**，不是纯人工原创。这一点由
   `_input/Zero_Dossier_V2/10_参考资料/制作来源与V1迁移说明.md` 的自述
   （"**不能保证AI生成插画有独占版权**"）与验收报告 `P0-01` 共同确认。
2. 生成之后的**裁切、调色、改序、压字排版**由本项目完成；`NA-004..006-episode-card.webp`
   与 `evidence-case-00X-en.webp` 是**本地脚本重新排版**的产物。
3. **无法确认**某一张图对应哪一次生成、由哪个模型或账户产出——仓库内没有这类记录。
   因此本文件**不做逐张归属断言**，只记录能被证实的加工事实。
4. 本项目**不保证任何图片具有独占著作权**。见 §3。

---

## 2. 图片清单（含真实尺寸）

尺寸由 `PIL.Image.open(...).size` 实测，非估算。

### 2.1 `site/assets/` —— 15 个图片文件（另有 1 个非图片清单文件）

| # | 文件 | 尺寸 | 字节 | 站内用途 |
|---|---|---|---|---|
| 1 | `readme-hero.png` | 1600 × 800 | 1 578 612 | `README.md` 顶部 hero 图 |
| 2 | `github-social-preview.png` | 1280 × 640 | 265 081 | GitHub 社交预览（`og:image`）+ itch 封面候选 |
| 3 | `harbor-archive-background.webp` | 1672 × 941 | 183 512 | 首页 hero 背景（`site/index.html` L53、`site/styles/app.css` L136） |
| 4 | `archive-desk-background.webp` | 1672 × 941 | 150 384 | **当前版本未被任何代码引用**（`tools/build_itch.py` L33 注明"当前版本未引用"，但仍打进发行包） |
| 5 | `evidence-case-001.webp` | 1150 × 700 | 21 688 | NA-001 案件封面（中文） |
| 6 | `evidence-case-002.webp` | 1150 × 700 | 15 326 | NA-002 案件封面（中文） |
| 7 | `evidence-case-003.webp` | 1150 × 700 | 25 760 | NA-003 案件封面（中文） |
| 8 | `evidence-case-001-en.webp` | 1150 × 700 | 24 114 | NA-001 案件封面（英文，`site/app.mjs` L38 映射） |
| 9 | `evidence-case-002-en.webp` | 1150 × 700 | 19 108 | NA-002 案件封面（英文，`site/app.mjs` L39 映射） |
| 10 | `evidence-case-003-en.webp` | 1150 × 700 | 24 428 | NA-003 案件封面（英文，`site/app.mjs` L40 映射） |
| 11 | `NA-004-episode-card.webp` | 1200 × 675 | 100 220 | NA-004 案件卡（第二幕） |
| 12 | `NA-005-episode-card.webp` | 1200 × 675 | 98 772 | NA-005 案件卡（第二幕） |
| 13 | `NA-006-episode-card.webp` | 1200 × 675 | 97 396 | NA-006 案件卡（第三幕） |
| 14 | `archive-emblem.svg` | 512 × 512（`viewBox`） | 803 | 站点 Logo / 印章（纯矢量源码） |
| 15 | `archive-emblem-512.png` | 512 × 512 | 28 433 | `apple-touch-icon`、itch 缩略图 |

非图片文件：`site/assets/cover-art.json`（1 859 B）——记录每张封面**从左到右物件顺序**，
供 `tools/check_cover_art.py` 检查"封面不得按答案顺序排列"。它不是素材，是校验清单。

### 2.2 `docs/screenshots/` —— 12 张对外展示截图

| # | 文件 | 尺寸 | 说明 |
|---|---|---|---|
| 1 | `01-home.png` | 1440 × 900 | 首页（桌面视口） |
| 2 | `02-cabinet.png` | 1440 × 900 | 档案柜（桌面视口） |
| 3 | `03-desk.png` | 1440 × 900 | 调查桌（桌面视口） |
| 4 | `04-verdict.png` | 1440 × 900 | 结案复盘（桌面视口） |
| 5 | `05-mobile-home.png` | 780 × 1688 | 首页（手机 390 × 844 @2x） |
| 6 | `06-mobile-desk.png` | 780 × 1688 | 调查桌（手机 390 × 844 @2x） |
| 7 | `en-03-cabinet.png` | 1440 × 900 | 英文档案柜 |
| 8 | `en-mini-01-home.png` | 780 × 1688 | 英文首页（手机） |
| 9 | `en-mini-02-desk.png` | 780 × 1688 | 英文调查桌（手机） |
| 10 | `engine-chromium.png` | 1440 × 700 | Chromium 实拍 |
| 11 | `engine-firefox.png` | 1440 × 700 | Firefox 实拍 |
| 12 | `engine-webkit.png` | 1440 × 700 | WebKit 实拍 |

**诚实说明**：这 12 张的**生成脚本没有入库**，无法从仓库一键复现（红队 `RT-013` 仍未关闭）。
已知 `tests/browser/e2e.py` 只写 `screenshots/`（`full_page=True` 全页图），不写本目录；
本目录是**视口尺寸**截图，二者不是同一批文件。这不构成造假——两套都是真实浏览器产物，
只是截取参数不同——但"可复现路径"确实缺失，已登记为 §6 的 `PENDING_OWNER-6`。

---

## 3. 来源分类表

**分类词表**（只填能证实的）：

- `生成式AI输出（经人工裁切/调色/重排）`
- `本项目脚本程序化生成`
- `真实运行截图（浏览器实拍）`
- `本项目自有矢量源码` —— *本节唯一补充标签*，仅用于 `archive-emblem.svg`
  与其栅格化派生件。它既非生成式 AI 输出，也非"脚本程序化生成"（仓库内没有对应
  栅格化脚本，见 `PENDING_OWNER-6`）；若强行归入前两类会造成错误陈述，故单列。

### 3.1 `site/assets/` 位图

| 文件 / 组 | 来源类别 | 人工参与 | 生成式工具参与 | 许可归属 | 待确认项 |
|---|---|---|---|---|---|
| `readme-hero.png` | 生成式AI输出（经人工裁切/调色/重排） | 裁切为 2:1、左侧压暗渐变、标题/副标题/三枚圆角标签排版、"0" 印章矢量叠加 | **是**（底图场景为生成式图像输出；据验收报告为前期 ChatGPT 图像生成流程） | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2/3` |
| `github-social-preview.png` | 生成式AI输出（经人工裁切/调色/重排） | 1280×640 二次构图、左侧压暗、标题/标语/三枚标签排版、印章叠加 | **是**（与 `readme-hero.png` 同一场景底图） | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2/3` |
| `harbor-archive-background.webp` | 生成式AI输出（经人工裁切/调色/重排） | 裁切至 1672×941、调色、WebP 压缩；站点以 `opacity:.72` 叠加使用 | **是** | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2/3` |
| `archive-desk-background.webp` | 生成式AI输出（经人工裁切/调色/重排） | 裁切、调色；**当前版本未被引用**，属遗留素材 | **是** | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2/3`；另需确认是否应从发行包移除 |
| `evidence-case-001.webp`（中文） | 生成式AI输出（经人工裁切/调色/重排） | 裁切、调色；**2026-10-30 因叙事审稿 C-04 发现原图按答案顺序绘制而重绘/改序**（见 `cover-art.json` L13） | **是** | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2/3` |
| `evidence-case-003.webp`（中文） | 生成式AI输出（经人工裁切/调色/重排） | 裁切、调色；**原图按序绘制且标了 1–5 序号，两处均已修正并改序**（见 `cover-art.json` L32） | **是** | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2/3` |
| `evidence-case-002.webp`（中文） | 生成式AI输出（经人工裁切/调色/重排） | 裁切、调色（四格空抽屉，不含可辨认物件，无泄题风险） | **是** | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2/3` |
| `evidence-case-001-en.webp`<br>`evidence-case-002-en.webp`<br>`evidence-case-003-en.webp` | 本项目脚本程序化生成 | 底图取自对应中文封面；英文标题/文字由本地脚本重排后导出，保证英文界面不出现烘死的中文 | **间接**：底图与中文版同源，即上表的生成式输出；排版环节为本地脚本，未再调用生成式模型 | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2`；排版脚本未入库，`PENDING_OWNER-6` |
| `NA-004-episode-card.webp`<br>`NA-005-episode-card.webp`<br>`NA-006-episode-card.webp` | 本项目脚本程序化生成 | 由**项目已有场景配图**经本地脚本重新排版为 1200×675 案件品牌卡（来源说明原文如此）；不含可辨认解题物件（`cover-art.json` 三案均 `contains_no_objects: true`） | **间接**：复用的"已有场景配图"属于本项目的生成式输出；卡片排版本身为本地脚本 | CC BY-NC-SA 4.0 | `PENDING_OWNER-1/2`：底图是否为 §3.1 已列任一张，仓库内无记录 |

### 3.2 `site/assets/` 矢量与派生

| 文件 / 组 | 来源类别 | 人工参与 | 生成式工具参与 | 许可归属 | 待确认项 |
|---|---|---|---|---|---|
| `archive-emblem.svg` | 本项目自有矢量源码 | 803 B 单行 SVG，仅含 `<rect>/<circle>/<path>/<text>` 几何指令与固定色值，可逐行核验 | **否**：无栅格嵌入、无外部引用、无位图 data URI，不存在图像生成痕迹 | CC BY-NC-SA 4.0 | `PENDING_OWNER-6`：手写还是脚本产出无法从仓库区分（不影响许可归属） |
| `archive-emblem-512.png` | 本项目自有矢量源码（栅格化派生） | 由 `archive-emblem.svg` 同款图形栅格化为 512×512 PNG | **否** | CC BY-NC-SA 4.0 | `PENDING_OWNER-6`：栅格化脚本未入库 |

### 3.3 `docs/screenshots/`

| 文件 / 组 | 来源类别 | 人工参与 | 生成式工具参与 | 许可归属 | 待确认项 |
|---|---|---|---|---|---|
| `docs/screenshots/*.png`（12 张，见 §2.2） | 真实运行截图（浏览器实拍） | 人工截取视口范围；未做内容修饰（无拼接、无补画） | **否**：画面是程序运行时渲染结果 | 随文档按 MIT 处理（见 `ASSETS_LICENSE.md` §1）；**截图内呈现的美术仍属 CC BY-NC-SA 4.0 素材** | `PENDING_OWNER-6`：生成脚本未入库 |

> **边界**：截图里有生成式 AI 生成的美术。截图本身是"实拍"，但**不等于**画面内容全部是人工原创。
> 任何人复用截图时，画面中的插画同样受 CC BY-NC-SA 4.0 约束。

---

## 4. 明确声明（不替项目方签署权利声明）

1. **本仓库不保证任何图片具有独占著作权。**
2. **生成式 AI 输出的可版权性在各法域存在不确定性**：不同国家/地区对"AI 生成物是否构成
   作品""由谁享有权利""需要多少人类创造性投入"的认定并不一致，且仍在演化。
3. **商用需专业法律审查。** 任何人（包括项目方自己）在把本仓库图片用于商业目的前，
   都应先取得独立法律意见，不要仅凭本文件或 `ASSETS_LICENSE.md` 判断。
4. 本文件**不构成权利声明、不构成法律意见、不构成对第三方的授权承诺**，也**不代表**
   项目方放弃或主张任何权利。`ASSETS_LICENSE.md` 中的 CC BY-NC-SA 4.0 是**项目方对
   自己可支配部分的授权意图**，其实际可执行范围受上述不确定性影响。
5. 本项目**不声称**这些图片是"纯人工原创"，也**不声称**具备任何真实机构、真实地点或
   现存个人的背书。
6. 反向也不夸大：**没有证据**说明某一张图对应哪一次生成、用了哪个提示词。
   本文件只登记"能证实的加工事实"，不推断未记录的过程。

---

## 5. 字体与第三方组件

### 5.1 字体：只用系统字体栈，未分发任何字体文件

自查命令与真实结果：

```bash
$ grep -rn "@font-face" site/
（无输出，匹配数 0）

$ git ls-files | grep -Ei "\.(woff2?|ttf|otf|eot)$"
（无输出：仓库内没有任何字体文件）

$ grep -rn "fonts.googleapis\|fonts.gstatic\|@import" site/
（无输出：无远程字体、无远程 @import）
```

站点实际只声明三条**访问者本机**字体回退栈（`site/styles/tokens.css` L27–L30）：

- `--font-ui`：`"Noto Sans SC", "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", system-ui, -apple-system, sans-serif`
- `--font-serif`：`"Songti SC", "SimSun", "Noto Serif SC", "Source Han Serif SC", Georgia, serif`
- `--font-mono`：`"Cascadia Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace`

因此本项目**不分发、不嵌入、不再许可**任何字体文件；字体本身的许可仍归各字体权利人，
与本项目无关。

### 5.2 第三方组件：`axe-core` 仅测试用

| 组件 | 位置 | 许可 | 是否进入运行时 |
|---|---|---|---|
| axe-core 4.10.2（Deque Systems） | `work/qa/a11y/axe.min.js`（553 290 B） | **MPL-2.0** | **否** |

证据（真实执行）：

```bash
$ python -c "import zipfile; z=zipfile.ZipFile('release/itch-html5-release.zip'); print([x for x in z.namelist() if 'axe' in x.lower()])"
[]          # 发行包 27 个文件里没有 axe
```

`dist/` 内出现 "axe" 字样的三处均为**文案**（`dist/index.html` L1370、`dist/styles/app.css` L954
的"无障碍修复（axe-core 实测…）"说明，以及 `readme-hero.png` 的二进制偶然字节），
**不是被打包的脚本**。

### 5.3 界面图标：内联 SVG，无第三方图标库

```bash
$ grep -o "<svg" site/index.html | wc -l
1
$ grep -c "<svg" site/app.mjs
0
```

全站不引用任何图标字体或图标库；`archive-emblem.svg` 与页面内联 SVG 均为本项目自有矢量源码，
随代码按 MIT 授权（矢量图形本身作为创作材料仍按 CC BY-NC-SA 4.0，见 §3.2）。

---

## 6. 待确认清单（`PENDING_OWNER`）

以下事项**必须由项目方（账号持有人）确认**，Agent 无权代为认定。
未确认前，对外表述应维持在 §4 的口径内。

**当前状态：6 项中 1 项已关闭（#5，有后台证据），5 项仍开放。**
带 `PENDING_OWNER` 标记的条目在补齐前，任何对外文案都不得写成"已确认/已授权"。

| ID | 待确认事项 | 为什么不能由 Agent 代答 | 建议的补齐方式 |
|---|---|---|---|
| **PENDING_OWNER-1** | **生成工具与账户**：每一张图由哪个模型、哪个账户/会话、哪一天生成；是否有原始提示词留存 | 仓库内没有任何生成记录；验收报告只给出"来自前期 ChatGPT 图像生成流程"的概括，无法定位到单张 | 项目方翻查历史会话/导出记录，能补几张补几张；补不了就在此表标注"不可追溯" |
| **PENDING_OWNER-2** | **人工加工的具体范围**：除 001/003 改序与 `-en` 重排外，逐张的裁切、调色、修图由谁完成、用什么脚本 | 仓库内无逐张加工日志 | 补一份加工说明或保留脚本；否则接受"仅知粗粒度"的现状 |
| **PENDING_OWNER-3** | **是否混入第三方素材**：是否使用过图库/他人作品/第三方底纹、笔刷、字体纹理 | 无法从仓库验证；这决定许可是否可能侵权 | 项目方自查生成会话与素材来源，明确"全部由生成式模型产出，无图库素材"或列出例外 |
| **PENDING_OWNER-4** | **是否需要专业法律意见 / 商用授权路径**：生成式 AI 输出的可版权性、CC BY-NC-SA 能否有效覆盖、商用授权怎么谈 | 属法律判断，超出文档整理范围 | 咨询知识产权律师；在拿到意见前，`ASSETS_LICENSE.md` §4 的措辞保持"请先取得书面许可" |
| **PENDING_OWNER-5** | ~~itch.io 后台 Graphics 勾选状态的可核对证据~~ **→ 已关闭** | 曾因"勾选发生在账号后台、仓库无法自证"而挂起 | **已取证**：`screenshots/itch-ai-disclosure-before.json`（Graphics `false`）→ `screenshots/itch-ai-disclosure-after.json`（Graphics `true`），同一编辑页 `itch.io/game/edit/5261339`，两次抓取间隔 29 秒，唯一差异为 Graphics 勾选。详见 `marketing/ITCH_PAGE_DRAFT.md` §0.1 |
| **PENDING_OWNER-6** | **缺失的生成脚本**：`archive-emblem-512.png` 的栅格化脚本、`docs/screenshots/` 的截图脚本、`evidence-case-*-en.webp` 的排版脚本 | 三个产物在仓库内都找不到对应脚本 | 补脚本，或在相应文件中注明"手工执行、无脚本" |

---

## 7. 复核方法（可复跑）

```bash
cd zero-dossier-office

# 1) 素材清单与真实尺寸
ls -la site/assets/
python -c "from PIL import Image; import os; [print(f, Image.open('site/assets/'+f).size) for f in sorted(os.listdir('site/assets')) if f.endswith(('.png','.webp'))]"

# 2) 字体自查（期望：0 匹配 / 无输出）
grep -rn "@font-face" site/
git ls-files | grep -Ei "\.(woff2?|ttf|otf|eot)$"

# 3) 第三方组件是否进发行包（期望：[]）
python -c "import zipfile; z=zipfile.ZipFile('release/itch-html5-release.zip'); print([x for x in z.namelist() if 'axe' in x.lower()])"

# 4) 许可覆盖门禁（本文件属 docs/*，按 MIT 覆盖）
python tools/check_license_coverage.py
```

---

## 8. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-30 | 新建。回应验收报告 `P0-01` / `P1 第 3 项`；确认"至少部分美术为生成式 AI 输出"，登记 6 项 `PENDING_OWNER`；同步修正 `ASSETS_LICENSE.md` 的来源表述。 |
| 2026-10-30 | `PENDING_OWNER-5` 关闭：拿到 itch 后台 Graphics 勾选的前后抓取证据（`screenshots/itch-ai-disclosure-before.json` / `-after.json`）。剩余 5 项开放。 |
