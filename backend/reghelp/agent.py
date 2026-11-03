import re
import logging
from .query import plan_query
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


def is_korean_followup(question):
    text = question.lower()
    language = any(word in text for word in ('korean', '한국어', '한글'))
    action = any(word in text for word in ('translat', 'summar', '번역', '요약'))
    return language and action


class Agent:
    def __init__(self, store, models, vectors, ingestor):
        self.store, self.models, self.vectors, self.ingestor = store, models, vectors, ingestor

    async def korean_summary(self, previous, question):
        import logging
        result = {**previous, 'claims': [], 'mode': 'references_only',
                  'trace': [*previous.get('trace', []), 'Korean follow-up: reused the previous answer evidence; no new search or source recheck.'],
                  'warnings': list(previous.get('warnings', []))}
        # The context is a server-held answer, never client-supplied source text.
        evidence = previous.get('sources', [])
        claims = []
        if evidence:
            try:
                payload = await self.models.generate(evidence,
                    '한국어로 이전 답변의 근거를 쉽게 요약하세요. 새로운 법적 결론을 추가하지 마세요. '
                    '영문 원문의 정확한 인용 quote와 기존 evidence_id는 유지하세요. '
                    '자료가 질문에 답하지 못하면 그 불확실성을 유지하세요. Previous research question: '
                    + previous.get('research_question', '') + '\nFollow-up: ' + question,
                    as_of={key: previous[key] for key in ('as_of_date', 'timezone', 'server_time')})
                claims = validated_claims(payload, evidence)
            except Exception as exc:
                logging.getLogger(__name__).warning('Korean summary failed: %s', type(exc).__name__)
        result['claims'] = claims
        result['mode'] = 'grounded_summary' if claims else 'references_only'
        result['message'] = ('이전 답변에 사용한 자료를 한국어로 요약했습니다. 원문 출처와 인용은 유지했으며, 새로운 자료 검색은 하지 않았습니다. 이전 답변에서 확인하지 못한 적용 여부는 여전히 미확인입니다.'
            if claims else '이전 답변과 출처는 찾았지만, 한국어 요약을 생성하거나 검증하지 못했습니다. 로컬 Ollama 모델의 상태를 확인하세요. 관련 없는 자료를 새로 검색하지 않았습니다. 아래 출처는 이전 답변의 자료입니다.')
        result['answered_at'] = now()
        return result

    async def answer(self, question, live=False):
        clock = clock_context()
        if re.fullmatch(r'\s*(?:hello|hi|hey|안녕(?:하세요)?)[!.?\s]*', question, flags=re.IGNORECASE):
            return {**clock, 'freshness': 'not_applicable', 'mode': 'welcome',
                    'message': 'Hello! Ask me a specific UK regulatory question, such as: What are the PRA expectations for model risk management? I will check permitted official sources and show supporting references or explain what I could not verify.',
                    'claims': [], 'sources': [], 'official_sources': [], 'warnings': [],
                    'trace': ['Greeting only. No regulatory documents were checked.'],
                    'answered_at': now(), 'live_requested': live}
        plan = plan_query(question)
        trace = [f"Assessment date: {clock['as_of_date']} (Europe/London), read from the backend clock.", 'Searched the indexed official documents.', f'Query plan: {plan.institution or "unspecified institution"}; {plan.jurisdiction}; {plan.intent}.', 'Retrieval concepts: '+plan.search_text]
        rows, warnings = await retrieve(question, self.store, self.models, self.vectors)
        if live:
            refresh = list(dict.fromkeys((r['url'], r['source']) for r in rows))
            trace.extend(await self.ingestor.update(question, refresh))
            rows, new_warnings = await retrieve(question, self.store, self.models, self.vectors)
            warnings.extend(new_warnings)
        evidence = [{'citation': f'S{i+1}', 'title': r['title'], 'url': r['url'], 'section': r['section'],
                     'page': r['page'], 'text': r['text'], 'kind': r['kind'], 'reference': r['reference'],
                     'published': r['published'], 'checked': r['checked'], 'version': r['hash'],
                     'relevance_score': r.get('relevance_score'), 'relevance_reason': r.get('relevance_reason'), 'effective_date': None, 'legal_status': r.get('status', 'Not independently verified')} for i, r in enumerate(rows)]
        fresh = bool(evidence) and live and all(checked_since(r['checked'], clock['server_time']) for r in evidence)
        freshness = 'sources_rechecked' if fresh else 'current_status_unverified'
        if not fresh:
            warnings.append(f"Current applicability as of {clock['as_of_date']} could not be verified: one or more sources were not successfully rechecked for this request.")
        claims = []
        if evidence and (fresh or not live):
            try:
                claims = validated_claims(await self.models.generate(evidence, question, as_of=clock), evidence)
                trace.append('Checked citation IDs, exact quotations and regulatory references.')
            except Exception as exc:
                code = getattr(exc, 'code', type(exc).__name__)
                logging.getLogger(__name__).warning('Answer generation failed: %s', code)
                warnings.append(f'Answer generation failed ({code}); showing relevant excerpts only. Check Ollama and the PC app console.')
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
                'query_plan': plan.public(), 'official_sources': [{'name': s['name'], 'url': s['home']} for s in self.ingestor.sources],
                'clarification': plan.clarification, 'warnings': list(dict.fromkeys(warnings)), 'trace': trace, 'answered_at': now(), 'live_requested': live}
