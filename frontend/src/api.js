export function validateEndpoint(value) {
  const url = new URL(value);
  const local = ['localhost', '127.0.0.1'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(local && url.protocol === 'http:')) throw new Error('Use an HTTPS backend URL.');
  if (url.username || url.password || url.search || url.hash) throw new Error('Enter a backend URL without credentials, query or fragment.');
  return url.href.replace(/\/$/, '');
}
export async function request(base, token, path, body, timeout=550000) {
  const response = await fetch(base + path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    ...(base.startsWith('http://127.0.0.1:') ? {targetAddressSpace:'loopback'} : {}),
    headers: {...(token ? {'Authorization': `Bearer ${token}`} : {}), ...(body === undefined ? {} : {'Content-Type': 'application/json'})},
    ...(body === undefined ? {} : {body: JSON.stringify(body)}),
    signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    if (response.status === 404) throw new Error('Research service not found. Open the app using Start Helpdesk.cmd, not a GitHub Pages address.');
    throw new Error(typeof data.detail === 'string' ? data.detail : `Backend returned ${response.status}`);
  }
  return response.json();
}
