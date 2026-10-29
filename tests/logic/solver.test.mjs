/** 第零证物局 · JS 规则核心单元测试（node --test，零依赖） */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  checkRule, verifyOrder, countSolutions, necessityReport,
  describeRule, assertCaseShape,
} from '../../engine/solver.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const PUBLIC = join(ROOT, 'cases', 'public');
const AUTHOR = join(ROOT, 'cases', 'author');

const cases = readdirSync(PUBLIC)
  .filter((f) => f.endsWith('.json'))
  .sort()
  .map((f) => JSON.parse(readFileSync(join(PUBLIC, f), 'utf8')));

const RELEASED = ['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006'];

/* ------------------------------------------------------------------ */
/* 发布集与数据卫生                                                    */
/* ------------------------------------------------------------------ */
test('只发布 6 个已审案件', () => {
  assert.deepEqual(cases.map((c) => c.id), RELEASED);
});

test('public 案卷不含作者答案与内部字段', () => {
  for (const c of cases) {
    for (const field of ['expected_solution', 'editorial_note', 'status']) {
      assert.equal(Object.hasOwn(c, field), false, `${c.id} 泄漏了 ${field}`);
    }
  }
});

test('public 与 author 的结构化约束逐字段一致', () => {
  for (const c of cases) {
    const author = JSON.parse(readFileSync(join(AUTHOR, `${c.id}.json`), 'utf8'));
    assert.deepEqual(c.constraints, author.constraints, `${c.id} 约束漂移`);
    // items 的顺序被故意打乱以防泄漏答案，只校验集合相同
    assert.deepEqual([...c.items].sort(), [...author.items].sort());
    assert.deepEqual(c.slots, author.slots);
    assert.deepEqual(
      c.evidence.map((e) => [e.id, e.constraint_ids]),
      author.evidence.map((e) => [e.id, e.constraint_ids]),
    );
  }
});

/* ------------------------------------------------------------------ */
/* 每个案件：结构、唯一解、逐条必要性                                  */
/* ------------------------------------------------------------------ */
for (const c of cases) {
  test(`${c.id} 结构自检通过`, () => {
    assert.equal(assertCaseShape(c), true);
  });

  test(`${c.id} 客户端规则推导出唯一解`, () => {
    const { count, solution } = countSolutions(c.items, c.constraints);
    assert.equal(count, 1, `${c.id} 应只有一个解`);
    assert.ok(solution, '唯一解应被返回');
  });

  test(`${c.id} 倒序排列被拒绝`, () => {
    const reversed = [...c.items].reverse();
    if (reversed.join() === c.items.join()) return; // 退化情形，不适用
    const checks = verifyOrder(reversed, c.constraints);
    assert.ok(checks.some((x) => !x.valid), `${c.id} 的倒序不应满足全部约束`);
  });

  test(`${c.id} 每条约束都不可省略`, () => {
    const report = necessityReport(c.items, c.constraints);
    for (const r of report) {
      assert.equal(r.essential, true, `${c.id}/${r.id} 去掉后仍有 ${r.remaining} 个解，属冗余约束`);
    }
  });

  test(`${c.id} 三档提示齐备且互不重复`, () => {
    assert.ok(c.hints.length >= 3, '至少 3 段提示');
    assert.equal(new Set(c.hints).size, c.hints.length, '提示不应重复');
  });

  test(`${c.id} 每条证据都有玩家可读的关系描述`, () => {
    for (const e of c.evidence) {
      assert.ok(e.body && e.body.length > 10, `${e.id} 正文过短`);
      for (const cid of e.constraint_ids) {
        const rule = c.constraints.find((r) => r.id === cid);
        assert.ok(rule, `${e.id} 引用了不存在的 ${cid}`);
        const text = describeRule(rule, c.slots);
        assert.ok(text.length > 6 && !text.includes('未知'), `${cid} 无法生成玩家语言`);
      }
    }
  });
}

