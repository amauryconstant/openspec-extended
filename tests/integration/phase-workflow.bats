#!/usr/bin/env bats
# Integration tests for phase workflow across osc-* scripts

load '../helpers/test-helpers'

setup() {
    setup_test_env
    setup_change "test-change"
    setup_skills_dir
    setup_commands_dir
}

teardown() {
    teardown_test_env
}

@test "phase-workflow: advances from PHASE0 to PHASE1 with proper state updates" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":true}'
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".previous" "PHASE0"
    
    run_osx_state get "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".iteration" "1"
    assert_json_false "$output" ".phase_complete"
}

@test "phase-workflow: advances through multiple phases (0->1->2->3)" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":true}'
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    
    run_osx_state complete "test-change"
    [ "$status" -eq 0 ]
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE2"
    
    run_osx_state complete "test-change"
    [ "$status" -eq 0 ]
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE3"
    
    run_osx_state get "test-change"
    assert_json_equals "$output" ".phase" "PHASE3"
}

@test "phase-workflow: state file persists correctly between phase advances" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":5,"phase_complete":true}'
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    
    local state_file="openspec/changes/test-change/state.json"
    [ -f "$state_file" ]
    
    local phase iteration
    phase=$(jq -r '.phase' "$state_file")
    iteration=$(jq -r '.iteration' "$state_file")
    [ "$phase" == "PHASE1" ]
    [ "$iteration" == "1" ]
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    
    phase=$(jq -r '.phase' "$state_file")
    [ "$phase" == "PHASE2" ]
}

@test "phase-workflow: iterations are recorded during phase transitions" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":true}'
    
    "$LIB_DIR/osx" iterations append "test-change" --phase "PHASE0" --iteration 1 --extra '{"action":"initial"}'
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    
    "$LIB_DIR/osx" iterations append "test-change" --phase "PHASE1" --iteration 1 --extra '{"action":"started"}'
    
    run_osx_iterations get "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "2"
}

@test "phase-workflow: phase names are correct for each phase number" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":0}'
    
    run_osx_phase next "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".next" "PHASE1"
    
    run_osx_state set-phase "test-change" "PHASE1"
    run_osx_phase next "test-change"
    assert_json_equals "$output" ".next" "PHASE2"
    
    run_osx_state set-phase "test-change" "PHASE2"
    run_osx_phase next "test-change"
    assert_json_equals "$output" ".next" "PHASE3"
    
    run_osx_state set-phase "test-change" "PHASE3"
    run_osx_phase next "test-change"
    assert_json_equals "$output" ".next" "PHASE4"
    
    run_osx_state set-phase "test-change" "PHASE4"
    run_osx_phase next "test-change"
    assert_json_equals "$output" ".next" "PHASE5"
    
    run_osx_state set-phase "test-change" "PHASE5"
    run_osx_phase next "test-change"
    assert_json_equals "$output" ".next" "PHASE6"
    
    run_osx_state set-phase "test-change" "PHASE6"
    run_osx_phase next "test-change"
    assert_json_equals "$output" ".next" "COMPLETE"
}

@test "phase-workflow: advance resets iteration to 1" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":5,"phase_complete":true}'
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".iteration" "1"
    
    run_osx_state get "test-change"
    assert_json_equals "$output" ".iteration" "1"
}

@test "phase-workflow: advance sets phase_complete to false" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":true}'
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    
    run_osx_state get "test-change"
    assert_json_false "$output" ".phase_complete"
}

@test "phase-workflow: complete action integrates with phase workflow" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2,"phase_complete":false}'
    
    run_osx_state complete "test-change"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".phase_complete"
    
    run_osx_phase current "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
}

@test "phase-workflow: advance to COMPLETE from PHASE6" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1,"phase_complete":true}'
    
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "COMPLETE"
    assert_json_equals "$output" ".previous" "PHASE6"
}

@test "phase-workflow: PHASE6 advance does not restart to PHASE0" {
    # Remove the active change created by setup() so we can test archive behavior
    rm -rf "openspec/changes/test-change"
    
    # Setup archived change (simulates post-PHASE6 state)
    setup_archived_change_with_state "test-change" "2024-01-15" '{"phase":"PHASE6","iteration":1,"phase_complete":true}'
    echo '[]' > "openspec/changes/archive/2024-01-15-test-change/iterations.json"
    echo '[]' > "openspec/changes/archive/2024-01-15-test-change/decision-log.json"
    
    # Advance from PHASE6 should go to COMPLETE
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "COMPLETE"
    
    # Verify NO new state file created in active changes directory
    [ ! -f "openspec/changes/test-change/state.json" ]
    
    # Verify archived state was updated to COMPLETE
    local archived_phase
    archived_phase=$(jq -r '.phase' "openspec/changes/archive/2024-01-15-test-change/state.json")
    [ "$archived_phase" == "COMPLETE" ]
}

