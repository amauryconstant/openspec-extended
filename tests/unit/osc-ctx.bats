#!/usr/bin/env bats
# Unit tests for osc-ctx

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

@test "osc-ctx: missing change argument returns error" {
    run_osc_ctx
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-ctx: nonexistent change returns error" {
    run_osc_ctx "nonexistent-change"
    [ "$status" -eq 1 ]
    assert_output_contains "change_not_found"
}

@test "osc-ctx: returns change name in output" {
    setup_change "test-change"
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".change" "test-change"
}

@test "osc-ctx: returns artifact status for all required files" {
    setup_change "test-change"
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    # Check all artifacts are reported
    local has_proposal has_specs has_design has_tasks
    has_proposal=$(echo "$output" | jq '.artifacts | has("proposal")')
    has_specs=$(echo "$output" | jq '.artifacts | has("specs")')
    has_design=$(echo "$output" | jq '.artifacts | has("design")')
    has_tasks=$(echo "$output" | jq '.artifacts | has("tasks")')
    
    [ "$has_proposal" == "true" ]
    [ "$has_specs" == "true" ]
    [ "$has_design" == "true" ]
    [ "$has_tasks" == "true" ]
}

@test "osc-ctx: reports existing artifacts correctly" {
    setup_change "test-change"
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    assert_json_true "$output" ".artifacts.proposal.exists"
    assert_json_true "$output" ".artifacts.design.exists"
    assert_json_true "$output" ".artifacts.tasks.exists"
    assert_json_true "$output" ".artifacts.specs.exists"
}

@test "osc-ctx: reports missing artifacts correctly" {
    setup_change "test-change"
    rm openspec/changes/test-change/proposal.md
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    assert_json_false "$output" ".artifacts.proposal.exists"
}

@test "osc-ctx: reports specs count" {
    setup_change "test-change"
    echo "# Spec 2" > openspec/changes/test-change/specs/spec2.md
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".artifacts.specs.count" "2"
}

@test "osc-ctx: includes state when state.json exists" {
    setup_change_with_state "test-change" '{"phase":"PHASE1","iteration":2,"phase_complete":false}'
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    assert_json_equals "$output" ".state.phase" "PHASE1"
    assert_json_equals "$output" ".state.iteration" "2"
}

@test "osc-ctx: provides default state when state.json missing" {
    setup_change "test-change"
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    # Should have state object with defaults
    local has_state
    has_state=$(echo "$output" | jq 'has("state")')
    [ "$has_state" == "true" ]
}

@test "osc-ctx: includes history counts" {
    setup_change "test-change"
    echo '[{"entry":1},{"entry":2}]' > openspec/changes/test-change/decision-log.json
    echo '[{"iteration":1},{"iteration":2},{"iteration":3}]' > openspec/changes/test-change/iterations.json
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    assert_json_equals "$output" ".history.decision_log_entries" "2"
    assert_json_equals "$output" ".history.iterations_recorded" "3"
}

@test "osc-ctx: reports zero counts for missing history files" {
    setup_change "test-change"
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    assert_json_equals "$output" ".history.decision_log_entries" "0"
    assert_json_equals "$output" ".history.iterations_recorded" "0"
}

@test "osc-ctx: includes git status" {
    setup_change "test-change"
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    local has_git
    has_git=$(echo "$output" | jq 'has("git")')
    [ "$has_git" == "true" ]
}

@test "osc-ctx: reports file sizes for artifacts" {
    setup_change "test-change"
    echo "This is a longer proposal content" >> openspec/changes/test-change/proposal.md
    
    run_osc_ctx "test-change"
    [ "$status" -eq 0 ]
    
    # Size should be > 0
    local size
    size=$(echo "$output" | jq '.artifacts.proposal.size')
    [ "$size" -gt 0 ]
}
