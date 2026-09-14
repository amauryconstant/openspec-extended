#!/usr/bin/env bash
# E2E test helpers - sourced by all E2E bats files
# Each test runs in an isolated /tmp directory

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/orchestrator/resources/opencode/scripts"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures"
# Prefer the onedir bundle (cold-start ~150ms) over the single-file
# distribution binary (~310ms) when both are present. Falls back to the
# single-file so non-build workflows (e.g. running bats against an
# externally-built onefile) still work.
if [ -x "$PROJECT_ROOT/dist/openspec-extended-onedir/openspec-extended-onedir" ]; then
    OPENSPEC_BIN="$PROJECT_ROOT/dist/openspec-extended-onedir/openspec-extended-onedir"
else
    OPENSPEC_BIN="$PROJECT_ROOT/dist/openspec-extended"
fi

require_e2e_confirm() {
    if [[ "${E2E_CONFIRM:-}" != "1" ]]; then
        skip "Set E2E_CONFIRM=1 to run E2E tests"
    fi
}

setup_file() {
    # Build the pre-installed opencode tree once per bats file (instead of
    # once per test). Each per-test setup() then copies this tree into a
    # fresh tmpdir, which is ~10x faster than re-running the install.
    SHARED_E2E_DIR=$(mktemp -d /tmp/openspec-shared-XXXXXX)
    cd "$SHARED_E2E_DIR" || exit 1

    git init -q
    git config user.email "e2e@test.com"
    git config user.name "E2E Test"

    echo "# E2E Test Repo" > README.md
    git add README.md
    git commit -q -m "Initial commit"

    "$OPENSPEC_BIN" install opencode --with-core --with-autonomous >/dev/null 2>&1

    mkdir -p openspec/changes

    export SHARED_E2E_DIR
}

teardown_file() {
    if [[ -n "${SHARED_E2E_DIR:-}" ]] && [[ -d "$SHARED_E2E_DIR" ]]; then
        rm -rf "$SHARED_E2E_DIR"
    fi
}

setup_e2e_repo() {
    # Per-test isolated copy of the pre-installed tree built in setup_file.
    # Tests that want a clean repo (e.g. `install ... --with-autonomous`
    # smoke tests) `cd "$BATS_TEST_TMPDIR"` and run their own install; this
    # helper only needs to provide an opencode-equipped cwd for the
    # `setup_minimal_change`-based tests (round-trip, state transitions).
    E2E_DIR=$(mktemp -d /tmp/openspec-e2e-XXXXXX)

    cp -a "$SHARED_E2E_DIR/.opencode" "$E2E_DIR/.opencode"
    cp -a "$SHARED_E2E_DIR/.gitignore" "$E2E_DIR/.gitignore" 2>/dev/null || true
    cp -a "$SHARED_E2E_DIR/.git" "$E2E_DIR/.git"
    mkdir -p "$E2E_DIR/openspec/changes"

    cd "$E2E_DIR" || exit 1
    export E2E_DIR
}

teardown_e2e_repo() {
    local exit_code=$?
    cd "$PROJECT_ROOT" 2>/dev/null || true
    if [[ -n "${E2E_DIR:-}" ]] && [[ -d "$E2E_DIR" ]]; then
        rm -rf "$E2E_DIR"
    fi
    return $exit_code
}

copy_fixture() {
    local fixture="${1:-add-hello-script}"
    if [[ -d "$FIXTURES_DIR/changes/$fixture" ]]; then
        cp -r "$FIXTURES_DIR/changes/$fixture" "openspec/changes/$fixture"
    else
        echo "Fixture not found: $fixture" >&2
        return 1
    fi
}

run_osx_orchestrate() {
    # Bats subprocesses inherit the parent's stdin, so on a TTY the
    # dirty-git prompt in validate_git (engine.py:262) blocks forever
    # because setup_e2e_repo leaves the test repo uncommitted. --force
    # is the documented escape hatch; prepending it here keeps every
    # bats caller non-interactive by default.
    run "$OPENSPEC_BIN" orchestrate --force "$@"
}

run_streaming() {
    local tmp_file
    tmp_file=$(mktemp)

    # Check if FD 3 is available (BATS terminal output)
    local output_fd=1
    if { true >&3; } 2>/dev/null; then
        output_fd=3
    fi

    # Execute command directly - bash handles multi-word commands correctly
    # Stream to terminal via FD 3 (BATS) or stdout, while capturing to file
    "$@" 2>&1 | tee "$tmp_file" >&$output_fd
    local exit_code=${PIPESTATUS[0]}

    # Ensure all output is captured and flushed
    sync
    sleep 0.1

    output=$(cat "$tmp_file")
    status=$exit_code
    lines=()
    while IFS= read -r line; do
        lines+=("$line")
    done <<< "$output"

    rm -f "$tmp_file"
    return $exit_code
}

