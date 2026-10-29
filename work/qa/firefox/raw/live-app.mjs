/**
 * 第零证物局 · 应用层
 * 纯静态、零依赖、零网络（除同源案件 JSON 与静态资源）。
 * 所有 DOM 写入使用 textContent / createElement，绝不拼接 innerHTML 到用户可见数据。
 */
import {
  checkRule,
  countSolutions,
  describeRule,
  explainWhy,
  necessityReport,
  verifyOrder,
  assertCaseShape,
} from './engine/solver.mjs';

/* ------------------------------------------------------------------ */
/* 常量与状态                                                          */
/* ------------------------------------------------------------------ */
const STORAGE_PREFIX = 'zd:v1:';
const BUILD = '33f9ae0c70bea5692b83a98a6be18784ff890fa8';

/** 只有四项审查全部 PASS 的案件才出现在正式档案柜。 */
const RELEASED = new Set(['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006']);

const ACTS = [
  {
    roman: 'I',
    title: '错位的开端',
    desc: '每件东西都还在。问题是，人们把它们放进了错误的顺序。',
    cases: ['NA-001', 'NA-002', 'NA-003'],
  },
  {
    roman: 'II',
    title: '灯塔与回信',
    desc: '两套登记系统，在同一个夜晚留下不同版本的事实。',
    cases: ['NA-004', 'NA-005'],
  },
  {
    roman: 'III',
    title: '第零张底片',
    desc: '你终于找到那个从未被拍下的瞬间。',
    cases: ['NA-006'],
  },
];

/** 每案的图片与钩子（不剧透）；数据正文仍来自 cases JSON。 */
const CASE_META = {
  'NA-001': { img: 'evidence-case-001.webp', hook: '同一台打票机，半小时里打出四张互相错位的存根。' },
  'NA-002': { img: 'evidence-case-002.webp', hook: '四格抽屉都被上锁，清点记录却对不上任何一件东西。' },
  'NA-003': { img: 'evidence-case-003.webp', hook: '五个包裹经过同一条分拣线，三份日志各自只说了一半。' },
  'NA-004': { img: 'NA-004-episode-card.webp', hook: '第五盏灯整夜没亮，检修记录却坚持它从未熄灭。' },
  'NA-005': { img: 'NA-005-episode-card.webp', hook: '一封回信被签收，但邮袋里没有人记得把它寄出去。' },
  'NA-006': { img: 'NA-006-episode-card.webp', hook: '第零号底片上什么都没有，却占据了编号最靠前的一格。' },
};

const state = {
  route: 'home',
  caseId: null,
  cases: new Map(),      // id -> case data
  order: [],             // 当前排列
  selected: null,        // 当前选中的格位索引
  hintIndex: 0,          // 已揭开的提示数
  history: [],           // 撤销栈
  attempts: 0,
  solved: false,
  rulesMeta: new Map(),  // id -> 约束元信息
  necessity: new Map(),  // id -> necessity
  eventAbort: null,      // 当前视图的事件监听 AbortController
};

/* ------------------------------------------------------------------ */
/* 极小的 DOM 工具（不使用 innerHTML）                                 */
/* ------------------------------------------------------------------ */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (k === 'style') node.setAttribute('style', v);
    else if (k === 'aria') {
      for (const [ak, av] of Object.entries(v)) {
        if (av == null || av === false) continue;
        node.setAttribute(ak.startsWith('aria-') ? ak : `aria-${ak}`, String(av));
      }
    }
    else if (k === 'on') for (const [ek, fn] of Object.entries(v)) node.addEventListener(ek, fn);
    else node.setAttribute(k, v === true ? '' : String(v));
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    node.append(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
  }
  return node;
}

/** 内联 SVG 图标（装饰性，全部 aria-hidden）。 */
const ICON = {
  chevron: () => svg('M6 9l6 6 6-6'),
  up: () => svg('M12 19V5M5 12l7-7 7 7'),
  down: () => svg('M12 5v14M19 12l-7 7-7-7'),
  grip: () => svg('M9 6h.01M9 12h.01M9 18h.01M15 6h.01M15 12h.01M15 18h.01', 2.6),
  check: () => svg('M20 6L9 17l-5-5'),
  info: () => svg('M12 16v-4M12 8h.01', 2),
  arrow: () => svg('M5 12h14M13 5l7 7-7 7'),
  lock: () => svg('M7 11V7a5 5 0 0110 0v4M5 11h14v10H5z'),
};

function svg(d, width = 2) {
  const NS = 'http://www.w3.org/2000/svg';
  const s = document.createElementNS(NS, 'svg');
  s.setAttribute('viewBox', '0 0 24 24');
  s.setAttribute('fill', 'none');
  s.setAttribute('stroke', 'currentColor');
  s.setAttribute('stroke-width', String(width));
  s.setAttribute('stroke-linecap', 'round');
  s.setAttribute('stroke-linejoin', 'round');
  s.setAttribute('aria-hidden', 'true');
  s.setAttribute('focusable', 'false');
  const p = document.createElementNS(NS, 'path');
  p.setAttribute('d', d);
  s.append(p);
  s.style.width = '20px';
  s.style.height = '20px';
  s.style.flex = '0 0 auto';
  return s;
}

