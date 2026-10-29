/**
 * 第零证物局 · 运行时国际化（i18n）
 * ------------------------------------------------------------------
 * 设计原则：
 *  1. 中文是**源语言**，永远内联在 HTML 与 cases 里 —— 语言包加载失败时游戏完全可玩。
 *  2. 英文是**附加层**：`site/i18n/en.json` 是纯数据，通过 `?lang=en` 或语言按钮启用。
 *  3. 只替换 `data-i18n` 标注过的文本节点与若干运行时模板，绝不猜字符串。
 *  4. 案件数据（标题/证物/提示/后记）走 `localizeCase()`，在 loadCase 之后应用，
 *     因为它们是数据而非 DOM 常量。
 */

const STORAGE_KEY = 'zd:v1:lang';

let pack = null;        // 当前语言包
let locale = 'zh';      // 'zh' | 'en'

/**
 * 支持的语言。用 Object.create(null) 建"无原型字典"：
 * 普通 {} 会让 AVAILABLE['__proto__'] / ['constructor'] 返回真值，
 * 从而通过"是否支持"的判断并拼出 /i18n/__proto__.json 这样的请求。
 * 用 null 原型字典后，只有登记过的 key 才为真。
 */
const AVAILABLE = Object.assign(Object.create(null), { zh: '中文', en: 'English' });

/** 严格判定：必须是字符串且是自有属性。 */
function isSupported(value) {
  return typeof value === 'string'
    && Object.prototype.hasOwnProperty.call(AVAILABLE, value);
}

/** 读取用户选择：?lang= 优先，其次 localStorage，最后默认中文。 */
export function detectLocale() {
  try {
    const q = new URLSearchParams(location.search).get('lang');
    if (isSupported(q)) return q;
  } catch { /* 忽略 */ }
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isSupported(saved)) return saved;
  } catch { /* 忽略 */ }
  return 'zh';
}

export function currentLocale() {
  return locale;
}

export function availableLocales() {
  return Object.keys(AVAILABLE).reduce((acc, k) => {
    acc[k] = AVAILABLE[k];
    return acc;
  }, {});
}

/**
 * 载入语言包。返回 true 表示成功切换到该语言。
 * 载入失败时保持中文，不抛错、不阻塞游戏。
 */
