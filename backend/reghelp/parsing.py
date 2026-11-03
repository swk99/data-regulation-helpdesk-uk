"""Structure-preserving extraction; unknown dates/status remain unknown."""
import io
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pypdf import PdfReader
from .fetch import canonical


@dataclass
class Document:
    title: str
    sections: list[dict]
    published: str = ''
    kind: str = 'Unclassified publication'
    links: list[tuple[str, str]] = field(default_factory=list)
    status: str = 'Current legal status not verified'


def links_from(body, base, xml=False):
    soup = BeautifulSoup(body, 'xml' if xml else 'lxml')
    result = {}
    for node in soup.find_all(['loc', 'link'] if xml else ['a']):
        raw = node.get('href') or (node.get_text(strip=True) if node.name in ('loc', 'link') else '')
        if not raw:
            continue
        try:
            url = canonical(urljoin(base, raw))
        except ValueError:
            continue
        label = node.get_text(' ', strip=True)
        if node.parent and node.parent.name in ('item', 'entry'):
            title = node.parent.find('title')
            label = title.get_text(' ', strip=True) if title else label
        result[url] = label or url
    return list(result.items())


def classify(title, url):
    context = (title + ' ' + url).lower()
    for marker, kind in [('consultation', 'Consultation'), ('discussion-paper', 'Discussion paper'),
                         ('supervisory-statement', 'Supervisory statement'), ('supervisory statement', 'Supervisory statement'),
                         ('policy-statement', 'Policy statement'), ('policy statement', 'Policy statement'),
                         ('guidance', 'Guidance')]:
        if marker in context:
            return kind
    return 'Unclassified publication'


def parse(download):
    if download.body.startswith(b'%PDF'):
        reader = PdfReader(io.BytesIO(download.body))
        if len(reader.pages) > 600:
            raise ValueError('PDF exceeds page budget')
        sections = [{'section': f'PDF page {i+1}', 'page': i+1, 'text': p.extract_text() or ''} for i, p in enumerate(reader.pages)]
        title = str((reader.metadata or {}).get('/Title') or download.url.rsplit('/', 1)[-1])
        if sum(len(s['text'].strip()) for s in sections) < 100:
            raise ValueError('PDF has insufficient extractable text; OCR/manual review needed')
        return Document(title, sections, kind=classify(title, download.url))
    if 'html' not in download.content_type:
        raise ValueError('Unsupported document type; expected HTML or PDF')
    soup = BeautifulSoup(download.body, 'lxml')
    title_node = soup.find('h1') or soup.find('title')
    title = title_node.get_text(' ', strip=True) if title_node else download.url
    published = ''
    for key in ('article:published_time', 'datePublished', 'DC.date.issued'):
        node = soup.find('meta', attrs={'property': key}) or soup.find('meta', attrs={'name': key})
        if node:
            published = node.get('content', '')
            break
    if not published:
        node = soup.find('time', attrs={'datetime': True})
        if node:
            published = node['datetime']
    links = links_from(download.body, download.url)
    main = soup.find('main') or soup.find('article') or soup.body or soup
    for node in main.select('script,style,nav,header,footer,aside,form,noscript'):
        node.decompose()
    sections, heading, buf = [], 'Document text', []
    def flush():
        if buf:
            sections.append({'section': heading, 'page': 0, 'text': '\n\n'.join(buf)})
            buf.clear()
    for node in main.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'table']):
        if node.find_parent(['table', 'li']) is not None:
            continue
        text = node.get_text(' ', strip=True)
        if not text:
            continue
        if node.name.startswith('h'):
            flush()
            heading = text
        elif node.name == 'table':
            buf.append('\n'.join(' | '.join(c.get_text(' ', strip=True) for c in tr.find_all(['th', 'td'])) for tr in node.find_all('tr')))
        else:
            buf.append(text)
    flush()
    if sum(len(s['text']) for s in sections) < 150:
        raise ValueError('Insufficient readable text; this source may require JavaScript or an official API')
    return Document(title, sections, published, classify(title, download.url), links)


def chunk(document, limit=1600):
    out = []
    for section in document.sections:
        # Keep numbered rule/paragraph boundaries where the extracted source exposes them.
        paragraphs = re.split(r'\n\s*\n|\n(?=\d+(?:\.\d+)+\s)', section['text'])
        current = ''
        for paragraph in paragraphs:
            pieces = [paragraph[i:i+limit] for i in range(0, len(paragraph), limit)]
            for piece in pieces:
                if current and len(current) + len(piece) + 2 > limit:
                    out.append({**section, 'text': current})
                    current = ''
                current = (current + '\n\n' + piece).strip()
        if current:
            out.append({**section, 'text': current})
    for c in out:
        match = re.search(r'\b([A-Z][A-Z0-9]+\s+\d+(?:\.\d+)+(?:\s*[REGD])?)\b', c['text'])
        c['status'] = document.status
        c['reference'] = match.group(1) if match else ''
        # Only explicit FCA provision markers establish a provision type.
        c['kind'] = document.kind
        if match and match.start() == 0 and match.group(1).endswith('R'):
            c['kind'] = 'Rule marker R — applicability unverified'
        elif match and match.start() == 0 and match.group(1).endswith('G'):
            c['kind'] = 'Guidance marker G'
    return out
