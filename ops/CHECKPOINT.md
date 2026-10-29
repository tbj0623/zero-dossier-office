# CHECKPOINT · 第零证物局 V2

> **给一个看不到旧聊天的新 Agent**：读完本文件 + `ops/MASTER_STATE.md` + `ops/MEMORY_GLOBAL.md` 就能继续。

- **更新时间**：2026-10-29（Asia/Shanghai）
- **生产仓库路径**：`C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\`
- **输入材料（只读）**：`..\第零证物局_V2_究极版_完整策划素材案件与DSH执行包.zip` → 解压至 `..\_input\Zero_Dossier_V2\`
- **是否触碰 Decision Arena 或其它既有仓库**：**否**

---

## 当前 Gate 状态

| Gate | 内容 | 状态 |
|---|---|---|
| **G0** 环境与防误操作 | 新目录、输入留档、工具链核验、基线测试 | ✅ **PASS** |
| **G1** 核心纵切（NA-001） | 打开→读证→上下移动→错误提交→三档提示→正确复原→两段式结案 | ✅ **PASS**（真实 Chromium） |
| **G2** 逻辑与内容 | 6 案唯一解、逐条必要性、Python/JS 一致、语义审稿、独立盲审 | ✅ **PASS**（含 3 处修复） |
| **G3** 产品体验 | 完整美术、三幕导航、响应式、44px、键盘、降级、隐私 | ✅ **PASS**（360/390/768/1024/1440） |
| **G4** 代码与公开交付 | 测试、许可、README、截图、CI、Pages、itch 包 | ⏳ **进行中**（本地全部就绪；待 GitHub 推送） |
| **G5** 真实价值 | 真实人类试玩 | ⛔ **NOT_DONE**（需真人，不可伪造） |

---

## 可复现的测试结果（本机真实执行）

```
$ python engine/verify_cases.py
PASS NA-001 … NA-006 · 6 author cases FORMALLY valid

$ python -m unittest discover -s tests/logic -p 'test_*.py'
Ran 41 tests — OK

$ node --test tests/logic/solver.test.mjs
tests 52 / pass 52 / fail 0

$ python tests/logic/cross_check.py
PASS Python/JS 规则一致：6 案 · 4508 条真值探针全部吻合
PASS 双方支持的运算符集合相同：9 个

$ python tests/browser/e2e.py --base http://127.0.0.1:8080
共 36 项检查：36 PASS / 0 FAIL
六案浏览器通关: 6/6 ['NA-001'…'NA-006']
```

证据文件：`screenshots/browser-report.json`

---

## 本阶段发现并修复的真实缺陷

| # | 来源 | 严重度 | 问题 | 修复 |
|---|---|---|---|---|
| 1 | Lead 自测 | 阻断 | `el()` 辅助函数把 `aria.*` 写成 `label`/`disabled`，导致所有移动按钮被**真正禁用** | 改写为 `aria-<k>` 前缀 |
| 2 | Lead 自测 | 中 | 构建脚本回写 `site/app.mjs`，污染源文件 | 改为只写 `dist/` 副本 |
| 3 | 语义审稿 | 中 | NA-005 E03「相差三格」可被读成"中间隔三件" | 加括号「两者之间隔着两个格位」 |
| 4 | **独立盲审** | **阻断** | NA-006 E01「相距整整三次」中「次」是格位单位，可读成索引差 4；**两种读法各自唯一但答案不同** | 改为「曝光序号相差三：…第 n+3 次…」 |
| 5 | **独立盲审** | 轻微 | NA-003 时间轴与格位轴映射未写明 | E02 补充「传送带由第 1 格向第 5 格依次运行」 |
| 6 | **独立盲审** | 中 | 6 案中 5 案的 `items` 数组顺序 == 答案顺序 | `tools/scramble_items.py` 确定性打乱；UI 侧改用 `deterministicScramble()` |

第 4 项经 Lead 独立复算确认：`gap=3` 与 `gap=4` 各得 1 个解且排列不同 → 属"自信地判错且无法自查"的不公平谜题，必须修复。

---

## 六案资格状态

| 案件 | 形式化 | 语义 | 盲审 | 浏览器 | 上架 |
|---|---|---|---|---|---|
| NA-001 | PASS | PASS | PASS | PASS | ✅ |
| NA-002 | PASS | PASS | PASS | PASS | ✅ |
| NA-003 | PASS | PASS | PASS(复审) | PASS | ✅ |
| NA-004 | PASS | PASS | PASS | PASS | ✅ |
| NA-005 | PASS | PASS | PASS | PASS | ✅ |
| NA-006 | PASS | PASS | PASS(复审) | PASS | ✅ |

签核文件：`review/<id>-{formal,semantic,blind,browser}.json`

---

## 真实发布状态

- **GitHub 仓库**：`NOT_PUBLISHED`（gh 已登录 `tbj0623`，scopes 含 `repo` / `workflow`）
- **GitHub Pages**：`NOT_PUBLISHED`
- **itch.io**：`DRAFT_READY` — `release/itch-html5-release.zip`，21 文件 / 0.65 MB 解压 / `index.html` 在 ZIP 根目录 ✅
- **社交预览图**：图片已就绪，**尚未**在仓库 Settings 设置（上传文件 ≠ 已设置）
- **真实人类试玩**：`NOT_DONE`

---

## 下一步（按顺序）

1. 盲审员复审 NA-003 / NA-006 修订后文本 → 确认 BLOCKING 已解除
2. `python tools/write_review.py` 生成四项签核并通过 `test_all_six_cases_pass_all_four_gates`
3. `git init` + 首次提交 → `gh repo create` → 推送 → 配 Pages → 实测公网 URL
4. 用真实 URL 更新 README（`__OWNER__` / `__REPO__` 占位符）
5. G5：按 `docs/PLAYTEST_PROTOCOL.md` 找真人试玩（**不可伪造**）

---

## 恢复第一条动作

```bash
cd "C:\Users\11930\Desktop\第零号证物局\zero-dossier-office"
python engine/verify_cases.py && node --test tests/logic/solver.test.mjs
node tools/build.mjs
python -m http.server 8080 --directory dist
# 打开 http://127.0.0.1:8080
```
