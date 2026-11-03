const KEY = 'reghelp:pages-session:v1';
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
    return {base:localBase(params.get('port')),ticket,token:''};
  }
  try {
    const saved=JSON.parse(storage.getItem(KEY)||'null');
    if (saved && /^[\w-]{24,200}$/.test(saved.token)) {
      const url=new URL(saved.base);
      if (saved.base===localBase(url.port)) return {base:saved.base,token:saved.token};
    }
  } catch {}
  return {};
}
export function saveConnection(storage, base, token) {
  try { storage.setItem(KEY,JSON.stringify({base,token})); } catch {}
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
