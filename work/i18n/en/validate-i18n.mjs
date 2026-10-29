/**
 * validate-i18n.mjs — structural + placeholder + logic-marker validation for
 * work/i18n/en/{ui.json,cases.json} against the Chinese source.
 *
 * Run:  node work/i18n/en/validate-i18n.mjs
 * Writes validate-report.txt next to itself and exits non-zero on any FAIL.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '../../..');
const CASES_DIR = join(ROOT, 'cases', 'public');
const IDS = ['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006'];

const out = [];
const fails = [];
const warns = [];
const line = (s = '') => out.push(s);
const fail = (s) => { fails.push(s); line('  FAIL  ' + s); };
const warn = (s) => { warns.push(s); line('  WARN  ' + s); };
const ok = (s) => line('  ok    ' + s);

const readJson = (p) => JSON.parse(readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const zhCases = Object.fromEntries(IDS.map((id) => [id, readJson(join(CASES_DIR, id + '.json'))]));
const en = readJson(join(HERE, 'cases.json'));
const ui = readJson(join(HERE, 'ui.json'));

const CJK = /[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/;
const isNonEmptyStr = (v) => typeof v === 'string' && v.trim().length > 0;

/* ------------------------------------------------------------------ */
line('='.repeat(72));
line('The Zero Dossier Office — EN localization validation');
line('='.repeat(72));

/* ---- 1. case set ---- */
line('\n[1] Case set');
const zhIds = Object.keys(zhCases).sort();
const enIds = Object.keys(en.cases || {}).sort();
if (JSON.stringify(zhIds) === JSON.stringify(enIds)) ok(`cases present: ${enIds.join(', ')}`);
else fail(`case id mismatch: zh=[${zhIds}] en=[${enIds}]`);

/* ---- 2. per-case field + array parity ---- */
line('\n[2] Per-case field and array parity (a: evidence ids, b: hints, c: slots)');
const TX_FIELDS = ['title', 'subtitle', 'setting', 'objective', 'resolution', 'twist', 'motif', 'director_note', 'logic_recap', 'epilogue', 'difficulty', 'theme'];
const COPY_FIELDS = ['chapter', 'play_minutes'];

for (const id of zhIds) {
  const z = zhCases[id];
  const e = en.cases?.[id];
  line(`\n  ${id}  “${z.title}”`);
  if (!e) { fail(`${id}: missing entirely from cases.json`); continue; }

  // scalar fields
  let missing = [];
  for (const f of TX_FIELDS) if (!isNonEmptyStr(e[f])) missing.push(f);
  if (missing.length) fail(`${id}: missing/empty translated field(s): ${missing.join(', ')}`);
  else ok(`${id}: all ${TX_FIELDS.length} text fields present and non-empty`);

  for (const f of COPY_FIELDS) {
    if (JSON.stringify(e[f]) !== JSON.stringify(z[f])) fail(`${id}: field "${f}" must be copied verbatim (zh=${JSON.stringify(z[f])} en=${JSON.stringify(e[f])})`);
  }

  // (a) evidence ids
  const zEv = z.evidence || [], eEv = e.evidence || [];
  if (zEv.length !== eEv.length) fail(`${id}: evidence count ${eEv.length} != source ${zEv.length}`);
  else {
    const zIdsE = zEv.map((x) => x.id), eIdsE = eEv.map((x) => x.id);
    if (JSON.stringify(zIdsE) !== JSON.stringify(eIdsE)) fail(`${id}: evidence ids differ — zh=[${zIdsE}] en=[${eIdsE}]`);
    else ok(`${id}: (a) ${zEv.length} evidence ids match exactly [${zIdsE.join(', ')}]`);
  }
  const badEv = eEv.filter((x) => !isNonEmptyStr(x.title) || !isNonEmptyStr(x.body));
  if (badEv.length) fail(`${id}: evidence with empty title/body: ${badEv.map((x) => x.id).join(', ')}`);

  // (b) hints
  const zH = z.hints || [], eH = e.hints || [];
  if (zH.length !== eH.length) fail(`${id}: (b) hint count ${eH.length} != source ${zH.length}`);
  else if (eH.some((h) => !isNonEmptyStr(h))) fail(`${id}: (b) empty hint string present`);
  else ok(`${id}: (b) ${zH.length} hints, same count, none empty`);

  // (c) slots
  const zS = z.slots || [], eS = e.slots || [];
  if (zS.length !== eS.length) fail(`${id}: (c) slot count ${eS.length} != source ${zS.length}`);
  else if (eS.some((s) => !isNonEmptyStr(s))) fail(`${id}: (c) empty slot label present`);
  else ok(`${id}: (c) ${zS.length} slots, same count → [${eS.join(' | ')}]`);

  // items (extra, not required but needed for display mapping)
  const zI = z.items || [], eI = e.items || [];
  if (zI.length !== eI.length) fail(`${id}: item count ${eI.length} != source ${zI.length}`);
  else {
    const dup = eI.filter((x, i) => eI.indexOf(x) !== i);
    if (dup.length) fail(`${id}: duplicate English item name(s): ${[...new Set(dup)].join(', ')}`);
    else if (eI.some((x) => !isNonEmptyStr(x))) fail(`${id}: empty item name`);
    else ok(`${id}: ${eI.length} items, all unique → [${eI.join(' | ')}]`);
  }

  // constraints carry engine data (ids/ops/canonical zh item ids) plus an English
  // "text" sentence for the verdict table; both are required by tools/build_i18n.py.
  const zc = z.constraints || [], ec = e.constraints || [];
  if (ec.length !== zc.length) fail(`${id}: constraint count ${ec.length} != source ${zc.length}`);
  else {
    const mismatch = zc.filter((zr, i) => zr.id !== ec[i]?.id || zr.op !== ec[i]?.op);
    if (mismatch.length) fail(`${id}: constraint id/op mismatch at ${mismatch.map((x) => x.id).join(', ')}`);
    else {
      const untexted = ec.filter((r) => !isNonEmptyStr(r.text));
      if (untexted.length) fail(`${id}: constraint(s) without English text: ${untexted.map((r) => r.id).join(', ')}`);
      else ok(`${id}: ${ec.length} constraints, ids/ops identical to source, each with English text`);
    }
  }

  // no stray Chinese left in English prose
  const prose = [e.title, e.subtitle, e.setting, e.objective, e.resolution, e.twist, e.motif, e.director_note, e.logic_recap, e.epilogue,
    ...(e.hints || []), ...eEv.flatMap((x) => [x.title, x.body]), ...(eS || [])].join(' ');
  const cjk = prose.match(new RegExp(CJK.source, 'g'));
  if (cjk) fail(`${id}: untranslated CJK characters remain (${cjk.length}): ${[...new Set(cjk)].slice(0, 12).join('')}`);
  else ok(`${id}: no CJK left in English prose`);
}