run_osx_orchestrate_streaming() {
    run_streaming "$OPENSPEC_BIN" orchestrate "$@"
}

wait_for_file() {
    local file="$1"
    local timeout="${2:-60}"
    local elapsed=0

    while [[ ! -f "$file" ]] && [[ $elapsed -lt $timeout ]]; do
        sleep 1
        ((elapsed++))
    done

    [[ -f "$file" ]]
}

wait_for_phase_complete() {
    local change="$1"
    local timeout="${2:-300}"
    local elapsed=0

    while [[ $elapsed -lt $timeout ]]; do
        if [[ -f "openspec/changes/$change/complete.json" ]]; then
            return 0
        fi
        sleep 2
        ((elapsed += 2))
    done

    return 1
}

assert_file_exists() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        echo "Expected file to exist: $file"
        return 1
    fi
}

assert_file_not_exists() {
    local file="$1"
    if [[ -f "$file" ]]; then
        echo "Expected file to NOT exist: $file"
        return 1
    fi
}

assert_file_contains() {
    local file="$1"
    local pattern="$2"

    if ! grep -q "$pattern" "$file" 2>/dev/null; then
        echo "Expected file '$file' to contain pattern: $pattern"
        return 1
    fi
}

# Get archive directory for a change
get_archive_dir() {
    local change="$1"
    find openspec/changes/archive -name "*-$change" -type d 2>/dev/null | head -1
}

# Get log file path (works for both active and archived changes)
get_log_file() {
    local change="$1"
    local archive_dir
    archive_dir=$(get_archive_dir "$change")
    if [[ -n "$archive_dir" ]] && [[ -f "$archive_dir/osx-orchestrate.log" ]]; then
        echo "$archive_dir/osx-orchestrate.log"
    elif [[ -f "openspec/changes/$change/osx-orchestrate.log" ]]; then
        echo "openspec/changes/$change/osx-orchestrate.log"
    else
        echo ""
    fi
}

# Assert JSON file is valid and parseable
assert_valid_json() {
    local file="$1"
    [ -f "$file" ] || return 1

    jq empty "$file" >/dev/null 2>&1 || {
        echo "Invalid JSON: $file"
        return 1
    }
}

# Assert JSON array has minimum count
assert_json_count_ge() {
    local file="$1"
    local min_count="$2"

    local count
    count=$(jq '. | length' "$file")

    [[ "$count" -ge "$min_count" ]] || {
        echo "Expected ≥$min_count entries, got $count in $file"
        return 1
    }
}

# Assert JSON field exists and is not null
assert_json_field_exists() {
    local json="$1"
    local field="$2"

    local value
    value=$(echo "$json" | jq -r ".$field // empty")

    [[ -n "$value" ]] || {
        echo "Field not found: $field"
        return 1
    }
}

# Save shared state to JSON file (for BATS setup_file → test communication)
save_e2e_state() {
    local archive_dir="${1:-}"
    local change_name="${2:-}"
    local workflow_ran="${3:-false}"

    local state_json
    state_json=$(jq -n \
        --arg archive_dir "$archive_dir" \
        --arg change_name "$change_name" \
        --arg workflow_ran "$workflow_ran" \
        '{archive_dir: $archive_dir, change_name: $change_name, workflow_ran: $workflow_ran}')

    echo "$state_json" > .e2e-state.json
}

# Load shared state from JSON file
load_e2e_state() {
    if [[ -f ".e2e-state.json" ]]; then
        SHARED_ARCHIVE_DIR=$(jq -r '.archive_dir // empty' .e2e-state.json)
        SHARED_CHANGE_NAME=$(jq -r '.change_name // empty' .e2e-state.json)
        SHARED_WORKFLOW_RAN=$(jq -r '.workflow_ran // "false"' .e2e-state.json)
        export SHARED_ARCHIVE_DIR SHARED_CHANGE_NAME SHARED_WORKFLOW_RAN
    fi
}

setup_minimal_change() {
    local change="${1:-test-change}"
    local change_dir="openspec/changes/$change"

    mkdir -p "$change_dir/specs"

    cat > "$change_dir/proposal.md" << 'EOF'
# Test Proposal

Minimal test change for E2E testing.

## Summary
Test change for validating osx-orchestrate.
EOF

    cat > "$change_dir/design.md" << 'EOF'
# Test Design

Minimal design document.
EOF

    cat > "$change_dir/tasks.md" << 'EOF'
# Tasks

- [ ] Complete test task
EOF

    cat > "$change_dir/specs/spec.md" << 'EOF'
# Specification

**SHALL** complete successfully.
EOF
}
