"""PyInstaller entry point. Keep console visible for model downloads and shutdown."""
import multiprocessing
import sys


def self_test():
    import secrets
    import tempfile
    from pathlib import Path
    from fastapi.testclient import TestClient
    from reghelp.api import create_app
    from reghelp.config import Settings
    from reghelp.models import Vectors
    from reghelp.desktop import BUNDLE
    import zipfile
    with tempfile.TemporaryDirectory() as folder:
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
            vectors = Vectors(settings)
            vectors.upsert([{'id':'smoke', 'url':'https://www.bankofengland.co.uk/', 'version':'test'}], [[1.,0.,0.]])
            assert 'smoke' in vectors.search([1.,0.,0.])
    print('PACKAGED_SELF_TEST_OK', flush=True)


def main():
    if '--self-test' in sys.argv:
        self_test()
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