/* ------------------------------------------------------------------ */
/* 本地存储（全部包在 try/catch，隐私模式也能玩）                      */
/* ------------------------------------------------------------------ */
const store = {
  get(key, fallback = null) {
    try {
      const raw = localStorage.getItem(STORAGE_PREFIX + key);
      return raw == null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  remove(key) {
    try { localStorage.removeItem(STORAGE_PREFIX + key); } catch { /* 忽略 */ }
  },
  clearAll() {
    try {
      const keys = [];
      for (let i = 0; i < localStorage.length; i += 1) {
        const k = localStorage.key(i);
        if (k && k.startsWith(STORAGE_PREFIX)) keys.push(k);
      }
      keys.forEach((k) => localStorage.removeItem(k));
      return true;
    } catch {
      return false;
    }
  },
};

const progress = {
  all() { return store.get('progress', {}) || {}; },
  of(id) { return this.all()[id] || null; },
  markSolved(id, usedHints) {
    const all = this.all();
    const prev = all[id] || {};
    all[id] = {
      solved: true,
      usedHints: Boolean(prev.usedHints || usedHints),
      at: new Date().toISOString(),
      times: (prev.times || 0) + 1,
    };
    store.set('progress', all);
  },
  markHint(id) {
    const all = this.all();
    const prev = all[id] || {};
    all[id] = { ...prev, usedHints: true };
    store.set('progress', all);
  },
  savedOrder(id) { return store.get(`order:${id}`, null); },
  saveOrder(id, order, hintIndex) {
    store.set(`order:${id}`, { order, hintIndex, at: Date.now() });
  },
  dropOrder(id) { store.remove(`order:${id}`); },
  solvedCount() {
    return Object.values(this.all()).filter((x) => x && x.solved).length;
  },
};

/* ------------------------------------------------------------------ */
/* 提示条                                                              */
/* ------------------------------------------------------------------ */
let toastTimer = null;
function toast(text) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = text;
  t.dataset.show = 'true';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.dataset.show = 'false'; }, 2600);
}

/* ------------------------------------------------------------------ */
/* 确认对话框（原生 <dialog>，失败时回退到 window.confirm 语义）        */
/* ------------------------------------------------------------------ */
function confirmDialog({ title, body, okText = '确认' }) {
  const dlg = $('#confirm-dialog');
  if (!dlg || typeof dlg.showModal !== 'function') {
    return Promise.resolve(window.confirm(`${title}\n\n${body}`));
  }
  $('#confirm-title').textContent = title;
  $('#confirm-body').textContent = body;
  const ok = dlg.querySelector('[data-confirm="ok"]');
  ok.textContent = okText;
  return new Promise((resolve) => {
    let settled = false;
    const done = (value) => {
      if (settled) return;
      settled = true;
      dlg.removeEventListener('close', onClose);
      ok.removeEventListener('click', onOk);
      const cancel = dlg.querySelector('[data-confirm="cancel"]');
      cancel.removeEventListener('click', onCancel);
      if (dlg.open) dlg.close();
      resolve(value);
    };
    const onClose = () => done(dlg.returnValue === 'ok');
    const onOk = () => { dlg.returnValue = 'ok'; done(true); };
    const onCancel = () => { dlg.returnValue = 'cancel'; done(false); };
    dlg.addEventListener('close', onClose);
    ok.addEventListener('click', onOk);
    dlg.querySelector('[data-confirm="cancel"]').addEventListener('click', onCancel);
    dlg.showModal();
    ok.focus();
  });
}

/* ------------------------------------------------------------------ */
/* 路由                                                                */
/* ------------------------------------------------------------------ */
function parseHash() {
  const raw = (location.hash || '#/').replace(/^#/, '');
  const parts = raw.split('/').filter(Boolean);
  if (parts.length === 0) return { view: 'home' };
  if (parts[0] === 'case') {
    // 合法案件编号才进入调查桌；否则明确标记无法识别，给出可读提示
    if (/^NA-\d{3}$/.test(parts[1] || '')) return { view: 'case', id: parts[1] };
    return { view: 'home', invalid: true, raw };
  }
  if (['cabinet', 'manual', 'about'].includes(parts[0])) return { view: parts[0] };
  return { view: 'home', invalid: true, raw };
}

const ROUTES = ['home', 'cabinet', 'case', 'manual', 'about'];

/**
 * 确定性洗牌：用案件 ID 派生种子，保证同一案每次进入的初始排列一致
 * （便于测试复现），同时不会恰好等于答案或恰好满足全部约束。
 */
function deterministicScramble(items, seedText, constraints) {
  let seed = 0;
  for (let i = 0; i < seedText.length; i += 1) {
    seed = (seed * 31 + seedText.charCodeAt(i)) >>> 0;
  }
  const next = (n) => {
    seed ^= seed << 13; seed >>>= 0;
    seed ^= seed >>> 17;
    seed ^= seed << 5; seed >>>= 0;
    return seed % n;
  };
  const base = [...items];
  let out = base;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    out = [...base];
    for (let i = out.length - 1; i > 0; i -= 1) {
      const j = next(i + 1);
      [out[i], out[j]] = [out[j], out[i]];
    }
    const solved = constraints.every((r) => {
      try { return checkRule(out, r); } catch { return false; }
    });
    if (!solved && out.join('\u0000') !== base.join('\u0000')) return out;
  }
  // 兜底：直接交换首尾
  out = [...base];
  [out[0], out[out.length - 1]] = [out[out.length - 1], out[0]];
  return out;
}

function showView(name) {
  for (const r of ROUTES) {
    const node = $(`#view-${r}`);
    if (node) node.dataset.active = String(r === name);
  }
  $$('.site-nav a').forEach((a) => {
    const target = a.dataset.nav;
    const active = (name === 'case' && target === 'cabinet') || target === name;
    if (active) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  });
  // 关闭移动端菜单
  const nav = $('#site-nav');
  const toggle = $('#nav-toggle');
  if (nav) nav.dataset.open = 'false';
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
}

async function router() {
  const route = parseHash();
  state.route = route.view;

  if (state.eventAbort) state.eventAbort.abort();
  state.eventAbort = null;

  if (route.view === 'case') {
    showView('case');
    await openCase(route.id);
    // 从档案柜 / 结案页跳进来时，确保从调查桌顶端开始读，而不是停在上一页的滚动位置
    window.scrollTo({ top: 0, behavior: 'auto' });
    return;
  }

  showView(route.view);
  if (route.invalid) {
    toast('这个地址没有对应的档案，已回到封面。');
    if (history.replaceState) history.replaceState(null, '', '#/');
  }
  document.title = {
    home: '第零证物局｜雾港异常档案 · 原创互动推理',
    cabinet: '档案柜｜第零证物局',
    manual: '玩法说明｜第零证物局',
    about: '关于与隐私｜第零证物局',
  }[route.view] || '第零证物局';

  if (route.view === 'home') renderHomeCabinet();
  if (route.view === 'cabinet') renderCabinet();
  window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  $('#main')?.focus({ preventScroll: true });
}

