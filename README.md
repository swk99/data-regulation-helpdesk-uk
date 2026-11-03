# UK Regulation Helpdesk

**[Download Windows EXE](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/RegulationHelpdesk.exe)** · **[Open GitHub Pages chat](https://swk99.github.io/data-regulation-helpdesk-uk/)** · [한국어 사용법](docs/usage-ko.md) · [English guide](docs/local-windows.md)

Chat on GitHub Pages while **RegulationHelpdesk.exe** runs the research service and Ollama models on your Windows PC. Python is included in the EXE. You do not need to enter a backend URL, access token or model API key.

## 사용 방법 — Windows

1. **Ollama 설치 및 실행:** [Ollama for Windows](https://ollama.com/download/windows). 이미 설치했다면 그대로 사용하세요.
2. **[최신 RegulationHelpdesk.exe 다운로드](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/RegulationHelpdesk.exe)** 후 더블클릭하세요. 소스 코드 ZIP이나 Python을 따로 받을 필요는 없습니다.
3. 실행 창에 **`Helpdesk ready`**가 표시될 때까지 기다리세요. 첫 실행에는 없는 모델을 내려받느라 시간이 걸릴 수 있습니다.
4. **EXE가 자동으로 열어준 GitHub Pages 탭**을 사용하세요. 브라우저가 로컬 장치 접근을 물으면 허용하세요.
5. `Hello.`로 연결을 확인한 뒤 규제 질문을 입력하세요. **사용 중에는 EXE 실행 창을 켜두세요.**

예시 질문: `What are the PRA expectations for model risk management?`

**업데이트:** 이전 EXE 실행 창을 닫고 최신 EXE를 실행한 뒤, 자동으로 열린 탭에서 `Ctrl + Shift + R`을 누르세요. 기존 문서 인덱스는 유지됩니다. 이전 버전에서 질문 전송 시 발생하던 SQL 오류는 `windows-4-1`에서 수정했습니다.

**이미 실행 중인데 연결되지 않나요?** 자동으로 열린 탭에서 **Retry connection**을 누르세요. 원래 탭을 닫았다면 EXE 창을 닫았다가 다시 실행하세요. Ollama와 RegulationHelpdesk.exe가 모두 실행되어 있어야 합니다. [상세 사용법과 오류 해결](docs/usage-ko.md)

[공개 릴리스 및 버전 기록](https://github.com/swk99/data-regulation-helpdesk-uk/releases) · [최신 EXE SHA-256 체크섬](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/SHA256SUMS.txt)

An evidence-led research chatbot for UK banking and data science. One repository contains a **Python/FastAPI backend** and a **React/JavaScript frontend** for GitHub Pages.

Ask across FCA publications, the FCA Handbook, Bank of England publications, PRA publications and the PRA Rulebook. Answers include source titles, sections, URLs, retrieved passages and check timestamps. If a supported answer cannot be established, the interface shows references and uncertainty instead.

[Open the website](https://swk99.github.io/data-regulation-helpdesk-uk/) · [Validation record](docs/validation.md)

![Regulation Helpdesk interface](docs/screenshot.jpg)

## Windows: open the EXE, chat on GitHub Pages

[Download RegulationHelpdesk.exe](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/RegulationHelpdesk.exe) → **open it** → use the **GitHub Pages tab it opens**.

Python is bundled. Keep the app open and allow the browser's local device access prompt if shown. Ollama is required; installed models are reused and missing models download once. **No backend URL or token to enter.** [Windows setup & troubleshooting](docs/local-windows.md).

## Retrieval quality

The PC app now shows how it interpreted the question, expands ownership terms, filters jurisdiction mismatches and unrelated administrative passages, and discovers the current SS2/23 PDF for credit-union questions. See [retrieval checks and validation limits](docs/retrieval-quality.md). Download the latest EXE to enable these backend changes; GitHub Pages shows an update prompt for older PC apps.

## Application status

- Frontend: GitHub Pages deployment workflow included.
- Backend: runs on your PC through **RegulationHelpdesk.exe**, with automatic GitHub Pages connection. No hosted backend is required.
- Corpus: not bundled or redistributed. It is built on the backend host from permitted public documents.
- Live mode: bounded discovery and relevant-source revalidation, **not an exhaustive real-time search of every regulator page**.
- FCA general publications: indexing is permission-gated under FCA legal terms 3.3; direct source links remain available.
- FCA Handbook: its public landing page requires JavaScript. The adapter reports this limitation rather than indexing an empty shell. See source verification notes.
- Generated summaries require Ollama with the configured chat model. Without Ollama, indexed keyword search and evidence excerpts remain available.

## Features

- Persistent ChromaDB vectors with explicit Ollama embeddings; SQLite FTS5 keyword retrieval.
- Official HTTPS host allowlist, redirect validation, robots.txt checks, bounded downloads, rate limiting and retries.
- HTML/PDF parsing, headings, page numbers, publication metadata when exposed, and numbered-reference extraction.
- Immutable raw snapshots and version hashes; idempotent updates and active-version filtering.
- Rule/guidance markers and publication-type labels; no assumption that publication date equals effective date.
- A bounded research agent: retrieve → optionally discover/recheck → retrieve again → summarize → validate citations.
- Exact-quote and citation validation, plus references-only fallback. This does not prove semantic correctness; inspect source passages.
- Authenticated backend APIs, origin-restricted CORS for hosted APIs, automatic per-tab bearer session for GitHub Pages and HttpOnly cookie for the local UI, no question logging or chat persistence.
- Built-in six-hour update loop while the backend runs; CLI for external schedulers.

## Quick start for development

The source-code launcher needs Python 3.11/3.12 and Ollama. The packaged EXE includes Python. Node.js 22+ is only needed when editing the frontend:

```bash
npm ci --prefix frontend
npm run build --prefix frontend
python scripts/bundle_ui.py
python run_local.py
```

The launcher opens GitHub Pages and pairs with the loopback API. The executable also supports `--local` for a same-origin frontend fallback. To see frontend edits, rebuild the bundle and restart the launcher. `npm run dev --prefix frontend` is a visual preview only; it does not start an authenticated research service.

For advanced API-only hosting, see [docs/deployment.md](docs/deployment.md). Environment variables are read from the process; `.env` files are not automatically loaded.

## CLI

Run from `backend/` with the virtual environment active:

```bash
python -m reghelp.cli update
python -m reghelp.cli ask "What are the PRA expectations for model risk management?" --live
python -m reghelp.cli status
```

Run one backend process. Do not run CLI writes concurrently with that server against the same data directory. The in-process scheduler and live checks share an ingestion lock.

## Tests

```bash
# Repository root; PowerShell: $env:PYTHONPATH='backend'
PYTHONPATH=backend python -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
```

[Architecture](docs/architecture.md) · [Deployment](docs/deployment.md) · [Source verification and limits](docs/source-verification.md)

This is an independent research tool, not affiliated with any regulator. Public availability does not imply unrestricted reuse. Keep fetched content private to the permitted research use; review source terms before broader deployment. Never enter customer data, confidential bank information or credentials in chat.
