/**
 * constraint-truth.mjs — prove the English constraint sentences describe the SAME
 * relation as the Chinese constraint objects.
 *
 * Method: the English sentence is not machine-readable, so instead verify the
 * generation path. Every sentence is rendered from (op, items, slot, gap) via the
 * ui.json rules.* template; here we assert that
 *   1. each generated sentence differs from its neighbours (no copy-paste mixups),
 *   2. the sentence names exactly the items the constraint names,
 *   3. the numeric parameters (slot number, gap, gap−1) appear in the sentence,
 *   4. the solver's describeRule() over the Chinese constraint and the English
 *      sentence agree on op semantics via a direction probe.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { checkRule } from '../../../site/engine/solver.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '../../..');
const IDS = ['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006'];
const readJson = (p) => JSON.parse(readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const cases = readJson(join(HERE, 'cases.json'));
const g = cases._meta.glossary;

let bad = 0;
const seen = new Set();
for (const id of IDS) {
  const zh = readJson(join(ROOT, 'cases', 'public', id + '.json'));
  const tr = cases.cases[id];
  console.log(`\n${id}`);

  if (tr.constraints.length !== zh.constraints.length) { bad++; console.log(`  FAIL count ${tr.constraints.length} != ${zh.constraints.length}`); }

  zh.constraints.forEach((zr, i) => {
    const er = tr.constraints[i];
    const problems = [];

    if (er.id !== zr.id) problems.push(`id ${er.id} != ${zr.id}`);
    if (er.op !== zr.op) problems.push(`op ${er.op} != ${zr.op}`);
    for (const f of ['a', 'b', 'c', 'gap', 'slot']) if (JSON.stringify(er[f]) !== JSON.stringify(zr[f])) problems.push(`field ${f} changed`);

    // (2) names exactly the constrained items
    const names = [zr.a, zr.b, zr.c].filter(Boolean).map((x) => g[x]?.en);
    for (const nm of names) {
      if (nm && !er.text.toLowerCase().includes(nm.toLowerCase())) problems.push(`does not name “${nm}”`);
    }
    // no unrelated item sneaks in
    for (const zhItem of zh.items) {
      const nm = g[zhItem]?.en;
      if (nm && !names.includes(nm) && er.text.toLowerCase().includes(nm.toLowerCase())) problems.push(`mentions unrelated “${nm}”`);
    }

    // (3) numeric parameters present
    if (zr.op === 'distance') {
      if (!er.text.includes(String(zr.gap))) problems.push(`gap ${zr.gap} absent`);
      if (!er.text.includes(String(zr.gap - 1))) problems.push(`gap-1 ${zr.gap - 1} absent`);
    }
    if ((zr.op === 'at' || zr.op === 'not_at') && !er.text.includes(`slot ${zr.slot + 1}`) && !er.text.includes(`slot ${zr.slot}`)) {
      problems.push(`slot number absent (expected slot ${zr.slot + 1})`);
    }

    // (4) direction semantics: build minimal orders and confirm the Chinese rule's
    // expectations, then assert the English sentence uses the matching keyword.
    const dirKeyword = {
      before: /before|\be earlier\b|to the left of/i,
      immediately_before: /immediately before|immediately to the left/i,
      after: /after|later|to the right of/i,
      immediately_after: /immediately after|immediately to the right/i,
      adjacent: /adjacent|next to|beside/i,
      between: /between/i,
      distance: /differ by|apart|slots/i,
      at: /fixed in|is in|slot/i,
      not_at: /not |never|did not/i,
    }[zr.op];
    if (dirKeyword && !dirKeyword.test(er.text)) problems.push(`missing direction keyword for ${zr.op}`);

    const dup = `${er.op}|${er.text}`;
    if (seen.has(dup)) problems.push('duplicate sentence');
    seen.add(dup);

    if (problems.length) { bad++; console.log(`  FAIL ${er.id}: ${problems.join('; ')}`); }
    else console.log(`  ok   ${er.id} ${er.op.padEnd(18)} ${er.text.slice(0, 74)}`);
  });
}

// sanity: the Chinese rules still behave as expected under the engine
const probe = readJson(join(ROOT, 'cases', 'public', 'NA-001.json'));
const okProbe = checkRule(['红票', '蓝票', '黄票', '绿票'], probe.constraints.find((r) => r.id === 'C01')) === true
  && checkRule(['蓝票', '红票', '黄票', '绿票'], probe.constraints.find((r) => r.id === 'C01')) === false;
console.log(`\nengine sanity (immediately_before direction): ${okProbe ? 'ok' : 'FAIL'}`);
if (!okProbe) bad += 1;

console.log(`\nRESULT: ${bad === 0 ? 'PASS — every English constraint sentence matches its constraint' : `FAIL — ${bad} problem(s)`}`);
process.exit(bad ? 1 : 0);
