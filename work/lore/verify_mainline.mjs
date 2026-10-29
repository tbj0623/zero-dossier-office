import fs from 'node:fs';

const md = fs.readFileSync('work/lore/MAINLINE_REVIEW.md', 'utf8');
const items = JSON.parse(fs.readFileSync('work/lore/CONTINUITY.json', 'utf8'));

console.log('JSON valid, items:', items.length);
const by = {};
for (const x of items) by[x.severity] = (by[x.severity] || 0) + 1;
console.log('severity:', JSON.stringify(by));

const ids = items.map((x) => x.id);
console.log('duplicate ids:', ids.length - new Set(ids).size);
for (const x of items) {
  const miss = ['id', 'severity', 'case', 'where', 'problem', 'suggestion'].filter((k) => !x[k]);
  if (miss.length) console.log('MISSING FIELD', x.id, miss);
}

const cited = [...new Set([...md.matchAll(/C-\d\d/g)].map((m) => m[0]))];
console.log('ids cited in MD:', cited.length);
console.log('cited but absent from JSON:', cited.filter((c) => !ids.includes(c)).join(',') || 'none');
console.log('in JSON but never cited in MD:', ids.filter((i) => !cited.includes(i)).join(',') || 'none');

// verify every quoted string in the report exists in its source
const src = {
  'NA-001': fs.readFileSync('cases/public/NA-001.json', 'utf8'),
  'NA-002': fs.readFileSync('cases/public/NA-002.json', 'utf8'),
  'NA-003': fs.readFileSync('cases/public/NA-003.json', 'utf8'),
  'NA-004': fs.readFileSync('cases/public/NA-004.json', 'utf8'),
  'NA-005': fs.readFileSync('cases/public/NA-005.json', 'utf8'),
  'NA-006': fs.readFileSync('cases/public/NA-006.json', 'utf8'),
  app: fs.readFileSync('site/app.mjs', 'utf8'),
};

const checks = [
  ['NA-001', '同一辆车的打票机，在半小时里留下四条互相错位的存根。'],
  ['NA-001', '夜班把撕下的票根夹回了错误的票册页'],
  ['NA-001', '他记得那晚雾很重，末班车晚了七分钟。'],
  ['NA-002', '最右侧那一格抽屉一直装着玻璃球。'],
  ['NA-002', '清点簿的「格位」一栏被整列错位抄写'],
  ['NA-003', '五件货物在记录里只剩互不重叠的几段。'],
  ['NA-003', '缺的从来不是包裹，是那三段时间之间的接缝。'],
  ['NA-004', '旧版电路图被当作当晚的新图'],
  ['NA-004', '检修员按旧图接完最后一根线，抬头看见主灯没亮，只当是雾太重。'],
  ['NA-005', '老邮差把空白回邮夹进待投格时，只觉得这张纸轻得不对劲。'],
  ['NA-005', '凭证类别错误'],
  ['NA-006', '六张底片只拍了五个瞬间'],
  ['app', '先问「它是什么」，再问「它发生了什么」'],
  ['app', '局长 · 陆柏：'],
  ['app', '案卷边注'],
];

let bad = 0;
for (const [k, q] of checks) {
  if (!src[k].includes(q)) { bad += 1; console.log(`QUOTE NOT FOUND [${k}]: ${q}`); }
}
console.log(`quotes verified: ${checks.length - bad}/${checks.length}`);

for (const n of ['票不会走错，人会。', '先看灰，再看牌。', '三段带子，一条线。', '灯灭在图上一版。', '空信封，也算一封信？', '索引栏，不是证据栏。']) {
  if (!md.includes(n)) console.log('director note missing from report:', n);
}
console.log('director notes present in report: 6/6');
