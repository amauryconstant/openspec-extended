#!/usr/bin/env bats
# Unit tests for osc-baseline

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

# Usage/Errors

@test "osc-baseline: missing action shows usage error" {
    run_osc_baseline
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-baseline: unknown action returns error" {
    run_osc_baseline invalid-action
    [ "$status" -eq 1 ]
    assert_output_contains "unknown_action"
}

# record action

@test "osc-baseline: record creates baseline file" {
    run_osc_baseline record
    [ "$status" -eq 0 ]
    [ -f ".openspec-baseline.json" ]
}

@test "osc-baseline: record returns commit/branch/timestamp" {
    run_osc_baseline record
    [ "$status" -eq 0 ]
    assert_json_has_field "$output" "commit"
    assert_json_has_field "$output" "branch"
    assert_json_has_field "$output" "timestamp"
}

@test "osc-baseline: record fails outside git repo" {
    rm -rf .git
    
    run_osc_baseline record
    [ "$status" -eq 1 ]
    assert_output_contains "not_git_repo"
}

# get action

@test "osc-baseline: get returns baseline content" {
    setup_baseline "abc123def" "feature-branch" "2024-01-15T10:30:00Z"
    
    run_osc_baseline get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".commit" "abc123def"
    assert_json_equals "$output" ".branch" "feature-branch"
    assert_json_equals "$output" ".timestamp" "2024-01-15T10:30:00Z"
}

@test "osc-baseline: get fails without baseline file" {
    run_osc_baseline get
    [ "$status" -eq 1 ]
    assert_output_contains "baseline_not_found"
}

@test "osc-baseline: get fails with invalid JSON" {
    echo "not valid json" > ".openspec-baseline.json"
    
    run_osc_baseline get
    [ "$status" -eq 1 ]
    assert_output_contains "invalid_json"
}
