import asyncio
import logging
import os
import re
from urllib.parse import urlsplit
import yaml
from .fetch import Fetcher
from .parsing import parse, chunk, links_from

log = logging.getLogger(__name__)


class Ingestor:
    def __init__(self, settings, store, models, vectors):
        self.s, self.store, self.models, self.vectors = settings, store, models, vectors
        self.sources = yaml.safe_load(settings.source_file.read_text())['sources']
        self.fetcher = Fetcher(settings)
        self.lock = asyncio.Lock()

    async def ingest(self, url, source, discovered_title=''):
        policy = next((s for s in self.sources if s['id'] == source), None)
        if (urlsplit(url).hostname == 'www.fca.org.uk' or (policy and policy.get('requires_permission'))) and os.getenv('FCA_RETRIEVAL_PERMISSION', '').lower() != 'granted':
            raise ValueError('FCA publication indexing requires prior written permission under FCA legal terms 3.3')
        previous = self.store.active(url)
        downloaded = await self.fetcher.get(url, (previous or {}).get('etag', ''), (previous or {}).get('modified', ''))
        if downloaded.not_modified:
            self.store.touch(url)
            version = previous['id']
        else:
            doc = parse(downloaded)
            if any(word in (doc.title+' '+discovered_title).lower() for word in ('[deleted]', 'withdrawn', 'superseded')):
                doc.status = 'Historical or withdrawn — explicit source title label'
            self.store.add_candidates(doc.links, source)
            version = self.store.save(downloaded, doc, chunk(doc), source)
        rows = self.store.rows(version=version)
        with self.store.connect() as db:
            model = db.execute('SELECT vector_model FROM versions WHERE id=?', (version,)).fetchone()[0]
        if model != self.s.embedding_model:
            try:
                for start in range(0, len(rows), 16):
                    batch = rows[start:start+16]
                    embedded = await self.models.embed([r['title'] + '\n' + r['section'] + '\n' + r['text'] for r in batch])
                    self.vectors.upsert(batch, embedded)
                with self.store.connect() as db:
                    db.execute('UPDATE versions SET vector_model=? WHERE id=?', (self.s.embedding_model, version))
            except Exception as exc:
                log.warning('Embedding unavailable: %s', type(exc).__name__)
                return 'Indexed for keyword search; embeddings pending'
        return 'Checked and indexed'

    async def update(self, question='', refresh_urls=None):
        if self.lock.locked():
            return ['An update is already running; using the current index.']
        async with self.lock:
            trace = []
            remaining = self.s.document_budget
            for url, source in (refresh_urls or [])[:5]:
                try:
                    trace.append(f'Rechecked source: {await self.ingest(url, source)}')
                except Exception as exc:
                    trace.append(f'Recheck failed: {url} — {str(exc)[:180]}')
                remaining -= 1
            per_source = max(1, remaining // len(self.sources))
            for source in self.sources:
                if source.get('requires_permission') and os.getenv('FCA_RETRIEVAL_PERMISSION', '').lower() != 'granted':
                    detail = 'Direct reference links only: FCA legal terms 3.3 require prior written permission for electronic retrieval systems.'
                    self.store.mark(source['id'], 'permission_required', detail)
                    trace.append(source['name'] + ': ' + detail)
                    continue
                discovered, errors, indexed = 0, [], 0
                pending = list(source['seeds'])
                seen = set()
                # Small fair budget per source; sitemap indexes can be followed, not crawled without bounds.
                while pending and len(seen) < 3:
                    url = pending.pop(0)
                    if url in seen:
                        continue
                    seen.add(url)
                    try:
                        d = await self.fetcher.get(url)
                        xml = 'xml' in d.content_type or d.body.lstrip().startswith(b'<?xml')
                        links = links_from(d.body, d.url, xml)
                        if not links:
                            raise ValueError('No discoverable links; JavaScript/API adapter may be needed')
                        document_links = []
                        for target, label in links[:5000]:
                            if 'sitemap' in target.lower() and target not in seen:
                                pending.append(target)
                            elif self.relevant(target):
                                document_links.append((target, label))
                        self.store.add_candidates(document_links, source['id'])
                        discovered += len(document_links)
                        if question:
                            words = set(re.findall(r'[a-z]{4,}', question.lower())) - {'what', 'does', 'which', 'should', 'with', 'from', 'have', 'about', 'before'}
                            topics = [(u, t) for u, t in document_links if '/policy-index/' in u or '/prudential-and-resolution-policy-index/banking/' in u]
                            topics.sort(key=lambda item: sum(w in (item[0]+' '+item[1]).lower() for w in words), reverse=True)
                            pending.extend(u for u, t in topics[:2] if any(w in (u+' '+t).lower() for w in words))
                    except Exception as exc:
                        errors.append(str(exc)[:180])
                for candidate in self.store.candidates(question, source['id'], per_source):
                    if remaining <= 0:
                        break
                    remaining -= 1
                    try:
                        note = await self.ingest(candidate['url'], source['id'], candidate['title'])
                        indexed += 1
                        if 'pending' in note:
                            errors.append(note)
                    except Exception as exc:
                        errors.append(str(exc)[:180])
                state = 'partial' if errors else ('checked' if discovered else 'unavailable')
                detail = f'{discovered} links discovered; {indexed} documents checked. ' + '; '.join(errors[:3])
                self.store.mark(source['id'], state, detail)
                trace.append(source['name'] + ': ' + detail)
            return trace

    @staticmethod
    def relevant(url):
        path = urlsplit(url).path.lower()
        if path == '/' or path.startswith('/rss') or any(x in path for x in ('/legal', '/privacy', '/cookies', '/contact', '/login')):
            return False
        return any(x in path for x in ('publication', 'prudential', 'handbook', 'rulebook', '/pra-rules', '/rules/', '/guidance/', '.pdf', 'policy', 'supervisory', '/report/', '/paper/', '/working-paper/', '/statement/'))
