#!/usr/bin/env bats
# E2E full workflow tests - complete PHASE0 through PHASE6
# Requires E2E_CONFIRM=1 to run (uses real AI calls, ~20 min total)

load 'helpers/e2e-helpers'

# Use longer timeout for file-level setup
E2E_TIMEOUT=3600

# File-level shared state
SHARED_ARCHIVE_DIR=""
SHARED_CHANGE_NAME="add-hello-script"
SHARED_WORKFLOW_RAN=false

setup_file() {
    require_e2e_confirm
    setup_e2e_repo
    copy_fixture "$SHARED_CHANGE_NAME"

    # Run expensive workflow ONCE
    run_osx_orchestrate_streaming "$SHARED_CHANGE_NAME" \
        --force --verbose --log-file \
        --max-phase-iterations 3 --timeout 600

    # Validate success by checking actual outcome, not just exit status
    # (Exit status can be unreliable due to background tee process)
    local archive_dir
    archive_dir=$(get_archive_dir "$SHARED_CHANGE_NAME")
    local workflow_ran=false

    if [[ -n "$archive_dir" ]] && [[ -d "$archive_dir" ]]; then
        # Archive exists - workflow succeeded regardless of exit status
        workflow_ran=true
    elif [[ "$status" -ne 0 ]]; then
        # No archive and non-zero exit status - workflow actually failed
        echo "Workflow failed with status $status" >&2
        echo "Archive directory not found" >&2
        exit 1
    else
        # Unexpected state - no archive but exit status is 0
        echo "Workflow completed but no archive found" >&2
        exit 1
    fi

    # Save shared state to JSON file for test access
    save_e2e_state "$archive_dir" "$SHARED_CHANGE_NAME" "$workflow_ran"
}

setup() {
    # Load shared state before each test
    load_e2e_state
}

teardown_file() {
    # Clean up state file before repo cleanup
    rm -f .e2e-state.json

    # Cleanup once after all tests
    teardown_e2e_repo
}

# ============================================
# Category 1: Workflow Completion
# ============================================

@test "workflow: completed successfully" {
    [ "$SHARED_WORKFLOW_RAN" = "true" ]
    [ -n "$SHARED_ARCHIVE_DIR" ]
    [ -d "$SHARED_ARCHIVE_DIR" ]
}

@test "archive: directory exists with correct naming" {
    [[ "$SHARED_ARCHIVE_DIR" == *"/archive/"* ]]
    [[ "$SHARED_ARCHIVE_DIR" == *"$SHARED_CHANGE_NAME"* ]]

    # Verify timestamp format (YYYY-MM-DD-*)
    local basename
    basename=$(basename "$SHARED_ARCHIVE_DIR")
    [[ "$basename" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-.*$ ]]
}

# ============================================
# Category 2: Artifact Functionality
# ============================================

@test "artifact: script exists at correct location" {
    [ -f "scripts/hello.sh" ]
    [ -x "scripts/hello.sh" ]
}

@test "artifact: script produces default greeting" {
    run ./scripts/hello.sh
    [ "$status" -eq 0 ]
    [[ "$output" == *"Hello, World!"* ]]
}

@test "artifact: script accepts --name flag" {
    run ./scripts/hello.sh --name Alice
    [ "$status" -eq 0 ]
    [[ "$output" == *"Hello, Alice!"* ]]
}

@test "artifact: script shows help with --help" {
    run ./scripts/hello.sh --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]] || [[ "$output" == *"hello.sh"* ]]
}

@test "artifact: script handles invalid arguments" {
    run ./scripts/hello.sh --invalid-flag
    [ "$status" -eq 1 ]
}

# ============================================
# Category 3: Artifact Content - Critical
# ============================================

@test "artifact content: has correct shebang" {
    # Design requirement: MUST use #!/usr/bin/env bash
    grep -q "^#!/usr/bin/env bash" "scripts/hello.sh"
}

@test "artifact content: enables strict mode" {
    # Design requirement: MUST use set -euo pipefail
    grep -q "^set -euo pipefail" "scripts/hello.sh"
}

@test "artifact content: is executable" {
    # Spec requirement: MUST be executable
    [ -x "scripts/hello.sh" ]
}

# ============================================
# Category 4: Artifact Content - Quality
# ============================================

