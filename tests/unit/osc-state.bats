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

# Transition tests

@test "osc-state: transition requires target phase" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition
    [ "$status" -eq 1 ]
    assert_output_contains "missing_target"
}

@test "osc-state: transition requires reason" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition "PHASE1"
    [ "$status" -eq 1 ]
    assert_output_contains "missing_reason"
}

@test "osc-state: transition validates target phase" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition "INVALID" "implementation_incorrect"
    [ "$status" -eq 1 ]
    assert_output_contains "invalid_target"
}

@test "osc-state: transition validates reason" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition "PHASE1" "invalid_reason"
    [ "$status" -eq 1 ]
    assert_output_contains "invalid_reason"
}

@test "osc-state: transition sets phase_complete and transition object" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition "PHASE1" "implementation_incorrect"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".success"
    assert_json_equals "$output" ".transition.target" "PHASE1"
    assert_json_equals "$output" ".transition.reason" "implementation_incorrect"
}

@test "osc-state: transition with details includes details field" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition "PHASE1" "implementation_incorrect" "ValidationPipeline missing early exit"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".transition.details" "ValidationPipeline missing early exit"
}

@test "osc-state: transition persists to file" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition "PHASE1" "artifacts_modified" "Spec updated"
    [ "$status" -eq 0 ]
    
    local phase_complete transition_target transition_reason
    phase_complete=$(jq -r '.phase_complete' "openspec/changes/test-change/state.json")
    transition_target=$(jq -r '.transition.target' "openspec/changes/test-change/state.json")
    transition_reason=$(jq -r '.transition.reason' "openspec/changes/test-change/state.json")
    
    [ "$phase_complete" == "true" ]
    [ "$transition_target" == "PHASE1" ]
    [ "$transition_reason" == "artifacts_modified" ]
}

@test "osc-state: transition accepts all valid reasons" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":false}'
    
    run_osc_state "test-change" transition "PHASE1" "implementation_incorrect"
    [ "$status" -eq 0 ]
    
    run_osc_state "test-change" transition "PHASE1" "artifacts_modified"
    [ "$status" -eq 0 ]
    
    run_osc_state "test-change" transition "PHASE2" "retry_requested"
    [ "$status" -eq 0 ]
}

@test "osc-state: transition fails without state.json" {
    setup_change "test-change"
    
    run_osc_state "test-change" transition "PHASE1" "implementation_incorrect"
    [ "$status" -eq 1 ]
    assert_output_contains "state_not_found"
}

@test "osc-state: clear-transition removes transition field" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}'
    
    run_osc_state "test-change" clear-transition
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".success"
    assert_json_true "$output" ".transition_cleared"
    
    # Verify transition removed from file
    local has_transition
    has_transition=$(jq 'has("transition")' "openspec/changes/test-change/state.json")
    [ "$has_transition" == "false" ]
}

@test "osc-state: clear-transition succeeds even without transition field" {
    setup_change_with_state "test-change" '{"phase":"PHASE2","iteration":1,"phase_complete":true}'
    
    run_osc_state "test-change" clear-transition
    [ "$status" -eq 0 ]
}

@test "osc-state: clear-transition fails without state.json" {
    setup_change "test-change"
    
    run_osc_state "test-change" clear-transition
    [ "$status" -eq 1 ]
    assert_output_contains "state_not_found"
}