/* ------------------------------------------------------------------ */
/* 案件数据加载                                                        */
/* ------------------------------------------------------------------ */
async function loadCase(id) {
  if (state.cases.has(id)) return state.cases.get(id);
  if (!RELEASED.has(id)) throw new Error('该案尚未通过全部门禁');
  const res = await fetch(`./cases/${id}.json`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`案件文件不可用（HTTP ${res.status}）`);
  const data = await res.json();
  if (data.id !== id) throw new Error('案件编号与文件名不一致');

  assertCaseShape(data);

  const solved = countSolutions(data.items, data.constraints);
  if (solved.count !== 1) throw new Error('该案未通过唯一解校验，已暂停展示');

  const necessity = necessityReport(data.items, data.constraints);
  state.necessity.set(id, new Map(necessity.map((n) => [n.id, n])));
  state.rulesMeta.set(id, new Map(data.constraints.map((r) => [r.id, r])));

  // 每张证据 -> 它承载的约束的玩家语言
  data.evidence = data.evidence.map((e) => ({
    ...e,
    readableRules: e.constraint_ids.map((cid) => {
      const rule = data.constraints.find((r) => r.id === cid);
      return describeRule(rule, data.slots);
    }),
  }));

  state.cases.set(id, data);
  return data;
}

/* ------------------------------------------------------------------ */
/* 档案柜渲染                                                          */
/* ------------------------------------------------------------------ */
function statusOf(id) {
  if (!RELEASED.has(id)) return 'locked';
  return progress.of(id)?.solved ? 'done' : 'ready';
}

function caseCard(id, { compact = false } = {}) {
  const c = state.cases.get(id);
  const meta = CASE_META[id] || {};
  const st = statusOf(id);
  const title = c?.title || id;
  const hook = meta.hook || '';
  const chapter = c?.chapter;

  const card = el('article', { class: `case-card${st === 'locked' ? ' case-card--locked' : ''}` });

  const thumb = el('div', { class: 'case-card__thumb' });
  if (meta.img) {
    const img = el('img', {
      src: `./assets/${meta.img}`,
      alt: '',
      loading: 'lazy',
      decoding: 'async',
      width: 640,
      height: 360,
    });
    thumb.append(img);
  }
  thumb.append(el('span', { class: 'case-card__no', text: `档案 #${id.slice(3)}` }));
  card.append(thumb);

  const body = el('div', { class: 'case-card__body' });
  body.append(el('h3', { class: 'case-card__title', text: title }));
  body.append(el('p', { class: 'case-card__hook', text: hook }));

  const metaRow = el('div', { class: 'case-card__meta' });
  if (c) {
    metaRow.append(el('span', { text: c.difficulty || '—' }));
    metaRow.append(el('span', { text: `设计预计 ${c.play_minutes?.[0] ?? '3'}–${c.play_minutes?.[1] ?? '5'} 分钟` }));
  }
  const badgeText = st === 'done' ? '已归档 · 可重看' : st === 'ready' ? '可调查' : '修复中 · 暂不可调查';
  const badgeCls = st === 'done' ? 'case-card__status--done' : st === 'ready' ? 'case-card__status--ready' : 'case-card__status--locked';
  metaRow.append(el('span', { class: `case-card__status ${badgeCls}`, text: badgeText }));
  body.append(metaRow);

  if (st === 'locked') {
    body.append(el('button', { class: 'btn btn--ghost case-card__cta', type: 'button', disabled: true }, [
      el('span', { text: '待开放' }),
    ]));
  } else {
    body.append(el('a', {
      class: 'btn btn--primary case-card__cta',
      href: `#/case/${id}`,
      aria: { label: `${st === 'done' ? '重看' : '调查'}档案 ${id.slice(3)}：${title}` },
    }, [
      el('span', { text: st === 'done' ? '重看此案' : '立即调查' }),
      ICON.arrow(),
    ]));
  }
  card.append(body);
  return card;
}

function renderActBlocks(host, { compact = false } = {}) {
  host.replaceChildren();
  for (const act of ACTS) {
    const available = act.cases.filter((id) => RELEASED.has(id));
    if (available.length === 0) continue;
    const section = el('section', { class: 'act' });
    const head = el('div', { class: 'act__head' });
    head.append(el('span', { class: 'act__roman', text: act.roman }));
    const headText = el('div');
    headText.append(el('h2', { class: 'act__title', text: `第 ${act.roman} 幕 · ${act.title}` }));
    headText.append(el('p', { class: 'act__desc', text: act.desc }));
    head.append(headText);
    section.append(head);
    const grid = el('div', { class: 'case-grid' });
    for (const id of available) grid.append(caseCard(id, { compact }));
    section.append(grid);
    host.append(section);
  }
}

function renderHomeCabinet() {
  const host = $('#home-cabinet');
  if (!host) return;
  // 首页只展示第一幕，避免剧透第 006 案
  host.replaceChildren();
  const act = ACTS[0];
  const section = el('section', { class: 'act' });
  const head = el('div', { class: 'act__head' });
  head.append(el('span', { class: 'act__roman', text: act.roman }));
  const t = el('div');
  t.append(el('h2', { class: 'act__title', text: `第 ${act.roman} 幕 · ${act.title}` }));
  t.append(el('p', { class: 'act__desc', text: act.desc }));
  head.append(t);
  section.append(head);
  const grid = el('div', { class: 'case-grid' });
  for (const id of act.cases.filter((x) => RELEASED.has(x))) grid.append(caseCard(id));
  section.append(grid);
  host.append(section);
}

function renderCabinet() {
  const host = $('#cabinet');
  if (!host) return;
  renderActBlocks(host);
  const done = progress.solvedCount();
  const badge = $('#progress-badge');
  if (badge) badge.textContent = `已归档 ${done} / ${RELEASED.size}`;
}

