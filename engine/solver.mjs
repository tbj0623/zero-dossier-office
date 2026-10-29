/**
 * 第零证物局 · 单一求解核心 (single source of truth)
 * ---------------------------------------------------------------
 * 纯确定性、零依赖、零网络。站点 UI 与 Node 测试共用同一份逻辑；
 * 站点通过 `site/engine/solver.mjs` 使用构建脚本生成的内容。
 *
 * 语义合同见 docs/AUTHOR_GUIDE.md：
 *  - 索引一律从 0 开始。
 *  - distance 的 gap 是「格位编号之差」，差 3 表示中间隔着 2 件物品。
 *  - between 是严格区间，不要求居中。
 *  - adjacent 不指定方向。
 */

const OPS = new Set([
  'at', 'not_at', 'before', 'after',
  'immediately_before', 'immediately_after',
  'adjacent', 'distance', 'between',
]);

export const SUPPORTED_OPS = Object.freeze([...OPS]);

const idx = (order, item) => {
  const v = order.indexOf(item);
  if (v < 0) throw new TypeError(`未知物件：${String(item)}`);
  return v;
};

/** 判定单个约束是否被某一完整排列满足。非法运算符/参数抛 TypeError，不静默。 */
export function checkRule(order, rule) {
  if (!rule || typeof rule !== 'object') throw new TypeError('约束必须是对象');
  if (!OPS.has(rule.op)) throw new TypeError(`未知约束运算符：${rule.op}`);
  const a = idx(order, rule.a);

  if (rule.op === 'at' || rule.op === 'not_at') {
    if (!Number.isInteger(rule.slot) || rule.slot < 0 || rule.slot >= order.length) {
      throw new TypeError('非法的 slot');
    }
    return rule.op === 'at' ? a === rule.slot : a !== rule.slot;
  }

  const b = idx(order, rule.b);
  if (a === b) throw new TypeError('约束的两端不能是同一物件');

  switch (rule.op) {
    case 'before': return a < b;
    case 'after': return a > b;
    case 'immediately_before': return a + 1 === b;
    case 'immediately_after': return a - 1 === b;
    case 'adjacent': return Math.abs(a - b) === 1;
    case 'distance': {
      if (!Number.isInteger(rule.gap) || rule.gap < 1 || rule.gap >= order.length) {
        throw new TypeError('非法的 gap');
      }
      return Math.abs(a - b) === rule.gap;
    }
    case 'between': {
      const c = idx(order, rule.c);
      if (c === a || c === b) throw new TypeError('between 需要三个不同物件');
      return Math.min(b, c) < a && a < Math.max(b, c);
    }
    default:
      throw new TypeError('未实现的运算符');
  }
}

/** 返回 [{id, valid}]，用于逐条回显（不排序、不猜测）。 */
export function verifyOrder(order, rules) {
  if (!Array.isArray(order)) throw new TypeError('order 必须是数组');
  if (new Set(order).size !== order.length) throw new TypeError('排列中出现重复物件');
  return rules.map((rule) => ({ id: rule.id, valid: checkRule(order, rule) }));
}

/**
 * 穷举 3..8 件物品的全部排列并计数。
 * 返回 {count, solution}；仅当 count===1 时 solution 才非 null。
 */
export function countSolutions(items, rules) {
  if (!Array.isArray(items)) throw new TypeError('items 必须是数组');
  if (items.length < 3 || items.length > 8) {
    throw new TypeError('穷举求解器仅支持 3..8 件物品');
  }
  if (new Set(items).size !== items.length) throw new TypeError('items 中存在重复');
  let n = 0;
  let only = null;

  const rec = (prefix, rest) => {
    if (rest.length === 0) {
      if (rules.every((rule) => checkRule(prefix, rule))) {
        n += 1;
        only = [...prefix];
      }
      return;
    }
    for (let i = 0; i < rest.length; i += 1) {
      rec(
        prefix.concat(rest[i]),
        rest.slice(0, i).concat(rest.slice(i + 1)),
      );
    }
  };

  rec([], items);
  return { count: n, solution: n === 1 ? only : null };
}

