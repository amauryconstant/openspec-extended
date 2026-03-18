#!/usr/bin/env bash
# Test helpers for osx-* unit tests
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

# Run osc Python tool with test environment
run_osx() {
    run "$LIB_DIR/osc" "$@"
}

# Convenience wrappers for common commands
# Note: osx Python tool expects action before change name
# Usage: run_osx_state get <change> (not run_osx_state <change> get)
run_osx_state() {
    local action="$1"
    shift
    run "$LIB_DIR/osx" state "$action" "$@"
}

run_osx_iterations() {
    local action="$1"
    shift
    run "$LIB_DIR/osx" iterations "$action" "$@"
}

run_osx_log() {
    local action="$1"
    shift
    run "$LIB_DIR/osx" log "$action" "$@"
}

run_osx_git() {
    run "$LIB_DIR/osx" git get "$@"
}

run_osx_ctx() {
    run "$LIB_DIR/osx" ctx get "$@"
}

run_osx_validate() {
    local action="$1"
    shift
    run "$LIB_DIR/osx" validate "$action" "$@"
}

run_osx_phase() {
    local action="$1"
    shift
    run "$LIB_DIR/osx" phase "$action" "$@"
}

run_osx_baseline() {
    local action="$1"
    shift
    run "$LIB_DIR/osx" baseline "$action" "$@"
}

run_osx_complete() {
    local action="$1"
    shift
    run "$LIB_DIR/osx" complete "$action" "$@"
}