/* ------------------------------------------------------------------ */
/* 调查桌                                                              */
/* ------------------------------------------------------------------ */
async function openCase(id) {
  const root = $('#case-root');
  if (!root) return;
  root.replaceChildren(el('div', { class: 'loading' }, [
    el('div', { class: 'spinner' }),
    el('p', { text: '正在取阅档案…' }),
  ]));

  let c;
  try {
    c = await loadCase(id);
  } catch (err) {
    root.replaceChildren(el('div', { class: 'empty-state' }, [
      el('h2', { text: '这份档案尚未完整送达' }),
      el('p', { text: err.message || '请刷新，或回到档案柜。' }),
      el('p', {}, [el('a', { class: 'btn btn--ghost', href: '#/cabinet', text: '返回档案柜' })]),
    ]));
    return;
  }

  state.caseId = id;
  state.solved = false;
  state.attempts = 0;
  state.history = [];
  state.selected = null;

  // 恢复进度：保存的排列 / 提示 / 是否已解
  const saved = progress.savedOrder(id);
  const prog = progress.of(id);
  const solvedBefore = Boolean(prog?.solved);

  // 存档校验：必须是本案物件的完整排列。旧版本存档 / 手改 localStorage / 案件改版
  // 都可能带来不存在的物件名，此时必须丢弃存档并重置，而不是让页面卡在加载态。
  let restored = null;
  if (Array.isArray(saved?.order)) {
    const legit = new Set(c.items);
    const unique = new Set(saved.order).size === saved.order.length;
    const sameLength = saved.order.length === c.items.length;
    const allKnown = saved.order.every((x) => legit.has(x));
    if (sameLength && unique && allKnown) restored = [...saved.order];
    else progress.dropOrder(id);   // 丢弃不兼容存档，顺带清掉损坏数据
  }
  state.order = restored ?? [...c.items];
  state.hintIndex = Number.isInteger(saved?.hintIndex) ? saved.hintIndex : 0;

  // 绝不默认给出答案：若初始排列恰好满足全部约束，做一次确定性错位。
  // 只交换前两格太容易被「照着顺序点」猜到，这里改用按案件 ID 派生的确定性洗牌，
  // 并保证结果既不等于答案、也不满足全部约束（连续洗牌直到两者都成立）。
  if (verifyOrder(state.order, c.constraints).every((r) => r.valid)) {
    state.order = deterministicScramble(state.order, c.id, c.constraints);
  }

  document.title = `${c.title}｜第零证物局`;
  const crumb = $('#crumb-case');
  if (crumb) crumb.textContent = `档案 #${id.slice(3)} · ${c.title}`;
  if (solvedBefore) toast('这份档案已在本地归档，你可以重看或重新调查。');

  try {
    renderDesk(c);
    bindDeskEvents(c);
  } catch (err) {
    // 渲染期异常同样兜底，绝不把玩家留在「正在取阅档案…」加载态
    root.replaceChildren(el('div', { class: 'empty-state' }, [
      el('h2', { text: '这份档案暂时无法展开' }),
      el('p', { text: err.message || '请刷新，或回到档案柜。' }),
      el('p', {}, [el('a', { class: 'btn btn--ghost', href: '#/cabinet', text: '返回档案柜' })]),
    ]));
  }
}

function renderDesk(c) {
  const root = $('#case-root');
  root.replaceChildren();

  const head = el('div', { class: 'desk-head' });
  const headText = el('div');
  headText.append(el('span', { class: 'eyebrow', text: `第 ${c.chapter || '?'} 幕 · ${c.theme || '雾港档案'}` }));
  headText.append(el('h1', { class: 'desk-head__title', id: 'case-title', text: c.title }));
  headText.append(el('p', { class: 'desk-head__sub', text: c.subtitle || '' }));
  head.append(headText);

  const meta = el('div', { style: 'display:flex;flex-wrap:wrap;gap:.5rem;align-items:center' });
  meta.append(el('span', { class: 'pill', text: c.difficulty || '—' }));
  meta.append(el('span', { class: 'pill pill--mist', text: `档案 #${c.id.slice(3)}` }));
  if (progress.of(c.id)?.solved) meta.append(el('span', { class: 'pill pill--ok', text: '已在本地归档' }));
  head.append(meta);
  root.append(head);

  const desk = el('div', { class: 'desk' });

  /* ---------- 左：证据 ---------- */
  const evCol = el('section', { class: 'evidence-col', aria: { labelledby: 'ev-heading' } });
  const evHead = el('div', { class: 'col-head' });
  evHead.append(el('h2', { class: 'h3', id: 'ev-heading', text: '已采集证物', style: 'font-size:var(--step-1);margin:0' }));
  evHead.append(el('p', { class: 'hint', text: `${c.evidence.length} 份 · 可逐张展开` }));
  evCol.append(evHead);

  const setup = el('div', { class: 'recap-block', style: 'margin-bottom:var(--sp-4);padding:var(--sp-4)' });
  setup.append(el('p', { style: 'margin-bottom:.5rem;font-size:var(--step--1);color:var(--text-dim)', text: c.setting || '' }));
  setup.append(el('p', { style: 'margin:0;color:var(--paper);font-weight:600;font-size:var(--step--1)', text: `目标：${c.objective || ''}` }));
  evCol.append(setup);

  const list = el('div', { class: 'evidence-list' });
  c.evidence.forEach((ev, i) => {
    const open = i === 0; // 默认展开第一张，降低进入成本
    const card = el('article', { class: 'ev-card', dataset: { open: String(open), evId: ev.id } });
    const btnId = `ev-btn-${ev.id}`;
    const bodyId = `ev-body-${ev.id}`;
    const summary = el('button', {
      class: 'ev-card__summary', type: 'button', id: btnId,
      aria: { expanded: String(open), controls: bodyId },
    }, [
      el('span', { class: 'ev-card__id', text: ev.id }),
      el('span', { class: 'ev-card__title', text: ev.title }),
      el('span', { class: 'ev-card__type', text: ev.type }),
      withClass(ICON.chevron(), 'ev-card__chev'),
    ]);
    const body = el('div', { class: 'ev-card__body', id: bodyId });
    if (!open) body.hidden = true;
    body.append(el('p', { text: ev.body }));
    if (ev.readableRules?.length) {
      const rule = el('span', { class: 'ev-card__rule' });
      rule.append(el('strong', { text: '可核对的关系：' }));
      rule.append(document.createTextNode(ev.readableRules.join(' ')));
      body.append(rule);
    }
    card.append(summary, body);
    list.append(card);
  });
  evCol.append(list);

  // 主线彩蛋 + 局长短句：放在证物册末尾，读不读都不影响解题（非承重）
  const afterword = el('div', { class: 'case-afterword' });
  if (c.motif) {
    afterword.append(el('p', { class: 'case-afterword__motif' }, [
      el('span', { class: 'case-afterword__tag', text: '案卷边注' }),
      document.createTextNode(c.motif),
    ]));
  }
  if (c.director_note) {
    afterword.append(el('p', { class: 'case-afterword__note' }, [
      el('span', { class: 'case-afterword__who', text: '局长 · 陆柏：' }),
      document.createTextNode(`「${c.director_note}」`),
    ]));
  }
  if (afterword.childElementCount) evCol.append(afterword);

  desk.append(evCol);

  /* ---------- 右：复原板 ---------- */
  const orderCol = el('section', { class: 'order-col', aria: { labelledby: 'board-heading' } });
  const board = el('div', { class: 'board' });

  const bHead = el('div', { class: 'col-head' });
  bHead.append(el('h2', { id: 'board-heading', text: '复原格位', style: 'font-size:var(--step-1);margin:0' }));
  bHead.append(el('p', { class: 'hint', text: `共 ${c.slots.length} 格` }));
  board.append(bHead);

  const goal = el('div', { class: 'board__goal' });
  goal.append(ICON.info());
  goal.append(el('span', { text: '点击卡片选中，再点目标格位交换；也可以用 ↑ ↓ 按钮。键盘可用 Tab 与上下方向键。' }));
  board.append(goal);

  const slots = el('ol', { class: 'slots', id: 'slots', aria: { label: '复原格位列表' } });
  board.append(slots);
  orderCol.append(board);

  const actions = el('div', { class: 'actions' });
  actions.append(el('button', { class: 'btn btn--primary', type: 'button', id: 'btn-submit', text: '提交复原' }));
  actions.append(el('button', { class: 'btn', type: 'button', id: 'btn-undo', text: '撤销一步' }));
  actions.append(el('button', { class: 'btn', type: 'button', id: 'btn-hint', text: '查看提示' }));
  actions.append(el('button', { class: 'btn btn--danger', type: 'button', id: 'btn-reset', text: '重置此案' }));
  board.append(actions);

  const status = el('div', { class: 'status-bar' });
  status.append(el('span', { class: 'status-dot', id: 'status-dot', dataset: { state: 'idle' }, aria: { hidden: 'true' } }));
  status.append(el('span', { id: 'status-text', text: '准备核对' }));
  board.append(status);

  const msg = el('div', { class: 'message', id: 'message', role: 'status', aria: { live: 'polite' } });
  board.append(msg);

  const hints = el('div', { class: 'hints', id: 'hints', role: 'region', aria: { label: '已揭开的提示' } });
  board.append(hints);

  desk.append(orderCol);
  root.append(desk);

  drawSlots();
  drawHints();
  syncButtons();
}

