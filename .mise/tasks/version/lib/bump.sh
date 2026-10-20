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

# Idempotently rewrite the on-disk CHANGELOG.md into the canonical
# post-tag form expected by `.opencode/rules/version-management.md`:
# a fresh empty `## [Unreleased]` header followed by a
# `## [<new_version>] - <date>` section carrying the entries that were
# in `[Unreleased]`. The earlier `check_changelog_for_release` gate
# already verified that at least one of these sections is populated;
# this helper does the move so the maintainer doesn't have to.
#
# Behaviour matrix (matches the rules doc):
#
#   1. [Unreleased] populated, [<X.Y.Z>] absent
#      → move [Unreleased] body into a new `## [<X.Y.Z>] - <date>`
#        section, insert empty `## [Unreleased]` header above
#   2. [Unreleased] empty, [<X.Y.Z>] populated
#      → leave body untouched; ensure a fresh empty `## [Unreleased]`
#        header sits above the version section
#   3. Both populated
#      → keep the [version] body as authoritative (the maintainer
#        hand-curated it), clear the [Unreleased] body, surface a
#        warning on stderr so it's visible in the dry-run log
#   4. Both empty (gate should have failed before reaching here)
#      → no-op, return 0 without mutating the file
#
# Idempotent — running twice produces byte-identical output. Returned
# exit code is 0 on success, 1 only on filesystem errors.
#
# Args: <new_version> [date] [changelog_path]
#   new_version: upcoming semver (e.g. "1.12.1")
#   date: YYYY-MM-DD, defaults to "$(date -u +%Y-%m-%d)"
#   changelog_path: defaults to "$BUMP_PROJECT_ROOT/CHANGELOG.md"
apply_unreleased_rename() {
    local new_version="$1"
    local date="${2:-$(date -u +%Y-%m-%d)}"
    local changelog_path="${3:-$BUMP_PROJECT_ROOT/CHANGELOG.md}"

    if [[ ! -f "$changelog_path" ]]; then
        printf '  Skip: no CHANGELOG.md at %s\n' "$changelog_path"
        return 0
    fi

    if ! python3 - "$changelog_path" "$new_version" "$date" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
new_version = sys.argv[2]
date = sys.argv[3]
text = path.read_text()
lines = text.splitlines()

UNRELEASED = "## [Unreleased]"
VERSION_HEADER = f"## [{new_version}]"
VERSION_HEADER_DATED = f"{VERSION_HEADER} - {date}"


def find_sections(lines):
    """Return list of [kind, header_index, body_start, body_end].
    Only H2 sections are tracked; body ends at the next H2 header
    (or EOF)."""
    out = []
    for i, line in enumerate(lines):
        if not line.startswith("## ") or line.startswith("### "):
            continue
        if line == UNRELEASED:
            kind = "unreleased"
        elif line.startswith(VERSION_HEADER):
            kind = "version"
        else:
            kind = "other"
        out.append([kind, i, i + 1, len(lines)])
    for k in range(len(out) - 1):
        out[k][3] = out[k + 1][1]
    return out


def body(section):
    return lines[section[2]:section[3]]


def is_blank(b):
    return not any(line.strip() for line in b)


def strip_blanks(b):
    a = list(b)
    while a and a[0].strip() == "":
        a.pop(0)
    while a and a[-1].strip() == "":
        a.pop()
    return a


sections = find_sections(lines)
unreleased = next((s for s in sections if s[0] == "unreleased"), None)
version = next((s for s in sections if s[0] == "version"), None)

u_body = body(unreleased) if unreleased else []
v_body = body(version) if version else []

# Decide the version body the canonical file should carry. Priority:
# 1. Maintainer-pre-typed [version] body (case 2 / case 3)
# 2. [Unreleased] body (case 1)
# 3. Empty (case 4 — gate should have caught this; we no-op silently)
warned = False
if not is_blank(v_body):
    version_body = strip_blanks(v_body)
    warned = not is_blank(u_body)  # case 3: both populated
elif not is_blank(u_body):
    version_body = strip_blanks(u_body)
else:
    # Case 4: nothing to do — leave the file alone.
    sys.exit(0)

# Slice the file around the H2 sections we're touching. `preamble` is
# everything before the first [Unreleased] or [version] header (kept
# verbatim). `tail` is everything from the end of the last such
# section onward (preserves prior version blocks). Other H2 sections
# between them are not expected in any of the four cases, so this
# slicing is safe.
relevant = [s for s in (unreleased, version) if s is not None]
preamble_end = min(s[1] for s in relevant)
tail_start = max(s[3] for s in relevant)
preamble = lines[:preamble_end]
tail = lines[tail_start:]

# Build the canonical top block: empty [Unreleased] header, a blank
# line, the dated version header, a blank line, then the version body,
# then a trailing blank that bridges to the tail.
canonical_top = [
    UNRELEASED,
    "",
    VERSION_HEADER_DATED,
    "",
] + version_body + [""]

new_lines = preamble + canonical_top + tail
new_text = "\n".join(new_lines)
if text.endswith("\n") and not new_text.endswith("\n"):
    new_text += "\n"

if warned:
    print(
        f"warning: both `## [Unreleased]` and `## [{new_version}]` were "
        "populated; using the version section as authoritative and "
        "clearing [Unreleased].",
        file=sys.stderr,
    )

path.write_text(new_text)
PY
    then
        return 1
    fi
    printf '    OK CHANGELOG.md (%s section stamped)\n' "$new_version"
    return 0
}
