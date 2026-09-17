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

# Bump the __version__ in orchestrator/source/__init__.py.
bump_py_init_version() {
    local new_version="$1"
    local dry_run="${2:-false}"
    local py_init="$BUMP_PROJECT_ROOT/orchestrator/source/__init__.py"

    if [[ "$dry_run" == "true" ]]; then
        printf '    [DRY-RUN] orchestrator/source/__init__.py\n'
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
    printf '    OK orchestrator/source/__init__.py\n'
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

# Verify CHANGELOG.md has at least one entry for the upcoming release.
# The release pipeline commits and tags after this passes; an empty
# `## [Unreleased]` plus a missing `## [<new_version>]` block fails.
# A `## [Unreleased]` section counts as a placeholder the maintainer
# intends to rename on tag, and is accepted when it carries at least
# one non-blank line (a category header is enough — bullets not
# required so a stub section lets a hotfix ship without forcing a
# hand-curated entry on every patch).
#
# Args: <new_version> [changelog_path]
#   new_version: the upcoming semver (e.g. "1.10.8")
#   changelog_path: defaults to "$BUMP_PROJECT_ROOT/CHANGELOG.md"
#
# Returns 0 when the gate passes (CHANGELOG.md absent also passes — the
# rule is "fail if CHANGELOG.md exists but is missing the entry", not
# "force a CHANGELOG.md to exist"). Returns 1 with a stderr hint when
# the gate fails.
check_changelog_for_release() {
    local new_version="$1"
    local changelog_path="${2:-$BUMP_PROJECT_ROOT/CHANGELOG.md}"

    if [[ ! -f "$changelog_path" ]]; then
        printf '  Skip: no CHANGELOG.md at %s\n' "$changelog_path"
        return 0
    fi

    local unreleased_section version_section

    # Slice the file into the body of `## [Unreleased]` (or empty if
    # absent). `head`/`tail` line counts come from grep -n.
    unreleased_section=$(python3 - "$changelog_path" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
try:
    text = path.read_text()
except FileNotFoundError:
    sys.exit(0)
lines = text.splitlines()
start = None
for i, line in enumerate(lines):
    if line.strip() == "## [Unreleased]":
        start = i + 1
        break
if start is None:
    sys.exit(0)
end = len(lines)
for j in range(start, len(lines)):
    if lines[j].startswith("## ") and not lines[j].startswith("### "):
        end = j
        break
body = lines[start:end]
sys.stdout.write("\n".join(body))
PY
)

    version_section=$(python3 - "$changelog_path" "$new_version" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
target = sys.argv[2]
try:
    text = path.read_text()
except FileNotFoundError:
    sys.exit(0)
lines = text.splitlines()
header = f"## [{target}]"
start = None
for i, line in enumerate(lines):
    if line.startswith(header):
        start = i + 1
        break
if start is None:
    sys.exit(0)
end = len(lines)
for j in range(start, len(lines)):
    if lines[j].startswith("## ") and not lines[j].startswith("### "):
        end = j
        break
body = lines[start:end]
sys.stdout.write("\n".join(body))
PY
)

    if [[ -n "$(printf '%s' "$unreleased_section" | tr -d '[:space:]')" ]] \
        || [[ -n "$(printf '%s' "$version_section" | tr -d '[:space:]')" ]]; then
        printf '  OK: CHANGELOG.md has entry for v%s\n' "$new_version"
        return 0
    fi

    printf '  Error: CHANGELOG.md has no entry for the upcoming release v%s.\n' "$new_version" >&2
    cat <<EOF >&2
         Populate \`## [Unreleased]\` (we will rename it on tag) or add a \`## [v${new_version}] - <date>\` section.
         Re-run with --skip-changelog-check to bypass (hotfix only).
EOF
    return 1
}