function withClass(node, cls) {
  node.classList.add(cls);
  return node;
}

function drawSlots(focus = null) {
  const c = state.cases.get(state.caseId);
  const host = $('#slots');
  if (!c || !host) return;
  host.replaceChildren();

  state.order.forEach((item, i) => {
    const selected = state.selected === i;
    const li = el('li', {
      class: 'slot',
      dataset: { index: String(i), selected: String(selected) },
      draggable: 'true',
    });

    li.append(el('span', { class: 'slot__index', text: String(i + 1), aria: { hidden: 'true' } }));

    const main = el('div', { class: 'slot__main' });
    main.append(el('span', { class: 'slot__label', text: c.slots[i] || `第${i + 1}格` }));
    main.append(el('span', { class: 'slot__item', text: item }));
    li.append(main);

    const acts = el('div', { class: 'slot__actions' });

    const grip = el('span', { class: 'slot__grip', title: '拖动此卡到其它格位', aria: { hidden: 'true' } }, [ICON.grip()]);
    acts.append(grip);

    const up = el('button', {
      class: 'icon-btn', type: 'button',
      dataset: { act: 'up' },
      aria: { label: `将「${item}」上移一格`, disabled: String(i === 0) },
      disabled: i === 0,
    }, [ICON.up()]);
    const down = el('button', {
      class: 'icon-btn', type: 'button',
      dataset: { act: 'down' },
      aria: { label: `将「${item}」下移一格`, disabled: String(i === state.order.length - 1) },
      disabled: i === state.order.length - 1,
    }, [ICON.down()]);
    const pick = el('button', {
      class: 'icon-btn', type: 'button',
      dataset: { act: 'pick' },
      aria: { label: selected ? `取消选中「${item}」` : `选中「${item}」以交换位置`, pressed: String(selected) },
    }, [ICON.check()]);

    acts.append(up, down, pick);
    li.append(acts);

    // 让整行可点击选中（但按钮区域除外）
    li.addEventListener('click', (e) => {
      if (e.target.closest('button')) return;
      onPick(i);
    });

    host.append(li);
  });

  if (focus) {
    const target = host.querySelector(`[data-index="${focus.index}"] [data-act="${focus.act}"]`);
    if (target && !target.disabled) target.focus();
    else {
      const pick = host.querySelector(`[data-index="${focus.index}"] [data-act="pick"]`);
      pick?.focus();
    }
  }
}

function drawHints() {
  const c = state.cases.get(state.caseId);
  const host = $('#hints');
  if (!c || !host) return;
  host.replaceChildren();
  const shown = c.hints.slice(0, state.hintIndex);
  shown.forEach((text, i) => {
    const card = el('div', { class: 'hint-card' });
    card.append(el('span', { class: 'hint-card__no', text: `档案员注 ${String(i + 1).padStart(2, '0')} ／ ${String(c.hints.length).padStart(2, '0')}` }));
    card.append(document.createTextNode(text));
    host.append(card);
  });
}

function syncButtons() {
  const c = state.cases.get(state.caseId);
  if (!c) return;
  const hintBtn = $('#btn-hint');
  if (hintBtn) {
    const exhausted = state.hintIndex >= c.hints.length;
    hintBtn.disabled = exhausted;
    hintBtn.textContent = exhausted ? '提示已全部解封' : (state.hintIndex === 0 ? '查看提示' : `查看提示（${state.hintIndex}/${c.hints.length}）`);
  }
  const undo = $('#btn-undo');
  if (undo) undo.disabled = state.history.length === 0;
}

