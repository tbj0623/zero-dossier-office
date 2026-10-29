# ENV_CHECK · 第零证物局 V2

记录时间：2026-10-29（Asia/Shanghai）。**不含任何密钥原文。**

## 1. 工作区隔离

| 项 | 实测值 |
|---|---|
| 输入 ZIP | `../第零证物局_V2_究极版_完整策划素材案件与DSH执行包.zip`（2,658,755 B，67 entries） |
| 解压位置 | `../_input/Zero_Dossier_V2/`（只读输入材料，不修改） |
| 生产仓库 | `C:\Users\11930\Desktop\第零号证物局\zero-dossier-office\` |
| 是否触碰既有 Decision Arena 仓库 | **否**。本会话从未 `cd` 进入、未读写、未 git 操作任何其它仓库。 |
| 父目录既有仓库检查 | 父目录仅有本 ZIP、总纲 md、START_HERE.txt；`git rev-parse` 在父目录非仓库。 |

## 2. 工具链真实版本

| 工具 | 版本 | 状态 |
|---|---|---|
| Python | 3.14.7 | 可用 |
| Node | v24.20.0 | 可用 |
| Git | 2.56.0.windows.2 | 可用 |
| gh CLI | 2.100.0 (2026-09-03) | 已登录 `tbj0623`，scopes: `delete_repo, gist, read:org, repo, workflow` |
| Playwright (Python) | 已安装，chromium-1248 缓存可用 | 冒烟测试通过（`set_content` + `textContent` 读到中文） |
| Microsoft Edge | `/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe` | 存在，作为第二浏览器引擎真实测试用 |
| Google Chrome | 未安装 | 记录为不可用 |
| 中文字体 | 使用系统字体栈（Microsoft YaHei / Noto Sans SC 回退） | 无 CDN 依赖 |

## 3. 模型与费用

- 本会话模型：`deepseek-v4.1-flash`（由宿主注入，未在客户端自行切换供应商）。
- 未调用任何付费 API、未申请付费额度、未购买域名或服务。
- 全部站点运行时为纯静态 + 本地确定性求解，**零服务器推理开销**。
- 无法在本会话内读取计费后台真实账单；不声称任何费用金额，仅声明"未发生新增付费调用"。

## 4. Team 工具实测

- `list_agents` 可用，当前仅 `lead` 一名成员。
- `spawn_teammate` / `send_message` / `wait_agent` / `team_task_*` 均在本会话工具清单中可用。
- 结论：Team 机制可用，但**本任务为单机串行可完成的工作**，且共享同一工作目录、无文件锁；为降低写冲突风险，采用 Lead 单一写入 + 独立子 Agent 只读审查的降级混合模式，不批量创建占位队友。

## 5. 初始基线测试（本机真实重跑，不沿用预制包口头统计）

```
$ python '04_验证引擎/verify_cases.py'
PASS NA-001 items 4 clues 3 unique 1 answer [...]
PASS NA-002 items 4 clues 3 unique 1 answer [...]
PASS NA-003 items 5 clues 4 unique 1 answer [...]
PASS NA-004 items 5 clues 4 unique 1 answer [...]
PASS NA-005 items 5 clues 4 unique 1 answer [...]
PASS NA-006 items 6 clues 4 unique 1 answer [...]
PASS 6 author cases FORMALLY valid.

$ python -m unittest discover -s '04_验证引擎' -p 'test_*.py'
Ran 12 tests in 0.052s — OK

$ node --test '05_可运行原型/solver.test.mjs'
tests 18 / pass 18 / fail 0
```

基线结论：**形式化唯一解与 Python/JS 一致性成立**；语义审稿、盲审、真实浏览器均未完成（原包自述一致，本机复核确认）。

## 6. 数据完整性复核（本机执行）

- `author/` 与 `public/` 的 `constraints` / `items` / `slots` / `evidence` / `hints` **逐字段相等**。
- `public/` 不含 `expected_solution`、`editorial_note`、`status`。
- `blind/` 不含 `constraints`、`expected_solution`、`hints`、`epilogue`、`logic_recap`、`twist`、`resolution`。

## 7. 已知限制 / 不承诺项

- 无 Google Chrome，跨引擎覆盖为 Chromium(Playwright) + Edge。
- 真实人类盲测需要真人，本会话只能提供**可复现的盲测包与流程**，不会伪造玩家数据。
- GitHub Pages 与 itch.io 的最终外网可访问性以部署后实测为准；未实测前不声明上线。
- Social Preview 需在仓库 Settings 单独设置，上传图片文件 ≠ 已设置。
