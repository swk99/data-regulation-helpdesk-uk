# Architecture

The frontend is a static React build. FastAPI owns all source access, retrieval, inference and persistent data. No model provider key is embedded in browser assets.

## Request lifecycle

1. Authenticate a bounded-length question; refuse overlapping research requests.
2. Retrieve with SQLite FTS5 and Ollama embeddings + ChromaDB, merging by reciprocal rank.
3. In live mode, recheck up to five retrieved URLs, then discover permitted official links and ingest a small fair budget across the five sources.
4. Retrieve again, filtering to active SQLite versions and limiting two passages per document.
5. Ask Ollama for structured claims with exact supporting quotations and evidence IDs.
6. Reject unknown citations, non-exact quotes and regulatory references absent from cited evidence.
7. Return metadata-generated source cards and activity. If generation fails or no claim passes, return excerpts explicitly labelled references-only.

Document text is untrusted evidence. It is never used to select executable commands. The agent has no shell, financial-action or arbitrary-URL tool. The orchestration is bounded and deterministic; it is not an open-ended autonomous browser.

## Persistence

`data/registry.sqlite3` stores versions, chunks, FTS5 search, discovered links and source checks. Raw bytes are content-addressed in `data/raw/`. ChromaDB lives in `data/chroma/` with separate collections per embedding-model identifier. Bind the model identifier to a fixed tag/digest in production; changing weights behind an unchanged name requires rebuilding its collection.

A successful parse creates an immutable snapshot and transactionally activates its text chunks. Unchanged content reuses its version. Changed content deactivates the prior version without deleting it. Embedding failures leave keyword-searchable text and are retried later. Retrieval cross-checks vector IDs against active versions, so old vectors cannot become current evidence. Historical point-in-time legal reconstruction is not implemented; version history describes observed copies, not authoritative commencement dates.

## Files

- `backend/reghelp/fetch.py`: URL policy, robots, retry and byte limits.
- `parsing.py`: HTML/PDF extraction, classification and chunking.
- `storage.py`: metadata, raw snapshots, FTS and history.
- `models.py`: Ollama and persistent ChromaDB.
- `ingestion.py`: source discovery, incremental indexing, update lock.
- `retrieval.py`: hybrid ranking and active-version filtering.
- `agent.py`: research orchestration and evidence validation.
- `api.py`: authenticated endpoints, scheduler and lifecycle.
- `cli.py`: commands for a backend operator.
- `frontend/src`: responsive chat, source library, index status and connection settings.

## Limits that affect accuracy

A valid quote does not prove that a generated paraphrase is legally correct. Publication class alone does not establish applicability. Effective dates, amendments and historical status require authoritative verification; unknown fields remain unknown. PDF layout and cross-page tables may be imperfect. Scanned PDFs are rejected, not silently treated as text. Source outages retain old evidence with its actual last-successful-check timestamp.

The current discovery budget does not exhaust large sitemaps, recursively follow all cross-references, or provide complete regulatory coverage. Context windows contain retrieved chunks, not whole documents. No confidence percentage is fabricated. Evaluation uses deterministic fixtures; a representative legal-answer benchmark and human review remain necessary before operational reliance.

## Current-date checks

Every web chat request forces a live source check, regardless of a submitted `live: false` value. The backend captures its actual current clock in `Europe/London` for each assessment and passes that date to the model. It never relies on the model's training cutoff or a date supplied in the question as today's date. If any returned evidence was not successfully checked since this request started, the web response falls back to references and explicitly marks current applicability unverified. A successful fresh fetch still does not prove legal commencement or applicability.

The footer displays the English UK calendar date and refreshes its clock each minute. It uses the backend clock when connected, or the same-origin website HTTP Date header (adjusted for CDN Age) when disconnected. If neither server clock is available, it labels the device-time fallback explicitly. Displaying a date does not imply that the undeployed backend has checked regulations. The CLI's explicit offline mode remains available for inspecting saved evidence.
