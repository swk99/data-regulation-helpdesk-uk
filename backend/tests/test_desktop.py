import secrets
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from reghelp.api import create_app
from reghelp.config import Settings
from reghelp.desktop import choose_model, extract_ui, prepare_ollama
from reghelp.local_session import COOKIE


@pytest.fixture
def local_client(tmp_path):
    ui = tmp_path / 'ui'
    ui.mkdir()
    (ui / 'index.html').write_text('<html>local research</html>')
    settings = Settings(data_dir=tmp_path / 'data', api_token=secrets.token_urlsafe(32))
    app = create_app(settings, local_origin='http://127.0.0.1:8765', launch_ticket='once-only', ui_dir=ui)
    with TestClient(app, base_url='http://127.0.0.1:8765') as client:
        yield client


def test_local_bootstrap_authenticates_refresh_without_exposing_token(local_client):
    client = local_client
    assert client.get('/api/status').status_code == 401
    assert client.get('/local/start?key=wrong').status_code == 401
    response = client.get('/local/start?key=once-only', follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/'
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie
    assert response.headers['cache-control'] == 'no-store'
    assert client.get('/api/status').status_code == 200
    assert client.get('/').text == '<html>local research</html>'
    assert client.cookies[COOKIE] not in client.get('/').text
    assert client.get('/api/status').status_code == 200  # browser reload
    assert client.get('/local/start?key=once-only').status_code == 401  # replay


def test_foreign_origins_hosts_and_cross_site_navigation_rejected(local_client):
    client = local_client
    assert client.get('/local/start?key=once-only', headers={'sec-fetch-site': 'cross-site'}).status_code == 403
    client.get('/local/start?key=once-only')
    for headers in ({'host': 'attacker.example:8765'}, {'origin': 'https://swk99.github.io'},
                    {'origin': 'null'}, {'sec-fetch-site': 'cross-site'}):
        assert client.get('/api/status', headers=headers).status_code == 403
        assert client.post('/api/chat', headers=headers, json={'question':'Test'}).status_code == 403
    assert client.get('/api/status', headers={'origin': 'http://127.0.0.1:8765'}).status_code == 200


def test_remote_api_cannot_use_desktop_cookie(tmp_path):
    token = secrets.token_urlsafe(32)
    with TestClient(create_app(Settings(data_dir=tmp_path, api_token=token))) as client:
        client.cookies.set(COOKIE, token)
        assert client.get('/api/status').status_code == 401
        assert client.get('/local/start').status_code == 404
        assert client.get('/api/status', headers={'Authorization': 'Bearer '+token}).status_code == 200


def test_model_selection_reuses_installed_model_and_allows_override():
    assert choose_model({'qwen3.5:4b'}) == 'qwen3.5:4b'
    assert choose_model({'nomic-embed-text:latest', 'llama3.1:8b'}) == 'llama3.1:8b'
    assert choose_model(set()) == 'qwen2.5:3b'
    assert choose_model(set(), 'my-model:custom') == 'my-model:custom'


def test_installed_ollama_does_not_download_again(monkeypatch):
    import reghelp.desktop as module
    monkeypatch.delenv('CHAT_MODEL', raising=False)
    monkeypatch.delenv('EMBEDDING_MODEL', raising=False)
    monkeypatch.setattr(module, 'get_json', lambda _: {'models': [{'name':'qwen3.5:4b'}, {'name':'nomic-embed-text:latest'}]})
    download = Mock()
    monkeypatch.setattr(module.subprocess, 'run', download)
    assert prepare_ollama()[1:] == ('qwen3.5:4b', 'nomic-embed-text')
    download.assert_not_called()


def test_bundle_serves_built_ui_without_node(tmp_path, monkeypatch):
    import reghelp.desktop as module
    import shutil
    root = Path(__file__).resolve().parents[2]
    (tmp_path / 'frontend').mkdir()
    shutil.copyfile(root / 'frontend/local-ui.zip', tmp_path / 'frontend/local-ui.zip')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    destination = extract_ui()
    assert 'assets/index-' in (destination / 'index.html').read_text()
    assert list((destination / 'assets').glob('*.js'))
    assert extract_ui() == destination


def test_local_chat_still_runs_live_check(local_client, monkeypatch):
    from reghelp.agent import Agent
    observed = []
    async def answer(self, question, live=False):
        observed.append(live)
        return {'question':question, 'live':live}
    monkeypatch.setattr(Agent, 'answer', answer)
    local_client.get('/local/start?key=once-only')
    response = local_client.post('/api/chat', json={'question':'PRA model risk', 'live':False}, headers={'origin':'http://127.0.0.1:8765'})
    assert response.status_code == 200
    assert observed == [True]


def test_second_desktop_instance_is_blocked_and_lock_releases(tmp_path, monkeypatch):
    import reghelp.desktop as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    with module.single_instance():
        with pytest.raises(RuntimeError, match='already running'):
            with module.single_instance():
                pass
    with module.single_instance():
        pass


def test_desktop_serves_real_http_and_opens_authenticated_chat(tmp_path, monkeypatch):
    import shutil
    import httpx
    import uvicorn
    import reghelp.desktop as module
    from reghelp.agent import Agent
    root = Path(__file__).resolve().parents[2]
    (tmp_path / 'frontend').mkdir()
    shutil.copyfile(root / 'frontend/local-ui.zip', tmp_path / 'frontend/local-ui.zip')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'prepare_ollama', lambda: ('http://127.0.0.1:11434', 'test-model', 'nomic-embed-text'))
    real_server = uvicorn.Server
    running = []
    results = []
    def server(config):
        instance = real_server(config)
        running.append(instance)
        return instance
    monkeypatch.setattr(uvicorn, 'Server', server)
    async def answer(self, question, live):
        return {'question': question, 'live': live}
    monkeypatch.setattr(Agent, 'answer', answer)
    def browser(url):
        try:
            with httpx.Client(trust_env=False, follow_redirects=True, timeout=10) as client:
                response = client.get(url)
                assert response.status_code == 200 and 'assets/index-' in response.text
                origin = str(response.url).rstrip('/')
                assert client.get(origin+'/api/status').status_code == 200
                reply = client.post(origin+'/api/chat', json={'question':'PRA model risk'})
                assert reply.json()['live'] is True
                results.append('authenticated chat over real HTTP')
        except Exception as error:
            results.append(error)
        finally:
            running[0].should_exit = True
        return True
    monkeypatch.setattr(module.webbrowser, 'open', browser)
    module.main()
    assert results == ['authenticated chat over real HTTP']