/* ------------------------------------------------------------------ */
/* 运算符语义（防回归）                                                */
/* ------------------------------------------------------------------ */
test('adjacent 是对称的不定向关系', () => {
  const order = ['a', 'b', 'c', 'd'];
  assert.equal(checkRule(order, { op: 'adjacent', a: 'b', b: 'a' }), true);
  assert.equal(checkRule(order, { op: 'adjacent', a: 'a', b: 'c' }), false);
});

test('distance 的 gap 是格位编号之差，不是中间物品数', () => {
  const order = ['a', 'b', 'c', 'd', 'e'];
  // a 在 0，d 在 3：差 3，中间隔 2 件
  assert.equal(checkRule(order, { op: 'distance', a: 'a', b: 'd', gap: 3 }), true);
  assert.equal(checkRule(order, { op: 'distance', a: 'a', b: 'd', gap: 2 }), false);
});

test('between 是严格区间，不要求居中', () => {
  const order = ['a', 'b', 'c', 'd'];
  // b(1) 夹在 a(0) 与 d(3) 之间，虽然偏向 a
  assert.equal(checkRule(order, { op: 'between', a: 'b', b: 'a', c: 'd' }), true);
  assert.equal(checkRule(order, { op: 'between', a: 'a', b: 'b', c: 'd' }), false);
});

test('between 与端点顺序无关', () => {
  const order = ['x', 'y', 'z'];
  assert.equal(checkRule(order, { op: 'between', a: 'y', b: 'z', c: 'x' }), true);
});

test('immediately_before 比 before 更严格', () => {
  const order = ['a', 'x', 'b'];
  assert.equal(checkRule(order, { op: 'before', a: 'a', b: 'b' }), true);
  assert.equal(checkRule(order, { op: 'immediately_before', a: 'a', b: 'b' }), false);
});

test('未知运算符抛错而不是静默放行', () => {
  assert.throws(() => checkRule(['a', 'b'], { op: 'xor', a: 'a', b: 'b' }), /未知约束运算符/);
});

test('非法 gap 抛错', () => {
  const order = ['a', 'b', 'c'];
  assert.throws(() => checkRule(order, { op: 'distance', a: 'a', b: 'b', gap: 0 }), /gap/);
  assert.throws(() => checkRule(order, { op: 'distance', a: 'a', b: 'b', gap: 9 }), /gap/);
});

test('越界 slot 抛错', () => {
  assert.throws(() => checkRule(['a', 'b'], { op: 'at', a: 'a', slot: 5 }), /slot/);
});

test('未知物件抛错', () => {
  assert.throws(() => checkRule(['a', 'b'], { op: 'at', a: 'zz', slot: 0 }), /未知物件/);
});

test('verifyOrder 拒绝重复物件', () => {
  assert.throws(() => verifyOrder(['a', 'a'], []), /重复/);
});

test('countSolutions 拒绝少于 3 或多于 8 件', () => {
  assert.throws(() => countSolutions(['a', 'b'], []), /3\.\.8/);
  assert.throws(() => countSolutions(Array.from({ length: 9 }, (_, i) => `i${i}`), []), /3\.\.8/);
});

test('assertCaseShape 拒绝隐藏约束', () => {
  const bad = {
    id: 'NA-999', title: 't', slots: ['1', '2', '3'], items: ['a', 'b', 'c'],
    constraints: [
      { id: 'C1', op: 'at', a: 'a', slot: 0 },
      { id: 'C2', op: 'at', a: 'b', slot: 1 },
    ],
    evidence: [{ id: 'E1', body: '说明', constraint_ids: ['C1'] }],
    hints: ['x', 'y', 'z'],
  };
  assert.throws(() => assertCaseShape(bad), /隐藏约束/);
});

/* ------------------------------------------------------------------ */
/* 穷举规模合理性                                                      */
/* ------------------------------------------------------------------ */
test('最难的 NA-006 在 720 个排列内可穷举且够快', () => {
  const c = cases.find((x) => x.id === 'NA-006');
  const t0 = performance.now();
  const { count } = countSolutions(c.items, c.constraints);
  const ms = performance.now() - t0;
  assert.equal(count, 1);
  assert.ok(ms < 50, `穷举用时 ${ms.toFixed(1)}ms，超出预算`);
});
