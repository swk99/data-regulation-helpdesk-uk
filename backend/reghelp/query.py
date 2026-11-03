"""Auditable query planning and conservative, model-independent relevance gates.
These are explicit retrieval heuristics, not legal applicability determinations.
"""
import re
from dataclasses import dataclass, field

STOP = set('hi hello i m im s it its a an the in of to for and or is are was be been can could would should may must do does did we you me my our us uk united kingdom working work authorised authorized please tell explain what which how whether with from about above answer translate korean summary london new open'.split())
OWNERSHIP = ('subsidiar', 'daughter company', 'parent company', 'holding company', 'controlling interest',
             'control of', 'ownership', 'cuso', 'service organisation', 'service organization', 'ancillary services', 'majority stake', 'majority share', '지분', '자회사', '모회사')
NOISE = ('contents', 'your personal information', 'your personal data', 'privacy statement', 'privacy notice',
         'consent to publication', 'who will have access', 'acknowledgement', 'methodology', 'responses and next steps')


@dataclass
class QueryPlan:
    question: str
    institution: str = ''
    jurisdiction: str = 'Unspecified'
    intent: str = 'regulatory_research'
    terms: list[str] = field(default_factory=list)
    clarification: list[str] = field(default_factory=list)

    @property
    def search_text(self):
        return ' '.join(self.terms)

    def public(self):
        return {'institution': self.institution or 'Unspecified', 'jurisdiction': self.jurisdiction,
                'intent': self.intent, 'search_terms': self.terms, 'clarification': self.clarification,
                'method': 'Explicit retrieval heuristics; not a legal determination'}


def plan_query(question):
    text = question.lower().replace('compnay', 'company')
    credit = bool(re.search(r'credit[ -]?union|신용조합|신협|\bcuso', text))
    ni = 'northern ireland' in text or '북아일랜드' in text
    gb = bool(re.search(r'\blondon\b|\bengland\b|\bscotland\b|\bwales\b|great britain|런던|잉글랜드', text))
    region = 'UK / cross-jurisdiction' if ni and gb else 'Northern Ireland' if ni else 'Great Britain' if gb else 'Unspecified'
    ownership = any(word in text for word in OWNERSHIP) or bool(re.search(r'(set up|establish|form|open|create|설립).*(company|fintech|법인|회사)',text))
    terms = list(dict.fromkeys(w for w in re.findall(r'[a-z0-9]+', text) if len(w)>2 and w not in STOP))
    if credit:
        terms = [w for w in terms if w not in ('credit','union','unions')]
        terms += ['credit union', 'credit unions', 'CUSO']
    if ownership:
        terms += ['subsidiary', 'subsidiaries', 'controlling interest', 'ownership', 'holding company', 'ancillary services']
    p = QueryPlan(question, 'credit_union' if credit else '', region,
                  'ownership_structure' if ownership else 'regulatory_research', list(dict.fromkeys(terms)))
    if ownership and credit:
        p.clarification = ['Is the credit union to own the fintech, or is the fintech proposed to own/control the credit union?',
                           'Will services be limited to credit unions/members, or sold to the wider public?']
    return p


def rank_passage(row, plan):
    """Return (score, reason); zero means exclude even if it is a vector neighbour."""
    title, section, body = (str(row.get(k, '')).lower() for k in ('title','section','text'))
    url = row.get('url','').lower()
    context = title+' '+section+' '+body
    if str(row.get('status','')).startswith('Historical'):
        return 0, 'Historical source'
    if any(word in section for word in NOISE) and not any(word in plan.question.lower() for word in ('privacy','personal data','survey','methodology','개인정보','설문')):
        return 0, 'Administrative or survey section'
    if any(word in title for word in ('your personal data','privacy notice','privacy statement')) and not any(word in plan.question.lower() for word in ('privacy','personal data','개인정보')):
        return 0, 'Privacy administration document'
    if plan.jurisdiction == 'Great Britain' and ('northern ireland' in title or 'nicu-' in url):
        return 0, 'Northern Ireland-specific document for a Great Britain question'
    if plan.jurisdiction == 'Northern Ireland' and 'great britain' in title:
        return 0, 'Great Britain-specific document for a Northern Ireland question'
    if plan.institution == 'credit_union' and not re.search(r'credit[ -]?unions?|\bcuso', context):
        return 0, 'Institution mismatch'
    if plan.intent == 'ownership_structure' and not any(term in body for term in OWNERSHIP):
        return 0, 'No ownership or service-organisation evidence in the passage'
    hits = sum(1 for term in plan.terms if term.lower() in body)
    if not hits:
        return 0, 'No substantive query match in the passage'
    score = hits * 2 + sum(1 for term in plan.terms if term.lower() in section)
    kind = row.get('kind', '')
    if kind.startswith('Rule') or '/pra-rules/' in url:
        score += 5
    elif kind == 'Supervisory statement' or 'supervising credit unions' in title:
        score += 4
    elif kind in ('Consultation','Discussion paper'):
        score -= 2
    return max(0.1, score), 'Relevant passage; applicability still requires verification'


def candidate_score(title, url, plan):
    context = (title+' '+url).lower()
    if any(word in context for word in ('disclaimer-liap', 'privacy', 'personal-data', 'acknowledgement')):
        if not any(word in plan.question.lower() for word in ('privacy','personal data','개인정보')):
            return 0
    if plan.jurisdiction == 'Great Britain' and ('northern ireland' in context or 'nicu-' in context):
        return 0
    score = sum(1 for term in plan.terms if term.lower().replace(' ','-') in context or term.lower() in context)
    if plan.institution == 'credit_union' and ('credit-union' in context or 'credit union' in context):
        score += 3
    if plan.intent == 'ownership_structure' and ('supervising-credit-unions' in context or any(w in context for w in ('subsidiar','cuso','service-organisation'))):
        score += 6
    return score