/* ---- 3. item-name consistency across cases (zh→en mapping) ---- */
line('\n[3] Item glossary consistency across cases (same zh item ⇒ same en name)');
const map = new Map();
let collisions = 0;
for (const id of zhIds) {
  const z = zhCases[id], e = en.cases?.[id];
  if (!e?.items) continue;
  z.items.forEach((zi, i) => {
    const ei = e.items[i];
    if (!ei) return;
    if (map.has(zi) && map.get(zi) !== ei) {
      fail(`item “${zi}” rendered inconsistently: “${map.get(zi)}” vs “${ei}” (${id})`);
      collisions += 1;
    } else map.set(zi, ei);
  });
}
if (!collisions) ok(`${map.size} distinct source item names, every one rendered with a single consistent English name`);
const enVals = [...map.values()];
const enDup = enVals.filter((v, i) => enVals.indexOf(v) !== i);
if (enDup.length) fail(`two different Chinese items share one English name: ${[...new Set(enDup)].join(', ')}`);
else ok(`${map.size} English item names are all distinct from one another`);

/* ---- 4. logic-marker audit: does each translated body still carry its constraint? ---- */
line('\n[4] Logic audit — (i) both items of every constraint are named, (ii) the relation word survives');
// Reversed phrasing ("B after A") is logically identical to a `before` constraint on (A,B),
// and the Chinese source itself uses it, so both directions are accepted here.
const MARKERS = {
  immediately_before: [/immediately before/i, /immediately after/i, /immediately to the left of/i, /immediately to the right of/i],
  immediately_after: [/immediately after/i, /immediately before/i, /immediately to the right of/i, /immediately to the left of/i],
  before: [/before/i, /to the left of/i, /earlier/i, /after/i, /to the right of/i, /later/i],
  after: [/after/i, /to the right of/i, /later/i, /before/i, /to the left of/i, /earlier/i],
  adjacent: [/adjacent/i, /next to/i, /beside/i, /against/i, /neighbouring|neighboring/i],
  distance: [/differ by/i, /apart/i, /three slots/i, /\b\d+ slots\b/i],
  between: [/between/i],
  at: [/slot/i, /fixed/i, /rightmost/i, /last/i, /belongs?/i, /held/i],
  not_at: [/not\b/i, /never/i, /did not/i, /cannot/i],
};
let markerFails = 0, markerChecks = 0, itemMentionFails = 0;
for (const id of zhIds) {
  const z = zhCases[id], e = en.cases?.[id];
  if (!e?.evidence) continue;
  const cons = new Map((z.constraints || []).map((c) => [c.id, c]));
  const nameOf = new Map((z.items || []).map((zi, i) => [zi, e.items?.[i]]));
  z.evidence.forEach((zev, i) => {
    const eev = e.evidence?.[i];
    if (!eev) return;
    for (const cid of zev.constraint_ids || []) {
      const c = cons.get(cid);
      if (!c) continue;
      markerChecks += 1;
      // (i) every item named in the constraint must appear in the English body
      const needed = [c.a, c.b, c.c].filter(Boolean).map((x) => nameOf.get(x)).filter(Boolean);
      const missing = needed.filter((nm) => !new RegExp(nm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(eev.body));
      if (missing.length) {
        itemMentionFails += 1;
        fail(`${id} ${eev.id}: body never names ${missing.map((m) => `“${m}”`).join(', ')} (constraint ${cid}: ${c.op})`);
      }
      // (ii) the relation word for the op must survive
      const pats = MARKERS[c.op];
      if (pats && !pats.some((re) => re.test(eev.body))) {
        markerFails += 1;
        fail(`${id} ${eev.id}: body lacks any marker for op "${c.op}" (${cid}) — re-read this sentence`);
      }
    }
  });
}
if (!markerFails && !itemMentionFails) ok(`all ${markerChecks} evidence→constraint links name both items and keep their op marker`);

/* ---- 5. UI strings ---- */
line('\n[5] ui.json');
const S = ui.strings || {};
const keys = Object.keys(S);
// These entries legitimately keep Chinese in the English column: the language
// switcher must show “中文” as the name of the Chinese language, not translate it.
const KEEP_ZH_OK = new Set(['brand.sub', 'manual.keys.row1.key', 'manual.keys.row2.key', 'manual.keys.row3.key', 'manual.keys.row4.key', 'lang.switchToZh', 'lang.button.zh', 'lang.toggle.aria']);
let phFail = 0, emptyFail = 0, cjkFail = 0;
const phOf = (s) => [...String(s).matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
for (const k of keys) {
  const { zh, en: enStr } = S[k] || {};
  if (!isNonEmptyStr(zh) || !isNonEmptyStr(enStr)) { emptyFail += 1; fail(`ui "${k}": empty zh or en`); continue; }
  const a = phOf(zh), b = phOf(enStr);
  if (JSON.stringify(a) !== JSON.stringify(b)) { phFail += 1; fail(`ui "${k}": placeholder mismatch zh={${a}} en={${b}}`); }
  // zh/en identical strings are only legitimate for language names and key names
  if (zh === enStr && !KEEP_ZH_OK.has(k) && !S[k].note) {
    warn(`ui "${k}": zh and en are identical — confirm this is intentional (add a "note" to silence)`);
  }
  // English side must not contain Chinese punctuation/ideographs, except language names
  if (CJK.test(enStr) && !KEEP_ZH_OK.has(k)) { cjkFail += 1; fail(`ui "${k}": English text contains CJK`); }
}
line(`  → ${keys.length} UI entries; ${phFail} placeholder mismatches, ${emptyFail} empties, ${cjkFail} with stray CJK`);
if (!phFail && !emptyFail && !cjkFail) ok(`${keys.length} UI strings: every entry has zh+en and identical placeholder sets`);

const GL = ui._meta?.placeholder_glossary || {};
const usedPh = new Set(keys.flatMap((k) => [...String(S[k].en).matchAll(/\{(\w+)\}/g)].map((m) => m[1])));
const undocumented = [...usedPh].filter((p) => !GL[`{${p}}`]);
if (undocumented.length) warn(`placeholders used but not documented in _meta.placeholder_glossary: ${undocumented.join(', ')}`);
else ok(`all ${usedPh.size} distinct placeholders are documented in _meta.placeholder_glossary`);

/* ---- 6. glossary size ---- */
const g = en._meta?.glossary || {};
line(`\n[6] Glossary: ${Object.keys(g).length} entries in cases.json _meta.glossary`);

/* ---- summary ---- */
line('\n' + '='.repeat(72));
const summary = fails.length === 0
  ? `RESULT: PASS — 0 failures, ${warns.length} warnings`
  : `RESULT: FAIL — ${fails.length} failures, ${warns.length} warnings`;
line(summary);
line(`  cases                 : ${enIds.length}`);
line(`  UI strings            : ${keys.length}`);
line(`  glossary entries      : ${Object.keys(g).length}`);
line(`  evidence-id checks    : ${zhIds.reduce((n, id) => n + (zhCases[id].evidence?.length || 0), 0)}`);
line(`  hint-count checks     : ${zhIds.length}`);
line(`  slot-length checks    : ${zhIds.length}`);
line(`  logic-marker checks   : ${markerChecks}`);
line('='.repeat(72));

writeFileSync(join(HERE, 'validate-report.txt'), out.join('\n') + '\n', 'utf8');
console.log(out.filter((l) => /RESULT|FAIL|WARN|cases +:|UI strings|glossary entries|checks +:|=+$/.test(l)).join('\n'));
process.exit(fails.length ? 1 : 0);
