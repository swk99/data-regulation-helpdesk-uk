# Retrieval quality update

The PC app now builds an explicit query plan before retrieval. It keeps substantive words from the full question, expands recognised company ownership expressions, identifies explicit location and credit-union mentions, and asks for clarification about ownership direction and intended customers. This is a transparent set of retrieval heuristics, not a general legal reasoning model.

For the reported London credit-union question, the plan identifies Great Britain, credit unions and ownership structure, and adds subsidiary, controlling-interest, CUSO and ancillary-service concepts. Candidate discovery prioritises verified SS2/23 and PS5/26 official landing pages. The current-version PDF is discovered from the landing page at runtime; past PDFs on that landing page are not used as current-version candidates.

Keyword and vector retrieval are combined, then passage relevance is evaluated independently of the answer model. For ownership questions, a passage must contain ownership/service-organisation evidence. Institution and explicit jurisdiction mismatches, administrative/privacy sections, survey-methodology sections and tables of contents are excluded when unrelated to the question. Rules and supervisory statements receive priority over consultations, which remain labelled as consultations. No result is required when no passage passes the checks.

PDF paragraphs such as 18.2 are kept with page numbers. Existing document versions are reparsed on refresh when the parser version changes, without duplicating immutable source snapshots. Embeddings for restructured passages are regenerated. Queries and parsing remain bounded; filtered sources can be missed, particularly where the query contains unsupported terminology or ambiguous jurisdictions.

## Verification on 3 November 2026

Using the app's robots-aware fetcher, the current PDF was discovered and fetched from:

- [SS2/23 official landing page](https://www.bankofengland.co.uk/prudential-regulation/publication/2023/july/supervising-credit-unions)
- [Current PDF observed during verification](https://www.bankofengland.co.uk/-/media/boe/files/prudential-regulation/supervisory-statement/2026/ss223-february-2026-update.pdf)
- [PS5/26 official landing page](https://www.bankofengland.co.uk/prudential-regulation/publication/2026/february/credit-union-service-organisations-policy-statement)

Local parsing and relevance scoring of the live SS2/23 PDF ranked paragraph 18.2 (PDF page 27) first and 18.1 second for the ownership question. This smoke check validates discovery, parsing and ranking of that document; it does not establish completeness of legal coverage or the quality of a particular Ollama-generated answer.

Regression tests use clearly synthetic fixtures to verify that ownership evidence remains retrievable while Northern Ireland-specific documents, personal-information notices, survey-methodology passages and ordinary bond-investment paragraphs do not enter the answer for the London ownership question. They also verify that privacy questions can still retrieve privacy provisions, unsupported topics return no evidence, current-PDF discovery excludes past versions, and reparsing does not duplicate document versions.

Model errors distinguish Ollama HTTP status, timeout, unreachable service, invalid JSON and invalid claim schema. Only concise error codes are shown; retrieved text is not automatically promoted to a regulatory conclusion. Korean follow-ups reuse the previous answer's evidence and interpretation rather than starting another search.
