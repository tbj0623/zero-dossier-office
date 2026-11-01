import test from 'node:test';
import assert from 'node:assert/strict';
import { buildBackup, parseBackup, VAULT_FORMAT, VAULT_VERSION, VAULT_LIMIT_BYTES } from '../../site/save-vault.mjs';

const SPEC={ 'NA-001': {items:['a','b','c','d'],hintCount:3},
 'NA-002': {items:['e','f','g','h'],hintCount:3} };
const saved={ order:['d','a','b','c'], hintIndex:2, attempts:1,
 history:[['a','b','c','d']], redo:[], notes:[[2,0,0,0],[0,1,0,0],[0,0,0,0],[0,0,0,0]] };
const input={'NA-001':{progress:{solved:false,usedHints:true},session:saved}};
const good=buildBackup(input,SPEC,'2026-11-02T00:00:00Z');
const serialized=JSON.stringify(good);

test('backup format versioned and no extra fields',()=>{
 assert.equal(good.format,VAULT_FORMAT); assert.equal(good.version,VAULT_VERSION);
 assert.deepEqual(Object.keys(good),['format','version','exportedAt','cases']);
});
test('round-trip includes notes and order and completion metadata',()=>{
 const result=parseBackup(serialized,SPEC);
 assert.deepEqual(result['NA-001'].session.order,saved.order);
 assert.equal(result['NA-001'].session.notes[0][0],2);
 assert.equal(result['NA-001'].session.history.length,1);
 assert.deepEqual(result['NA-001'].progress,{solved:false,usedHints:true});
});
test('import does not share parsed nested arrays',()=>{
 const clone=parseBackup(serialized,SPEC);
 clone['NA-001'].session.notes[0][0]=0;
 assert.equal(good.cases['NA-001'].session.notes[0][0],2);
});
test('empty but valid save allows replacing current progress with none',()=>{
 assert.deepEqual(parseBackup(JSON.stringify(buildBackup({},SPEC)),SPEC),{});
});
test('reject unknown IDs, extra fields and fabricated progress fields',()=>{
 const variants=[
 {cases:{'NA-999':{session:saved}}},
 {cases:{'NA-001':{progress:{solved:true,admin:true}}}},
 {cases:{'NA-001':{progress:{times:-1}}}},
 {cases:{'NA-001':{session:{...saved,order:['a','a','b','c']}}}},
 {cases:{'NA-001':{session:{...saved,notes:[[999]]}}}},
 ];
 for(const variant of variants){
   const draft=structuredClone(good);
   draft.cases=variant.cases;
   // invalid notes are normalized safely (while valid order retained).
   if(variant.cases['NA-001']?.session?.notes?.[0]?.[0]===999){
     assert.deepEqual(parseBackup(JSON.stringify(draft),SPEC)['NA-001'].session.notes[0],
       [0,0,0,0]); continue;
   }
   assert.throws(()=>parseBackup(JSON.stringify(draft),SPEC));
 }
});
test('reject format, version, JSON parse error and oversized payload',()=>{
 for(const raw of ['not json','{}', JSON.stringify({...good,version:2}),
  JSON.stringify({...good,format:'other'}),
  JSON.stringify({...good,extra:'x'}), 'x'.repeat(VAULT_LIMIT_BYTES+1)]){
    assert.throws(()=>parseBackup(raw,SPEC));
 }
});
test('legacy saved session without notes gets blank grid',()=>{
 const legacy=buildBackup({'NA-002':{session:{order:['e','f','g','h'],hintIndex:0}}},SPEC);
 assert.equal(legacy.cases['NA-002'].session.notes.length,4);
 assert.equal(legacy.cases['NA-002'].session.notes[0][0],0);
});
