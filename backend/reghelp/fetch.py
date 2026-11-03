"""Bounded official-site fetcher. All redirects are rechecked against policy."""
import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit, urljoin
import httpx
from protego import Protego

HOSTS = {'www.fca.org.uk', 'handbook.fca.org.uk', 'www.handbook.fca.org.uk',
         'www.bankofengland.co.uk', 'www.prarulebook.co.uk'}
AGENT = 'RegulationHelpdesk/1.0'


def canonical(url: str) -> str:
    p = urlsplit(url.strip())
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Only approved official HTTPS sources are permitted')
    return urlunsplit(('https', p.hostname, p.path or '/', p.query, ''))


@dataclass
class Download:
    url: str
    body: bytes
    content_type: str
    etag: str = ''
    modified: str = ''
    not_modified: bool = False


class Fetcher:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=25, follow_redirects=False, headers={'User-Agent': AGENT, 'Accept-Encoding': 'identity'})
        self.robots = {}
        self.last = {}
        self.lock = asyncio.Lock()

    async def close(self):
        await self.client.aclose()

    async def request(self, url, headers=None):
        host = urlsplit(url).hostname
        async with self.lock:
            delay = self.settings.request_delay
            cached = self.robots.get(host)
            if cached:
                delay = max(delay, float(cached[1].crawl_delay(AGENT) or 0))
            await asyncio.sleep(max(0, delay - (time.monotonic() - self.last.get(host, 0))))
            self.last[host] = time.monotonic()
            async with self.client.stream('GET', url, headers=headers or {}) as r:
                body = bytearray()
                async for part in r.aiter_bytes():
                    body.extend(part)
                    if len(body) > self.settings.max_bytes:
                        raise ValueError('Document exceeds download size limit')
                return httpx.Response(r.status_code, headers=r.headers, content=bytes(body), request=r.request)

    async def permitted(self, url):
        host = urlsplit(url).hostname
        cached = self.robots.get(host)
        if not cached or time.monotonic() - cached[0] > 3600:
            response = await self.request(f'https://{host}/robots.txt')
            # Failure is not permission. A genuine missing robots file permits crawling.
            if response.status_code == 404:
                policy = Protego.parse('User-agent: *\nAllow: /')
            elif response.status_code == 200 and '<html' not in response.text.lower():
                policy = Protego.parse(response.text)
            else:
                raise ValueError('Robots policy unavailable; source was not fetched')
            self.robots[host] = (time.monotonic(), policy)
        return self.robots[host][1].can_fetch(url, AGENT)

    async def get(self, url, etag='', modified=''):
        url = canonical(url)
        headers = {}
        if etag:
            headers['If-None-Match'] = etag
        if modified:
            headers['If-Modified-Since'] = modified
        for _ in range(6):
            if not await self.permitted(url):
                raise ValueError('Blocked by source robots.txt')
            for attempt in range(3):
                r = await self.request(url, headers)
                if r.status_code not in (429, 500, 502, 503, 504):
                    break
                retry = r.headers.get('retry-after', '')
                if retry.isdigit() and int(retry) > 30:
                    raise ValueError('Source requested a longer retry delay; deferred')
                await asyncio.sleep(max(2 ** attempt, int(retry) if retry.isdigit() else 0))
            if r.status_code in (301, 302, 303, 307, 308):
                url = canonical(urljoin(url, r.headers['location']))
                headers = {}
                continue
            if r.status_code == 304:
                return Download(url, b'', '', etag, modified, True)
            r.raise_for_status()
            return Download(url, r.content, r.headers.get('content-type', ''), r.headers.get('etag', ''), r.headers.get('last-modified', ''))
        raise ValueError('Redirect limit exceeded')
