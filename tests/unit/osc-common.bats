#!/usr/bin/env bats
# Unit tests for osc-common

load '../helpers/test-helpers'

setup() {
    setup_test_env
    source "$LIB_DIR/osc-common"
}

teardown() {
    teardown_test_env
}

@test "osc_json_length: returns 0 for nonexistent file" {
    run osc_json_length "$TEST_DIR/nonexistent.json"
    [ "$status" -eq 0 ]
    [ "$output" == "0" ]
}

@test "osc_json_length: returns 0 for empty file" {
    touch "$TEST_DIR/empty.json"
    run osc_json_length "$TEST_DIR/empty.json"
    [ "$status" -eq 0 ]
    [ "$output" == "0" ]
}

@test "osc_json_length: returns correct count for valid array" {
    echo '[1,2,3]' > "$TEST_DIR/array.json"
    run osc_json_length "$TEST_DIR/array.json"
    [ "$status" -eq 0 ]
    [ "$output" == "3" ]
}

@test "osc_json_length: returns 0 for corrupted JSON" {
    echo 'not valid json' > "$TEST_DIR/corrupt.json"
    run osc_json_length "$TEST_DIR/corrupt.json"
    [ "$status" -eq 0 ]
    [ "$output" == "0" ]
}

@test "osc_json_length: returns 0 for JSON object (not array)" {
    echo '{"key":"value"}' > "$TEST_DIR/object.json"
    run osc_json_length "$TEST_DIR/object.json"
    [ "$status" -eq 0 ]
    [ "$output" == "0" ]
}

@test "osc_json_length: returns 0 for whitespace-only file" {
    echo '   ' > "$TEST_DIR/whitespace.json"
    run osc_json_length "$TEST_DIR/whitespace.json"
    [ "$status" -eq 0 ]
    [ "$output" == "0" ]
}

@test "osc_json_append: creates new file with entry" {
    run osc_json_append "$TEST_DIR/new.json" '{"test":1}'
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/new.json" ]
    
    local count
    count=$(jq 'length' "$TEST_DIR/new.json")
    [ "$count" == "1" ]
    
    local value
    value=$(jq -r '.[0].test' "$TEST_DIR/new.json")
    [ "$value" == "1" ]
}

@test "osc_json_append: appends to existing array" {
    echo '[{"a":1}]' > "$TEST_DIR/existing.json"
    run osc_json_append "$TEST_DIR/existing.json" '{"b":2}'
    [ "$status" -eq 0 ]
    
    local count
    count=$(jq 'length' "$TEST_DIR/existing.json")
    [ "$count" == "2" ]
    
    local last_value
    last_value=$(jq -r '.[1].b' "$TEST_DIR/existing.json")
    [ "$last_value" == "2" ]
}

@test "osc_json_append: returns 1 for invalid entry JSON" {
    echo '[]' > "$TEST_DIR/valid.json"
    run osc_json_append "$TEST_DIR/valid.json" 'not valid json'
    [ "$status" -eq 1 ]
    
    # File should remain unchanged
    local count
    count=$(jq 'length' "$TEST_DIR/valid.json")
    [ "$count" == "0" ]
}

@test "osc_json_append: cleans up tmp file on failure" {
    echo 'invalid' > "$TEST_DIR/bad.json"
    run osc_json_append "$TEST_DIR/bad.json" '{"test":1}'
    [ "$status" -eq 1 ]
    [ ! -f "$TEST_DIR/bad.json.tmp" ]
}

@test "osc_json_append: handles complex JSON entry" {
    run osc_json_append "$TEST_DIR/complex.json" '{"phase":"PHASE0","iteration":1,"data":{"nested":[1,2,3]}}'
    [ "$status" -eq 0 ]
    
    local phase
    phase=$(jq -r '.[0].phase' "$TEST_DIR/complex.json")
    [ "$phase" == "PHASE0" ]
    
    local nested_len
    nested_len=$(jq '.[0].data.nested | length' "$TEST_DIR/complex.json")
    [ "$nested_len" == "3" ]
}

@test "osc_json_update: updates JSON atomically" {
    echo '{"phase":"OLD"}' > "$TEST_DIR/state.json"
    run osc_json_update "$TEST_DIR/state.json" '.phase = $phase' --arg phase "NEW"
    [ "$status" -eq 0 ]
    
    local phase
    phase=$(jq -r '.phase' "$TEST_DIR/state.json")
    [ "$phase" == "NEW" ]
}

@test "osc_json_update: cleans up tmp file on failure" {
    echo 'invalid json' > "$TEST_DIR/bad.json"
    run osc_json_update "$TEST_DIR/bad.json" '.phase = "test"'
    [ "$status" -eq 1 ]
    [ ! -f "$TEST_DIR/bad.json.tmp" ]
}

