import test from 'node:test';
import assert from 'node:assert/strict';
import {search} from '../web/search.js';
const products=[{title:'Žalias sodas',artist:'Tadas',sizes:[[50,115],[60,140]],url:'a'},{title:'Other',artist:'B',sizes:[[115,50]],url:'b'},{title:'Unknown',sizes:[],url:'c'}];
test('both inclusive bounds must match the same variant',()=>{
 assert.deepEqual(search(products,{wmin:50,wmax:60,hmin:100,hmax:120,order:'wh'}).map(p=>p.url),['a']);
 assert.equal(search(products,{wmin:50,wmax:50,hmin:140,hmax:140,order:'wh'}).length,0);
});
test('order can be inverted explicitly',()=>assert.deepEqual(search(products,{wmin:50,wmax:60,hmin:100,hmax:120,order:'hw'}).map(p=>p.url),['b']));
test('accent insensitive text search',()=>assert.equal(search(products,{q:'zalias'}).length,1));
test('unknown sizes excluded only when size filter is active',()=>{assert.equal(search(products,{}).length,3);assert.equal(search(products,{wmin:1}).length,2)});
test('automatic order filters physical dimensions per work',()=>{
 const ps=[{url:'portrait',sizes:[[115,50]],size_order:'hw'},{url:'landscape',sizes:[[50,115]],size_order:'hw'},{url:'unknown',sizes:[[50,115]],size_order:'unknown'}];
 assert.deepEqual(search(ps,{wmin:50,wmax:60,hmin:100,hmax:120,order:'auto'}).map(p=>p.url),['portrait']);
 assert.equal(search(ps,{order:'auto'}).length,3);
});
test('artwork filter excludes accessories while permitting unclassified works',()=>{
 const ps=[{title:'Art',is_artwork:true},{title:'Bag',is_artwork:false},{title:'Unknown'}];
 assert.equal(search(ps,{kind:'art'}).length,2);
 assert.equal(search(ps,{kind:'all'}).length,3);
});
test('Algis Kriščiūnas is excluded by default',()=>{
 const ps=[{title:'A',artist:'Algis Kriščiūnas'},{title:'B',artist:'Other'}];
 assert.deepEqual(search(ps).map(p=>p.title),['B']);
});
test('multiple excluded authors use exact accent-insensitive names and compose with filters',()=>{
 const ps=[{title:'A',artist:'Algis Kriščiūnas'},{title:'B',artist:'Arūnas Rutkus'},{title:'C',artist:'Arūnas Rutkus Jr'},{title:'D',artist:''}];
 assert.deepEqual(search(ps,{excludedArtists:['algis krisciunas','Arunas Rutkus']}).map(p=>p.title),['C','D']);
 assert.equal(search(ps,{artist:'Arūnas Rutkus',excludedArtists:['Arūnas Rutkus']}).length,0);
});
test('empty exclusions explicitly restores all authors',()=>{
 assert.equal(search([{artist:'Algis Kriščiūnas'}],{excludedArtists:[]}).length,1);
});
