#!/usr/bin/env bats
# Integration tests for completion workflow

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

@test "completion-workflow: osc-complete set creates complete.json" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1,"phase_complete":true}'
    
    run_osc_complete set "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".status" "COMPLETE"
    
    [ -f "openspec/changes/test-change/complete.json" ]
}

@test "completion-workflow: osc-complete check returns correct status" {
    setup_change "test-change"
    
    run_osc_complete check "test-change"
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".exists"
    
    run_osc_complete set "test-change"
    [ "$status" -eq 0 ]
    
    run_osc_complete check "test-change"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".exists"
}

@test "completion-workflow: state is marked complete via osc-state" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1,"phase_complete":false}'
    
    run_osc_state complete "test-change"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".phase_complete"
    
    run_osc_state get "test-change"
    assert_json_true "$output" ".phase_complete"
}

@test "completion-workflow: iterations.json persists after completion" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1,"phase_complete":true}'
    
    "$LIB_DIR/osc" iterations append "test-change" --phase "PHASE0" --iteration 1 --extra '{"action":"start"}'
    
    "$LIB_DIR/osc" iterations append "test-change" --phase "PHASE1" --iteration 1 --extra '{"action":"implement"}'
    
    run_osc_complete set "test-change"
    [ "$status" -eq 0 ]
    
    [ -f "openspec/changes/test-change/iterations.json" ]
    
    run_osc_iterations get "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "2"
}

@test "completion-workflow: full completion flow with all artifacts" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1,"phase_complete":true}'
    
    run_osc_state complete "test-change"
    [ "$status" -eq 0 ]
    
    run_osc_complete set "test-change" "COMPLETE"
    [ "$status" -eq 0 ]
    
    run_osc_complete get "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".status" "COMPLETE"
    assert_json_false "$output" ".with_blocker"
}

@test "completion-workflow: completion with blocker records reason" {
    setup_change_with_state "test-change" '{"phase":"PHASE6","iteration":1,"phase_complete":true}'
    
    run_osc_complete set "test-change" "BLOCKED" --blocker-reason "Tests failed in CI"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".with_blocker"
    assert_json_equals "$output" ".blocker_reason" "Tests failed in CI"
    
    run_osc_complete get "test-change"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".with_blocker"
    assert_json_equals "$output" ".blocker_reason" "Tests failed in CI"
}
