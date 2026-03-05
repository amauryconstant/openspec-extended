#!/usr/bin/env bash
# E2E test helpers - sourced by all E2E bats files
# Each test runs in an isolated /tmp directory

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/resources/opencode/scripts"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures"
INSTALLER="$PROJECT_ROOT/bin/openspecx"

require_e2e_confirm() {
    if [[ "${E2E_CONFIRM:-}" != "1" ]]; then
        skip "Set E2E_CONFIRM=1 to run E2E tests"
    fi
}

setup_e2e_repo() {
    E2E_DIR=$(mktemp -d /tmp/openspec-e2e-XXXXXX)
    cd "$E2E_DIR" || exit 1

    git init -q
    git config user.email "e2e@test.com"
    git config user.name "E2E Test"

    echo "# E2E Test Repo" > README.md
    git add README.md
    git commit -q -m "Initial commit"

    "$INSTALLER" install opencode --with-core >/dev/null 2>&1

    mkdir -p openspec/changes

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

run_openspec_auto() {
    run .opencode/scripts/openspec-auto "$@"
}

run_streaming() {
    local tmp_file
    tmp_file=$(mktemp)

    # Check if FD 3 is available (BATS terminal output)
    local output_fd=1
    if { true >&3; } 2>/dev/null; then
        output_fd=3
    fi

    # Stream to terminal via FD 3 (BATS) or stdout, while capturing to file
    "$@" 2>&1 | tee "$tmp_file" >&$output_fd
    local exit_code=${PIPESTATUS[0]}

    # Wait for tee to finish writing (prevents race condition with buffered output)
    wait 2>/dev/null || true

    output=$(cat "$tmp_file")
    status=$exit_code
    lines=()
    while IFS= read -r line; do
        lines+=("$line")
    done <<< "$output"

    rm -f "$tmp_file"
    return $exit_code
}

run_openspec_auto_streaming() {
    run_streaming .opencode/scripts/openspec-auto "$@"
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

setup_minimal_change() {
    local change="${1:-test-change}"
    local change_dir="openspec/changes/$change"

    mkdir -p "$change_dir/specs"

    cat > "$change_dir/proposal.md" << 'EOF'
# Test Proposal

Minimal test change for E2E testing.

## Summary
Test change for validating openspec-auto.
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
