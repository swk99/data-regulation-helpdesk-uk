export function validateEndpoint(value) {
  const url = new URL(value);
  const local = ['localhost', '127.0.0.1'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(local && url.protocol === 'http:')) throw new Error('Use an HTTPS backend URL.');
  if (url.username || url.password || url.search || url.hash) throw new Error('Enter a backend URL without credentials, query or fragment.');
  return url.href.replace(/\/$/, '');
}
export async function request(base, token, path, body, timeout=550000) {
  let response;
  try { response = await fetch(base + path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    ...(base.startsWith('http://127.0.0.1:') ? {targetAddressSpace:'loopback'} : {}),
    headers: {...(token ? {'Authorization': `Bearer ${token}`} : {}), ...(body === undefined ? {} : {'Content-Type': 'application/json'})},
    ...(body === undefined ? {} : {body: JSON.stringify(body)}),
    signal: AbortSignal.timeout(timeout),
  });
  } catch(error) {
    if(error.name==='TimeoutError'||error.name==='AbortError') throw new Error('The request timed out. Keep the PC app open and try a narrower question.');
    if(!(error instanceof TypeError))throw error;
    let reachable=false;
    try {
      const health=await fetch(base+'/api/time',{method:'GET',credentials:'omit',
        ...(base.startsWith('http://127.0.0.1:')?{targetAddressSpace:'loopback'}:{}),signal:AbortSignal.timeout(4000)});
      reachable=health.ok;
    } catch {}
    throw new Error(reachable
      ? 'The PC app is reachable, but the request failed without a readable response. An older app can hide internal errors this way. Update RegulationHelpdesk.exe; if it persists, check its console. Your question was not sent again.'
      : 'Cannot reach the PC app from this tab. Keep RegulationHelpdesk.exe open, check for an error in its console, and allow local device access for this site. Your question was not sent again.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    if (response.status === 404) throw new Error('Research service not found. Open the app using Start Helpdesk.cmd, not a GitHub Pages address.');
    throw new Error(typeof data.detail === 'string' ? data.detail : `Backend returned ${response.status}`);
  }
  return response.json();
}
