import test from 'node:test';
import assert from 'node:assert/strict';
import {validateEndpoint,request} from './api.js';
test('endpoint validation keeps access tokens off insecure remote connections',()=>{
 assert.equal(validateEndpoint('https://api.example.com/'),'https://api.example.com');
 assert.equal(validateEndpoint('http://localhost:8000'),'http://localhost:8000');
 for(const u of ['http://example.com','javascript:alert(1)','https://user:pass@api.example.com','https://api.example.com?token=x'])assert.throws(()=>validateEndpoint(u));
});
test('API surfaces authentication failures',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>({ok:false,status:401,json:async()=>({detail:'Invalid token'})});
 try{await assert.rejects(request('https://api.example.com','bad','/api/status'),/Invalid token/);}finally{globalThis.fetch=original;}
});

import {formatToday} from './clock.js';
test('UK date crosses midnight correctly during British Summer Time',()=>{
 assert.equal(formatToday(new Date('2026-06-01T23:30:00Z')),'Tuesday, 2 June 2026');
 assert.equal(formatToday(new Date('2026-11-03T23:30:00Z')),'Tuesday, 3 November 2026');
});

import {websiteClock} from './clock.js';
test('website time accounts for CDN age and rejects missing headers',()=>{
 assert.equal(websiteClock({ok:true,headers:new Headers({date:'Tue, 03 Nov 2026 12:00:00 GMT',age:'60'})}),Date.parse('2026-11-03T12:01:00Z'));
 assert.throws(()=>websiteClock({ok:true,headers:new Headers()}));
});
