const KEY = 'reghelp:pages-session:v1';
const PENDING = 'reghelp:pages-pending:v1';
function persist(storage,key,value){try{storage.setItem(key,JSON.stringify(value));}catch{}}
function read(storage,key){try{return JSON.parse(storage.getItem(key)||'null');}catch{return null;}}
export function validSession(value){
 try {const url=new URL(value?.base);return value.base===localBase(url.port)&&/^[\w-]{24,200}$/.test(value.token||'');}catch{return false;}
}
export function localBase(port) {
  if (!/^\d{1,5}$/.test(String(port)) || Number(port)<1024 || Number(port)>65535) throw new Error('Invalid local app port. Start RegulationHelpdesk.exe again.');
  return `http://127.0.0.1:${Number(port)}`;
}
export function readConnection(location, history, storage) {
  if (['127.0.0.1','localhost'].includes(location.hostname)) return {base:location.origin,token:'',local:true};
  if (location.origin !== 'https://swk99.github.io') return {};
  const params = new URLSearchParams(location.hash.slice(1));
  if (params.has('ticket') || params.has('port')) {
    // Strip the single-use credential before any requests, links or UI render.
    history.replaceState(null,'',location.pathname+location.search);
    try { storage.removeItem(KEY); } catch {}
    const ticket=params.get('ticket')||'';
    if (!/^[\w-]{24,200}$/.test(ticket)) throw new Error('Invalid launch link. Run RegulationHelpdesk.exe again.');
    const pending={base:localBase(params.get('port')),ticket,token:'',savedAt:Date.now()};
    persist(storage,PENDING,pending);
    return pending;
  }
  const saved=read(storage,KEY);
  if(validSession(saved))return {base:saved.base,token:saved.token};
  const pending=read(storage,PENDING);
  if(pending && Number.isFinite(pending.savedAt) && Date.now()-pending.savedAt < 300000 && Date.now()>=pending.savedAt && /^[\w-]{24,200}$/.test(pending.ticket||'')){
    try {const url=new URL(pending.base);if(pending.base===localBase(url.port))return pending;}catch{}
  }

  return {};
}
export function saveConnection(storage, base, token) {
  persist(storage,KEY,{base,token});
  try{storage.removeItem(PENDING);}catch{}
}
export async function pairConnection(base, ticket) {
  const response=await fetch(base+'/api/pair',{
    method:'POST',headers:{'Content-Type':'application/json'},credentials:'omit',
    targetAddressSpace:'loopback',body:JSON.stringify({key:ticket}),signal:AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error('Launch link expired. Close the PC app and run RegulationHelpdesk.exe again.');
  const data=await response.json();
  if (!/^[\w-]{24,200}$/.test(data.token||'')) throw new Error('Invalid local app response. Restart the PC app.');
  return data.token;
}

// BroadcastChannel is restricted by the browser to this origin/profile. Share
// only an already authenticated session, never an unused pairing ticket.
export function createSessionBridge(getSession, Channel=globalThis.BroadcastChannel){
 if(!Channel)return {request:async()=>({}),close(){}};
 const channel=new Channel('reghelp:pages-connection:v1');
 const pending=new Map();
 channel.onmessage=({data})=>{
  if(!data||typeof data.id!=='string')return;
  if(data.type==='request'){
   const session=getSession();
   if(validSession(session))channel.postMessage({type:'session',id:data.id,base:session.base,token:session.token});
  }else if(data.type==='session'&&pending.has(data.id)&&validSession(data)){
   pending.get(data.id)({base:data.base,token:data.token});
  }
 };
 return {
  request(timeout=1800){return new Promise(resolve=>{
   const id=crypto.randomUUID();
   const timer=setTimeout(()=>finish({}),timeout);
   const finish=value=>{clearTimeout(timer);pending.delete(id);resolve(value);};
   pending.set(id,finish);channel.postMessage({type:'request',id});
  });},
  close(){for(const finish of [...pending.values()])finish({});channel.close();}
 };
}
