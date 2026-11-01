
import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeGuide} from '../../site/player-state.mjs';

test('guide defaults to incomplete without trusting old or invalid saves',()=>{
 assert.deepEqual(normalizeGuide(), {read:false,moved:false,submitted:false,dismissed:false});
 assert.deepEqual(normalizeGuide([]), {read:false,moved:false,submitted:false,dismissed:false});
 assert.deepEqual(normalizeGuide({read:'true',moved:1,submitted:null,dismissed:true}),
   {read:false,moved:false,submitted:false,dismissed:true});
});
test('guide state accepts only known boolean entries',()=>{
 assert.deepEqual(normalizeGuide({read:true,moved:true,submitted:false,dismissed:false,cheat:true}),
   {read:true,moved:true,submitted:false,dismissed:false});
});