function setStatus(kind, text) {
  const dot = $('#status-dot');
  const label = $('#status-text');
  if (dot) dot.dataset.state = kind;
  if (label) label.textContent = text;
}

function setMessage(kind, content) {
  const msg = $('#message');
  if (!msg) return;
  msg.replaceChildren();
  msg.className = `message message--${kind}`;
  msg.dataset.show = 'true';
  for (const node of [].concat(content)) {
    if (node == null) continue;
    msg.append(typeof node === 'string' ? document.createTextNode(node) : node);
  }
}

function clearMessage() {
  const msg = $('#message');
  if (!msg) return;
  msg.dataset.show = 'false';
  msg.replaceChildren();
}

function persist() {
  if (!state.caseId) return;
  progress.saveOrder(state.caseId, state.order, state.hintIndex);
}

/* ---------- 交互动作 ---------- */
function onPick(i) {
  if (state.solved) return;
  if (state.selected == null) {
    state.selected = i;
    clearMessage();
    drawSlots({ index: i, act: 'pick' });   // 重建 DOM 后把焦点放回同一格
    const item = state.order[i];
    setStatus('warn', `已选中「${item}」，请点目标格位`);
    toast(`已选中「${item}」，再点一个格位即可交换`);
    return;
  }
  if (state.selected === i) {
    state.selected = null;
    drawSlots({ index: i, act: 'pick' });
    setStatus('idle', '准备核对');
    return;
  }
  swap(state.selected, i);
  state.selected = null;
}

function swap(a, b) {
  if (a === b) return;
  state.history.push([...state.order]);
  [state.order[a], state.order[b]] = [state.order[b], state.order[a]];
  clearMessage();
  setStatus('idle', '已调整排列，等待核对');
  persist();
  drawSlots();
  drawHints();
  syncButtons();
}

function move(i, delta, act = delta < 0 ? 'up' : 'down') {
  if (state.solved) return;
  const j = i + delta;
  if (j < 0 || j >= state.order.length) return;
  state.history.push([...state.order]);
  [state.order[i], state.order[j]] = [state.order[j], state.order[i]];
  state.selected = null;
  clearMessage();
  setStatus('idle', '已调整排列，等待核对');
  persist();
  drawSlots({ index: j, act });
  syncButtons();
}

function undo() {
  if (state.history.length === 0) return;
  state.order = state.history.pop();
  state.selected = null;
  clearMessage();
  setStatus('idle', '已撤销一步');
  persist();
  drawSlots();
  syncButtons();
}

function revealHint() {
  const c = state.cases.get(state.caseId);
  if (!c) return;
  if (state.hintIndex >= c.hints.length) {
    setMessage('info', '提示已全部解封，你仍可继续自由尝试。');
    return;
  }
  state.hintIndex += 1;
  progress.markHint(c.id);
  persist();
  drawHints();
  syncButtons();
  const card = $('#hints')?.lastElementChild;
  card?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  setMessage('info', '提示只是帮你推进，不会自动完成排列。');
}

/* ---------- 提交 ---------- */
function submit() {
  const c = state.cases.get(state.caseId);
  if (!c || state.solved) return;
  state.attempts += 1;

  const checks = verifyOrder(state.order, c.constraints);
  const bad = checks.filter((x) => !x.valid);

  if (bad.length > 0) {
    // 先按证据分组：不透露正确位置，只说哪张证据与你的排列冲突
    const conflicting = c.evidence.filter((e) => e.constraint_ids.some((cid) => bad.some((b) => b.id === cid)));
    const list = el('ul');
    for (const e of conflicting) {
      list.append(el('li', { text: `${e.id}「${e.title}」中描述的关系与你的排列不一致。` }));
    }
    setMessage('bad', [
      el('strong', { text: `档案仍有不一致：${bad.length} 条关系未满足。` }),
      el('p', { style: 'margin:.5rem 0 .25rem', text: '你的排列已保留，可以继续核对先后、距离或「夹在中间」的描述。' }),
      list,
    ]);
    setStatus('bad', `存在 ${bad.length} 处与证据不符的关系`);
    // 轻声标记冲突格位（不提示正确答案，只标记被涉及物件所在位置）
    flashConflicts(bad, c);
    return;
  }

  // ---- 成功 ----
  state.solved = true;
  progress.markSolved(c.id, state.hintIndex > 0);
  progress.dropOrder(c.id);
  setStatus('ok', '全部关系均已满足 · 可以归档');
  setMessage('ok', `档案归位。你用了 ${state.hintIndex} 条提示。正在生成结案页…`);
  const stateBox = $('.status-bar');
  stateBox?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  setTimeout(() => renderVerdict(c, checks), 420);
}

function flashConflicts(bad, c) {
  const involved = new Set();
  for (const b of bad) {
    const rule = state.rulesMeta.get(c.id)?.get(b.id);
    if (!rule) continue;
    involved.add(rule.a);
    if (rule.b) involved.add(rule.b);
    if (rule.c) involved.add(rule.c);
  }
  $$('#slots .slot').forEach((li) => {
    const i = Number(li.dataset.index);
    if (involved.has(state.order[i])) {
      li.dataset.flash = 'bad';
      setTimeout(() => { delete li.dataset.flash; }, 1400);
    }
  });
}

