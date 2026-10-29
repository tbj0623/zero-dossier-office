# 案件格式与作者指南 · AUTHOR GUIDE

本文件是「案件 JSON v2」的语义合同。**机器唯一解 ≠ 玩家理解唯一**，所以格式只是第一道门。

## 1. 数据分级

| 目录 | 用途 | 含答案？ | 是否进站点 |
|---|---|---|---|
| `cases/author/NA-xxx.json` | 作者源，含 `expected_solution`、内部审稿说明 | **是** | ❌ 绝不 |
| `cases/public/NA-xxx.json` | 白名单导出的发布候选 | 否 | ✅ 是 |
| `work/blind-src/NA-xxx.json` | 剥离答案/约束/提示/尾声的盲审包 | 否 | ❌ 绝不 |

> **静态游戏不可能在源码层面防作弊。** 客户端能从规则枚举出解，这是设计使然，不要宣传「无法看答案」。

## 2. 必填字段

```jsonc
{
  "id": "NA-001",              // 必须匹配 /^NA-\d{3}$/
  "slug": "last-tram-tickets", // ASCII slug，用于 URL
  "title": "末班车的四张车票",
  "subtitle": "一句话悬念，不解释原因",
  "difficulty": "新手",         // 新手 / 进阶 / 挑战
  "play_minutes": [3, 5],      // 设计估计，不是实测均值
  "chapter": 1,                // 1..3，对应三幕
  "theme": "开卷：雾港的错位记录",
  "mechanic": "order",         // 当前仅支持 order
  "setting": "背景叙述",
  "objective": "明确告诉玩家要排什么",
  "slots": ["22:00", "..."],   // 长度必须等于 items
  "items": ["红票", "..."],     // 必须唯一
  "evidence": [ /* 见下 */ ],
  "constraints": [ /* 见下 */ ],
  "hints": ["…", "…", "…"],    // 3–4 段，必须逐案定制
  "expected_solution": ["红票", "..."],   // 仅 author 版
  "resolution": "结论",
  "twist": "哪种记录机制造成了误会",
  "logic_recap": "严格可证明的排序说明",
  "epilogue": "结案后补充的叙事（不声称由排序证明）"
}
```

## 3. `evidence[*]`

```jsonc
{
  "id": "E01",
  "title": "粘连的票根",
  "type": "物证",              // 物证 / 记录 / 证词 / 设备记录 / 影像记录 / 现场记录 / 文字记录 / 机器记录
  "body": "玩家能读到的正文",
  "constraint_ids": ["C01"],   // 必须恰好覆盖它承载的约束
  "illustration_hint": "插画描述（不给玩家）"
}
```

**硬规则**：`evidence[*].constraint_ids` 的并集必须**等于**全部约束 ID 的集合。
- 少了 → 存在**隐藏约束**，玩家不可能推出唯一解，校验失败。
- 多了 → 引用不存在的约束，校验失败。

## 4. `constraints[*]` —— 九个算子

索引一律从 **0** 开始。

| `op` | 必需字段 | 形式化语义 | 玩家语言示例 | ⚠️ 常见误写 |
|---|---|---|---|---|
| `at` | `a`, `slot` | `index(a) == slot` | "海图放在第 4 格"（`slot:3`） | 把"第4格"写成 `slot:4` |
| `not_at` | `a`, `slot` | `index(a) != slot` | "第一格不是空白回邮" | — |
| `before` | `a`, `b` | `index(a) < index(b)` | "红票更早" | 用 `before` 表达"紧挨着" |
| `after` | `a`, `b` | `index(a) > index(b)` | "红票更晚" | 同上 |
| `immediately_before` | `a`, `b` | `index(a) + 1 == index(b)` | "红票紧接蓝票之前" | 与 `adjacent` 混用 |
| `immediately_after` | `a`, `b` | `index(a) - 1 == index(b)` | "蓝票紧挨红票之后" | 同上 |
| `adjacent` | `a`, `b` | `abs(index(a) - index(b)) == 1` | "两件挨着，未记先后" | 正文写"在前"却用无方向的 `adjacent` |
| `distance` | `a`, `b`, `gap` | `abs(...) == gap` | "格位编号相差 3" | **写成"中间隔 3 件"**（实际隔 2 件） |
| `between` | `a`, `b`, `c` | `min(b,c) < index(a) < max(b,c)` | "A 在 B 和 C 之间，不一定正中央" | 让玩家读成"正好居中" |

### 两个最容易写错的地方

1. **`distance` 的 `gap` 是索引差，不是中间物品数。**
   `gap: 3` ⇒ 两者中间隔着 **2 件**。正文请写「格位编号相差三格（两者之间隔着两个格位）」。
2. **`between` 是严格区间，不要求居中。**
   正文请写「夹在……之间，不要求正好居中」。

### 定向 vs 不定向

- 玩家能确定的只有"谁在谁前面"时 → 用 `before` / `immediately_before`。
- 正文明确说"没有记下前后方向 / 谁高谁低" → 才能用 `adjacent`。
- **绝不允许**正文写"紧挨在……左侧"却在代码里用 `adjacent`。

## 5. 提示的写法

三段递进，**逐案定制**，杜绝通用模板：

1. **方法**：先固定哪个位置、把什么当成一组。
2. **关键组合**：指出哪两条关系必须一起用。
3. **较直接的推导**：说出一个中间结论，但**不给出完整排列**。

禁止："你居然没发现"、"这很明显"、自动填答案、"提示会扣分"。

## 6. 结案：逻辑与叙事必须分家

- `logic_recap`：**只能**陈述可以从约束严格推出的事实（顺序、位置）。
- `epilogue`：可以讲故事（为什么误会、主人公情绪、半枚 0 章），但 UI 上必须标为「结案后补充记录」，且**不得声称是刚才排序的结论**。

判定标准：如果后记里的事实对玩法答案至关重要，就必须在证物正文里给出对应约束并重新校验，否则它只是叙事，不能当证据。

## 7. 新增案件的完整流程

```bash
# 1. 写 cases/author/NA-xxx.json
python engine/verify_cases.py                       # 必须 PASS（唯一解 + 逐条必要性）

# 2. 导出 public 版（去掉 expected_solution / editorial_note / status）
python tools/export_case.py NA-xxx

# 3. 生成盲审包（去掉 constraints / hints / epilogue / logic_recap / twist）
python tools/export_case.py NA-xxx --blind

# 4. 四项签核：formal / semantic / blind / browser
#    结果写入 review/NA-xxx-{formal,semantic,blind,browser}.json

# 5. 把 ID 加入 RELEASED 白名单（site/app.mjs 与 tools/build.mjs），重建
node tools/build.mjs
```

**任何一项没 PASS，该案必须保持 `BLOCKED`，不得出现在正式档案柜。** 宁可少一案，不上一案没验证的。

## 8. 规模限制

- 求解器穷举 3–8 件物品。超过 8 件需要另写可证明的 CSP/SAT 求解器，**不允许**直接放宽上限。
- 六案实际最多 6 件（720 种排列），性能充足。

## 9. 内容伦理底线

- 不影射真实死者、真实事故、真实机构或现存个人。
- 不伪造真实历史机构文书冒充证据。
- 不把"没解出来"的玩家当傻子；不设虚构排行榜或假稀缺。
- 真相应涉及**不同的记录机制**（顺序、标签、观察窗口、版本号、凭证类别、校准行为），不要六案都是"管理员放错了"。
