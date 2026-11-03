import test from 'node:test';
import assert from 'node:assert/strict';
import {localBase,readConnection,saveConnection,pairConnection} from './connection.js';
function storage(){const map=new Map();return {getItem:k=>map.get(k),setItem:(k,v)=>map.set(k,v),removeItem:k=>map.delete(k)};}
const ticket='a'.repeat(40);
const page={origin:'https://swk99.github.io',hostname:'swk99.github.io',pathname:'/data-regulation-helpdesk-uk/',search:'',hash:`#port=8123&ticket=${ticket}`};
test('pairing only targets loopback and clears launch secret from URL',()=>{
 let cleared;const c=readConnection(page,{replaceState:(a,b,c)=>cleared=c},storage());
 assert.equal(c.base,'http://127.0.0.1:8123');assert.equal(c.ticket,ticket);assert.equal(cleared,page.pathname);
 for(const port of ['0','80','65536','evil.com','8123/path'])assert.throws(()=>localBase(port));
 assert.deepEqual(readConnection({...page,origin:'https://evil.example'},{},storage()),{});
});
test('tab session survives reload and rejects a substituted remote endpoint',()=>{
 const s=storage();saveConnection(s,'http://127.0.0.1:8123',ticket);
 assert.equal(readConnection({...page,hash:''},{},s).token,ticket);
 saveConnection(s,'https://evil.example:8123',ticket);
 assert.deepEqual(readConnection({...page,hash:''},{},s),{});
});
test('one-use pairing sends secret only in POST body without cookies',async()=>{
 const original=globalThis.fetch;let options;
 globalThis.fetch=async(u,o)=>{assert.equal(u,'http://127.0.0.1:8123/api/pair');options=o;return{ok:true,json:async()=>({token:ticket})}};
 try {assert.equal(await pairConnection(localBase(8123),ticket),ticket);assert.equal(options.credentials,'omit');assert.equal(options.targetAddressSpace,'loopback');assert.equal(JSON.parse(options.body).key,ticket);}finally{globalThis.fetch=original;}
});

test('refresh during blocked pairing retains the pending ticket only in this tab',()=>{
 const s=storage();readConnection(page,{replaceState(){}},s);
 const resumed=readConnection({...page,hash:''},{},s);
 assert.equal(resumed.ticket,ticket);assert.equal(resumed.base,'http://127.0.0.1:8123');
 saveConnection(s,resumed.base,'b'.repeat(40));
 const connected=readConnection({...page,hash:''},{},s);
 assert.equal(connected.token,'b'.repeat(40));assert.equal(connected.ticket,undefined);
});
test('expired pending pairing is not reused',()=>{
 const s=storage();readConnection(page,{replaceState(){}},s);
 const old=Date.now;Date.now=()=>old()+300001;
 try{assert.deepEqual(readConnection({...page,hash:''},{},s),{});}finally{Date.now=old;}
});
test('new tab receives an authenticated session from another open tab',async()=>{
 const {createSessionBridge}=await import('./connection.js');
 const owner=createSessionBridge(()=>({base:'http://127.0.0.1:8123',token:ticket}));
 const newcomer=createSessionBridge(()=>null);
 try{assert.deepEqual(await newcomer.request(),{base:'http://127.0.0.1:8123',token:ticket});}finally{owner.close();newcomer.close();}
});
test('unpaired tabs do not broadcast tickets as credentials',async()=>{
 const {createSessionBridge}=await import('./connection.js');
 const owner=createSessionBridge(()=>({base:'http://127.0.0.1:8123',ticket}));
 const newcomer=createSessionBridge(()=>null);
 try{assert.deepEqual(await newcomer.request(50),{});}finally{owner.close();newcomer.close();}
});