/* ------------------------------------------------------------------ */
/* 结案复盘：逻辑（严格可证明）+ 档案后记（叙事）分两段               */
/* ------------------------------------------------------------------ */
function renderVerdict(c, checks) {
  const root = $('#case-root');
  const necessity = state.necessity.get(c.id) || new Map();

  const box = el('section', { class: 'verdict', aria: { labelledby: 'verdict-title' } });

  box.append(el('div', { class: 'stamp', text: '档案归位' }));
  box.append(el('h1', { id: 'verdict-title', class: 'verdict__h1', tabindex: '-1', text: '档案归位。' }));
  box.append(el('p', { class: 'verdict__lede', text: '没有凭空消失的证物，只有尚未排列好的事实。' }));

  /* --- 第一部分：逻辑复盘（严格可证明） --- */
  const logic = el('div', { class: 'recap-block' });
  logic.append(el('span', { class: 'recap-block__label' }, [ICON.check(), document.createTextNode(' 逻辑复盘 · 可由证据严格证明')]));

  const strip = el('ol', { class: 'solution-strip', aria: { label: '最终排列' } });
  state.order.forEach((item, i) => {
    strip.append(el('li', {}, [
      el('span', { text: item }),
      el('small', { text: ` ${c.slots[i] || `第${i + 1}格`}`, style: 'color:var(--brass);font-family:var(--font-ui);font-weight:600' }),
    ]));
  });
  logic.append(el('h2', { class: 'recap-h', text: '你的最终排列' }));
  logic.append(strip);

  logic.append(el('h2', { class: 'recap-h', style: 'margin-top:var(--sp-5)', text: '每条证据如何锁死一个位置' }));
  const scroll = el('div', { class: 'table-scroll' });
  const table = el('table', { class: 'chain-table' });
  table.append(el('thead', {}, [el('tr', {}, [
    el('th', { text: '证据' }),
    el('th', { text: '这条关系说的是' }),
    el('th', { text: '为什么必须' }),
  ])]));
  const tbody = el('tbody');

  c.evidence.forEach((ev) => {
    const rules = ev.constraint_ids.map((cid) => state.rulesMeta.get(c.id)?.get(cid)).filter(Boolean);
    const desc = rules.map((r) => describeRule(r, c.slots)).join(' ');
    const why = rules.map((r) => explainWhy(necessity.get(r.id))).filter(Boolean).join(' ');
    tbody.append(el('tr', {}, [
      el('td', {}, [el('span', { text: ev.id }), el('br', {}), el('span', { text: ev.title, style: 'font-family:var(--font-ui);color:var(--text);font-size:.8rem' })]),
      el('td', { text: desc }),
      el('td', { class: 'why', text: why }),
    ]));
  });
  table.append(tbody);
  scroll.append(table);
  logic.append(scroll);
  logic.append(el('p', {
    style: 'margin-top:var(--sp-4);font-size:var(--step--1);color:var(--mist);margin-bottom:0',
    text: `形式化核对：${checks.length} 条关系全部满足；在 ${c.items.length} 件物件的全部排列中，这一组证据只允许 1 种排法。上述内容只陈述可由证据推出的顺序事实。`,
  }));
  box.append(logic);

  /* --- 第二部分：档案后记（叙事，不是形式化结论） --- */
  const story = el('div', { class: 'recap-block recap-block--story' });
  story.append(el('span', { class: 'recap-block__label' }, [ICON.info(), document.createTextNode(' 档案后记 · 结案后补充记录')]));
  story.append(el('p', { style: 'color:var(--paper);font-size:var(--step-1);line-height:1.75', text: c.epilogue || c.resolution || '' }));
  if (c.twist) {
    story.append(el('p', { style: 'margin-bottom:0;color:var(--text-dim);font-size:var(--step--1)' }, [
      el('strong', { text: '本案的记录机制：' }), document.createTextNode(c.twist),
    ]));
  }
  story.append(el('p', {
    style: 'margin-top:var(--sp-4);margin-bottom:0;font-size:0.76rem;color:var(--mist);border-top:1px dashed rgb(158 183 180/.25);padding-top:.6rem',
    text: '以上后记为调查人员事后补写的虚构叙述，用于交代人物与背景；它不构成刚才排序推理的证明。',
  }));
  box.append(story);

  /* --- 操作 --- */
  const actions = el('div', { class: 'verdict__actions' });
  const nextId = nextReleasedCase(c.id);
  if (nextId) {
    actions.append(el('a', { class: 'btn btn--primary', href: `#/case/${nextId}`, text: c.id === 'NA-006' ? '查看终章' : `继续下一案 #${nextId.slice(3)}` }));
  }
  actions.append(el('a', { class: 'btn', href: '#/cabinet', text: '返回档案柜' }));
  actions.append(el('button', { class: 'btn btn--ghost', type: 'button', id: 'btn-replay', text: '重新调查此案' }));
  box.append(actions);

  if (c.id === 'NA-006') {
    const finale = el('div', { class: 'recap-block', style: 'margin-top:var(--sp-6);border:1px solid rgb(223 185 120/.35)' });
    finale.append(el('span', { class: 'recap-block__label', text: '终章 · 第零号 ／ 结案后补充记录' }));
    finale.append(el('p', { style: 'font-family:var(--font-serif);font-size:var(--step-2);line-height:1.5;color:var(--paper)', text: '第零号，不是第一张之前的照片。' }));
    finale.append(el('p', { style: 'color:var(--text-dim)', text: '它是一条不该被当成事件的记录。底片没有骗人——错的是那一栏「拍摄内容」：一次校准光圈的动作，被登记成了第六次真实曝光，六张底片于是看起来比五个瞬间多出一张。' }));
    finale.append(el('p', { style: 'color:var(--text-dim);font-weight:600', text: '所以「第零号证物」不是超自然物件，而是一次分类错误：把「校准」写进了「事件」的类目。' }));
    finale.append(el('p', { style: 'color:var(--text-dim)', text: '局长把半圈「0」章盖在每一份分类不确定的档案上，从来不是为了隐藏真相，而是为了提醒下一位读档者：先问「它是什么」，再问「它发生了什么」。' }));
    box.append(finale);
  }

  root.replaceChildren(box);
  root.scrollIntoView({ block: 'start', behavior: 'smooth' });
  $('#verdict-title')?.focus?.();

  $('#btn-replay')?.addEventListener('click', async () => {
    const ok = await confirmDialog({
      title: '重新调查此案？',
      body: '会清空本案的本地排列进度（归档标记保留）。',
      okText: '重新开始',
    });
    if (!ok) return;
    progress.dropOrder(c.id);
    state.hintIndex = 0;
    state.history = [];
    state.selected = null;
    openCase(c.id);
  });
}

function nextReleasedCase(id) {
  const all = ACTS.flatMap((a) => a.cases).filter((x) => RELEASED.has(x));
  const i = all.indexOf(id);
  return i >= 0 && i < all.length - 1 ? all[i + 1] : null;
}

