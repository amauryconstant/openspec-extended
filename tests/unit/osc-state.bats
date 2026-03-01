#!/usr/bin/env bats
# Unit tests for osc-state

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

@test "osc-state: missing change argument shows usage error" {
    run_osc_state
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-state: nonexistent change returns error" {
    run_osc_state "nonexistent-change" get
    [ "$status" -eq 1 ]
    assert_output_contains "change_not_found"
}

@test "osc-state: get without state.json returns error" {
    setup_change "test-change"
    
    run_osc_state "test-change" get
    [ "$status" -eq 1 ]
    assert_output_contains "state_not_found"
}

@test "osc-state: get returns correct state" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2,"phase_complete":false}'
    
    run_osc_state "test-change" get
    [ "$status" -eq 0 ]
    
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".iteration" "2"
    assert_json_false "$output" ".phase_complete"
}

@test "osc-state: get with phase_complete true" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":true}'
    
    run_osc_state "test-change" get
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".phase_complete"
}

@test "osc-state: set-phase requires phase value" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1}'
    
    run_osc_state "test-change" set-phase
    [ "$status" -eq 1 ]
    assert_output_contains "missing_value"
}

@test "osc-state: set-phase updates phase" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" set-phase "PHASE1"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    assert_json_equals "$output" ".previous_phase" "PHASE0"
    assert_json_true "$output" ".success"
}

@test "osc-state: set-phase persists to file" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1}'
    
    run_osc_state "test-change" set-phase "PHASE2"
    [ "$status" -eq 0 ]
    
    # Verify file was updated
    local updated_phase
    updated_phase=$(jq -r '.phase' "openspec/changes/test-change/state.json")
    [ "$updated_phase" == "PHASE2" ]
}

@test "osc-state: set-phase fails without state.json" {
    setup_change "test-change"
    
    run_osc_state "test-change" set-phase "PHASE1"
    [ "$status" -eq 1 ]
    assert_output_contains "state_not_found"
}

@test "osc-state: complete sets phase_complete to true" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2,"phase_complete":false}'
    
    run_osc_state "test-change" complete
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".success"
    assert_json_true "$output" ".phase_complete"
}

@test "osc-state: complete persists to file" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2,"phase_complete":false}'
    
    run_osc_state "test-change" complete
    [ "$status" -eq 0 ]
    
    local complete
    complete=$(jq -r '.phase_complete' "openspec/changes/test-change/state.json")
    [ "$complete" == "true" ]
}

@test "osc-state: complete fails without state.json" {
    setup_change "test-change"
    
    run_osc_state "test-change" complete
    [ "$status" -eq 1 ]
    assert_output_contains "state_not_found"
}

@test "osc-state: unknown action returns error" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1}'
    
    run_osc_state "test-change" invalid-action
    [ "$status" -eq 1 ]
    assert_output_contains "unknown_action"
}

@test "osc-state: get is default action" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":3,"phase_complete":false}'
    
    run_osc_state "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE2"
}

@test "osc-state: handles missing optional fields gracefully" {
    setup_change_with_state "test-change" '{"phase":"PHASE0"}'
    
    run_osc_state "test-change" get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".iteration" "0"
    assert_json_false "$output" ".phase_complete"
}
