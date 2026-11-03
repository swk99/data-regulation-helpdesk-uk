"""Run after npm run build --prefix frontend; bundles the UI for Python-only users."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def source_digest():
    files = sorted((ROOT / 'frontend/src').rglob('*'))
    files += [ROOT / 'frontend' / name for name in ('index.html', 'package.json', 'package-lock.json', 'vite.config.js')]
    h = hashlib.sha256()
    for file in files:
        if file.is_file():
            h.update(file.relative_to(ROOT).as_posix().encode())
            h.update(file.read_bytes().replace(b'\r\n', b'\n'))
    return h.hexdigest()


if __name__ == '__main__':
    import sys
    archive = ROOT / 'frontend/local-ui.zip'
    if '--check' in sys.argv:
        with zipfile.ZipFile(archive) as bundle:
            assert json.loads(bundle.read('build.json'))['source_sha256'] == source_digest(), 'Rebuild the local UI bundle'
            assert 'index.html' in bundle.namelist()
    else:
        dist = ROOT / 'frontend/dist'
        if not (dist / 'index.html').is_file():
            raise SystemExit('Run npm run build --prefix frontend first')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
            assets = re.findall(r'(?:src|href)="\./([^"]+)"', (dist / 'index.html').read_text())
            for file in [dist / 'index.html', *(dist / asset for asset in assets)]:
                if file.is_file():
                    info = zipfile.ZipInfo(file.relative_to(dist).as_posix(), (2026, 1, 1, 0, 0, 0))
                    bundle.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
            bundle.writestr('build.json', json.dumps({'source_sha256': source_digest()}))
        print(f'Bundled {archive.stat().st_size:,} bytes')