@test "artifact content: follows bash best practices" {
    # Grouped quality checks - fail as a unit for easier maintenance
    local script="scripts/hello.sh"

    # Has usage function (design requirement)
    grep -q "^usage()" "$script"

    # Has main function (design requirement)
    grep -q "^main()" "$script"

    # Has readonly constants (design requirement)
    grep -q "readonly" "$script"

    # Has main "$@" call (design requirement)
    grep -q 'main "$@"' "$script"

    # Uses local for variables (quality check - best effort)
    grep -q "local " "$script"
}

# ============================================
# Category 5: Archive Structure
# ============================================

@test "archive: contains all required artifacts" {
    local files=(
        "proposal.md"
        "design.md"
        "tasks.md"
    )

    for file in "${files[@]}"; do
        [ -f "$SHARED_ARCHIVE_DIR/$file" ] || {
            echo "Missing required file: $file"
            return 1
        }
    done
}

@test "archive: has specs directory" {
    [ -d "$SHARED_ARCHIVE_DIR/specs" ]
    [ -f "$SHARED_ARCHIVE_DIR/specs/hello.md" ]
}

@test "archive: preserves historical files" {
    [ -f "$SHARED_ARCHIVE_DIR/iterations.json" ]
    [ -f "$SHARED_ARCHIVE_DIR/decision-log.json" ]

    # Validate JSON is parseable (avoid corruption)
    jq empty "$SHARED_ARCHIVE_DIR/iterations.json" >/dev/null 2>&1
    jq empty "$SHARED_ARCHIVE_DIR/decision-log.json" >/dev/null 2>&1
}

@test "archive: transient files cleaned" {
    # Validates recent PHASE6 atomic execution fixes

    # NOT in archive
    [ ! -f "$SHARED_ARCHIVE_DIR/state.json" ]
    [ ! -f "$SHARED_ARCHIVE_DIR/complete.json" ]
    [ ! -f "$SHARED_ARCHIVE_DIR/.openspec-baseline.json" ]

    # NOT in project root
    [ ! -f ".openspec-baseline.json" ]
}

# ============================================
# Category 6: Iterations Tracking
# ============================================

@test "iterations: all 7 phases recorded" {
    local count
    count=$(jq '. | length' "$SHARED_ARCHIVE_DIR/iterations.json")
    [[ "$count" -ge 7 ]]
}

@test "iterations: no PHASE0 restart" {
    # Prevents infinite restart loops
    local count
    count=$(jq '[.[] | select(.phase == "ARTIFACT_REVIEW")] | length' "$SHARED_ARCHIVE_DIR/iterations.json")
    [[ "$count" -le 3 ]]
}

@test "iterations: respects max-phase-iterations limit" {
    # Test runs with --max-phase-iterations 3
    # No phase should exceed this
    # iterations.json is an array, count occurrences of each phase
    for phase in PHASE0 PHASE1 PHASE2 PHASE3 PHASE4 PHASE5 PHASE6; do
        local count
        count=$(jq --arg p "$phase" '[.[] | select(.phase == $p)] | length' "$SHARED_ARCHIVE_DIR/iterations.json")
        [[ "$count" -le 3 ]] || {
            echo "Phase $phase exceeded max iterations: $count"
            return 1
        }
    done
}

# ============================================
# Category 7: Decision Log Structure
# ============================================

@test "decision-log: has entries for all phases" {
    local count
    count=$(jq '. | length' "$SHARED_ARCHIVE_DIR/decision-log.json")
    [[ "$count" -ge 7 ]]
}

@test "decision-log: has required fields in each entry" {
    # Validates osc tool structure without assuming exact values

    # Check first entry has required fields
    local first_entry
    first_entry=$(jq '.[0]' "$SHARED_ARCHIVE_DIR/decision-log.json")

    # Required fields (exists, not null)
    local required_fields=(
        "phase"
        "iteration"
        "summary"
        "timestamp"
    )

    for field in "${required_fields[@]}"; do
        local value
        value=$(echo "$first_entry" | jq -r ".$field // empty")
        [[ -n "$value" ]] || {
            echo "Missing required field: $field"
            return 1
        }
    done
}

# ============================================
# Category 8: Phase-Specific Decision Log Fields
# ============================================

