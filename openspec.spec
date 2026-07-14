import sys
import os
from pathlib import Path

block_cipher = None

project_root = Path.cwd()
opencode_resources_path = project_root / "resources" / "opencode"
claude_resources_path = project_root / "resources" / "claude"
package_path = project_root / "source"


def _collect_files_excluding_agents_md(src_dir, dst_prefix):
    items = []
    src = Path(src_dir)
    if not src.exists():
        return items
    for path in src.rglob("*"):
        if path.is_file() and path.name != "AGENTS.md":
            rel = path.relative_to(src)
            dst = str(Path(dst_prefix) / rel.parent)
            items.append((str(path), dst))
    return items


a = Analysis(
    [str(package_path / "__main__.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=(
        _collect_files_excluding_agents_md(
            opencode_resources_path, "resources/opencode"
        )
        + _collect_files_excluding_agents_md(
            claude_resources_path, "resources/claude"
        )
        + _collect_files_excluding_agents_md(
            project_root / "source" / "orchestrator", "source/orchestrator"
        )
        + _collect_files_excluding_agents_md(
            project_root / "source" / "lib", "source/lib"
        )
    ),
    hiddenimports=[
        "typer",
        "toml",
        "rich",
        "rich.console",
        "rich.table",
        "yaml",
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
