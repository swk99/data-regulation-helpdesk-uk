# Deployment

## GitHub Pages frontend

The `Publish GitHub Pages` workflow builds `frontend/` and publishes `frontend/dist/` on pushes to main. The configured URL is expected to be:

https://swk99.github.io/data-regulation-helpdesk-uk/

If automatic Pages enablement is unavailable to the workflow token, open **Repository Settings → Pages → Build and deployment → Source: GitHub Actions**, then rerun the workflow. No backend secrets are needed in Pages or Actions.

## Python backend (not deployed by this repository)

Use an always-on host with Python 3.11+, persistent disk, and Ollama reachable over a private connection. The chosen model determines RAM/VRAM requirements. The backend must have outbound HTTPS access to official regulator hosts. Keep the service single-process (`--workers 1`) because the embedded vector database and update lock are local.

1. Install `backend/requirements.txt` or build the provided Dockerfile from `backend/`.
2. Configure `API_TOKEN` as a random secret of at least 24 characters, `OLLAMA_URL`, `CHAT_MODEL`, `EMBEDDING_MODEL`, `DATA_DIR` and `CORS_ORIGINS`.
3. Pull the selected embedding/chat models on the Ollama host. Do not expose Ollama's unauthenticated port publicly.
4. Mount persistent storage at `DATA_DIR`. Back up SQLite, snapshots and ChromaDB together while writes are stopped.
5. Run `uvicorn reghelp.api:app --host 0.0.0.0 --port 8000 --workers 1` behind an HTTPS reverse proxy. Allow long-running requests (up to nine minutes) and enforce connection/request limits at that proxy.
6. Open Pages, select Backend connection and enter the HTTPS origin plus the token. The token is kept in tab memory; it is not stored in localStorage or committed to the repository.
7. Run a first update and inspect per-source status. Source unavailability and pending embeddings are visible in Index activity.

Example Docker build:

```bash
docker build -t regulation-helpdesk ./backend
docker run --env-file /secure/backend.env -v regulation-data:/data -p 127.0.0.1:8000:8000 regulation-helpdesk
```

Supply the real Ollama address in `/secure/backend.env`; localhost inside a container points at that container, not the host. The env file is outside this repository. Do not place the access token in `VITE_*` variables, public workflow artifacts or URLs.

The static frontend is public. Its authenticated backend is intended for one user/private research, not an anonymous public regulatory corpus service. Review source reuse terms before allowing public access to generated extracts.

## Updates

The backend runs a six-hour update timer after startup; the first update is manual. Set `UPDATE_INTERVAL_SECONDS` (minimum one hour) to change it. Restarting the backend restarts the timer. No updates run while the backend is stopped. Windows Task Scheduler or a host scheduler can instead invoke `python -m reghelp.cli update` while the server is stopped. Do not use GitHub Actions to publish the downloaded corpus.

## Troubleshooting

- **Backend not connected**: no server URL/token has been configured; the site does not fabricate demo answers.
- **401**: wrong token. Restarting the browser clears the in-memory token.
- **CORS**: permit `https://swk99.github.io`, without a path, on the backend.
- **Keyword-only**: Ollama/embedding model is unavailable. Start/pull the configured model and update again.
- **References only**: insufficient evidence or no validated model output. Read sources directly.
- **Source unavailable**: review robots, HTTP errors and JavaScript/API requirements in Index activity.
- **502/504**: ensure the proxy permits long requests; use indexed mode while sources are slow.
