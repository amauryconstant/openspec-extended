#!/usr/bin/env bash
# Shared bump helpers for version updates.
# Source this file from check / update / release. Do not run directly.

BUMP_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUMP_PROJECT_ROOT="$(cd "$BUMP_LIB_DIR/../../../.." && pwd)"

# Bump the SCRIPT_VERSION in a script file.
# Args: <file_path> <new_version> [--dry-run]
# Echoes "OK <basename>" or "[DRY-RUN] <basename>" on success.
bump_script_version_in_file() {
    local file_path="$1"
    local new_version="$2"
    local dry_run="${3:-false}"

    if [[ "$dry_run" == "true" ]]; then
        printf '    [DRY-RUN] %s\n' "$(basename "$file_path")"
        return 0
    fi

    python3 - "$file_path" "$new_version" <<'PY'
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
new_version = sys.argv[2]
text = path.read_text()
new_text, n = re.subn(
    r'^(\s*)SCRIPT_VERSION\s*=\s*"[^"]*"',
    rf'\1SCRIPT_VERSION = "{new_version}"',
    text,
    count=1,
    flags=re.MULTILINE,
)
if n != 1:
    sys.exit(f"SCRIPT_VERSION not found in {path}")
path.write_text(new_text)
PY
    printf '    OK %s\n' "$(basename "$file_path")"
}

# Bump the __version__ in source/__init__.py.
bump_py_init_version() {
    local new_version="$1"
    local dry_run="${2:-false}"
    local py_init="$BUMP_PROJECT_ROOT/source/__init__.py"

    if [[ "$dry_run" == "true" ]]; then
        printf '    [DRY-RUN] source/__init__.py\n'
        return 0
    fi

    python3 - "$py_init" "$new_version" <<'PY'
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
new_version = sys.argv[2]
text = path.read_text()
new_text, n = re.subn(
    r'^(__version__\s*=\s*)"[^"]*"',
    rf'\1"{new_version}"',
    text,
    count=1,
    flags=re.MULTILINE,
)
if n != 1:
    sys.exit(f"__version__ not found in {path}")
path.write_text(new_text)
PY
    printf '    OK source/__init__.py\n'
}

# Bump the [project] version in pyproject.toml.
bump_pyproject_version() {
    local new_version="$1"
    local dry_run="${2:-false}"
    local pyproject="$BUMP_PROJECT_ROOT/pyproject.toml"

    if [[ "$dry_run" == "true" ]]; then
        printf '    [DRY-RUN] pyproject.toml\n'
        return 0
    fi

    python3 - "$pyproject" "$new_version" <<'PY'
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
new_version = sys.argv[2]
text = path.read_text()
new_text, n = re.subn(
    r'^(version\s*=\s*)"[^"]*"',
    rf'\1"{new_version}"',
    text,
    count=1,
    flags=re.MULTILINE,
)
if n != 1:
    sys.exit(f"version field not found in {path}")
path.write_text(new_text)
PY
    printf '    OK pyproject.toml\n'
}

# Update version references in README.md.
update_readme_version() {
    local new_version="$1"
    local dry_run="${2:-false}"
    local readme="$BUMP_PROJECT_ROOT/README.md"

    if [[ ! -f "$readme" ]]; then
        return 0
    fi

    if [[ "$dry_run" == "true" ]]; then
        printf '    [DRY-RUN] README.md\n'
        return 0
    fi

    sed -i.bak \
        -e "s/version-v[0-9]*\.[0-9]*\.[0-9]*/version-v${new_version}/g" \
        -e "s/VERSION=v[0-9]*\.[0-9]*\.[0-9]*/VERSION=v${new_version}/g" \
        "$readme"
    rm -f "$readme.bak"
    printf '    OK README.md\n'
}
