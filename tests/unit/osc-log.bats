#!/usr/bin/env bats
# Unit tests for osc-log

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

@test "osc-log: missing change argument shows usage error" {
    run_osc_log
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-log: nonexistent change returns error" {
    run_osc_log "nonexistent-change" get
    [ "$status" -eq 1 ]
    assert_output_contains "change_not_found"
}

@test "osc-log: get without decision-log.json returns empty array" {
    setup_change "test-change"
    
    run_osc_log "test-change" get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "0"
}

@test "osc-log: get returns existing entries" {
    setup_change_with_decision_log "test-change" '[{"entry":1,"phase":"PHASE0"},{"entry":2,"phase":"PHASE1"}]'
    
    run_osc_log "test-change" get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "2"
}

@test "osc-log: append requires stdin input" {
    setup_change "test-change"
    
    # In BATS run context, stdin is empty which is not valid JSON
    run_osc_log "test-change" append
    [ "$status" -eq 1 ]
    assert_output_contains "invalid_json"
}

@test "osc-log: append requires valid JSON" {
    setup_change "test-change"
    
    run bash -c "echo 'not json' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 1 ]
}

@test "osc-log: append requires phase field" {
    setup_change "test-change"
    
    run bash -c "echo '{\"iteration\":1}' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 1 ]
    assert_output_contains "missing_field"
}

@test "osc-log: append requires iteration field" {
    setup_change "test-change"
    
    run bash -c "echo '{\"phase\":\"PHASE0\"}' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 1 ]
    assert_output_contains "missing_field"
}

@test "osc-log: append creates new decision-log.json" {
    setup_change "test-change"
    
    run bash -c "echo '{\"phase\":\"PHASE0\",\"iteration\":1}' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".success"
    assert_json_equals "$output" ".entry" "1"
    
    [ -f "openspec/changes/test-change/decision-log.json" ]
}

@test "osc-log: append adds to existing log" {
    setup_change_with_decision_log "test-change" '[{"entry":1,"phase":"PHASE0","iteration":1}]'
    
    run bash -c "echo '{\"phase\":\"PHASE1\",\"iteration\":1}' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".entry" "2"
    
    local count
    count=$(jq 'length' "openspec/changes/test-change/decision-log.json")
    [ "$count" == "2" ]
}

@test "osc-log: append adds timestamp and entry number" {
    setup_change "test-change"
    
    run bash -c "echo '{\"phase\":\"PHASE0\",\"iteration\":1}' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 0 ]
    
    local has_timestamp has_entry
    has_timestamp=$(jq '.[0].timestamp != null' "openspec/changes/test-change/decision-log.json")
    has_entry=$(jq '.[0].entry == 1' "openspec/changes/test-change/decision-log.json")
    
    [ "$has_timestamp" == "true" ]
    [ "$has_entry" == "true" ]
}

@test "osc-log: append returns entry details" {
    setup_change "test-change"
    
    run bash -c "echo '{\"phase\":\"PHASE2\",\"iteration\":3}' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 0 ]
    
    assert_json_equals "$output" ".phase" "PHASE2"
    assert_json_equals "$output" ".iteration" "3"
}

@test "osc-log: unknown action returns error" {
    setup_change "test-change"
    
    run_osc_log "test-change" invalid-action
    [ "$status" -eq 1 ]
    assert_output_contains "unknown_action"
}

@test "osc-log: get is default action" {
    setup_change_with_decision_log "test-change" '[{"entry":1}]'
    
    run_osc_log "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "1"
}

@test "osc-log: preserves all input fields" {
    setup_change "test-change"
    
    run bash -c "echo '{\"phase\":\"PHASE0\",\"iteration\":1,\"summary\":\"test\",\"decisions\":[\"a\",\"b\"],\"errors\":[\"err\"]}' | $LIB_DIR/osc-log test-change append"
    [ "$status" -eq 0 ]
    
    local summary decisions errors
    summary=$(jq -r '.[0].summary' "openspec/changes/test-change/decision-log.json")
    decisions=$(jq '.[0].decisions | length' "openspec/changes/test-change/decision-log.json")
    errors=$(jq '.[0].errors | length' "openspec/changes/test-change/decision-log.json")
    
    [ "$summary" == "test" ]
    [ "$decisions" == "2" ]
    [ "$errors" == "1" ]
}
