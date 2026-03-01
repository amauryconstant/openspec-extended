#!/usr/bin/env bash
# Test helpers for osc-* unit tests
# Source this file in each .bats file

# Get the project root directory (3 levels up from this file)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$PROJECT_ROOT/resources/opencode/scripts/lib"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures"

# Setup a clean test environment
setup_test_env() {
    TEST_DIR=$(mktemp -d)
    pushd "$TEST_DIR" > /dev/null || exit 1
    
    # Create openspec changes directory structure
    mkdir -p openspec/changes
    
    # Initialize a git repo for git-dependent tests
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test User"
    
    export LIB_DIR
    export FIXTURES_DIR
}

# Cleanup test environment
teardown_test_env() {
    popd > /dev/null 2>&1 || true
    rm -rf "$TEST_DIR"
}

# Setup a minimal change directory with required files
setup_change() {
    local change="${1:-test-change}"
    local change_dir="openspec/changes/$change"
    
    mkdir -p "$change_dir/specs"
    
    echo "# Proposal" > "$change_dir/proposal.md"
    echo "# Design" > "$change_dir/design.md"
    echo "# Tasks" > "$change_dir/tasks.md"
    echo "# Spec" > "$change_dir/specs/spec.md"
}

# Setup a change with a pre-existing state.json
setup_change_with_state() {
    local change="$1"
    local state_json="$2"
    
    setup_change "$change"
    echo "$state_json" > "openspec/changes/$change/state.json"
}

# Setup a change with iterations.json
setup_change_with_iterations() {
    local change="$1"
    local iterations_json="$2"
    
    setup_change "$change"
    echo "$iterations_json" > "openspec/changes/$change/iterations.json"
}

# Setup a change with decision-log.json
setup_change_with_decision_log() {
    local change="$1"
    local log_json="$2"
    
    setup_change "$change"
    echo "$log_json" > "openspec/changes/$change/decision-log.json"
}

# Assert JSON contains expected key-value pair
assert_json_equals() {
    local json="$1"
    local key="$2"
    local expected="$3"
    
    local actual
    actual=$(echo "$json" | jq -r "$key")
    
    if [[ "$actual" != "$expected" ]]; then
        echo "Expected $key to be '$expected', got '$actual'"
        return 1
    fi
}

# Assert JSON key is true
assert_json_true() {
    local json="$1"
    local key="$2"
    
    local actual
    actual=$(echo "$json" | jq -r "$key")
    
    if [[ "$actual" != "true" ]]; then
        echo "Expected $key to be true, got '$actual'"
        return 1
    fi
}

# Assert JSON key is false
assert_json_false() {
    local json="$1"
    local key="$2"
    
    local actual
    actual=$(echo "$json" | jq -r "$key")
    
    if [[ "$actual" != "false" ]]; then
        echo "Expected $key to be false, got '$actual'"
        return 1
    fi
}

# Assert output contains string
assert_output_contains() {
    local needle="$1"
    
    if [[ "$output" != *"$needle"* ]]; then
        echo "Expected output to contain '$needle'"
        echo "Actual output: $output"
        return 1
    fi
}

# Run osc-state with test environment
run_osc_state() {
    run "$LIB_DIR/osc-state" "$@"
}

# Run osc-iterations with test environment
run_osc_iterations() {
    run "$LIB_DIR/osc-iterations" "$@"
}

# Run osc-log with test environment
run_osc_log() {
    run "$LIB_DIR/osc-log" "$@"
}

# Run osc-git with test environment
run_osc_git() {
    run "$LIB_DIR/osc-git" "$@"
}

# Run osc-ctx with test environment
run_osc_ctx() {
    run "$LIB_DIR/osc-ctx" "$@"
}
