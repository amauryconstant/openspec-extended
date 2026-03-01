#!/usr/bin/env bats
# Unit tests for osc-iterations

load '../helpers/test-helpers'

setup() {
    setup_test_env
}

teardown() {
    teardown_test_env
}

@test "osc-iterations: missing change argument shows usage error" {
    run_osc_iterations
    [ "$status" -eq 1 ]
    assert_output_contains "usage"
}

@test "osc-iterations: nonexistent change returns error" {
    run_osc_iterations "nonexistent-change" get
    [ "$status" -eq 1 ]
    assert_output_contains "change_not_found"
}

@test "osc-iterations: get without iterations.json returns empty array" {
    setup_change "test-change"
    
    run_osc_iterations "test-change" get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "0"
}

@test "osc-iterations: get returns existing iterations" {
    setup_change_with_iterations "test-change" '[{"iteration":1,"phase":"PHASE0"},{"iteration":2,"phase":"PHASE1"}]'
    
    run_osc_iterations "test-change" get
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "2"
}

@test "osc-iterations: append requires stdin input" {
    setup_change "test-change"
    
    # When stdin is empty/EOF (as with 'run'), it fails with invalid_json
    # since it can't parse empty input as JSON
    run_osc_iterations "test-change" append
    [ "$status" -eq 1 ]
    assert_output_contains "invalid_json"
}

@test "osc-iterations: append requires valid JSON" {
    setup_change "test-change"
    
    run bash -c "echo 'not json' | $LIB_DIR/osc-iterations test-change append"
    [ "$status" -eq 1 ]
}

@test "osc-iterations: append requires iteration field" {
    setup_change "test-change"
    
    run bash -c "echo '{\"phase\":\"PHASE0\"}' | $LIB_DIR/osc-iterations test-change append"
    [ "$status" -eq 1 ]
    assert_output_contains "missing_field"
}

@test "osc-iterations: append creates new iterations.json" {
    setup_change "test-change"
    
    run bash -c "echo '{\"iteration\":1,\"phase\":\"PHASE0\"}' | $LIB_DIR/osc-iterations test-change append"
    [ "$status" -eq 0 ]
    assert_json_true "$output" ".success"
    assert_json_equals "$output" ".total_count" "1"
    
    # Verify file exists
    [ -f "openspec/changes/test-change/iterations.json" ]
}

@test "osc-iterations: append adds to existing iterations" {
    setup_change_with_iterations "test-change" '[{"iteration":1,"phase":"PHASE0"}]'
    
    run bash -c "echo '{\"iteration\":2,\"phase\":\"PHASE1\"}' | $LIB_DIR/osc-iterations test-change append"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".total_count" "2"
    
    local count
    count=$(jq 'length' "openspec/changes/test-change/iterations.json")
    [ "$count" == "2" ]
}

@test "osc-iterations: append adds timestamp if missing" {
    setup_change "test-change"
    
    run bash -c "echo '{\"iteration\":1,\"phase\":\"PHASE0\"}' | $LIB_DIR/osc-iterations test-change append"
    [ "$status" -eq 0 ]
    
    local has_timestamp
    has_timestamp=$(jq 'any(.timestamp != null)' "openspec/changes/test-change/iterations.json")
    [ "$has_timestamp" == "true" ]
}

@test "osc-iterations: append preserves existing timestamp" {
    setup_change "test-change"
    
    run bash -c "echo '{\"iteration\":1,\"phase\":\"PHASE0\",\"timestamp\":\"2024-01-01T00:00:00Z\"}' | $LIB_DIR/osc-iterations test-change append"
    [ "$status" -eq 0 ]
    
    local ts
    ts=$(jq -r '.[0].timestamp' "openspec/changes/test-change/iterations.json")
    [ "$ts" == "2024-01-01T00:00:00Z" ]
}

@test "osc-iterations: get returns error for non-array JSON" {
    setup_change "test-change"
    echo '{"not":"array"}' > "openspec/changes/test-change/iterations.json"
    
    run_osc_iterations "test-change" get
    [ "$status" -eq 1 ]
    assert_output_contains "invalid_format"
}

@test "osc-iterations: unknown action returns error" {
    setup_change "test-change"
    
    run_osc_iterations "test-change" invalid-action
    [ "$status" -eq 1 ]
    assert_output_contains "unknown_action"
}

@test "osc-iterations: get is default action" {
    setup_change_with_iterations "test-change" '[{"iteration":1}]'
    
    run_osc_iterations "test-change"
    [ "$status" -eq 0 ]
    assert_json_equals "$output" ".count" "1"
}
