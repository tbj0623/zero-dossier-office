/**
 * semantic-check.mjs — prove the English layer did not disturb puzzle logic.
 *
 * Per case:
 *  1. the Chinese constraints still admit exactly ONE arrangement;
 *  2. the English-labelled solution (positional en→zh map) satisfies those constraints;
 *  3. the English logic_recap still refers to every item (Chinese recap does too);
 *  4. every explicit positional claim in the English recap ("X is fixed in the
 *     fourth slot", "Y can only be first", "Z falls into the third slot", "the only
 *     lawful order is …") agrees with the unique solution.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { countSolutions, verifyOrder, describeRule } from '../../../site/engine/solver.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '../../..');
const IDS = ['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006'];
const readJson = (p) => JSON.parse(readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));

const ORDINALS = {
  first: 1, second: 2, third: 3, fourth: 4, fifth: 5, sixth: 6,
  1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6,
};
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Distinctive tokens an English item can be referred to by (source abbreviates too). */
function tokens(name) {
  const words = name.split(/\s+/).filter((w) => w.length > 2);
  const set = new Set([name, ...words]);
  // drop generic head nouns so “Old Lens” is also found as “Lens”, never as “Image”
  return [...set].filter((w) => !['Image', 'Negative'].includes(w)).sort((a, b) => b.length - a.length);
}

let failed = 0;
for (const id of IDS) {
  const zh = readJson(join(ROOT, 'cases', 'public', id + '.json'));
  const e = readJson(join(HERE, 'cases.json')).cases[id];

  const zh2en = new Map(zh.items.map((z, i) => [z, e.items[i]]));
  const en2zh = new Map(e.items.map((x, i) => [x, zh.items[i]]));

  const { count, solution } = countSolutions(zh.items, zh.constraints);
  const enSolution = solution.map((z) => zh2en.get(z));
  const posOf = new Map(enSolution.map((nm, i) => [nm, i + 1]));

  // (2) English ordering satisfies every constraint
  const satisfied = verifyOrder(enSolution.map((x) => en2zh.get(x)), zh.constraints).every((r) => r.valid);

  // (3) recap still refers to every item
  const recap = e.logic_recap;
  const unreferenced = enSolution.filter((nm) => !tokens(nm).some((t) => new RegExp(esc(t), 'i').test(recap)));

  // (4) explicit positional claims must agree with the solution
  //     The inter-word gap may NOT cross a comma, semicolon or full stop: those are
  //     clause boundaries, and letting the gap cross one makes the pattern steal a
  //     neighbouring item's claim (e.g. attributing “Glass Shade falls into third”
  //     to “Lens” because both appear in the same sentence).
  const claims = [];
  for (const nm of enSolution) {
    for (const t of tokens(nm).slice(0, 2)) {
      // “X is fixed in the fourth slot” / “X belongs to the fourth slot” / “X falls into the third slot”
      const a = new RegExp(`${esc(t)}[^.;,]{0,40}?(?:fixed in|belongs? to|falls? into|sits? in|is in)\\s+the\\s+(first|second|third|fourth|fifth|sixth|\\d)(?:\\s+slot)?`, 'gi');
      for (const m of recap.matchAll(a)) claims.push({ nm, stated: ORDINALS[m[1].toLowerCase()], via: m[0].trim() });
      // “X can only be first” / “X can only be in the first slot”
      const b = new RegExp(`${esc(t)}[^.;,]{0,40}?can only be(?:\\s+in)?\\s+(?:the\\s+)?(first|second|third|fourth|fifth|sixth|\\d)`, 'gi');
      for (const m of recap.matchAll(b)) claims.push({ nm, stated: ORDINALS[m[1].toLowerCase()], via: m[0].trim() });
    }
  }
  // explicit “only lawful order is: A, B, C…” enumeration, if present
  const orderMatch = recap.match(/only (?:lawful )?order is:?\s*([^.]*)\./i);
  if (orderMatch) {
    const listed = enSolution
      .map((nm) => ({ nm, at: orderMatch[1].toLowerCase().indexOf(tokens(nm)[0].toLowerCase()) }))
      .filter((x) => x.at >= 0)
      .sort((a, b) => a.at - b.at)
      .map((x) => x.nm);
    if (listed.length >= 2) {
      const okList = listed.every((nm, i) => i === 0 || posOf.get(nm) > posOf.get(listed[i - 1]));
      claims.push({ nm: '(enumerated order)', stated: okList ? 'consistent' : 'INCONSISTENT', via: orderMatch[1].trim().slice(0, 80) });
    }
  }
  const badClaims = claims.filter((c) => c.stated !== 'consistent' && c.stated !== posOf.get(c.nm));

  const pass = count === 1 && satisfied && unreferenced.length === 0 && badClaims.length === 0;
  if (!pass) failed += 1;

  console.log(`\n${id}  ${pass ? 'PASS' : 'FAIL'}`);
  console.log(`  unique solution        : ${count === 1 ? 'yes (exactly 1)' : `NO (${count})`}`);
  console.log(`  solution (zh)          : ${solution.join(' → ')}`);
  console.log(`  solution (en)          : ${enSolution.join(' → ')}`);
  console.log(`  english satisfies rules: ${satisfied ? 'yes' : 'NO'}`);
  console.log(`  recap refers to all    : ${unreferenced.length === 0 ? 'yes' : 'NO → missing ' + unreferenced.join(', ')}`);
  if (claims.length) {
    console.log(`  positional claims      :`);
    for (const c of claims) {
      const verdictOk = c.stated === 'consistent' || c.stated === posOf.get(c.nm);
      console.log(`    ${verdictOk ? 'ok  ' : 'BAD '} ${c.nm} → ${c.stated}${typeof c.stated === 'number' ? '' : ''}  “${c.via}”`);
    }
  } else console.log(`  positional claims      : (none stated expressly)`);
  console.log(`  english rule sentences :`);
  zh.constraints.forEach((r, i) => console.log(`    ${r.id}  ${describeRule(r, e.slots)}`));
}

console.log(`\n${failed === 0 ? 'RESULT: PASS' : 'RESULT: FAIL'} — ${IDS.length - failed}/${IDS.length} cases semantically intact`);
process.exit(failed ? 1 : 0);