/* ------------------------------------------------------------------ */
/* 调查桌事件绑定                                                      */
/* ------------------------------------------------------------------ */
function bindDeskEvents(c) {
  state.eventAbort = new AbortController();
  const { signal } = state.eventAbort;

  const root = $('#case-root');
  root.addEventListener('click', (e) => {
    const summary = e.target.closest('.ev-card__summary');
    if (summary) {
      const card = summary.closest('.ev-card');
      const open = card.dataset.open === 'true';
      card.dataset.open = String(!open);
      summary.setAttribute('aria-expanded', String(!open));
      const body = card.querySelector('.ev-card__body');
      if (body) body.hidden = open;
      return;
    }

    const btn = e.target.closest('[data-act]');
    if (btn) {
      const li = btn.closest('.slot');
      const i = Number(li.dataset.index);
      const act = btn.dataset.act;
      if (act === 'up') move(i, -1, 'up');
      else if (act === 'down') move(i, 1, 'down');
      else if (act === 'pick') onPick(i);
    }
  }, { signal });

  root.addEventListener('keydown', (e) => {
    // Esc 取消选中：不要求焦点在格位内（玩家可能刚点过别处）
    if (e.key === 'Escape' && state.selected != null) {
      state.selected = null;
      drawSlots();
      setStatus('idle', '已取消选中');
      return;
    }
    const li = e.target.closest('.slot');
    if (!li) return;
    // 只在格位区域内响应上下键，避免影响页面滚动时误触
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      const i = Number(li.dataset.index);
      const delta = e.key === 'ArrowUp' ? -1 : 1;
      if ((delta < 0 && i === 0) || (delta > 0 && i === state.order.length - 1)) return;
      e.preventDefault();
      move(i, delta, delta < 0 ? 'up' : 'down');
    }
  }, { signal });

  $('#btn-submit')?.addEventListener('click', submit, { signal });
  $('#btn-undo')?.addEventListener('click', undo, { signal });
  $('#btn-hint')?.addEventListener('click', revealHint, { signal });
  $('#btn-reset')?.addEventListener('click', async () => {
    const ok = await confirmDialog({
      title: '重置此案？',
      body: '重置会清空这份档案的本地排列进度。确定吗？',
      okText: '确认重置',
    });
    if (!ok) return;
    state.order = [...c.items];
    if (verifyOrder(state.order, c.constraints).every((r) => r.valid)) {
      state.order = deterministicScramble(state.order, c.id, c.constraints);
    }
    state.history = [];
    state.selected = null;
    state.hintIndex = 0;
    progress.dropOrder(c.id);
    clearMessage();
    setStatus('idle', '准备核对');
    drawSlots();
    drawHints();
    syncButtons();
    toast('已重置本案排列与提示进度');
  }, { signal });

  // ---- 拖放（增强项；按钮始终可用）----
  let dragFrom = null;
  root.addEventListener('dragstart', (e) => {
    const li = e.target.closest('.slot');
    if (!li) return;
    dragFrom = Number(li.dataset.index);
    li.dataset.dragging = 'true';
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', String(dragFrom)); } catch { /* 忽略 */ }
  }, { signal });
  root.addEventListener('dragend', () => {
    dragFrom = null;
    $$('#slots .slot').forEach((x) => { delete x.dataset.dragging; delete x.dataset.dragover; });
  }, { signal });
  root.addEventListener('dragover', (e) => {
    const li = e.target.closest('.slot');
    if (!li || dragFrom == null) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    $$('#slots .slot').forEach((x) => { delete x.dataset.dragover; });
    li.dataset.dragover = 'true';
  }, { signal });
  root.addEventListener('drop', (e) => {
    const li = e.target.closest('.slot');
    if (!li || dragFrom == null) return;
    e.preventDefault();
    const to = Number(li.dataset.index);
    const from = dragFrom;
    dragFrom = null;
    delete li.dataset.dragover;
    if (from !== to) swap(from, to);
  }, { signal });
}

/* ------------------------------------------------------------------ */
/* 全局导航 & 启动                                                     */
/* ------------------------------------------------------------------ */
function bindGlobal() {
  window.addEventListener('hashchange', router);

  // 「跳到主要内容」不能让 #main 变成路由的一部分（#main 会被 parseHash 当成未知路由）。
  // 改为直接聚焦 <main>，不改 URL、不触发路由。
  document.addEventListener('click', (e) => {
    const skip = e.target.closest('[data-skip]');
    if (!skip) return;
    e.preventDefault();
    const main = $('#main');
    if (!main) return;
    main.setAttribute('tabindex', '-1');
    main.focus({ preventScroll: false });
    main.scrollIntoView({ block: 'start', behavior: 'auto' });
  });

  const toggle = $('#nav-toggle');
  const nav = $('#site-nav');
  toggle?.addEventListener('click', () => {
    const open = nav?.dataset.open === 'true';
    if (nav) nav.dataset.open = String(!open);
    toggle.setAttribute('aria-expanded', String(!open));
    toggle.setAttribute('aria-label', !open ? '关闭导航菜单' : '打开导航菜单');
  });

  $('#clear-progress')?.addEventListener('click', async () => {
    const ok = await confirmDialog({
      title: '清除本机全部进度？',
      body: '这会删除本站在你浏览器中保存的全部归档状态与排列进度，且不可撤销。',
      okText: '全部清除',
    });
    if (!ok) return;
    store.clearAll();
    toast('已清除本机全部进度');
    renderCabinet();
  });

  const briefing = $('#briefing-card');
  const dismiss = $('#briefing-dismiss');
  if (briefing && store.get('briefing_dismissed', false)) briefing.hidden = true;
  dismiss?.addEventListener('click', () => {
    if (!briefing) return;
    briefing.hidden = true;
    store.set('briefing_dismissed', true);
    toast('随时可以在「玩法说明」里重看局规。');
  });

  const ver = $('#build-version');
  if (ver && BUILD && !BUILD.startsWith('__')) ver.textContent = BUILD;
}

async function boot() {
  bindGlobal();
  // 预加载全部已发布案件元数据，供档案柜显示标题
  await Promise.all([...RELEASED].map(async (id) => {
    try { await loadCase(id); } catch { /* 单案失败只影响该卡，不阻塞整站 */ }
  }));
  await router();
}

boot();
