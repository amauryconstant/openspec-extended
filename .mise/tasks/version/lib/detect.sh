#!/usr/bin/env bash
# Diff-based bump detection for version tasks.
# Source this file from check / update. Do not run directly.

# Detect bump type from staged diff for a file.
# Echoes one of: major|minor|patch
detect_bump_type() {
    local file_path="$1"

    if ! diff_text=$(git diff --cached -- "$file_path" 2>/dev/null); then
        printf 'patch\n'
        return 0
    fi

    local lower="${diff_text,,}"

    if [[ "$lower" == *"break:"* || "$lower" == *"breaking"* || "$lower" == *"major:"* ]]; then
        printf 'major\n'; return 0
    fi
    if [[ "$lower" == *"feat:"* || "$lower" == *"add:"* || "$lower" == *"new:"* ]]; then
        printf 'minor\n'; return 0
    fi
    if [[ "$lower" == *"fix:"* || "$lower" == *"patch:"* || "$lower" == *"bug:"* ]]; then
        printf 'patch\n'; return 0
    fi

    local added removed
    added=$(grep -cE '^\+(?!\+\+)' <<< "$diff_text" || true)
    removed=$(grep -cE '^-(?!--)' <<< "$diff_text" || true)

    if (( removed > added * 2 )); then
        printf 'major\n'; return 0
    fi
    if (( added > 0 )); then
        printf 'minor\n'; return 0
    fi

    printf 'patch\n'
}