/**
 * 逐条必要性：去掉该约束后还剩几种解。
 * essential === true 表示「这条关系不可或缺」。
 */
export function necessityReport(items, rules) {
  return rules.map((rule, i) => {
    const rest = rules.filter((_, j) => j !== i);
    const { count } = countSolutions(items, rest);
    return {
      id: rule.id,
      remaining: count,
      essential: count > 1,
    };
  });
}

/* ------------------------------------------------------------------ */
/* 面向玩家的中文描述（UI 与复盘共用，避免各处各写一套话术）           */
/* ------------------------------------------------------------------ */

const SLOT_LABEL = (slots, i) => (slots && slots[i] != null
  ? `第${i + 1}格（${slots[i]}）`
  : `第${i + 1}格`);

/** 把结构化约束翻译成一句可核对的玩家语言。 */
export function describeRule(rule, slots) {
  const { a, b, c } = rule;
  switch (rule.op) {
    case 'at':
      return `${a} 固定在${SLOT_LABEL(slots, rule.slot)}。`;
    case 'not_at':
      return `${a} 不在${SLOT_LABEL(slots, rule.slot)}。`;
    case 'before':
      return `${a} 在 ${b} 之前（不要求相邻）。`;
    case 'after':
      return `${a} 在 ${b} 之后（不要求相邻）。`;
    case 'immediately_before':
      return `${a} 紧接在 ${b} 之前，中间没有其它物件。`;
    case 'immediately_after':
      return `${a} 紧接在 ${b} 之后，中间没有其它物件。`;
    case 'adjacent':
      return `${a} 与 ${b} 相邻，但记录没有写明谁在前。`;
    case 'distance':
      return `${a} 与 ${b} 的格位编号相差 ${rule.gap}（中间隔着 ${rule.gap - 1} 件）。`;
    case 'between':
      return `${a} 夹在 ${b} 与 ${c} 之间，不要求正好居中。`;
    default:
      return '未知关系。';
  }
}

/** 复盘用：这条关系的必要性说明。 */
export function explainWhy(necessity) {
  if (!necessity) return '';
  if (necessity.essential) {
    return `删去它，其余证据仍允许 ${necessity.remaining} 种排列——它是唯一解的必要一环。`;
  }
  return '删去它，其余证据仍只剩一种排列：它与其它线索互相印证。';
}

/** 轻量结构自检：站点加载任何案件前的第一道闸门。 */
export function assertCaseShape(c) {
  const need = ['id', 'title', 'slots', 'items', 'evidence', 'constraints', 'hints'];
  for (const k of need) {
    if (c == null || c[k] == null) throw new TypeError(`案件缺少字段：${k}`);
  }
  if (!/^NA-\d{3}$/.test(c.id)) throw new TypeError('案件编号格式不合法');
  if (c.items.length !== c.slots.length) throw new TypeError('items 与 slots 长度不一致');
  if (new Set(c.items).size !== c.items.length) throw new TypeError('items 重复');
  if (!Array.isArray(c.evidence) || c.evidence.length === 0) throw new TypeError('证据为空');
  const ids = new Set(c.constraints.map((r) => r.id));
  if (ids.size !== c.constraints.length) throw new TypeError('约束 ID 重复');
  const used = new Set();
  for (const e of c.evidence) {
    if (!e.body || !Array.isArray(e.constraint_ids) || e.constraint_ids.length === 0) {
      throw new TypeError(`证据 ${e.id} 缺少正文或形式化引用`);
    }
    for (const ref of e.constraint_ids) {
      if (!ids.has(ref)) throw new TypeError(`证据 ${e.id} 引用了不存在的约束 ${ref}`);
      used.add(ref);
    }
  }
  if (used.size !== ids.size) throw new TypeError('存在没有证据承载的隐藏约束');
  for (const rule of c.constraints) checkRule(c.items, rule);
  return true;
}
