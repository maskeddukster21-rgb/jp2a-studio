# PyInstaller spec for jp2a Studio (Windows onedir build).
# Build from repo root with:
#   pyinstaller packaging/windows/jp2a-studio.spec
# Produces dist/jp2a-studio/jp2a-studio.exe plus its bundled data.
# The CI workflow copies a cross-compiled jp2a.exe (+ required mingw DLLs)
# into dist/jp2a-studio/ afterwards so server.py's bundled-binary lookup finds it.

import sys
from pathlib import Path

block_cipher = None
REPO_ROOT = Path(SPECPATH).resolve().parent.parent  # packaging/windows -> repo root

a = Analysis(
    [str(REPO_ROOT / "app" / "server.py")],
    pathex=[str(REPO_ROOT / "app")],
    binaries=[],
    datas=[(str(REPO_ROOT / "app" / "static"), "static")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jp2a-studio",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(REPO_ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="jp2a-studio",
)
