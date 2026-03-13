#!/usr/bin/env bats
# Integration tests for full change lifecycle

load '../helpers/test-helpers'

setup() {
    setup_test_env
    setup_change "lifecycle-test"
    setup_skills_dir
    setup_commands_dir
}

teardown() {
    teardown_test_env
}

@test "change-lifecycle: create change -> advance phases -> complete" {
    setup_change_with_state "lifecycle-test" '{"phase":"PHASE0","iteration":0,"phase_complete":false}'
    
    run_osx_phase current "lifecycle-test"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE0"
    
    run_osx_state complete "lifecycle-test"
    [ "$status" -eq 0 ]
    
    run_osx_phase advance "lifecycle-test"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    
    run_osx_state complete "lifecycle-test"
    run_osx_phase advance "lifecycle-test"
    assert_json_equals "$output" ".phase" "PHASE2"
    
    run_osx_state complete "lifecycle-test"
    run_osx_phase advance "lifecycle-test"
    assert_json_equals "$output" ".phase" "PHASE3"
    
    run_osx_state complete "lifecycle-test"
    run_osx_phase advance "lifecycle-test"
    assert_json_equals "$output" ".phase" "PHASE4"
    
    run_osx_state complete "lifecycle-test"
    run_osx_phase advance "lifecycle-test"
    assert_json_equals "$output" ".phase" "PHASE5"
    
    run_osx_state complete "lifecycle-test"
    run_osx_phase advance "lifecycle-test"
    assert_json_equals "$output" ".phase" "PHASE6"
    
    run_osx_state complete "lifecycle-test"
    run_osx_phase advance "lifecycle-test"
    assert_json_equals "$output" ".phase" "COMPLETE"
    
    run_osx_complete set "lifecycle-test"
    [ "$status" -eq 0 ]
    
    run_osx_complete check "lifecycle-test"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".exists"
}

@test "change-lifecycle: context aggregation across full lifecycle" {
    setup_change_with_state "lifecycle-test" '{"phase":"PHASE1","iteration":2,"phase_complete":false}'
    
    "$LIB_DIR/osx" iterations append "lifecycle-test" --phase "PHASE0" --iteration 1 --extra '{"notes":"review"}'
    
    "$LIB_DIR/osx" iterations append "lifecycle-test" --phase "PHASE1" --iteration 1 --extra '{"notes":"implement"}'
    
    run_osx_ctx "lifecycle-test"
    [ "$status" -eq 0 ]
    
    assert_json_equals "$output" ".change" "lifecycle-test"
    assert_json_equals "$output" ".state.phase" "PHASE1"
    assert_json_true "$output" ".artifacts.proposal.exists"
    assert_json_true "$output" ".artifacts.design.exists"
    assert_json_true "$output" ".artifacts.tasks.exists"
    assert_json_equals "$output" ".history.iterations_recorded" "2"
}

@test "change-lifecycle: archive workflow creates archive directory" {
    setup_change_with_state "lifecycle-test" '{"phase":"PHASE6","iteration":1,"phase_complete":true}'
    
    run_osx_complete set "lifecycle-test"
    [ "$status" -eq 0 ]
    
    setup_archive "lifecycle-test" "2024-01-15"
    
    [ -d "openspec/changes/archive" ]
    [ -d "openspec/changes/archive/2024-01-15-lifecycle-test" ]
}

@test "change-lifecycle: multiple changes can coexist independently" {
    setup_change "change-alpha"
    setup_change "change-beta"
    
    setup_change_with_state "change-alpha" '{"phase":"PHASE1","iteration":1}'
    setup_change_with_state "change-beta" '{"phase":"PHASE3","iteration":2}'
    
    run_osx_phase current "change-alpha"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE1"
    
    run_osx_phase current "change-beta"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE3"
    
    run_osx_phase advance "change-alpha"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".phase" "PHASE2"
    
    run_osx_phase current "change-beta"
    assert_json_equals "$output" ".phase" "PHASE3"
}
