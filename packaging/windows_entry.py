"""PyInstaller entry point. Keep console visible for model downloads and shutdown."""
import multiprocessing
import sys


def self_test(folder):
    import secrets
    from pathlib import Path
    from fastapi.testclient import TestClient
    from reghelp.api import create_app
    from reghelp.config import Settings
    from reghelp.models import Vectors
    from reghelp.desktop import BUNDLE
    import zipfile
    root = Path(folder)
    with zipfile.ZipFile(BUNDLE / 'frontend/local-ui.zip') as bundle:
        bundle.extractall(root / 'ui')
    settings = Settings(data_dir=root / 'data', api_token=secrets.token_urlsafe(32),
                        source_file=BUNDLE / 'backend/sources.yaml')
    key = secrets.token_urlsafe(32)
    app = create_app(settings, local_origin='http://127.0.0.1:8123', launch_ticket=key,
                     ui_dir=root / 'ui', pages_origin='https://swk99.github.io')
    with TestClient(app, base_url='http://127.0.0.1:8123') as client:
        assert client.get('/api/status').status_code == 401
        pair = client.post('/api/pair', json={'key':key}, headers={'Origin':'https://swk99.github.io'})
        assert pair.status_code == 200, pair.text
        assert client.get('/api/status', headers={'Authorization':'Bearer '+pair.json()['token'], 'Origin':'https://swk99.github.io'}).status_code == 200
        assert client.get('/').status_code == 200
        headers={'Authorization':'Bearer '+pair.json()['token'], 'Origin':'https://swk99.github.io'}
        hello=client.post('/api/chat',json={'question':'Hello.'},headers=headers)
        assert hello.status_code==200 and hello.json()['mode']=='welcome',hello.text
        # Exercise the entire empty-index discovery/SQL/retrieval path in the
        # packaged binary, with only external I/O replaced by an outage fixture.
        from unittest.mock import patch
        from reghelp.fetch import Fetcher
        from reghelp.models import Ollama
        async def unavailable(*args,**kwargs):
            raise RuntimeError('Offline packaging test')
        with patch.object(Fetcher,'get',unavailable), patch.object(Ollama,'embed',unavailable):
            research=client.post('/api/chat',json={'question':'PRA model risk management'},headers=headers)
            assert research.status_code==200,research.text
            assert research.json()['mode']=='references_only'
            assert research.json()['sources']==[]
        vectors = Vectors(settings)
        vectors.upsert([{'id':'smoke', 'url':'https://www.bankofengland.co.uk/', 'version':'test'}], [[1.,0.,0.]])
        assert 'smoke' in vectors.search([1.,0.,0.])
    print('PACKAGED_SELF_TEST_OK', flush=True)


def main():
    if '--self-test-worker' in sys.argv:
        self_test(sys.argv[sys.argv.index('--self-test-worker')+1])
        return
    if '--self-test' in sys.argv:
        # Chroma keeps native file handles until process exit on Windows. Run the
        # assertions in a child, then clean temporary storage after it has exited.
        import tempfile
        import subprocess
        command = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, __file__]
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(command + ['--self-test-worker', folder], check=True)
        return
    from reghelp.desktop import main as run, single_instance
    try:
        with single_instance():
            run(pages='--local' not in sys.argv)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f'\nCould not start Helpdesk: {error}', flush=True)
        input('Press Enter to close...')
        raise SystemExit(1)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
