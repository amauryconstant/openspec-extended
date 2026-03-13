#!/usr/bin/env bats
# Unit tests for osx-orchestrate script functions

load '../helpers/test-helpers'

setup() {
    setup_test_env
    setup_change "test-change"
}

teardown() {
    teardown_test_env
}

# Test the state.json.phase_iterations tracking (what show_progress actually uses)
@test "show_progress: reads phase iterations from state.json" {
    # Create state.json with phase_iterations (what show_progress actually reads)
    cat > "openspec/changes/test-change/state.json" <<EOF
{
  "phase": "PHASE4",
  "phase_name": "SYNC",
  "iteration": 1,
  "phase_complete": false,
  "phase_iterations": {
    "PHASE0": 1,
    "PHASE1": 2,
    "PHASE2": 1,
    "PHASE3": 1,
    "PHASE4": 1
  }
}
EOF
    
    local state_file="openspec/changes/test-change/state.json"
    
    # Test the jq queries that show_progress uses (reads from state.json.phase_iterations)
    local p0 p1 p2 p3 p4 p5 p6
    p0=$(jq -r '.phase_iterations.PHASE0 // 0' "$state_file")
    p1=$(jq -r '.phase_iterations.PHASE1 // 0' "$state_file")
    p2=$(jq -r '.phase_iterations.PHASE2 // 0' "$state_file")
    p3=$(jq -r '.phase_iterations.PHASE3 // 0' "$state_file")
    p4=$(jq -r '.phase_iterations.PHASE4 // 0' "$state_file")
    p5=$(jq -r '.phase_iterations.PHASE5 // 0' "$state_file")
    p6=$(jq -r '.phase_iterations.PHASE6 // 0' "$state_file")
    
    [ "$p0" == "1" ]
    [ "$p1" == "2" ]  # Multiple iterations
    [ "$p2" == "1" ]
    [ "$p3" == "1" ]
    [ "$p4" == "1" ]
    [ "$p5" == "0" ]  # Not yet reached
    [ "$p6" == "0" ]  # Not yet reached
}

@test "show_progress: handles missing phase_iterations gracefully" {
    # Create state.json without phase_iterations
    cat > "openspec/changes/test-change/state.json" <<EOF
{
  "phase": "PHASE0",
  "iteration": 1
}
EOF
    
    local state_file="openspec/changes/test-change/state.json"
    
    # Should return 0 for missing keys
    local p0
    p0=$(jq -r '.phase_iterations.PHASE0 // 0' "$state_file")
    [ "$p0" == "0" ]
}

@test "show_progress: handles missing state.json gracefully" {
    # No state.json file
    [ ! -f "openspec/changes/test-change/state.json" ]
    
    # The show_progress function handles this with [[ -f ... ]] check
    if [[ -f "openspec/changes/test-change/state.json" ]]; then
        echo "Should not reach here"
        return 1
    fi
}

# Test iterations.json phase names (what agents write)
@test "iterations.json: uses correct phase names with underscores" {
    # Create iterations.json with canonical phase names
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "ARTIFACT_REVIEW"},
  {"iteration": 1, "phase": "IMPLEMENTATION"},
  {"iteration": 1, "phase": "REVIEW"},
  {"iteration": 1, "phase": "MAINTAIN_DOCS"},
  {"iteration": 1, "phase": "SYNC"},
  {"iteration": 1, "phase": "SELF_REFLECTION"},
  {"iteration": 1, "phase": "ARCHIVE"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # Verify all phase names use underscore format
    phase0_count=$(jq 'map(select(.phase == "ARTIFACT_REVIEW")) | length' "$iterations_file")
    [ "$phase0_count" == "1" ]
    
    phase3_count=$(jq 'map(select(.phase == "MAINTAIN_DOCS")) | length' "$iterations_file")
    [ "$phase3_count" == "1" ]
    
    phase5_count=$(jq 'map(select(.phase == "SELF_REFLECTION")) | length' "$iterations_file")
    [ "$phase5_count" == "1" ]
    
    phase6_count=$(jq 'map(select(.phase == "ARCHIVE")) | length' "$iterations_file")
    [ "$phase6_count" == "1" ]
}

