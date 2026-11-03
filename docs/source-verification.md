# Official source verification

Reviewed 3 November 2026. Source links are configuration, not a promise of complete corpus coverage.

| Source | Entry point | Constraints |
|---|---|---|
| FCA | https://www.fca.org.uk/publications | Robots prohibit search paths and query URLs. Discover publication links and the published sitemap instead. |
| FCA sitemap | https://www.fca.org.uk/sitemap-main.xml | Advertised and permitted by FCA robots. Traversal is bounded. |
| FCA Handbook | https://handbook.fca.org.uk/ | The `www` URL redirects here. The current public shell requires JavaScript. Do not claim Handbook coverage unless readable sections have actually been indexed. |
| BoE publications feed | https://www.bankofengland.co.uk/rss/publications | Linked from the official RSS directory. Runtime checks validate XML and source access. |
| PRA publications feed | https://www.bankofengland.co.uk/rss/prudential-regulation-publications | Linked from the official RSS directory. |
| PRA policy index | https://www.bankofengland.co.uk/prudential-regulation/prudential-and-resolution-policy-index | Official index for supervisory material and related policy. |
| PRA Rulebook | https://www.prarulebook.co.uk/ | Public rules/guidance entry point. Robots/availability checked at runtime. |

Official RSS directory: https://www.bankofengland.co.uk/rss

## Terms

- FCA: https://www.fca.org.uk/legal
- FCA Handbook: https://handbook.fca.org.uk/footer-widget/terms-and-conditions
- BoE: https://www.bankofengland.co.uk/legal
- PRA Rulebook: https://www.prarulebook.co.uk/legal

BoE terms describe personal/internal non-commercial use and separate Rulebook terms. PRA Rulebook terms permit personal/internal extracts with attribution and restrict third-party redistribution and commercial reuse. This repository publishes code, not downloaded regulator content. The service is authenticated for private research. Deployment operators must check terms for their use and obtain any required permission before wider distribution. Robots permission alone is not a reuse licence.

Unknown robots policies, blocked paths and access errors stop fetching. No anti-bot bypass, authenticated regulator content, internal bank files, local-file upload or customer-data connector is implemented.

## FCA publication permission gate

FCA general legal terms clause 3.3 expressly require prior written permission for inclusion in a public or private electronic retrieval system. Consequently **general FCA publication ingestion is disabled by default**; the source remains visible as a reference link. Only set `FCA_RETRIEVAL_PERMISSION=granted` after obtaining the required permission. This does not bypass robots restrictions. FCA Handbook content has a separate Open Government Licence route, as described on the FCA legal page; the Handbook is not covered by this general-publication switch.

## Executed HTTP checks

The backend fetcher successfully retrieved and parsed both BoE XML feeds (51 official links each), the PRA Rulebook entry page and its CRR-firm directory, and the PRA banking policy index during development. The banking index exposes topic pages that the agent can follow within its discovery budget. The Handbook robots response could not be validated in this environment, so the fetcher refused to proceed. The official Handbook FAQ documents an authenticated API; API credentials and its production contract are not supplied, and that integration is not claimed as working.

- https://www.prarulebook.co.uk/pra-rules/crr-firms
- https://www.prarulebook.co.uk/pra-rules/non-crr-firms
- https://www.bankofengland.co.uk/prudential-regulation/prudential-and-resolution-policy-index/banking
- https://handbook.fca.org.uk/guides/faq

The live checks establish availability at test time, not future availability or comprehensive legal coverage.
