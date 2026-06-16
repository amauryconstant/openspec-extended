#!/usr/bin/env bash
# Shared manifest helpers for version tasks.
# Source this file from check / update. Do not run directly.

# Resolve the project root (4 levels up from this file: .mise/tasks/version/lib/).
MANIFEST_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_PROJECT_ROOT="$(cd "$MANIFEST_LIB_DIR/../../../.." && pwd)"

# Path to the manifest file for a given platform.
manifest_path_for_platform() {
    local platform="$1"
    printf '%s\n' "$MANIFEST_PROJECT_ROOT/resources/$platform/manifest.toml"
}

# Parse resource info (type:name) from a staged file path.
# Returns "type:name" on stdout, empty on miss.
resource_info_from_path() {
    local file_path="$1"
    local parts
    IFS='/' read -r -a parts <<< "$file_path"
    local idx=-1
    for i in "${!parts[@]}"; do
        if [[ "${parts[$i]}" == "resources" ]]; then
            idx=$i
            break
        fi
    done
    if (( idx < 0 )) || (( ${#parts[@]} <= idx + 3 )); then
        return 1
    fi
    local resource_type="${parts[$idx + 2]}"
    local resource_name="${parts[$idx + 3]%.md}"
    printf '%s\n' "$resource_type:$resource_name"
}

# Parse platform from a staged file path.
platform_for_path() {
    local file_path="$1"
    local parts
    IFS='/' read -r -a parts <<< "$file_path"
    local idx=-1
    for i in "${!parts[@]}"; do
        if [[ "${parts[$i]}" == "resources" ]]; then
            idx=$i
            break
        fi
    done
    if (( idx < 0 )) || (( ${#parts[@]} <= idx + 1 )); then
        return 1
    fi
    local platform="${parts[$idx + 1]}"
    if [[ "$platform" != "opencode" && "$platform" != "claude" ]]; then
        return 1
    fi
    printf '%s\n' "$platform"
}

# Get current version of a resource in a platform manifest.
# Echoes version on success, returns 1 if not found.
get_resource_version() {
    local manifest="$1"
    local resource_type="$2"
    local resource_name="$3"
    if [[ ! -f "$manifest" ]]; then
        return 1
    fi
    parse_resource_version_from_stdin "$resource_type" "$resource_name" < "$manifest"
}

# Parse a version value from a resource section in manifest content on stdin.
# Lets callers feed `git show HEAD:<manifest>` or any other stream through
# the same parser that get_resource_version uses on a file path.
# Echoes version on success, returns 1 if not found.
parse_resource_version_from_stdin() {
    local resource_type="$1"
    local resource_name="$2"
    local section="[resources.${resource_type}.${resource_name}]"
    awk -v section="$section" '
        $0 == section { in_section = 1; next }
        in_section && /^[[:space:]]*$/ { in_section = 0 }
        in_section && /^version[[:space:]]*=/ {
            sub(/^version[[:space:]]*=[[:space:]]*"/, "")
            sub(/"$/, "")
            print
            exit
        }
    '
}

# Set the version of a resource in a platform manifest, in place.
set_resource_version() {
    local manifest="$1"
    local resource_type="$2"
    local resource_name="$3"
    local new_version="$4"
    local section="[resources.${resource_type}.${resource_name}]"

    # Build a python one-liner to do safe in-place update. The manifest
    # format is controlled by us; we use python's tomllib to avoid
    # regex edge cases around indentation and ordering.
    python3 - "$manifest" "$section" "$new_version" <<'PY'
import sys, re, tomllib
from pathlib import Path

manifest_path = Path(sys.argv[1])
section = sys.argv[2]
new_version = sys.argv[3]

text = manifest_path.read_text()
data = tomllib.loads(text)

type_name = section.removeprefix("[resources.").removesuffix("]")
resource_type, _, resource_name = type_name.partition(".")
data.setdefault("resources", {}).setdefault(resource_type, {})[resource_name] = {"version": new_version}

# Re-emit using tomli_w would be nice; for now we just regex-swap the
# version line scoped to the matching section.
pattern = re.compile(
    rf"(\[resources\.{re.escape(resource_type)}\.{re.escape(resource_name)}\][^\[]*?version\s*=\s*)\"[^\"]*\"",
    re.DOTALL,
)
new_text, n = pattern.subn(rf'\1"{new_version}"', text, count=1)
if n != 1:
    sys.exit(f"Failed to update {section} in {manifest_path}")
manifest_path.write_text(new_text)
PY
}

# Validate X.Y.Z strict semver (no prerelease/build).
validate_semver() {
    [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

# Bump X.Y.Z by type (major|minor|patch). Echoes the new version.
bump_semver() {
    local version="$1"
    local bump_type="$2"
    local major minor patch
    IFS='.' read -r major minor patch <<< "$version"
    case "$bump_type" in
        major) ((major += 1)); minor=0; patch=0 ;;
        minor) ((minor += 1)); patch=0 ;;
        patch|"") ((patch += 1)) ;;
        *) printf 'Unknown bump type: %s\n' "$bump_type" >&2; return 1 ;;
    esac
    printf '%d.%d.%d\n' "$major" "$minor" "$patch"
}

# Pick the highest bump type from a list of "major|minor|patch".
highest_bump_type() {
    local best=""
    local rank_best=0
    local t rank
    for t in "$@"; do
        case "$t" in
            major) rank=3 ;;
            minor) rank=2 ;;
            patch) rank=1 ;;
            *) rank=0 ;;
        esac
        if (( rank > rank_best )); then
            best="$t"
            rank_best=$rank
        fi
    done
    printf '%s\n' "$best"
}
