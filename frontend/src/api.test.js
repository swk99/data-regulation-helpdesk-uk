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
