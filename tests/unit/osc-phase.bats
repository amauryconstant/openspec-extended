#!/usr/bin/env bats
# Unit tests for osc-phase

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# Usage/Errors

@test "osc-phase: missing arguments shows usage error" {
    run_osc_phase
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-phase: nonexistent change returns error" {
    run_osc_phase "nonexistent-change" current
    [ "$status" -eq 1 ]
    assert_output_contains "change_not_found"
}

@test "osc-phase: unknown action returns error" {
    setup_change "test-change"
    
    run_osc_phase "test-change" invalid-action
    [ "$status" -eq 1 ]
    assert_output_contains "unknown_action"
}

# current action

@test "osc-phase: current returns phase info" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2}'
    
    run_osc_phase "test-change" current
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".next" "PHASE2"
    assert_json_equals "$output" ".iteration" "2"
}

@test "osc-phase: current creates initial state when missing" {
    setup_change "test-change"
    
    run_osc_phase "test-change" current
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE0"
    assert_json_equals "$output" ".iteration" "1"
    
    [ -f "openspec/changes/test-change/state.json" ]
}

@test "osc-phase: current fails with missing phase field" {
    setup_change_with_state "test-change" '{"iteration":1}'
    
    run_osc_phase "test-change" current
    [ "$status" -eq 1 ]
    assert_output_contains "invalid_state"
}

# next action

@test "osc-phase: next returns PHASE1 from PHASE0" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1}'
    
    run_osc_phase "test-change" next
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".next" "PHASE1"
}

@test "osc-phase: next returns PHASE2 from PHASE1" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":1}'
    
    run_osc_phase "test-change" next
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".next" "PHASE2"
}

@test "osc-phase: next returns COMPLETE from PHASE6" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1}'
    
    run_osc_phase "test-change" next
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".next" "COMPLETE"
}

@test "osc-phase: next creates initial state when missing" {
    setup_change "test-change"
    
    run_osc_phase "test-change" next
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".next" "PHASE1"
    
    [ -f "openspec/changes/test-change/state.json" ]
}

@test "osc-phase: next returns PHASE3 from PHASE2" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1}'
    
    run_osc_phase "test-change" next
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".next" "PHASE3"
}

# advance action

@test "osc-phase: advance updates state.json" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":3,"phase_complete":true}'
    
    run_osc_phase "test-change" advance
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".previous" "PHASE0"
    assert_json_equals "$output" ".next" "PHASE2"
    assert_json_equals "$output" ".iteration" "1"
    
    local updated_phase updated_iteration
    updated_phase=$(jq -r '.phase' "openspec/changes/test-change/state.json")
    updated_iteration=$(jq -r '.iteration' "openspec/changes/test-change/state.json")
    [ "$updated_phase" == "PHASE1" ]
    [ "$updated_iteration" == "1" ]
}

@test "osc-phase: advance returns previous/next info" {
    setup_change_with_state "test-change" '{"phase":"PHASE3","iteration":2}'
    
    run_osc_phase "test-change" advance
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE4"
    assert_json_equals "$output" ".previous" "PHASE3"
    assert_json_equals "$output" ".next" "PHASE5"
}

@test "osc-phase: advance creates initial state when missing" {
    setup_change "test-change"
    
    run_osc_phase "test-change" advance
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".previous" "PHASE0"
    
    [ -f "openspec/changes/test-change/state.json" ]
}

@test "osc-phase: advance from PHASE6 goes to COMPLETE" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1}'
    
    run_osc_phase "test-change" advance
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "COMPLETE"
    assert_json_equals "$output" ".previous" "PHASE6"
    assert_json_equals "$output" ".next" "COMPLETE"
}
