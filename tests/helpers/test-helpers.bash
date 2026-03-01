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
    
    # Create initial commit so git rev-parse HEAD works
    echo "# Test repo" > README.md
    git add README.md
    git commit -q -m "Initial commit"
    
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

# Run osc-validate with test environment
run_osc_validate() {
    run "$LIB_DIR/osc-validate" "$@"
}

# Run osc-phase with test environment
run_osc_phase() {
    run "$LIB_DIR/osc-phase" "$@"
}

# Run osc-baseline with test environment
run_osc_baseline() {
    run "$LIB_DIR/osc-baseline" "$@"
}

# Run osc-complete with test environment
run_osc_complete() {
    run "$LIB_DIR/osc-complete" "$@"
}

# Setup .opencode/skills directory with required skills
setup_skills_dir() {
    local skills_dir=".opencode/skills"
    mkdir -p "$skills_dir"
    
    local skills=(
        "openspec-concepts"
        "openspec-review-artifacts"
        "openspec-modify-artifacts"
        "openspec-apply-change"
        "openspec-review-test-compliance"
        "openspec-verify-change"
        "openspec-maintain-ai-docs"
        "openspec-sync-specs"
        "openspec-archive-change"
    )
    
    for skill in "${skills[@]}"; do
        mkdir -p "$skills_dir/$skill"
        echo "# $skill" > "$skills_dir/$skill/SKILL.md"
    done
}

# Setup .opencode/commands directory with required commands
setup_commands_dir() {
    local commands_dir=".opencode/commands"
    mkdir -p "$commands_dir"
    
    local commands=(
        "openspec-phase0"
        "openspec-phase1"
        "openspec-phase2"
        "openspec-phase3"
        "openspec-phase4"
        "openspec-phase5"
        "openspec-phase6"
    )
    
    for cmd in "${commands[@]}"; do
        echo "# $cmd" > "$commands_dir/$cmd.md"
    done
}

# Setup archive directory with a timestamped change archive
setup_archive() {
    local change="$1"
    local timestamp="${2:-2024-01-15}"
    
    mkdir -p "openspec/changes/archive"
    mkdir -p "openspec/changes/archive/${timestamp}-${change}"
}

# Setup a change with complete.json
setup_change_with_complete() {
    local change="$1"
    local complete_json="$2"
    
    setup_change "$change"
    echo "$complete_json" > "openspec/changes/$change/complete.json"
}

# Setup a change with baseline file
setup_baseline() {
    local commit="${1:-abc123}"
    local branch="${2:-main}"
    local timestamp="${3:-2024-01-15T10:00:00Z}"
    
    cat > ".openspec-baseline.json" <<EOF
{
  "commit": "$commit",
  "branch": "$branch",
  "timestamp": "$timestamp"
}
EOF
}

# Assert output is valid JSON
assert_valid_json() {
    local json="$1"
    
    if ! echo "$json" | jq -e . &>/dev/null; then
        echo "Expected valid JSON, got: $json"
        return 1
    fi
}

# Assert error has standard schema (error + message fields)
assert_error_schema() {
    local json="$1"
    
    if ! echo "$json" | jq -e '.error' &>/dev/null; then
        echo "Error JSON missing 'error' field: $json"
        return 1
    fi
    
    if ! echo "$json" | jq -e '.message' &>/dev/null; then
        echo "Error JSON missing 'message' field: $json"
        return 1
    fi
}

# Assert JSON has a specific field
assert_json_has_field() {
    local json="$1"
    local field="$2"
    
    if ! echo "$json" | jq -e --arg f "$field" 'has($f)' &>/dev/null; then
        echo "JSON missing field '$field': $json"
        return 1
    fi
}

# Assert JSON array length
assert_json_array_length() {
    local json="$1"
    local field="$2"
    local expected="$3"
    
    local actual
    actual=$(echo "$json" | jq ".$field | length")
    
    if [[ "$actual" != "$expected" ]]; then
        echo "Expected $field array length to be $expected, got $actual"
        return 1
    fi
}