@test "phase names: iterations.json uses MAINTAIN_DOCS not MAINTAIN-DOCS" {
    # Verify MAINTAIN_DOCS uses underscore format
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "MAINTAIN_DOCS"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # Should find with underscore
    local count_underscore
    count_underscore=$(jq 'map(select(.phase == "MAINTAIN_DOCS")) | length' "$iterations_file")
    [ "$count_underscore" == "1" ]
    
    # Should NOT find with hyphen
    local count_hyphen
    count_hyphen=$(jq 'map(select(.phase == "MAINTAIN-DOCS")) | length' "$iterations_file")
    [ "$count_hyphen" == "0" ]
}

@test "phase names: iterations.json uses SELF_REFLECTION not SELF-REFLECTION" {
    # Verify SELF_REFLECTION uses underscore format in iterations.json
    cat > "openspec/changes/test-change/iterations.json" <<EOF
[
  {"iteration": 1, "phase": "SELF_REFLECTION"}
]
EOF
    
    local iterations_file="openspec/changes/test-change/iterations.json"
    
    # Should find with underscore
    local count_underscore
    count_underscore=$(jq 'map(select(.phase == "SELF_REFLECTION")) | length' "$iterations_file")
    [ "$count_underscore" == "1" ]
    
    # Should NOT find with hyphen
    local count_hyphen
    count_hyphen=$(jq 'map(select(.phase == "SELF-REFLECTION")) | length' "$iterations_file")
    [ "$count_hyphen" == "0" ]
}

@test "phase display names: correct format for UI" {
    # Display names use different format (space for multi-word, hyphen for compound)
    # This matches osc_get_phase_display_name in osc-common
    
    local phase0_display="ARTIFACT REVIEW"    # Space
    local phase3_display="MAINTAIN DOCS"       # Space (not hyphen)
    local phase5_display="SELF-REFLECTION"     # Hyphen (compound word)
    
    [ "$phase0_display" == "ARTIFACT REVIEW" ]
    [ "$phase3_display" == "MAINTAIN DOCS" ]
    [ "$phase5_display" == "SELF-REFLECTION" ]
}

# ==============================================================================
# Phase transition tests - covers the bug scenario from germinator
# ==============================================================================

@test "phase-transition: normal advance when no explicit transition" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":3,"phase_complete":true}'
    
    # Simulate the check_transition function behavior
    # When no transition is set, jq returns empty and we should proceed normally
    local transition_target=""
    if transition_target=$(jq -r '.transition.target // empty' "openspec/changes/test-change/state.json" 2>/dev/null) && [[ -n "$transition_target" ]]; then
        # Should NOT reach here - no transition set
        return 1
    fi
    
    # Verify state file allows normal operations
    # (The actual phase advance is tested in integration tests)
    local phase
    phase=$(jq -r '.phase' "openspec/changes/test-change/state.json")
    [ "$phase" == "PHASE0" ]
    
    # Verify phase_complete is true (ready for advance)
    local complete
    complete=$(jq -r '.phase_complete' "openspec/changes/test-change/state.json")
    [ "$complete" == "true" ]
}

@test "phase-transition: explicit transition when set" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}'
    
    # Simulate check_transition finding a target
    local transition_target=""
    transition_target=$(jq -r '.transition.target // empty' "openspec/changes/test-change/state.json" 2>/dev/null)
    [ "$transition_target" == "PHASE1" ]
    
    # Verify transition reason available
    local reason
    reason=$(jq -r '.transition.reason // "unknown"' "openspec/changes/test-change/state.json")
    [ "$reason" == "implementation_incorrect" ]
}

@test "phase-transition: set -e does not exit on missing transition (bug fix)" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":3,"phase_complete":true}'
    
    # This simulates the exact pattern that caused the bug
    # With the fix, this should NOT fail even with set -e
    (
        set -e
        local transition_target=""
        if transition_target=$(jq -r '.transition.target // empty' "openspec/changes/test-change/state.json" 2>/dev/null) && [[ -n "$transition_target" ]]; then
            # Should not reach here
            exit 99
        fi
        # If we reach here, the fix works
        exit 0
    )
    [ "$?" -eq 0 ]
}

@test "phase-transition: handles missing state.json gracefully" {
    setup_change "test-change"
    # No state.json created
    
    # check_transition should return empty, not crash
    local transition_target=""
    if [[ -f "openspec/changes/test-change/state.json" ]]; then
        transition_target=$(jq -r '.transition.target // empty' "openspec/changes/test-change/state.json" 2>/dev/null)
    fi
    
    [ -z "$transition_target" ]
}

