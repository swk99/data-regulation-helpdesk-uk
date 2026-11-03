# Windows executable + GitHub Pages

1. [Download RegulationHelpdesk.exe](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/RegulationHelpdesk.exe).
2. Open the executable and keep its console window open. **Python is bundled**; you do not need Python, Node.js, WSL or Docker. Ollama must already be installed: <https://ollama.com/download/windows>.
3. The app opens <https://swk99.github.io/data-regulation-helpdesk-uk/> and pairs automatically. Allow **local device / local network access** if Chrome or Edge asks. No address, token or API key needs to be entered.
4. Ask questions on GitHub Pages. Close the console or press Ctrl+C when finished. Close/reopen the executable to start a new session.

This is a Windows x64 executable built and tested by the repository's Windows CI. It is not code-signed. Releases include `SHA256SUMS.txt` so the download can be checked. A managed work PC may require IT approval; do not disable security controls. Model inference and the document index run on your PC, while the UI is hosted on GitHub Pages.

Existing supported Ollama models are reused, preferring `qwen3.5:4b` when installed. If none is present, the app downloads `qwen2.5:3b`. It downloads `nomic-embed-text` when missing. Model downloads may use several GB. The executable stores the index in `%LOCALAPPDATA%\UKRegulationHelpdesk\data`; replacing the executable does not discard it.

Every chat request attempts a bounded live check of permitted official sources, using the PC's current date in Europe/London. Keep Windows date/time synchronisation enabled. Internet access is required for current documents and initial downloads; model inference and storage stay on the PC. Current legal applicability is only reported as supported when evidence supports it. FCA general publications remain permission-gated, and Handbook access limitations remain visible. This is not exhaustive web search.

## Troubleshooting

- **App already running, but this tab is disconnected:** you do not need to download it again. Use the GitHub tab opened by the EXE and refresh that tab once to load the connection fix. Other tabs in the same browser/profile can now request the authenticated session from that tab via **Retry connection**. If no linked tab remains, close the EXE console and reopen the EXE to get a fresh launch link. Ollama alone does not start the research backend.
- **Local device access blocked:** keep the EXE open, verify its console says `Helpdesk ready`, allow local device access for `swk99.github.io` in the browser, then click Retry connection. Status checks now time out after 15 seconds and display an explanation.
- **Expired session:** close the console and reopen the executable. Pairing links are single-use and expire after five minutes.
- **Ollama failed:** open the Ollama desktop app and retry. The console explains missing models, downloads or errors.
- **Slow first question:** discovery, downloads, indexing and model loading take time. The corpus starts empty. Unsupported answers return references and uncertainty.
- **Browser or organisation blocks loopback access:** use the all-local fallback by starting `RegulationHelpdesk.exe --local`. No browser protections need to be disabled.
- **Duplicate app:** use the existing window or close it before opening another copy.

## Source-code alternative

Download and extract the repository ZIP, then open `Start Helpdesk.cmd`. This route requires Python 3.11/3.12 and Ollama; it installs Python dependencies in `.venv-desktop` and opens GitHub Pages with the same automatic pairing flow. Developers rebuilding the UI run `npm run build --prefix frontend` and `python scripts/bundle_ui.py`.

## Automatic authentication

The service listens only on IPv4 loopback on an OS-assigned port. A fresh, five-minute, single-use pairing secret is placed in the URL fragment (not sent to GitHub's HTTP server). The frontend immediately removes the fragment, POSTs the secret to the local service and keeps the resulting bearer session in this tab's sessionStorage so refresh works. An unused pairing ticket is also retained in this tab for up to five minutes so refreshing during the permission prompt does not lose it. Already authenticated tabs can share the session with another helpdesk tab in the same browser/profile via a same-origin BroadcastChannel; recipients verify it with the local API before showing connected. It is not saved to localStorage, source code or server access logs. Sessions change on each restart. No public tunnel or port forwarding is created.

Host and Origin checks restrict browser API access to the local app and the configured `https://swk99.github.io` origin. CORS cannot distinguish paths within that origin, so all applications on that personal Pages origin should be trusted. Other origins are rejected even if they send a token. Browser local-network permission still applies. The `--local` fallback uses a same-origin HttpOnly cookie instead.

## Build and verification

The Windows workflow packages the app with PyInstaller, executes `--self-test`, then publishes the EXE and SHA-256 checksum as a GitHub Release. Self-test checks startup, bundled source configuration, automatic authentication and persistent Chroma vector storage without calling Ollama or regulators. Full live model quality depends on the PC and installed model and is not established by that smoke test.