export async function setLocale(next) {
  if (!isSupported(next)) return false;

  if (next === 'zh') {
    locale = 'zh';
    pack = null;
    applyToDocument();
    notify();
    persist('zh');
    return true;
  }

  if (!pack || locale !== next) {
    try {
      const res = await fetch(`./i18n/${next}.json`, { cache: 'force-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      pack = await res.json();
    } catch {
      // 语言包不可用：静默回退中文，游戏继续可玩
      return false;
    }
  }
  locale = next;
  applyToDocument();
  notify();
  persist(next);
  return true;
}

function persist(loc) {
  try { localStorage.setItem(STORAGE_KEY, loc); } catch { /* 忽略 */ }
}

/* ------------------------------------------------------------------ */
/* 文案查询                                                            */
/* ------------------------------------------------------------------ */

/** 取一条 UI 文案；缺失时返回中文回退值。 */
export function t(key, fallback = '') {
  if (locale === 'zh' || !pack) return fallback;
  const entry = pack.strings?.[key];
  return entry?.en || fallback;
}

/**
 * 带变量的模板：`{n}` / `{item}` / `{x}` 会被替换。
 * 英文语序与中文不同，所以模板整体交给译者控制。
 */
export function tf(key, vars, fallback = '') {
  let text = t(key, fallback);
  for (const [k, v] of Object.entries(vars || {})) {
    text = text.replaceAll(`{${k}}`, String(v));
  }
  return text;
}

/** 对案件数据做英文替换；中文模式下原样返回。 */
export function localizeCase(c) {
  if (locale === 'zh' || !pack || !c) return c;
  const tr = pack.cases?.[c.id];
  if (!tr) return c;

  const out = { ...c };
  for (const field of ['title', 'subtitle', 'setting', 'objective',
                       'resolution', 'twist', 'motif', 'director_note',
                       'logic_recap', 'epilogue']) {
    if (tr[field]) out[field] = tr[field];
  }
  if (Array.isArray(tr.slots) && tr.slots.length === c.slots.length) {
    out.slots = tr.slots;
  }
  if (Array.isArray(tr.hints) && tr.hints.length === c.hints.length) {
    out.hints = tr.hints;
  }
  if (Array.isArray(tr.evidence)) {
    const byId = new Map(tr.evidence.map((e) => [e.id, e]));
    out.evidence = c.evidence.map((e) => {
      const te = byId.get(e.id);
      return te ? { ...e, title: te.title || e.title, body: te.body || e.body, type: te.type || e.type } : e;
    });
  }
  // difficulty / theme 也翻译（若有）
  if (tr.difficulty) out.difficulty = tr.difficulty;
  if (tr.theme) out.theme = tr.theme;
  return out;
}

/* ------------------------------------------------------------------ */
/* DOM 应用                                                            */
/* ------------------------------------------------------------------ */

/**
 * 把 `data-i18n` 应用到文档：
 *   <span data-i18n="nav.cabinet">档案柜</span>          → 取该 key 的英文
 *   <input data-i18n-attr="placeholder:search.placeholder">
 * 中文模式下把原文恢复（原文在加载时被记在 dataset 里）。
 */
export function applyToDocument(root = document) {
  root.querySelectorAll('[data-i18n]').forEach((node) => {
    if (!node.dataset.i18nZh) node.dataset.i18nZh = node.textContent;
    const key = node.dataset.i18n;
    node.textContent = locale === 'zh' ? node.dataset.i18nZh : t(key, node.dataset.i18nZh);
  });

  root.querySelectorAll('[data-i18n-attr]').forEach((node) => {
    if (!node.dataset.i18nAttrZh) node.dataset.i18nAttrZh = '{}';
    let mapping;
    try { mapping = JSON.parse(node.dataset.i18nAttrZh); } catch { mapping = {}; }
    const specs = node.dataset.i18nAttr.split(',').map((s) => s.trim()).filter(Boolean);
    for (const spec of specs) {
      const [attr, key] = spec.split(':').map((s) => s.trim());
      if (!attr || !key) continue;
      if (!(attr in mapping)) mapping[attr] = node.getAttribute(attr) || '';
      const zh = mapping[attr];
      node.setAttribute(attr, locale === 'zh' ? zh : t(key, zh));
    }
    node.dataset.i18nAttrZh = JSON.stringify(mapping);
  });

  const html = document.documentElement;
  html.setAttribute('lang', locale === 'zh' ? 'zh-CN' : locale);

  document.title = locale === 'zh'
    ? (html.dataset.titleZh || document.title)
    : t(`title.${currentRouteKey()}`, document.title);
}

function currentRouteKey() {
  const h = (location.hash || '#/').replace(/^#\/?/, '');
  if (!h) return 'home';
  if (h.startsWith('case/')) return 'case';
  return h.split('/')[0] || 'home';
}



/* ------------------------------------------------------------------ */
/* 物件名：求解器用中文规范 ID，界面显示走术语表                        */
/* ------------------------------------------------------------------ */

/**
 * 把规范物件 ID（中文）映射为当前语言的显示名。
 * 中文模式或术语表缺失时原样返回，因此不会破坏任何逻辑。
 */
export function itemLabel(canonical) {
  if (locale === 'zh' || !pack) return canonical;
  const g = pack._meta?.glossary;
  if (!g) return canonical;
  const v = g[canonical];
  return (typeof v === 'string' ? v : v?.en) || canonical;
}

/** 反向映射：显示名 -> 规范 ID（用于存档兼容，存的一直是规范 ID）。 */
export function itemCanonical(display) {
  if (locale === 'zh' || !pack) return display;
  const g = pack._meta?.glossary;
  if (!g) return display;
  for (const [canon, v] of Object.entries(g)) {
    const en = typeof v === 'string' ? v : v?.en;
    if (en === display) return canon;
  }
  return display;
}


/* ------------------------------------------------------------------ */
/* 约束句（结案表格用）：由 op + 术语表生成，不依赖翻译的散文            */
/* ------------------------------------------------------------------ */

const OP_EN = {
  at: (a, r, L) => `${a} is in the slot numbered ${r.slot + 1}`,
  not_at: (a, r, L) => `${a} is not in the slot numbered ${r.slot + 1}`,
  before: (a, r, L) => `${a} comes before ${L(r.b)}`,
  after: (a, r, L) => `${a} comes after ${L(r.b)}`,
  immediately_before: (a, r, L) => `${a} comes immediately before ${L(r.b)}, with nothing in between`,
  immediately_after: (a, r, L) => `${a} comes immediately after ${L(r.b)}, with nothing in between`,
  adjacent: (a, r, L) => `${a} is next to ${L(r.b)} (no order implied)`,
  distance: (a, r, L) => `the slot numbers of ${a} and ${L(r.b)} differ by ${r.gap}`,
  between: (a, r, L) => `${a} is strictly between ${L(r.b)} and ${L(r.c)}`,
};

/** 用当前语言描述一条约束。中文模式下退回 solver 的 describeRule。 */
export function describeRuleI18n(rule, slots, fallback) {
  if (locale === 'zh' || !pack) return fallback;
  const fn = OP_EN[rule.op];
  if (!fn) return fallback;
  const label = (canon) => itemLabel(canon);
  return fn(itemLabel(rule.a), rule, label);
}


/** 结案表格「为什么必须」列。中文模式退回 solver 原文。 */
export function explainWhyI18n(necessity, fallback) {
  if (locale === 'zh' || !pack || !necessity) return fallback;
  if (necessity.essential) {
    const tpl = pack.strings?.['verdict.why.essential']?.en
      || 'Remove it and the remaining evidence still permits {n} arrangements — this is the one necessary link.';
    return tpl.replaceAll('{n}', String(necessity.remaining));
  }
  return pack.strings?.['verdict.why.corrob']?.en
    || 'Remove it and the remaining evidence still permits only one arrangement: it corroborates the others.';
}


/**
 * 结案表格用：优先取译者提供的 constraint.text（经过 22 条规则的语义审计），
 * 缺失时才用 op+术语表即时生成，最后退回 solver 中文。
 */
export function ruleText(caseId, ruleId, rule, slots, fallback) {
  if (locale === 'zh' || !pack) return fallback;
  const tr = pack.cases?.[caseId]?.constraints?.find((x) => x.id === ruleId);
  if (tr?.text) return tr.text;
  return describeRuleI18n(rule, slots, fallback);
}

/* ------------------------------------------------------------------ */
/* 订阅：语言变化后，应用层需要重新渲染案件桌                          */
/* ------------------------------------------------------------------ */
const listeners = new Set();

export function onLocaleChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function notify() {
  for (const fn of listeners) {
    try { fn(locale); } catch { /* 单个监听器失败不影响其它 */ }
  }
}
