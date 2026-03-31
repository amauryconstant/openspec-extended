import sys
import os
from pathlib import Path

block_cipher = None

project_root = Path.cwd()
resources_path = project_root / "resources" / "opencode"
package_path = project_root / "source"

a = Analysis(
    [str(package_path / "__main__.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(resources_path), "resources/opencode"),
    ],
    hiddenimports=[
        "typer",
        "toml",
        "rich",
        "rich.console",
        "rich.table",
        "subprocess",
        "tempfile",
        "select",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="openspec-extended",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
