import test from 'node:test';
import assert from 'node:assert/strict';
import { blankNotes, normalizeNotes, nextNote, noteCounts } from '../../site/deduction-notes.mjs';
import { normalizeSavedSession } from '../../site/player-state.mjs';

test('空白笔记独立行、尺寸受限', () => {
  const notes=blankNotes(4);
  assert.equal(notes.length,4);
  notes[0][0]=2;
  assert.equal(notes[1][0],0);
  assert.deepEqual(blankNotes(0),[]);
  assert.deepEqual(blankNotes(9),[]);
});
test('三态标记闭环，不读取求解器也不修改原顺序', () => {
  assert.equal(nextNote(0),1);
  assert.equal(nextNote(1),2);
  assert.equal(nextNote(2),0);
  assert.deepEqual(noteCounts([[0,1],[2,1]]), { possible:2, excluded:1 });
});
test('只接受整齐矩阵、合法三态，无效输入安全降级', () => {
  const n=3, original=[[0,1,2],[1,0,2],[2,0,1]];
  assert.deepEqual(normalizeNotes(original,n),original);
  const out=normalizeNotes(original,n);
  out[0][0]=2;
  assert.equal(original[0][0],0);
  for(const bad of [null,{},[],[[0,0,0]],[[0,1,2],null,[0,0,0]],
    [[0,1,2],[0,1,3],[0,0,0]],[[0,1,2],[0,-1,2],[0,0,0]],
    [[0,1,2],[0,NaN,2],[0,0,0]]]) {
      assert.deepEqual(normalizeNotes(bad,n),blankNotes(n));
  }
});
test('旧存档默认空笔记，新存档保存内容并复制而非共享数组', () => {
  const items=['a','b','c'];
  const old=normalizeSavedSession({order:items},items,3);
  assert.deepEqual(old.notes,blankNotes(3));
  const original=[[2,0,0],[0,1,0],[0,0,0]];
  const restored=normalizeSavedSession({order:items,notes:original},items,3);
  assert.deepEqual(restored.notes,original);
  restored.notes[0][0]=0;
  assert.equal(original[0][0],2);
});
