#!/usr/bin/env bats
# Unit tests for osc-complete

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# Usage/Errors

@test "osc-complete: missing arguments shows usage error" {
    run_osc_complete
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-complete: nonexistent change returns error" {
    run_osc_complete "nonexistent-change" check
    [ "$status" -eq 1 ]
    assert_output_contains "change_not_found"
}

@test "osc-complete: unknown action returns error" {
    setup_change "test-change"
    
    run_osc_complete "test-change" invalid-action
    [ "$status" -eq 1 ]
    assert_output_contains "unknown_action"
}

# check action

@test "osc-complete: check returns exists:true when file present" {
    setup_change_with_complete "test-change" '{"status":"COMPLETE"}'
    
    run_osc_complete "test-change" check
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".exists"
}

@test "osc-complete: check returns exists:false when missing" {
    setup_change "test-change"
    
    run_osc_complete "test-change" check
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".exists"
}

@test "osc-complete: check returns exists:false for invalid JSON" {
    setup_change "test-change"
    echo "not valid json" > "openspec/changes/test-change/complete.json"
    
    run_osc_complete "test-change" check
    [ "$status" -eq 1 ]
    assert_json_false "$output" ".exists"
}

# get action

@test "osc-complete: get returns status and with_blocker" {
    setup_change_with_complete "test-change" '{"status":"COMPLETE","with_blocker":false}'
    
    run_osc_complete "test-change" get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".status" "COMPLETE"
    assert_json_false "$output" ".with_blocker"
}

@test "osc-complete: get includes blocker_reason when present" {
    setup_change_with_complete "test-change" '{"status":"COMPLETE","with_blocker":true,"blocker_reason":"Critical bug found"}'
    
    run_osc_complete "test-change" get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".status" "COMPLETE"
    assert_json_true "$output" ".with_blocker"
    assert_json_equals "$output" ".blocker_reason" "Critical bug found"
}

@test "osc-complete: get fails without complete.json" {
    setup_change "test-change"
    
    run_osc_complete "test-change" get
    [ "$status" -eq 1 ]
    assert_output_contains "complete_not_found"
}

# set action

@test "osc-complete: set creates complete.json" {
    setup_change "test-change"
    
    run_osc_complete "test-change" set
    [ "$status" -eq 0 ]
    [ -f "openspec/changes/test-change/complete.json" ]
    assert_json_equals "$output" ".status" "COMPLETE"
    assert_json_false "$output" ".with_blocker"
}

@test "osc-complete: set with blocker creates blocker fields" {
    setup_change "test-change"
    
    run_osc_complete "test-change" set "COMPLETE" "true" "Test blocker"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".with_blocker"
    assert_json_equals "$output" ".blocker_reason" "Test blocker"
}

@test "osc-complete: set output matches file content" {
    setup_change "test-change"
    
    run_osc_complete "test-change" set "COMPLETE" "false"
    [ "$status" -eq 0 ]
    
    local file_status file_blocker
    file_status=$(jq -r '.status' "openspec/changes/test-change/complete.json")
    file_blocker=$(jq -r '.with_blocker' "openspec/changes/test-change/complete.json")
    
    [ "$file_status" == "COMPLETE" ]
    [ "$file_blocker" == "false" ]
}

@test "osc-complete: set with custom status" {
    setup_change "test-change"
    
    run_osc_complete "test-change" set "FAILED" "false"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".status" "FAILED"
    
    local file_status
    file_status=$(jq -r '.status' "openspec/changes/test-change/complete.json")
    [ "$file_status" == "FAILED" ]
}
