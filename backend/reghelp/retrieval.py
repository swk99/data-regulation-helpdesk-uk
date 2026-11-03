import logging
from collections import Counter
from .query import plan_query, rank_passage
log = logging.getLogger(__name__)


async def retrieve(question, store, models, vectors, limit=6):
    plan = plan_query(question)
    rankings = [store.lexical(question)]
    warnings = []
    try:
        vector = (await models.embed([question + "\nRetrieval concepts: " + plan.search_text], query=True))[0]
        rankings.append(vectors.search(vector))
    except Exception as exc:
        log.warning('Semantic retrieval unavailable: %s', type(exc).__name__)
        warnings.append('Semantic search unavailable; using exact/keyword search.')
    scores = {}
    for ranking in rankings:
        for i, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0) + 1 / (60 + i + 1)
    rows = store.rows(ids=list(scores))  # Filters out historical vectors.
    rejected = Counter()
    kept = []
    for row in rows:
        relevance, reason = rank_passage(row, plan)
        if relevance <= 0:
            rejected[reason] += 1
            continue
        row['relevance_score'] = relevance
        row['relevance_reason'] = reason
        kept.append(row)
    rows = sorted(kept, key=lambda row: (row['relevance_score'], scores[row['id']]), reverse=True)
    warnings.extend(f'Excluded {count} passage(s): {reason}.' for reason, count in rejected.items())
    selected, counts = [], {}
    for row in rows:
        if row.get('status', '').startswith('Historical'):
            warnings.append('Explicitly withdrawn/historical material was excluded from current-topic results.')
            continue
        if counts.get(row['url'], 0) >= 2:
            continue
        counts[row['url']] = counts.get(row['url'], 0) + 1
        selected.append(row)
        if len(selected) == limit:
            break
    return selected, warnings