# Setup .opencode/skills directory with required skills
setup_skills_dir() {
    local skills_dir=".opencode/skills"
    mkdir -p "$skills_dir"
    
    local skills=(
        "osx-concepts"
        "osx-review-artifacts"
        "osx-modify-artifacts"
        "osx-apply-change"
        "osx-review-test-compliance"
        "osx-verify-change"
        "osx-maintain-ai-docs"
        "osx-sync-specs"
        "osx-archive-change"
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
        "osx-phase0"
        "osx-phase1"
        "osx-phase2"
        "osx-phase3"
        "osx-phase4"
        "osx-phase5"
        "osx-phase6"
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

# Setup an archived change with complete state
setup_archived_change_with_state() {
    local change="$1"
    local timestamp="$2"
    local state_json="$3"
    
    local archive_dir="openspec/changes/archive/${timestamp}-${change}"
    mkdir -p "$archive_dir/specs"
    echo "# Proposal" > "$archive_dir/proposal.md"
    echo "# Design" > "$archive_dir/design.md"
    echo "# Tasks" > "$archive_dir/tasks.md"
    echo "# Spec" > "$archive_dir/specs/spec.md"
    echo "$state_json" > "$archive_dir/state.json"
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

# Assert current phase equals expected
assert_phase_equals() {
    local change="$1"
    local expected_phase="$2"
    
    local actual
    actual=$("$LIB_DIR/osx" state "$change" get 2>/dev/null | jq -r '.phase')
    
    if [[ "$actual" != "$expected_phase" ]]; then
        echo "Expected phase to be '$expected_phase', got '$actual'"
        return 1
    fi
}

# Assert change is marked complete
assert_change_complete() {
    local change="$1"
    
    if [[ ! -f "openspec/changes/$change/complete.json" ]]; then
        echo "Change '$change' is not complete (complete.json missing)"
        return 1
    fi
    
    local status
    status=$(jq -r '.status' "openspec/changes/$change/complete.json")
    
    if [[ "$status" != "COMPLETE" ]]; then
        echo "Change '$change' status is '$status', expected 'COMPLETE'"
        return 1
    fi
}

# Setup a complete change with all artifacts
setup_full_change() {
    local change="${1:-test-change}"
    local change_dir="openspec/changes/$change"
    
    mkdir -p "$change_dir/specs"
    
    echo "# Proposal for $change" > "$change_dir/proposal.md"
    echo "# Design for $change" > "$change_dir/design.md"
    echo "# Tasks for $change" > "$change_dir/tasks.md"
    echo "# Spec for $change" > "$change_dir/specs/spec.md"
    
    cat > "$change_dir/state.json" <<EOF
{
  "phase": "PHASE0",
  "iteration": 0,
  "phase_complete": false
}
EOF
}

# Run through all phases from PHASE0 to COMPLETE
run_full_phase_cycle() {
    local change="$1"
    
    for phase in PHASE0 PHASE1 PHASE2 PHASE3 PHASE4 PHASE5 PHASE6; do
        "$LIB_DIR/osx" state "$change" complete >/dev/null 2>&1 || true
        "$LIB_DIR/osx" phase "$change" advance >/dev/null 2>&1 || true
    done
}

# ============================================
# Install test helpers
# ============================================

OPENCODEX_BIN="$PROJECT_ROOT/bin/openspec-extended"
INSTALL_SCRIPT="$PROJECT_ROOT/install.sh"
FIXTURES_INSTALL="$FIXTURES_DIR/install"

# Setup a fake installed openspec-extended location
setup_installed_osx() {
    local prefix="${1:-$TEST_DIR/.local}"
    local install_dir="$prefix/share/openspec-extended"
    
    mkdir -p "$install_dir/resources/opencode/skills"
    mkdir -p "$install_dir/resources/opencode/agents"
    mkdir -p "$install_dir/resources/opencode/commands"
    mkdir -p "$install_dir/resources/opencode/scripts/lib"
    mkdir -p "$install_dir/openspec-core/.opencode/skills"
    mkdir -p "$install_dir/openspec-core/.opencode/commands"
    mkdir -p "$install_dir/bin"
    mkdir -p "$prefix/bin"
    
    # Copy minimal resources
    cp -r "$PROJECT_ROOT/resources/opencode/skills"/* "$install_dir/resources/opencode/skills/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/resources/opencode/agents"/* "$install_dir/resources/opencode/agents/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/resources/opencode/commands"/* "$install_dir/resources/opencode/commands/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/resources/opencode/scripts"/* "$install_dir/resources/opencode/scripts/" 2>/dev/null || true
    
    # Copy openspec-extended binary
    cp "$OPENCODEX_BIN" "$install_dir/bin/openspec-extended"
    chmod +x "$install_dir/bin/openspec-extended"
    
    # Create symlink
    ln -sf "$install_dir/bin/openspec-extended" "$prefix/bin/openspec-extended"
    
    echo "$prefix"
}

# Create a minimal test tarball for install.sh tests
create_test_tarball() {
    local output="$1"
    local temp_dir
    temp_dir=$(mktemp -d)
    
    local pkg_dir="$temp_dir/OpenSpec-extended-test"
    mkdir -p "$pkg_dir/bin"
    mkdir -p "$pkg_dir/resources/opencode/skills/test-skill"
    mkdir -p "$pkg_dir/resources/opencode/agents"
    mkdir -p "$pkg_dir/resources/opencode/commands"
    mkdir -p "$pkg_dir/resources/opencode/scripts"
    mkdir -p "$pkg_dir/openspec-core/.opencode/skills"
    
    # Minimal openspec-extended
    cat > "$pkg_dir/bin/openspec-extended" << 'EOF'
#!/usr/bin/env bash
echo "openspec-extended test"
EOF
    chmod +x "$pkg_dir/bin/openspec-extended"
    
    # Minimal skill
    echo "# Test Skill" > "$pkg_dir/resources/opencode/skills/test-skill/SKILL.md"
    
    # Minimal manifest
    echo '{"version":"0.0.0-test"}' > "$pkg_dir/resources/opencode/manifest.json"
    
    # Create tarball
    tar -czf "$output" -C "$temp_dir" "OpenSpec-extended-test"
    
    rm -rf "$temp_dir"
}

# Run openspec-extended with test environment
run_osx() {
    run "$OPENCODEX_BIN" "$@"
}

# Assert directory exists
assert_dir_exists() {
    local path="$1"
    
    if [[ ! -d "$path" ]]; then
        echo "Expected directory to exist: $path"
        return 1
    fi
}

# Assert file exists
assert_file_exists() {
    local path="$1"
    
    if [[ ! -f "$path" ]]; then
        echo "Expected file to exist: $path"
        return 1
    fi
}

# Assert file is executable
assert_executable() {
    local path="$1"
    
    if [[ ! -x "$path" ]]; then
        echo "Expected file to be executable: $path"
        return 1
    fi
}

# Assert symlink points to target
assert_symlink_to() {
    local link="$1"
    local target="$2"
    
    if [[ ! -L "$link" ]]; then
        echo "Expected symlink: $link"
        return 1
    fi
    
    local resolved
    resolved=$(readlink -f "$link")
    
    if [[ "$resolved" != *"$target"* ]]; then
        echo "Expected symlink $link to point to $target, got $resolved"
        return 1
    fi
}

# Mock opencode run command for testing
# Usage: setup_mock_opencode <temp_dir>
# Creates a mock opencode binary that simulates agent output
setup_mock_opencode() {
    local mock_dir="$1"
    mkdir -p "$mock_dir"
    
    cat > "$mock_dir/opencode" << 'EOF'
#!/bin/bash
# Mock opencode for testing orchestration logging

if [[ "$1" == "run" ]]; then
    shift
    
    # Simulate successful agent run with typical output
    echo "> osx-builder · glm-5"
    echo "I'll process the request..."
    echo "→ Read proposal.md"
    echo "→ Read design.md"
    echo "→ Glob specs/*.md"
    echo "✓ Task complete"
    exit 0
elif [[ "$1" == "version" ]]; then
    echo "opencode 1.0.0-mock"
    exit 0
elif [[ "$1" == "help" ]] || [[ "$1" == "--help" ]]; then
    echo "Mock opencode for testing"
    exit 0
else
    # For other commands, just exit success
    exit 0
fi
EOF
    chmod +x "$mock_dir/opencode"
    
    # Prepend to PATH so mock is found first
    export PATH="$mock_dir:$PATH"
}

# Mock git for testing archive operations
# Usage: setup_mock_git <temp_dir>
# Creates a minimal git mock that handles essential operations
setup_mock_git() {
    local mock_dir="$1"
    mkdir -p "$mock_dir"
    
    cat > "$mock_dir/git" << 'EOF'
#!/bin/bash
# Minimal git mock for testing orchestration logging

# Handle essential git operations
case "$1" in
    init)
        # Git init - no-op in test env
        exit 0
        ;;
    config)
        # Git config - no-op in test env
        shift
        exit 0
        ;;
    add)
        # Git add - no-op (files already tracked)
        exit 0
        ;;
    commit|--amend)
        # Git commit - no-op (simulate success)
        exit 0
        ;;
    rev-parse)
        # Return mock values for rev-parse
        case "$2" in
            --is-inside-work-tree)
                echo "true"
                ;;
            HEAD)
                echo "abc123def456"
                ;;
            *)
                exit 0
                ;;
        esac
        ;;
    branch|--show-current)
        echo "test-branch"
        exit 0
        ;;
    status|--porcelain)
        # Return clean status
        exit 0
        ;;
    diff|--quiet|--cached)
        # Return clean status (no changes)
        exit 0
        ;;
    *)
        # Other operations - minimal response
        exit 0
        ;;
esac
EOF
    chmod +x "$mock_dir/git"
    
    # Prepend to PATH so mock is found first
    export PATH="$mock_dir:$PATH"
}
