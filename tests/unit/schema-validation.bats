#!/usr/bin/env bats
# Schema validation tests for all osc-* scripts
# Ensures consistent JSON output format across all scripts

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# Error schema consistency

@test "schema: osc-state error format has error and message fields" {
    run_osc_state get "nonexistent-change"
    [ "$status" -eq 1 ]
    assert_error_schema "$output"
}

@test "schema: osc-iterations error format has error and message fields" {
    run_osc_iterations get "nonexistent-change"
    [ "$status" -eq 1 ]
    assert_error_schema "$output"
}

@test "schema: osc-log error format has error and message fields" {
    run_osc_log get "nonexistent-change"
    [ "$status" -eq 1 ]
    assert_error_schema "$output"
}

@test "schema: osc-git returns valid output even without git repo" {
    setup_change "test-change"
    rm -rf .git
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    # Should return branch as "unknown" when not in git repo
    assert_json_equals "$output" ".branch" "unknown"
}

@test "schema: osc-ctx error format has error and message fields" {
    run_osc_ctx "nonexistent"
    [ "$status" -eq 1 ]
    assert_error_schema "$output"
}

@test "schema: osc-validate error format has error and message fields" {
    # osc validate returns {"valid": false, "errors": [...]} format, not {"error": "...", "message": "..."}
    run_osc_validate change-dir "nonexistent-change"
    [ "$status" -eq 1 ]
    # Check for valid=false format instead of error/message format
    if ! echo "$output" | jq -e '.valid == false' &>/dev/null; then
        echo "Expected valid=false, got: $output"
        return 1
    fi
}

@test "schema: osc-phase error format has error and message fields" {
    run_osc_phase current "nonexistent-change"
    [ "$status" -eq 1 ]
    assert_error_schema "$output"
}

@test "schema: osc-baseline error format has error and message fields" {
    run_osc_baseline get
    [ "$status" -eq 1 ]
    assert_error_schema "$output"
}

@test "schema: osc-complete error format has error and message fields" {
    run_osc_complete get "nonexistent-change"
    [ "$status" -eq 1 ]
    assert_error_schema "$output"
}

# Success schema consistency

@test "schema: osc-state get output has required fields" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2,"phase_complete":false}'
    
    run_osc_state get "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "phase"
    assert_json_has_field "$output" "iteration"
    assert_json_has_field "$output" "phase_complete"
    assert_json_has_field "$output" "change"
}

@test "schema: osc-iterations get output has required fields" {
    setup_change_with_iterations "test-change" '[{"iteration":1}]'
    
    run_osc_iterations get "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "count"
    assert_json_has_field "$output" "iterations"
}

@test "schema: osc-log get output has required fields" {
    setup_change_with_decision_log "test-change" '[{"entry":1}]'
    
    run_osc_log get "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "count"
    assert_json_has_field "$output" "entries"
}

@test "schema: osc-git output has required fields" {
    setup_change "test-change"
    
    run_osc_git "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "modified"
    assert_json_has_field "$output" "added"
    assert_json_has_field "$output" "untracked"
    assert_json_has_field "$output" "clean"
    assert_json_has_field "$output" "branch"
}

@test "schema: osc-ctx output has required fields" {
    setup_change "test-change"
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "change"
    assert_json_has_field "$output" "state"
    assert_json_has_field "$output" "git"
    assert_json_has_field "$output" "artifacts"
    assert_json_has_field "$output" "history"
}

@test "schema: osc-validate output has valid field" {
    setup_change "test-change"
    
    run_osc_validate change-dir "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "valid"
}

@test "schema: osc-validate invalid output has errors array" {
    mkdir -p "openspec/changes/test-change"
    
    run_osc_validate change-dir "test-change"
    [ "$status" -eq 1 ]
    assert_json_has_field "$output" "valid"
    assert_json_has_field "$output" "errors"
}

@test "schema: osc-phase current output has required fields" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2}'
    
    run_osc_phase current "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "phase"
    assert_json_has_field "$output" "next"
    assert_json_has_field "$output" "iteration"
}

@test "schema: osc-phase advance output has required fields" {
    setup_change_with_state "test-change" '{"phase":"PHASE0","iteration":1}'
    
    run_osc_phase advance "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "phase"
    assert_json_has_field "$output" "previous"
    assert_json_has_field "$output" "next"
    assert_json_has_field "$output" "iteration"
}

@test "schema: osc-baseline get output has required fields" {
    setup_baseline "abc123" "main" "2024-01-15T10:00:00Z"
    
    run_osc_baseline get
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "commit"
    assert_json_has_field "$output" "branch"
    assert_json_has_field "$output" "timestamp"
}

@test "schema: osc-baseline record output has required fields" {
    run_osc_baseline record
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "commit"
    assert_json_has_field "$output" "branch"
    assert_json_has_field "$output" "timestamp"
}

@test "schema: osc-complete get output has required fields" {
    setup_change_with_complete "test-change" '{"status":"COMPLETE","with_blocker":false}'
    
    run_osc_complete get "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "status"
    assert_json_has_field "$output" "with_blocker"
}

@test "schema: osc-complete check output has exists field" {
    setup_change_with_complete "test-change" '{"status":"COMPLETE"}'
    
    run_osc_complete check "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "exists"
}

@test "schema: osc-complete set output has required fields" {
    setup_change "test-change"
    
    run_osc_complete set "test-change"
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "status"
    assert_json_has_field "$output" "with_blocker"
}