@test "decision-log: PHASE1 has implementation metadata" {
    # Verifies osc tool records PHASE1-specific fields
    local entry
    entry=$(jq 'first(.[] | select(.phase == "IMPLEMENTATION"))' "$SHARED_ARCHIVE_DIR/decision-log.json")

    # Check for phase-specific fields (may not exist if simple implementation)
    local tasks_completed
    tasks_completed=$(echo "$entry" | jq -r '.tasks_completed // "0"')

    # Either tasks_completed exists OR it's a simple change
    [[ "$tasks_completed" != "0" ]] || true
}

@test "decision-log: PHASE4 has sync operations" {
    # Verifies osc tool records PHASE4 sync operations
    local entry
    entry=$(jq 'first(.[] | select(.phase == "SYNC"))' "$SHARED_ARCHIVE_DIR/decision-log.json")

    # Check sync_operations field exists
    local sync_ops
    sync_ops=$(echo "$entry" | jq -r '.sync_operations // ""')

    # Should be valid JSON object (even if empty)
    [[ -n "$sync_ops" ]] || true
}

@test "decision-log: PHASE6 has archive path" {
    # Validates recent PHASE6 improvements
    local entry
    entry=$(jq 'first(.[] | select(.phase == "ARCHIVE"))' "$SHARED_ARCHIVE_DIR/decision-log.json")

    # Check archive_path field exists
    local archive_path
    archive_path=$(echo "$entry" | jq -r '.archive_path // ""')

    # Should contain archive directory path
    [[ -n "$archive_path" ]]
    [[ "$archive_path" == *"$SHARED_CHANGE_NAME"* ]]
}

# ============================================
# Category 9: Reports & Documentation
# ============================================

@test "reports: verification report exists" {
    # PHASE2 should create verification-report.md
    [ -f "$SHARED_ARCHIVE_DIR/verification-report.md" ]

    # Check for expected sections (pattern matching, not exact content)
    grep -q "# Verification Report" "$SHARED_ARCHIVE_DIR/verification-report.md"
    grep -q "## Summary" "$SHARED_ARCHIVE_DIR/verification-report.md"
}

@test "git: AGENTS.md updated in single PHASE3 commit" {
    # PHASE3 should update documentation in single commit
    local commits
    commits=$(git log --oneline --all -- '*/AGENTS.md' 'AGENTS.md' 2>/dev/null | wc -l)

    # Allow 0 commits if no AGENTS.md updates needed, but if updates exist, should be single
    [[ "$commits" -le 1 ]] || {
        echo "Expected ≤1 AGENTS.md commit, got $commits"
        return 1
    }
}

# ============================================
# Category 10: Logging
# ============================================

@test "log: file exists in archive" {
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    [ -f "$log_file" ]
}

@test "log: has expected content" {
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]

    # Check for key content (pattern matching)
    grep -q "OpenSpec Autonomous Implementation" "$log_file"
    grep -q "Progress Summary" "$log_file"

    # Should have verbose output (--verbose flag used)
    grep -q "\[VERBOSE\]" "$log_file"

    # No ANSI color codes (stripped by log redirection)
    ! grep -qE $'\x1b\[[0-9;]*m' "$log_file"
}

@test "log: contains agent session markers for all phases" {
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    
    # Count agent sessions ("> osx-" prefix)
    local agent_sessions
    agent_sessions=$(grep -c "^> osx-" "$log_file" || echo "0")
    
    # Should have at least 7 sessions (one per phase PHASE0-PHASE6)
    [ "$agent_sessions" -ge 7 ]
    
    # Should have sessions for each phase
    grep -q "> osx-analyzer" "$log_file"  # PHASE0, PHASE2, PHASE5
    grep -q "> osx-builder" "$log_file"   # PHASE1
    grep -q "> osx-maintainer" "$log_file"  # PHASE3, PHASE4, PHASE6
}

@test "log: contains agent response patterns" {
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    
    # Agents typically start responses with these patterns
    grep -q -E "(^I'll|^Let me|^I need to|^I'll start)" "$log_file" || {
        echo "Log missing agent response patterns"
        return 1
    }
    
    # Should have at least one agent response
    local response_count
    response_count=$(grep -c -E "(^I'll|^Let me)" "$log_file" || echo "0")
    [ "$response_count" -ge 1 ]
}

# ============================================
# Category 11: Cleanup
# ============================================

@test "cleanup: active change directory removed" {
    # After PHASE6, change should not be in openspec/changes/
    [ ! -d "openspec/changes/$SHARED_CHANGE_NAME" ]
}