@test "osc_json_update: handles multiple jq args" {
    echo '{"phase":"OLD","iteration":1}' > "$TEST_DIR/multi.json"
    run osc_json_update "$TEST_DIR/multi.json" '.phase = $phase | .iteration = $iter' --arg phase "NEW" --argjson iter 2
    [ "$status" -eq 0 ]
    
    local phase
    phase=$(jq -r '.phase' "$TEST_DIR/multi.json")
    [ "$phase" == "NEW" ]
    
    local iteration
    iteration=$(jq -r '.iteration' "$TEST_DIR/multi.json")
    [ "$iteration" == "2" ]
}

@test "osc_json_update: returns 1 for invalid source JSON" {
    echo 'not json' > "$TEST_DIR/invalid.json"
    run osc_json_update "$TEST_DIR/invalid.json" '.test = 1'
    [ "$status" -eq 1 ]
}

@test "osc_json_update: preserves original file on failure" {
    echo '{"original":"data"}' > "$TEST_DIR/preserve.json"
    run osc_json_update "$TEST_DIR/preserve.json" '.test = |'  # Invalid jq expression
    [ "$status" -eq 1 ]
    
    # Original content should be preserved
    local original
    original=$(jq -r '.original' "$TEST_DIR/preserve.json")
    [ "$original" == "data" ]
}

@test "osc_json_length: handles large arrays" {
    # Create array with 100 elements
    jq -n '[range(100)]' > "$TEST_DIR/large.json"
    run osc_json_length "$TEST_DIR/large.json"
    [ "$status" -eq 0 ]
    [ "$output" == "100" ]
}

@test "osc_json_append: handles multiple sequential appends" {
    for i in 1 2 3 4 5; do
        osc_json_append "$TEST_DIR/seq.json" "{\"num\":$i}"
    done
    
    local count
    count=$(jq 'length' "$TEST_DIR/seq.json")
    [ "$count" == "5" ]
    
    local last
    last=$(jq -r '.[4].num' "$TEST_DIR/seq.json")
    [ "$last" == "5" ]
}

@test "osc_find_change_dir: returns primary path for active change" {
    mkdir -p "$TEST_DIR/openspec/changes/test-change"
    
    run osc_find_change_dir "test-change"
    [ "$status" -eq 0 ]
    [ "$output" == "openspec/changes/test-change" ]
}

@test "osc_find_change_dir: returns archive path for archived change" {
    mkdir -p "$TEST_DIR/openspec/changes/archive/2024-01-15-test-change"
    
    run osc_find_change_dir "test-change"
    [ "$status" -eq 0 ]
    [ "$output" == "openspec/changes/archive/2024-01-15-test-change" ]
}

@test "osc_find_change_dir: returns 1 for nonexistent change" {
    run osc_find_change_dir "nonexistent"
    [ "$status" -eq 1 ]
    [ -z "$output" ]
}

@test "osc_find_change_dir: handles missing archive directory" {
    mkdir -p "$TEST_DIR/openspec/changes"
    
    run osc_find_change_dir "nonexistent"
    [ "$status" -eq 1 ]
    [ -z "$output" ]
}

@test "osc_find_change_dir: prefers active over archive" {
    mkdir -p "$TEST_DIR/openspec/changes/test-change"
    mkdir -p "$TEST_DIR/openspec/changes/archive/2024-01-15-test-change"
    
    run osc_find_change_dir "test-change"
    [ "$status" -eq 0 ]
    [ "$output" == "openspec/changes/test-change" ]
}

# ==============================================================================
# capture_optional helper tests
# ==============================================================================

@test "capture_optional: captures successful output" {
    local result
    capture_optional result echo "test value"
    [ "$result" == "test value" ]
}

@test "capture_optional: returns empty on command failure" {
    local result="initial"
    capture_optional result false
    [ "$result" == "" ]
}

@test "capture_optional: suppresses stderr" {
    local result
    capture_optional result sh -c 'echo "error message" >&2; exit 1'
    [ "$result" == "" ]
}

@test "capture_optional: captures stdout even with stderr" {
    local result
    capture_optional result sh -c 'echo "error" >&2; echo "success"'
    [ "$result" == "success" ]
}

@test "capture_optional: handles empty output" {
    local result="unchanged"
    capture_optional result true
    [ "$result" == "" ]
}

@test "capture_optional: works with commands that produce JSON" {
    local result
    capture_optional result echo '{"phase":"PHASE1","iteration":1}'
    [ "$result" == '{"phase":"PHASE1","iteration":1}' ]
}

@test "capture_optional: handles commands with arguments" {
    local result
    capture_optional result printf "%s %s" "hello" "world"
    [ "$result" == "hello world" ]
}

@test "capture_optional: does not fail script with set -e" {
    # This is the key test - ensures capture_optional won't cause script exit
    (
        set -e
        local result=""
        capture_optional result false
        # If we reach here, the helper works correctly with set -e
        exit 0
    )
    [ "$?" -eq 0 ]
}