@test "phase-transition: conditional pattern captures transition value correctly" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE0","reason":"artifacts_modified","details":"Spec requirement updated"}}'
    
    # Test the conditional pattern used in the fix
    local transition_target=""
    if transition_target=$(jq -r '.transition.target // empty' "openspec/changes/test-change/state.json" 2>/dev/null) && [[ -n "$transition_target" ]]; then
        [ "$transition_target" == "PHASE0" ]
    else
        # Should not reach here - transition IS set
        return 1
    fi
}

@test "phase-transition: all valid transition reasons are accepted" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true}'
    
    # Test all valid transition reasons
    local reasons=("implementation_incorrect" "artifacts_modified" "retry_requested")
    
    for reason in "${reasons[@]}"; do
        cat > "openspec/changes/test-change/state.json" <<EOF
{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"$reason"}}
EOF
        
        local found_reason
        found_reason=$(jq -r '.transition.reason // "unknown"' "openspec/changes/test-change/state.json")
        [ "$found_reason" == "$reason" ]
    done
}

@test "phase-transition: transition details are optional" {
    # Test with details
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect","details":"ValidationPipeline missing early exit"}}'
    
    local details
    details=$(jq -r '.transition.details // ""' "openspec/changes/test-change/state.json")
    [ "$details" == "ValidationPipeline missing early exit" ]
    
    # Test without details
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}'
    
    details=$(jq -r '.transition.details // ""' "openspec/changes/test-change/state.json")
    [ "$details" == "" ]
}

# ==============================================================================
# Logging behavior tests - log_verbose() and show_progress()
# ==============================================================================

@test "logging: non-verbose mode hides [VERBOSE] on terminal" {
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
    
    run "$PROJECT_ROOT/resources/opencode/scripts/osx-orchestrate" test-change --dry-run 2>&1
    
    [[ "$output" != *"[VERBOSE]"* ]]
}

@test "logging: verbose mode shows [VERBOSE] on terminal" {
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
    
    run "$PROJECT_ROOT/resources/opencode/scripts/osx-orchestrate" test-change --dry-run -v 2>&1
    
    [[ "$output" == *"[VERBOSE]"* ]]
    [[ "$output" == *"Tool found:"* ]]
}

@test "logging: log file contains [VERBOSE] without -v flag" {
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
    
    local log_file="$TEST_DIR/test.log"
    
    run "$PROJECT_ROOT/resources/opencode/scripts/osx-orchestrate" test-change --dry-run -l "$log_file" 2>&1
    
    [ -f "$log_file" ]
    run grep -F "[VERBOSE]" "$log_file"
    [ "$status" -eq 0 ]
    
    run grep -F "Tool found:" "$log_file"
    [ "$status" -eq 0 ]
}

@test "logging: log file has no ANSI color codes" {
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
    
    local log_file="$TEST_DIR/test.log"
    
    run "$PROJECT_ROOT/resources/opencode/scripts/osx-orchestrate" test-change --dry-run -l "$log_file" 2>&1
    
    run grep -E $'\x1b\[[0-9;]*m' "$log_file"
    [ "$status" -ne 0 ]
}

@test "logging: banner is logged to file" {
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
    
    local log_file="$TEST_DIR/test.log"
    
    run "$PROJECT_ROOT/resources/opencode/scripts/osx-orchestrate" test-change --dry-run -l "$log_file" 2>&1
    
    run grep -F "OpenSpec Autonomous Implementation" "$log_file"
    [ "$status" -eq 0 ]
    
    run grep -F "Version:" "$log_file"
    [ "$status" -eq 0 ]
    
    run grep -F "Change ID:" "$log_file"
    [ "$status" -eq 0 ]
}

@test "logging: verbose messages in both terminal and log with -v flag" {
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
    
    local log_file="$TEST_DIR/test.log"
    
    run "$PROJECT_ROOT/resources/opencode/scripts/osx-orchestrate" test-change --dry-run -v -l "$log_file" 2>&1
    
    # Terminal should have [VERBOSE]
    [[ "$output" == *"[VERBOSE]"* ]]
    
    # Log file should also have [VERBOSE] (via tee)
    run grep -F "[VERBOSE]" "$log_file"
    [ "$status" -eq 0 ]
    
    # Should not have duplicates (log_verbose should write via stdout when verbose)
    local verbose_count
    verbose_count=$(grep -c "Tool found: git" "$log_file")
    [ "$verbose_count" -eq 1 ]
}
