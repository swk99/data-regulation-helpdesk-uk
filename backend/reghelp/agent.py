import re
from .retrieval import retrieve
from .storage import now
from .clock import clock_context, checked_since

REFERENCE = re.compile(r'\b(?:[A-Z]{2,}\s+\d+(?:\.\d+)+(?:\s*[REGD])?|(?:SS|PS|CP)\s*\d+/\d+)\b')


def validated_claims(payload, evidence):
    by_id = {r['citation']: r for r in evidence}
    valid = []
    for item in payload.get('claims', [])[:5]:
        if not isinstance(item, dict):
            continue
        text, quote, cid = item.get('text', ''), item.get('quote', ''), item.get('evidence_id', '')
        if not all(isinstance(x, str) for x in (text, quote, cid)):
            continue
        row = by_id.get(cid)
        if not row or not text or len(text) > 1200 or len(quote.strip()) < 20:
            continue
        normalize = lambda value: ' '.join(value.split())
        if normalize(quote) not in normalize(row['text']) or 'http' in text.lower():
            continue
        if any(ref not in row['text'] + row['title'] + row['section'] for ref in REFERENCE.findall(text)):
            continue
        valid.append({'text': text, 'citation': cid, 'quote': quote})
    return valid


class Agent:
    def __init__(self, store, models, vectors, ingestor):
        self.store, self.models, self.vectors, self.ingestor = store, models, vectors, ingestor

    async def answer(self, question, live=False):
        clock = clock_context()
        trace = [f"Assessment date: {clock['as_of_date']} (Europe/London), read from the backend clock.", 'Searched the indexed official documents.']
        rows, warnings = await retrieve(question, self.store, self.models, self.vectors)
        if live:
            refresh = list(dict.fromkeys((r['url'], r['source']) for r in rows))
            trace.extend(await self.ingestor.update(question, refresh))
            rows, new_warnings = await retrieve(question, self.store, self.models, self.vectors)
            warnings.extend(new_warnings)
        evidence = [{'citation': f'S{i+1}', 'title': r['title'], 'url': r['url'], 'section': r['section'],
                     'page': r['page'], 'text': r['text'], 'kind': r['kind'], 'reference': r['reference'],
                     'published': r['published'], 'checked': r['checked'], 'version': r['hash'],
                     'effective_date': None, 'legal_status': r.get('status', 'Not independently verified')} for i, r in enumerate(rows)]
        fresh = bool(evidence) and live and all(checked_since(r['checked'], clock['server_time']) for r in evidence)
        freshness = 'sources_rechecked' if fresh else 'current_status_unverified'
        if not fresh:
            warnings.append(f"Current applicability as of {clock['as_of_date']} could not be verified: one or more sources were not successfully rechecked for this request.")
        claims = []
        if evidence and (fresh or not live):
            try:
                claims = validated_claims(await self.models.generate(evidence, question, as_of=clock), evidence)
                trace.append('Checked citation IDs, exact quotations and regulatory references.')
            except Exception:
                warnings.append('Answer model unavailable; showing retrieved source excerpts instead.')
        mode = 'grounded_summary' if claims else 'references_only'
        if not claims:
            claims = [{'text': r['text'][:650], 'citation': r['citation'], 'quote': '', 'extract': True} for r in evidence[:3]]
        message = ('These findings are based on retrieved passages. Verify applicability and effective dates in the linked source.' if mode == 'grounded_summary'
                   else 'I could not establish a supported answer. These are relevant passages to review, not a confirmed regulatory conclusion.' if evidence
                   else 'I do not have enough indexed evidence to answer. Try a live check or open the official sources below.')
        warnings.append('Coverage is bounded. A recent fetch does not establish that a rule is currently in force. Historical point-in-time legal answers are not supported.')
        message = f"As of {clock['as_of_date']} (Europe/London): " + message
        if live and not fresh:
            message = f"Current applicability as of {clock['as_of_date']} is unverified. Review the references below; I cannot confirm that these requirements apply today."
        return {**clock, 'freshness': freshness, 'mode': mode, 'message': message, 'claims': claims, 'sources': evidence,
                'official_sources': [{'name': s['name'], 'url': s['home']} for s in self.ingestor.sources],
                'warnings': list(dict.fromkeys(warnings)), 'trace': trace, 'answered_at': now(), 'live_requested': live}