def test_pages_pairing_cors_and_one_use_secret(tmp_path):
    ui = tmp_path / 'ui'
    ui.mkdir()
    (ui / 'index.html').write_text('app')
    key = secrets.token_urlsafe(32)
    origin = 'https://swk99.github.io'
    app = create_app(Settings(data_dir=tmp_path / 'data', api_token=secrets.token_urlsafe(32)),
                     local_origin='http://127.0.0.1:8123', launch_ticket=key, ui_dir=ui, pages_origin=origin)
    with TestClient(app, base_url='http://127.0.0.1:8123') as client:
        headers = {'Origin': origin, 'Sec-Fetch-Site':'cross-site'}
        preflight = client.options('/api/pair', headers={**headers,'Access-Control-Request-Method':'POST', 'Access-Control-Request-Headers':'content-type', 'Access-Control-Request-Private-Network':'true'})
        assert preflight.status_code == 200
        assert preflight.headers['access-control-allow-origin'] == origin
        assert preflight.headers['access-control-allow-private-network'] == 'true'
        assert client.post('/api/pair', json={'key':key}, headers={'Origin':'https://evil.example'}).status_code == 403
        assert client.post('/api/pair', json={'key':key}).status_code == 403
        paired = client.post('/api/pair', json={'key':key}, headers=headers)
        assert paired.status_code == 200
        assert paired.headers['cache-control'] == 'no-store'
        token = paired.json()['token']
        assert client.post('/api/pair', json={'key':key}, headers=headers).status_code == 401
        assert client.get('/api/status', headers=headers).status_code == 401
        assert client.get('/api/status', headers={**headers,'Authorization':'Bearer '+token}).status_code == 200
        assert client.get('/api/status', headers={'Origin':'https://evil.example','Authorization':'Bearer '+token}).status_code == 403
        assert client.get('/local/start?key='+key, headers=headers).status_code == 403


def test_pairing_expires(tmp_path, monkeypatch):
    import reghelp.local_session as session
    ui = tmp_path / 'ui'
    ui.mkdir()
    (ui / 'index.html').write_text('app')
    key = secrets.token_urlsafe(32)
    app = create_app(Settings(data_dir=tmp_path / 'data', api_token=secrets.token_urlsafe(32)),
                     local_origin='http://127.0.0.1:8123', launch_ticket=key, ui_dir=ui, pages_origin='https://swk99.github.io')
    with TestClient(app, base_url='http://127.0.0.1:8123') as client:
        old = session.time.monotonic()
        monkeypatch.setattr(session.time,'monotonic',lambda:old+301)
        assert client.post('/api/pair',json={'key':key},headers={'Origin':'https://swk99.github.io'}).status_code == 401
