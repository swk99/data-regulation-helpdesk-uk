import logging
log = logging.getLogger(__name__)


async def retrieve(question, store, models, vectors, limit=6):
    rankings = [store.lexical(question)]
    warnings = []
    try:
        vector = (await models.embed([question], query=True))[0]
        rankings.append(vectors.search(vector))
    except Exception as exc:
        log.warning('Semantic retrieval unavailable: %s', type(exc).__name__)
        warnings.append('Semantic search unavailable; using exact/keyword search.')
    scores = {}
    for ranking in rankings:
        for i, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0) + 1 / (60 + i + 1)
    rows = store.rows(ids=list(scores))  # Filters out historical vectors.
    rows.sort(key=lambda row: scores[row['id']], reverse=True)
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
