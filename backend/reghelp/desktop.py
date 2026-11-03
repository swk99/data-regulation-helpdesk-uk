"""Start Ollama, select local models, and open a private same-origin desktop UI."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
import webbrowser
import zipfile

ROOT = Path(__file__).resolve().parents[2]
# Never route local model/session requests through an enterprise HTTP proxy.
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get_json(url):
    with HTTP.open(url, timeout=3) as response:
        return json.load(response)


def choose_model(names, configured=None):
    if configured:
        return configured
    for preferred in ('qwen3.5:4b', 'qwen2.5:14b', 'llama3.1:8b', 'qwen2.5:7b', 'qwen2.5:3b'):
        if preferred in names:
            return preferred
    return 'qwen2.5:3b'


def prepare_ollama():
    executable = shutil.which('ollama')
    if not executable and os.name == 'nt':
        candidate = Path(os.getenv('LOCALAPPDATA', '')) / 'Programs/Ollama/ollama.exe'
        if candidate.is_file():
            executable = str(candidate)
    url = 'http://127.0.0.1:11434'
    try:
        tags = get_json(url + '/api/tags')
    except Exception:
        if not executable:
            raise RuntimeError('Install and open Ollama from https://ollama.com/download/windows then run this launcher again.')
        print('Starting Ollama...', flush=True)
        subprocess.Popen([executable, 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            try:
                tags = get_json(url + '/api/tags')
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Ollama did not start. Open the Ollama application and retry.')
    names = {model['name'] for model in tags.get('models', [])}
    chat = choose_model(names, os.getenv('CHAT_MODEL'))
    embedding = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')
    for model in (chat, embedding):
        if model not in names and model + ':latest' not in names:
            if not executable:
                raise RuntimeError(f'Ollama model {model} is missing. Install the Ollama CLI and restart.')
            print(f'Downloading {model} to this PC (first setup; models may use several GB)...', flush=True)
            subprocess.run([executable, 'pull', model], check=True)
    return url, chat, embedding


def extract_ui():
    archive = ROOT / 'frontend/local-ui.zip'
    if not archive.is_file():
        raise RuntimeError('Missing bundled UI. Download and extract the complete repository ZIP again.')
    import hashlib
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()[:16]
    destination = ROOT / 'data/desktop-ui' / digest
    if not (destination / 'index.html').is_file():
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                target = (destination / name).resolve()
                if not target.is_relative_to(destination.resolve()):
                    raise RuntimeError('Invalid UI archive path')
            bundle.extractall(destination)
    return destination


@contextmanager
def single_instance():
    path = ROOT / 'data/desktop.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Helpdesk is already running. Use its existing browser window, or close its console before restarting.')
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def main():
    import uvicorn
    from .api import create_app
    from .config import Settings
    ui_dir = extract_ui()
    url, chat, embedding = prepare_ollama()
    settings = Settings(data_dir=ROOT / 'data', ollama_url=url, chat_model=chat,
                        embedding_model=embedding, api_token=secrets.token_urlsafe(32), origins=[])
    # Reserve an OS-assigned port before opening the browser (no fixed-port collision).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        origin = f'http://127.0.0.1:{sock.getsockname()[1]}'
        ticket = secrets.token_urlsafe(32)
        app = create_app(settings, local_origin=origin, launch_ticket=ticket, ui_dir=ui_dir)
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', access_log=False, proxy_headers=False))
        def open_when_ready():
            for _ in range(120):
                if server.started:
                    print(f'\nHelpdesk ready: {origin}\nModel: {chat}\nKeep this window open. Press Ctrl+C to stop.', flush=True)
                    if not webbrowser.open(origin + '/local/start?key=' + ticket):
                        print('Could not open your browser automatically. Set a default browser and restart.', flush=True)
                    return
                time.sleep(.5)
        threading.Thread(target=open_when_ready, daemon=True).start()
        server.run(sockets=[sock])


if __name__ == '__main__':
    try:
        with single_instance():
            main()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f'\nCould not start Helpdesk: {error}', flush=True)
        raise SystemExit(1)