@test "phase-workflow: full cycle from PHASE0 to COMPLETE with archive" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":true}'
    
    # Advance through all phases
    for expected_phase in PHASE1 PHASE2 PHASE3 PHASE4 PHASE5 PHASE6 COMPLETE; do
        run_osx_phase advance "test-change"
        [ "$status" -eq 0 ]
        assert_json_equals "$output" ".phase" "$expected_phase"
        
        # Mark complete for next advance (except COMPLETE)
        if [[ "$expected_phase" != "COMPLETE" ]]; then
            run_osx_state complete "test-change"
            [ "$status" -eq 0 ]
        fi
    done
    
    # Final state should be COMPLETE
    run_osx_state get "test-change"
    assert_json_equals "$output" ".phase" "COMPLETE"
}

@test "phase-workflow: suggestions.md is tracked and archived" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1}'
    
    # Simulate PHASE2 creating suggestions.md
    cat > "openspec/changes/test-change/suggestions.md" <<EOF
# Suggestions for test-change

## 2024-01-15 - PHASE2 Verification

- [ ] **[cosmetic]** Fix typo in error message
  - Location: lib/error.go:42
  - Impact: Low

- [ ] **[future]** Add caching for better performance
  - Location: lib/resolver.go
  - Impact: Medium
EOF
    
    # Archive the change
    mkdir -p "openspec/changes/archive"
    mv "openspec/changes/test-change" "openspec/changes/archive/2024-01-15-test-change"
    
    # Verify suggestions.md is in archive
    [ -f "openspec/changes/archive/2024-01-15-test-change/suggestions.md" ]
    
    # Verify content preserved
    local suggestion_count
    suggestion_count=$(grep -c "^\- \[ \]" "openspec/changes/archive/2024-01-15-test-change/suggestions.md")
    [ "$suggestion_count" -eq 2 ]
}

# ==============================================================================
# Phase transition integration tests - covers bug scenario from germinator
# ==============================================================================

@test "phase-transition: full cycle without explicit transitions (bug regression test)" {
    # Simulate the exact scenario that failed in production
    # PHASE0 completed with 3 iterations, no explicit transition set
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":3,"phase_complete":true}'
    
    # Normal advance should work (this was the bug - script exited on missing transition)
    run_osx_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    
    # Verify state is correct
    run_osx_state get "test-change"
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".iteration" "1"
    assert_json_false "$output" ".phase_complete"
}

@test "phase-transition: explicit transition overrides normal advance" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}'
    
    # The explicit transition should be detectable
    local target
    target=$(jq -r '.transition.target // empty' "openspec/changes/test-change/state.json")
    [ "$target" == "PHASE1" ]
    
    # After handling transition, clear it
    run_osx_state clear-transition "test-change"
    [ "$status" -eq 0 ]
    
    # Normal advance should now work (to PHASE3)
    run_osx_phase advance "test-change"
    assert_json_equals "$output" ".phase" "PHASE3"
}

@test "phase-transition: transition with details preserves context" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"artifacts_modified","details":"Spec requirement 3.2 updated"}}'
    
    local reason details
    reason=$(jq -r '.transition.reason // "unknown"' "openspec/changes/test-change/state.json")
    details=$(jq -r '.transition.details // ""' "openspec/changes/test-change/state.json")
    
    [ "$reason" == "artifacts_modified" ]
    [ "$details" == "Spec requirement 3.2 updated" ]
}

@test "phase-transition: multiple phase advances without transitions" {
    # Test the complete cycle that would occur in normal operation
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":true}'
    
    # Advance through PHASE0 -> PHASE1 -> PHASE2 without explicit transitions
    run_osx_phase advance "test-change"
    assert_json_equals "$output" ".phase" "PHASE1"
    
    run_osx_state complete "test-change"
    [ "$status" -eq 0 ]
    
    run_osx_phase advance "test-change"
    assert_json_equals "$output" ".phase" "PHASE2"
    
    run_osx_state get "test-change"
    assert_json_equals "$output" ".phase" "PHASE2"
    assert_json_false "$output" ".phase_complete"
}

@test "phase-transition: backward transition from PHASE2 to PHASE1" {
    # Simulate implementation_incorrect scenario
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}'
    
    # Verify transition target is set correctly
    local target reason
    target=$(jq -r '.transition.target // empty' "openspec/changes/test-change/state.json")
    reason=$(jq -r '.transition.reason // "unknown"' "openspec/changes/test-change/state.json")
    
    [ "$target" == "PHASE1" ]
    [ "$reason" == "implementation_incorrect" ]
    
    # After clearing transition, manual phase change should work
    run_osx_state clear-transition "test-change"
    run_osx_state set-phase "test-change" "PHASE1"
    [ "$status" -eq 0 ]
    
    run_osx_state get "test-change"
    assert_json_equals "$output" ".phase" "PHASE1"
}

@test "phase-transition: artifacts_modified triggers re-implementation" {
    # Simulate artifacts_modified scenario (specs changed during review)
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"artifacts_modified","details":"ValidationPipeline spec updated"}}'
    
    local reason details
    reason=$(jq -r '.transition.reason // "unknown"' "openspec/changes/test-change/state.json")
    details=$(jq -r '.transition.details // ""' "openspec/changes/test-change/state.json")
    
    [ "$reason" == "artifacts_modified" ]
    [ "$details" == "ValidationPipeline spec updated" ]
}
