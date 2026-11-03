"""Standard-library bootstrap for the Windows launcher (no Node.js required)."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    if not (3, 11) <= sys.version_info[:2] <= (3, 12):
        raise RuntimeError('Install Python 3.12 from https://www.python.org/downloads/windows/ then run again.')
    env_dir = ROOT / '.venv-desktop'
    python = env_dir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('First run: creating a private Python environment...', flush=True)
        venv.EnvBuilder(with_pip=True).create(env_dir)
    requirements = ROOT / 'backend/requirements.txt'
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = env_dir / 'requirements.sha256'
    if not marker.exists() or marker.read_text() != digest:
        print('Installing application dependencies. First setup may take several minutes.', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        marker.write_text(digest)
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(ROOT / 'backend')
    return subprocess.call([str(python), '-m', 'reghelp.desktop'], cwd=ROOT, env=environment)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nHelpdesk stopped.')
        sys.exit(130)
    except Exception as error:
        print(f'\nSetup failed: {error}\nFix the issue above and double-click Start Helpdesk.cmd again.', file=sys.stderr)
        sys.exit(1)
