import test from 'node:test';
import assert from 'node:assert/strict';
import { isExactPermutation, normalizeSavedSession, pushUndo, HISTORY_LIMIT } from '../../site/player-state.mjs';

const ITEMS = ['a', 'b', 'c', 'd'];
const ORD = ['b', 'a', 'c', 'd'];
test('排列必须完整、唯一、只包含案件物件', () => {
  assert.equal(isExactPermutation(ORD, ITEMS), true);
  for (const bad of [null, [], ['a', 'b'], ['a','b','c','c'], ['a','b','c','x'], ['a','b','c','d','e']]) {
    assert.equal(isExactPermutation(bad, ITEMS), false);
  }
});
test('旧存档兼容，缺失历史时安全降级', () => {
  assert.deepEqual(normalizeSavedSession({order:ORD,hintIndex:2},ITEMS,3), {
    order:ORD,hintIndex:2,history:[],redo:[],attempts:0,at:0, notes: Array.from({ length:4 }, () => [0,0,0,0])
  });
});
test('损坏主排列一律拒绝，不能污染页面', () => {
  for(const raw of [null, 123, 'bad', [], {}, {order:['x','a','b','c']}, {order:['a','a','b','c']}]) {
    assert.equal(normalizeSavedSession(raw, ITEMS, 3),null);
  }
});
test('提示、尝试、时间均限制边界', () => {
  assert.deepEqual(
    (({hintIndex,attempts,at})=>({hintIndex,attempts,at}))(normalizeSavedSession({order:ORD,hintIndex:999,attempts:Infinity,at:-6},ITEMS,3)),
    {hintIndex:3,attempts:0,at:0}
  );
  assert.equal(normalizeSavedSession({order:ORD,hintIndex:-30,attempts:25000},ITEMS,3).attempts,9999);
});
test('污染历史项被过滤；历史栈限长，保留末尾有效状态', () => {
  const good = [ITEMS, ORD];
  const input = [...Array(90).fill(ITEMS), ['x','b','c','d'],...good];
  const saved = normalizeSavedSession({order:ORD,history:input,redo:input},ITEMS,3);
  assert.equal(saved.history.length,HISTORY_LIMIT);
  assert.equal(saved.redo.length,HISTORY_LIMIT);
  assert.deepEqual(saved.history.at(-1),ORD);
  const next = pushUndo(saved.history, ORD);
  assert.equal(next.length,HISTORY_LIMIT);
  next.at(-1)[0]='changed';
  assert.equal(ORD[0],'b', '应复制原数组而非共享引用');
});
