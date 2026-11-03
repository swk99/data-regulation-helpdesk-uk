# Run on your Windows PC — no backend URL or access token

1. Install **Python 3.12** from <https://www.python.org/downloads/windows/> and **Ollama** from <https://ollama.com/download/windows> if they are not installed. Python 3.11 is also supported.
2. [Download the project ZIP](https://github.com/swk99/data-regulation-helpdesk-uk/archive/refs/heads/main.zip), right-click it → **Extract All**. Put the extracted folder somewhere writable, such as `C:\Projects\fca-rag`.
3. Open the extracted folder and double-click **Start Helpdesk.cmd**. Do not run it inside the ZIP viewer.
4. Wait for setup. A local browser window opens automatically. Ask your question there. There are **no connection fields** to fill in.

Keep the launcher window open while using the app. Press Ctrl+C in that window to stop the research service. Ollama can stay running for other applications. You do not need Node.js, Docker, WSL, a hosted backend or a model API key.

First launch creates `.venv-desktop`, installs the pinned Python libraries and starts Ollama if necessary. It prefers an already-installed `qwen3.5:4b`, `qwen2.5:14b`, `llama3.1:8b`, `qwen2.5:7b` or `qwen2.5:3b`, in that order. If none is present, it downloads `qwen2.5:3b`. It also downloads `nomic-embed-text` if missing. Downloads may use several GB and take time. Later starts reuse installed packages and models. Set `CHAT_MODEL` or `EMBEDDING_MODEL` before launching to override the model choice.

Every chat request attempts a bounded live check of permitted official sources, using the PC's current date in Europe/London. Keep Windows date/time synchronisation enabled. Internet access is required for current documents and initial downloads; model inference and storage stay on the PC. Current legal applicability is only reported as supported when evidence supports it. FCA general publications remain permission-gated, and Handbook access limitations remain visible. This is not exhaustive web search.

## Troubleshooting

- **404 at a github.io address:** GitHub Pages is a preview and download page. Use the local browser window opened by the launcher.
- **Session expired / cannot connect:** close the launcher console, then run it again. Use the newly opened window. The port and session change on each launch; old bookmarks will not reconnect.
- **Ollama failed:** open the Ollama desktop application and retry. Missing model downloads require internet access and enough disk space.
- **Python missing:** install Python 3.12 with the Windows Python launcher. The launcher tries Python 3.12, then 3.11, then `python` on PATH.
- **Package download failed:** check internet/proxy restrictions, then rerun; installation failures are displayed in the console. No admin privileges are required for this project environment.
- **Slow first question:** the index begins empty. Discovery, document downloads, embedding and model loading take time. Research progress and unavailable sources are reported. A first run is not a pre-populated knowledge base.
- **No supported summary:** the app returns references and uncertainty, never a pretend answer. If the model cannot load due to memory constraints, try a smaller installed model via `CHAT_MODEL`.

## How automatic authentication works

The launcher binds only to `127.0.0.1` on an available port. It generates a fresh session secret and opens a single-use launch link; the server exchanges it for an HttpOnly, SameSite=Strict browser cookie and redirects to the app. Secrets are not embedded in JavaScript or saved to the repository. Host and Origin checks reject cross-site requests. API access remains authenticated. No port forwarding or public tunnel is created. The local launch link is not written to access logs; do not share it.

The bundled UI is `frontend/local-ui.zip`. Developers update it with `npm run build --prefix frontend` then `python scripts/bundle_ui.py`. CI checks its source fingerprint. Runtime files live in ignored `data/` and `.venv-desktop/` folders.
