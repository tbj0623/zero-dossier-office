<div align="center">

<img src="site/assets/readme-hero.png" alt="第零证物局 · 雾港异常档案" width="880">

# 第零证物局 · The Zero Dossier Office

**在雾港的异常档案局里，你不是找凶手，而是把互相错位的真实记录重新归位。**

[![CI](https://github.com/__OWNER__/__REPO__/actions/workflows/ci.yml/badge.svg)](https://github.com/__OWNER__/__REPO__/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-dfb978)](LICENSE)
[![Assets: CC BY-NC-SA 4.0](https://img.shields.io/badge/story%20%26%20art-CC%20BY--NC--SA%204.0-dfb978)](ASSETS_LICENSE.md)

**[▶ 立即游玩](https://__OWNER__.github.io/__REPO__/)** · [玩法说明](docs/GAMEPLAY.md) · [作者指南](docs/AUTHOR_GUIDE.md) · [隐私](docs/PRIVACY.md)

</div>

> ⚠️ 本仓库同时保存「可玩站点」与「制作档案」。`cases/author/` 含作者解答，**仅供内部校验**，不进入站点构建产物。

---

## 这是什么

一个原创、免费、**免注册**、低资源占用的浏览器微型推理游戏。六份档案分三幕：读证物 → 复原顺序 → 提交归档。

每案解决的不是「魔法」，而是**对事实的误读**：一次分类错误、一份错版图纸、一个被当成事件的校准动作。

- **不需要在线大模型**：所有判定都是浏览器内的确定性穷举求解。
- **不上传你的答案**：没有后端、没有账号、没有跟踪脚本。
- **手机与键盘均可完整游玩**：拖放只是增强，按钮才是主路径。

## 玩法

1. **读证物** —— 每张证物都写明了一种可核实的关系：先后、相邻、间距、夹在中间、固定格位。
2. **排格位** —— 点击卡片选中，再点目标格位交换；或使用 ↑↓ 按钮。
3. **提交复原** —— 系统逐条核对，只告诉你「哪些关系不符」，绝不替你排好。

三档提示逐级给出：方法 → 关键组合 → 较直接的推导。**提示不会自动完成排列，也不扣分。**

结案页分成两段：**逻辑复盘**（可由证据严格证明的排序）与**档案后记**（作者叙事，结案后补充）。二者在数据层就是分开的，不拿故事冒充推理结论。

## 六案与三幕

| 幕 | 档案 | 机制焦点 |
|---|---|---|
| I · 错位的开端 | NA-001 末班车的四张车票 | `immediately_before` + `not_at` |
| | NA-002 封存室的四格抽屉 | 绝对格位 + 定向相邻 |
| | NA-003 静默分拣线上的五个包裹 | 双链拼接 |
| II · 灯塔与回信 | NA-004 灯塔没有亮起的第五盏灯 | `adjacent`（无方向）+ `distance` + `between` |
| | NA-005 寄不到的第五封回信 | `between` 的逆向推理 + `distance` |
| III · 第零张底片 | NA-006 第零号空白底片 | 六件综合 + 终章 |

## 技术

| 层 | 说明 |
|---|---|
| 运行时 | 纯静态 HTML/CSS/ES Modules，**零依赖、零构建必需** |
| 判定 | `engine/solver.mjs` —— 单一求解核心，站点与测试共用同一份逻辑 |
| 校验 | `engine/verify_cases.py` —— 独立 Python 实现，用于交叉验证 |
| 规模 | 3–8 件物品穷举；最难的 NA-006 为 6! = 720 种排列 |
| 部署 | GitHub Pages（Actions 构建）或任意静态托管 |

### 本地运行

```bash
# 任意静态服务器即可，注意必须用 HTTP（ES Modules 不接受 file://）
python -m http.server 8080 --directory dist
# 打开 http://127.0.0.1:8080
```

### 构建与测试

```bash
node tools/build.mjs                       # 生成 dist/
python engine/verify_cases.py              # 作者版唯一解 + 逐条必要性
python -m unittest discover -s tests/logic -p 'test_*.py'
node --test tests/logic/solver.test.mjs
python tests/logic/cross_check.py          # Python ⇄ JS 真值表比对
python tests/browser/e2e.py --base http://127.0.0.1:8080   # 需要 Playwright
```

## 质量门禁

每个案件必须同时通过**四项独立签核**才会出现在正式档案柜：

1. **形式化**：唯一解 + 每条约束去掉后出现多解（无冗余线索）+ Python/JS 一致。
2. **语义**：每条 `evidence.body` 的中文读法与 `op` 参数严格同义，见 `work/lore/SEMANTIC_REVIEW.md`。
3. **盲审**：只给剥离答案的材料，由独立解题者自行推导，见 `work/blind/BLIND_REPORT.md`。
4. **浏览器**：真实浏览器完成通关，见 `screenshots/browser-report.json`。

签核结果逐案落在 `review/<id>-{formal,semantic,blind,browser}.json`。**任何一项缺失，该案状态为 `BLOCKED`，不进档案柜。**

## 隐私

- 无账户、无后端、无分析脚本、无第三方 CDN、无远程字体。
- 进度只写在 `localStorage`（键前缀 `zd:v1:`），可随时在「玩法说明」页一键清除。
- 求解完全在本地完成，**你的答案不会被发送给任何在线 AI 或服务器**。

详见 [docs/PRIVACY.md](docs/PRIVACY.md)。

## 许可

- **程序代码**：[MIT](LICENSE)
- **叙事、案件文本、视觉资产**：[CC BY-NC-SA 4.0](ASSETS_LICENSE.md)

字体不分发（使用访问者本机系统字体）。图片是氛围层，解题所需信息永远以 HTML 文本呈现。

## 虚构声明

全部人物、地点、机构与事件均为虚构的架空世界「雾港」。本作不影射真实死者、真实机构或现存个人，也不以伪造的历史文书冒充真实档案。

## 已知限制

- 静态 JavaScript 天然可被查看，**本作不提供、也不声称提供「无法看答案」的防作弊**。公平性靠设计，不靠代码隐藏。
- 形式化唯一解 **不等于** 好玩，也不等于文字无歧义——所以才有语义审稿与独立盲审。
- 本仓库的玩家反馈章节只记录**真实发生**的试玩；没有结果时明确写「未验证」。
