/**
 * coverage-check.mjs — will the runtime actually localize every visible string?
 *
 * Three concrete questions, matching how site/i18n.mjs works:
 *   A. every `data-i18n="key"` in index.html resolves to a key in ui.json,
 *      and the Chinese text in the HTML equals ui.json's zh value (no drift);
 *   B. every visible Chinese text node in index.html is either inside a
 *      `data-i18n` element or is deliberately language-neutral (kept Chinese);
 *   C. every Chinese string literal in app.mjs is covered by a ui.json entry,
 *      either exactly or through a placeholder template.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '../../..');
const ui = JSON.parse(readFileSync(join(HERE, 'ui.json'), 'utf8'));
const S = ui.strings;

const CJK = /[\u3400-\u4dbf\u4e00-\u9fff]/;
const hasCJK = (s) => CJK.test(s);
const norm = (s) => s.replace(/&nbsp;/g, ' ').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();

/* Deliberately kept in Chinese: language names and the bilingual switcher label. */
const NEUTRAL = [/^中文$/, /^EN$/, /^Switch to 中文$/];

let problems = 0;
const bad = (s) => { problems += 1; console.log('  ' + s); };

/* ---------------- A. data-i18n key integrity ---------------- */
const html = readFileSync(join(ROOT, 'site', 'index.html'), 'utf8');
console.log('\n[A] data-i18n keys in index.html');
// Compare TEXT ONLY on both sides: ui.json's zh preserves the source's inline
// <strong>/<code> markup for the template author, while the DOM holds bare text.
// Whitespace is also ignored (the source wraps sentences across lines).
const stripTags = (s) => s.replace(/<[^>]*>/g, '');
const squash = (s) => stripTags(s).replace(/\s+/g, '');
const tagRe = /<([a-z0-9]+)\b([^>]*?)\bdata-i18n="([^"]+)"([^>]*)>([\s\S]*?)<\/\1>/gi;
let tagged = 0, missingKey = 0, drift = 0;
for (const m of html.matchAll(tagRe)) {
  tagged += 1;
  const key = m[3];
  const text = norm(m[5]);
  const entry = S[key];
  if (!entry) { missingKey += 1; bad(`KEY MISSING  data-i18n="${key}" → no entry in ui.json`); continue; }
  if (text && squash(entry.zh) !== squash(text)) {
    drift += 1; bad(`ZH DRIFT      ${key}\n      html: ${JSON.stringify(text.slice(0, 90))}\n      ui  : ${JSON.stringify(stripTags(entry.zh).slice(0, 90))}`);
  }
}
console.log(`  ${tagged} tagged elements · ${missingKey} missing keys · ${drift} zh mismatches`);
if (!missingKey && !drift) console.log('  ok — every data-i18n key exists and matches its Chinese source');

/* ---------------- B. untagged visible Chinese ---------------- */
console.log('\n[B] visible Chinese text not wrapped in data-i18n');
const stripped = html
  .replace(/<script[\s\S]*?<\/script>/gi, '')
  .replace(/<style[\s\S]*?<\/style>/gi, '')
  .replace(/<!--[\s\S]*?-->/g, '');
/**
 * Collect text nodes outside any data-i18n element, then drop any that are only a
 * FRAGMENT of a longer ui.json zh string: when the source splits one sentence across
 * <strong>/<code> spans, the runtime must tag only the outermost element, so the
 * inner fragments are expected and are not a data gap.
 */
const untagged = [];
const stack = [];
for (const m of stripped.matchAll(/<(\/?)([a-z0-9]+)\b([^>]*)>|([^<]+)/gi)) {
  if (m[4] !== undefined) {
    const txt = norm(m[4]);
    if (!txt || !hasCJK(txt)) continue;
    if (stack.some((d) => d.tagged)) continue;
    if (NEUTRAL.some((re) => re.test(txt))) continue;
    untagged.push(txt);
  } else if (m[1] === '/') {
    stack.pop();
  } else {
    const attrs = m[3] || '';
    if (/\/$/.test(attrs) || /^(br|img|input|meta|link|hr|source|path|use|circle)$/i.test(m[2])) continue;
    stack.push({ tag: m[2], tagged: /\bdata-i18n=/.test(attrs) });
  }
}
const zhAll = Object.values(S).map((x) => x.zh);
/**
 * ui.json zh value as a regex, so “已归档 {done} / {total}” covers the rendered
 * “已归档 0 / 6”. Also handles fragments produced when app.mjs splits a sentence
 * around a live value, e.g. “站点版本” + version + “· 求解核心…” — the two halves are
 * checked separately by testing whether the full key contains each fragment.
 */
