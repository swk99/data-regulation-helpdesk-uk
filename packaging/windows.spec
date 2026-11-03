# Build on Windows: pyinstaller --clean --noconfirm packaging/windows.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH).parent
assets = [(str(root/'backend/sources.yaml'), 'backend'),
          (str(root/'frontend/local-ui.zip'), 'frontend')]
binaries = []
hidden = []
for package in ('chromadb', 'uvicorn', 'tzdata'):
    data, bins, imports = collect_all(package)
    assets += data
    binaries += bins
    hidden += imports
assets += copy_metadata('chromadb', recursive=True)
a = Analysis([str(root/'packaging/windows_entry.py')], pathex=[str(root/'backend')],
             binaries=binaries, datas=assets, hiddenimports=hidden,
             excludes=['pytest', 'IPython', 'matplotlib'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='RegulationHelpdesk',
          debug=False, strip=False, upx=False, console=True)
