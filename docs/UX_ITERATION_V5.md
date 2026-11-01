# V5 · 把翻译做进完整的玩家路径

## 决策与范围
V1–V4 已经保证六案唯一解、进度恢复、证据直达和移动端快速跳转。本轮进行审查时发现：
静态英文网页可以显示，但关键的确认对话框、操作后提示及错误页仍有硬编码中文。
这些时刻恰好涉及会丢失进度的操作，必须消除语言歧义。

另外，「清除游玩进度」原先错误地调用全站前缀删除，连语言偏好、首页说明关闭状态一起清掉；
这不符合按钮宣称的删除范围，也会让英文玩家刷新后突然回中文。

### 已实施
1. 重置此案、重新调查、清空游玩进度共三种确认弹窗均从本地化字典读取标题、解释和动作按钮。
2. 手机导航开/合 aria-label、初次以英文打开的菜单语义、旧地址错误提示和通关后的归档标记改为本地化处理。
3. 案件文件网络加载与校验异常在英文包中都有明确文案；终端错误详情不会原样漏到玩家界面。
4. 清空进度仅删除本项目 progress 和 order: 案件存档，保留语言偏好、说明关闭状态以及不属于本游戏的 localStorage。
   清空后同步重算首页续玩入口与档案柜，失败时向玩家提示。
5. 新增 Playwright V5 测试，实际打开弹窗并执行取消和确认，验证英文全链路、404 恢复与存储边界。
6. 将 V5 测试加入 GitHub CI 浏览器门禁，保留 V3/V4 和原有六案通关、三引擎/axe 测试。

### 不改变
- 六个已发布案件及唯一解、提示文本和故事内容
- 核心求解器、约束解释、存档前缀
- 无账号、无后端、无分析 SDK

### 待验证的产品假设
本轮仍是工程加固，**不是来自真实玩家访谈的用户满意度结论**。
陌生玩家试用仍是 0 样本；继续以 3–5 位未接触过项目的人进行观察式盲测，
尤其检查第一案对「紧邻、间距、夹在中间」的认知与结案后的第二案续玩动力。
如无重复证据，不急于增加强制教程、排行榜或额外谜题。

### 回归命令
- Python: python -m unittest discover -s tests/logic -p test_*.py
- JS: node --test tests/logic/solver.test.mjs tests/logic/player_state.test.mjs
- Cases: python engine/verify_cases.py
- Cross language logic: python tests/logic/cross_check.py
- Build: node tools/build.mjs
- Local server: python -m http.server 8140 --directory dist
- V5: python tests/browser/ux_v5.py --base http://127.0.0.1:8140
- Original: python tests/browser/e2e.py --base http://127.0.0.1:8140
- V3/V4: python tests/browser/ux_v3.py / ux_v4.py --base http://127.0.0.1:8140
- English: python tests/browser/e2e_en.py --base http://127.0.0.1:8140
- Accessibility: python tests/browser/a11y.py --base http://127.0.0.1:8140

只在本轮 CI 成功且 Pages 工作流成功，并且公开站点的 BUILD SHA 相同时，标记 V5 已上线。
itch.io HTML5 包需独立上传与验收，不能混淆。
