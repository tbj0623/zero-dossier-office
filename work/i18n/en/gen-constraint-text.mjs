/**
 * gen-constraint-text.mjs — fill cases[ID].constraints[id].text with the English
 * sentence the verdict table shows for that relation.
 *
 * The sentence is produced by the SAME template family as ui.json rules.* so the
 * wording in the verdict table and in the evidence card can never diverge.
 * Slots are filled from the case's translated slot labels.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '../../..');
const IDS = ['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006'];
const readJson = (p) => JSON.parse(readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));

const CASES_P = join(HERE, 'cases.json');
const cases = readJson(CASES_P);
const ui = readJson(join(HERE, 'ui.json')).strings;
const g = cases._meta.glossary;

/** Slot label exactly as the UI renders it: “slot 3 (Drawer 3)”. */
const slotLabel = (slots, i) =>
  slots && slots[i] != null
    ? ui['rules.slot.labeled'].en.replace('{n}', String(i + 1)).replace('{label}', slots[i])
    : ui['rules.slot.plain'].en.replace('{n}', String(i + 1));

const item = (canonical) => g[canonical]?.en || canonical;

function sentence(rule, slots) {
  const a = item(rule.a);
  const b = rule.b ? item(rule.b) : '';
  const c = rule.c ? item(rule.c) : '';
  switch (rule.op) {
    case 'at': return ui['rules.at'].en.replace('{a}', a).replace('{slot}', slotLabel(slots, rule.slot));
    case 'not_at': return ui['rules.not_at'].en.replace('{a}', a).replace('{slot}', slotLabel(slots, rule.slot));
    case 'before': return ui['rules.before'].en.replace('{a}', a).replace('{b}', b);
    case 'after': return ui['rules.after'].en.replace('{a}', a).replace('{b}', b);
    case 'immediately_before': return ui['rules.immediately_before'].en.replace('{a}', a).replace('{b}', b);
    case 'immediately_after': return ui['rules.immediately_after'].en.replace('{a}', a).replace('{b}', b);
    case 'adjacent': return ui['rules.adjacent'].en.replace('{a}', a).replace('{b}', b);
    case 'distance': return ui['rules.distance'].en
      .replace('{a}', a).replace('{b}', b)
      .replace('{gap}', String(rule.gap))
      .replace('{between}', String(rule.gap - 1));
    case 'between': return ui['rules.between'].en.replace('{a}', a).replace('{b}', b).replace('{c}', c);
    default: return ui['rules.unknown'].en;
  }
}

let n = 0;
for (const id of IDS) {
  const zh = readJson(join(ROOT, 'cases', 'public', id + '.json'));
  const tr = cases.cases[id];
  tr.constraints = zh.constraints.map((r) => {
    n += 1;
    // keep the ids and the machine data visible so the Lead can cross-check
    return { id: r.id, op: r.op, a: r.a, b: r.b, c: r.c, gap: r.gap, slot: r.slot, text: sentence(r, tr.slots) };
  });
  // drop undefined keys for a tidy file
  tr.constraints = tr.constraints.map((x) => Object.fromEntries(Object.entries(x).filter(([, v]) => v !== undefined)));
}
cases._meta.constraints_note =
  'cases[ID].constraints[] mirrors the Chinese source constraints exactly (same ids, ops, and canonical item ids — these are engine data and must not be translated). The extra "text" field is the English sentence shown in the verdict table, generated from the ui.json rules.* templates plus the translated item names and slot labels, so the table and the evidence card always word a relation identically.';
writeFileSync(CASES_P, JSON.stringify(cases, null, 2) + '\n', 'utf8');
console.log(`wrote ${n} constraint sentences across ${IDS.length} cases`);
for (const id of ['NA-001', 'NA-004', 'NA-006']) {
  console.log(`\n${id}`);
  cases.cases[id].constraints.forEach((c) => console.log(`  ${c.id}  ${c.text}`));
}