const zhPattern = (z) => {
  const holes = z.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\\\{[a-zA-Z]+\\\}/g, '\u0000');
  return new RegExp('^' + holes.split('\u0000').map((p) => p.replace(/\s+/g, '\\s*')).join('[\\s\\S]*') + '$');
};
const zhPats = zhAll.map(zhPattern);
const decodeEntities = (s) => s.replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
const isFragment = (t) => {
  const tt = squash(decodeEntities(t));
  if (!tt) return true;
  // (i) a piece of a longer ui.json string, or (ii) matches a templated ui.json value
  if (zhAll.some((z) => squash(stripTags(z)) !== tt && squash(stripTags(z)).includes(tt))) return true;
  if (zhPats.some((re) => re.test(decodeEntities(t)))) return true;
  // (iii) a fragment sitting between two holes of the same templated string:
  //       “站点版本{version}·求解核心…” is shown as the literal halves around the value.
  return zhAll.some((z) => {
    const parts = stripTags(z).split(/\{[a-zA-Z]+\}/).map(squash).filter(Boolean);
    return parts.length > 1 && parts.includes(tt);
  });
};
const realGaps = [...new Set(untagged)].filter((t) => !isFragment(t));
const fragments = [...new Set(untagged)].filter((t) => isFragment(t));

if (fragments.length) {
  console.log(`  ${fragments.length} inner fragments of sentences that ui.json already holds whole (expected when only the outer element is tagged):`);
  for (const f of fragments) console.log(`    · ${JSON.stringify(f.length > 60 ? f.slice(0, 60) + '…' : f)}`);
}
for (const t of realGaps) bad(`UNTAGGED  ${JSON.stringify(t.length > 100 ? t.slice(0, 100) + '…' : t)}`);
if (!realGaps.length) console.log('  ok — no untagged Chinese string is missing from ui.json');

/* ---------------- C. app.mjs literals ---------------- */
console.log('\n[C] Chinese string literals in app.mjs');
const app = readFileSync(join(ROOT, 'site', 'app.mjs'), 'utf8');
const codeOnly = app.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const zhVals = [...new Set(Object.values(S).map((x) => norm(x.zh)))];

function expandTernaries(src) {
  const re = /^([\s\S]*?)\$\{[^}]*?\?\s*'([^']*)'\s*:\s*'([^']*)'\s*\}([\s\S]*)$/;
  const m = src.match(re);
  if (m) return [m[1] + m[2] + m[4], m[1] + m[3] + m[4]];
  return [src];
}
function asPattern(src) {
  const holes = src
    .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    .replace(/\\\$\\\{[^}]*?\\\}/g, '\u0000')
    .replace(/\\\{[a-zA-Z]+\\\}/g, '\u0000');
  return new RegExp('^' + holes.split('\u0000').map((p) => p.replace(/\s+/g, '\\s*')).join('[\\s\\S]*') + '$');
}
const exact = new Set(zhVals);
const pats = zhVals.flatMap((z) => expandTernaries(z).map((a) => asPattern(norm(a))));

let literals = 0, uncovered = 0;
for (const m of codeOnly.matchAll(/'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)"|`((?:[^`\\]|\\.)*)`/g)) {
  const raw = norm(m[1] ?? m[2] ?? m[3] ?? '');
  if (!raw || !hasCJK(raw)) continue;

  // Skip the Chinese *fallback* argument of an already-localized tf(...)/t(...) call:
  //   tf('key', {vars}, `中文回退`)  — the fallback only shows when the key is missing.
  const before = codeOnly.slice(Math.max(0, m.index - 260), m.index);
  const inI18nCall = /\b(t|tf)\(\s*'[^']+'\s*,\s*(?:\{[^}]*\}\s*,\s*)?$/.test(before) ||
                     /\b(t|tf)\(\s*'[^']+'\s*,\s*$/.test(before);
  if (inI18nCall) continue;

  // Skip Chinese fragments that belong to an if (locale === 'zh') rendering branch and
  // are covered by a templated key used in the English branch (e.g. about.version.p).
  const nearby = codeOnly.slice(Math.max(0, m.index - 900), Math.min(codeOnly.length, m.index + 400));
  const coveredByTemplate = zhAll.some((z) => {
    const parts = stripTags(z).split(/\{[a-zA-Z]+\}/).map(squash).filter(Boolean);
    return parts.length > 1 && parts.some((p) => squash(p) === squash(raw));
  });
  if (coveredByTemplate && /currentLocale\(\)\s*===\s*'(zh|en)'/.test(nearby)) continue;

  literals += 1;
  if (exact.has(raw)) continue;
  const hit = expandTernaries(raw).some((v) => pats.some((re) => re.test(norm(v))));
  if (!hit) { uncovered += 1; bad(`UNCOVERED  ${JSON.stringify(raw.length > 110 ? raw.slice(0, 110) + '…' : raw)}`); }
}
console.log(`  ${literals} Chinese literals needing translation · ${uncovered} uncovered`);

console.log(`\nRESULT: ${problems === 0 ? 'PASS — every visible Chinese string has an English entry' : `FAIL — ${problems} problem(s)`}`);
process.exit(problems ? 1 : 0);
