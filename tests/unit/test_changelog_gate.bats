#!/usr/bin/env bats
# Unit tests for check_changelog_for_release() in
# .mise/tasks/version/lib/bump.sh.
#
# The function enforces the CHANGELOG.md gate in `mise run release`:
# the upcoming release fails to commit/tag when neither `## [Unreleased]`
# nor `## [<X.Y.Z>]` is populated. Cases:
#
#   1. CHANGELOG.md absent              → gate skipped, exit 0
#   2. CHANGELOG.md present, no entry   → fail (exit 1), stderr hint
#   3. `## [Unreleased]` populated      → pass (exit 0)
#   4. `## [Unreleased]` empty but
#      `## [<X.Y.Z>]` populated         → pass (exit 0)
#   5. Both empty                       → fail (exit 1)
#   6. Whitespace-only [Unreleased]
#      (kept as a stub)                 → fail (exit 1)
#   7. Error message references version and bypass flag
#
# Each test sources the lib via a subshell so we never pollute the
# bats test runner's shell environment.

load '../helpers/test-helpers'

setup() {
    BUMP_LIB_DIR="$PROJECT_ROOT/.mise/tasks/version/lib"
    [[ -f "$BUMP_LIB_DIR/bump.sh" ]]
    CHANGELOG="$BATS_TEST_TMPDIR/CHANGELOG.md"
}

# Run check_changelog_for_release with a temp CHANGELOG.md and capture
# stdout/stderr + exit code. Args: <content_or_-> <version>.
# Use "-" as the first arg for a missing file.
run_gate() {
    local content="$1"
    local version="$2"
    local changelog_path="$CHANGELOG"
    if [[ "$content" == "-" ]]; then
        changelog_path="$BATS_TEST_TMPDIR/does-not-exist-$$.md"
    else
        printf '%s' "$content" > "$changelog_path"
    fi
    bash -c '
        bump_lib="$1"
        changelog="$2"
        version="$3"
        # shellcheck source=/dev/null
        source "$bump_lib"
        check_changelog_for_release "$version" "$changelog"
    ' -- "$BUMP_LIB_DIR/bump.sh" "$changelog_path" "$version"
}

# Test 1: CHANGELOG.md absent → gate skipped, exit 0.
@test "missing CHANGELOG.md → skipped (exit 0)" {
    run run_gate "-" "1.10.8"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Skip: no CHANGELOG.md"* ]]
}

# Test 2: CHANGELOG.md present, [Unreleased] empty, target missing → fail.
@test "empty [Unreleased] + missing target → fail (exit 1)" {
    local content='## [Unreleased]

## [1.10.7] - 2026-09-16

### Changed

- Last real release.
'
    run run_gate "$content" "1.10.8"
    [ "$status" -eq 1 ]
}

# Test 3: Populated [Unreleased] → pass.
@test "populated [Unreleased] → pass (exit 0)" {
    local content='## [Unreleased]

### Changed

- Hand-curated entry for the upcoming release.
'
    run run_gate "$content" "1.10.8"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK: CHANGELOG.md has entry for v1.10.8"* ]]
}

# Test 4: Empty [Unreleased] but populated target section → pass.
@test "empty [Unreleased] + populated target section → pass (exit 0)" {
    local content='## [Unreleased]

## [1.10.8] - 2099-01-01

### Changed

- Pre-tagged entry.
'
    run run_gate "$content" "1.10.8"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK: CHANGELOG.md has entry for v1.10.8"* ]]
}

# Test 5: Both empty → fail.
@test "both empty → fail (exit 1)" {
    local content='## [Unreleased]

## [1.10.7] - 2026-09-16

### Changed

- Other release content.
'
    run run_gate "$content" "9.9.9"
    [ "$status" -eq 1 ]
}

# Test 6: Whitespace-only [Unreleased] (stub) → fail.
@test "whitespace-only [Unreleased] → fail (exit 1)" {
    local content='## [Unreleased]
                       

## [1.10.7] - 2026-09-16

### Changed

- Existing release.
'
    run run_gate "$content" "1.10.8"
    [ "$status" -eq 1 ]
}

# Test 7: Error message references the upcoming version and the
# --skip-changelog-check bypass.
@test "error message mentions version and bypass flag" {
    local content='## [Unreleased]

## [1.10.7] - 2026-09-16

### Changed

- Other release.
'
    run run_gate "$content" "9.9.9"
    [ "$status" -eq 1 ]
    [[ "$output" == *"v9.9.9"* ]]
    [[ "$output" == *"--skip-changelog-check"* ]]
}
