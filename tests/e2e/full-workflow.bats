#!/usr/bin/env bats
# E2E full workflow tests - complete PHASE0 through PHASE6
# Requires E2E_CONFIRM=1 to run (uses real AI calls, ~5-10 min per test)

load 'helpers/e2e-helpers'

# Use longer timeout for full workflow tests
E2E_TIMEOUT=3600

setup() {
    require_e2e_confirm
    setup_e2e_repo
    copy_fixture "add-hello-script"
}

teardown() {
    teardown_e2e_repo
}

@test "full-workflow: complete workflow produces hello.sh artifact" {
    local change="add-hello-script"

    run_openspec_auto_streaming "$change" --force --verbose --max-iterations 3 --timeout 600
    [ "$status" -eq 0 ]

    assert_file_exists "scripts/hello.sh"

    [[ -x "scripts/hello.sh" ]]

    run ./scripts/hello.sh
    [ "$status" -eq 0 ]
    [[ "$output" == *"Hello"* ]]
}

@test "full-workflow: state files cleaned on success" {
    local change="add-hello-script"
    local change_dir="openspec/changes/$change"

    run_openspec_auto_streaming "$change" --force --verbose --max-iterations 3 --timeout 600
    [ "$status" -eq 0 ]

    assert_file_not_exists "$change_dir/state.json"
    assert_file_not_exists "$change_dir/complete.json"
    assert_file_not_exists ".openspec-baseline.json"
}

@test "full-workflow: iterations.json populated with all phases" {
    local change="add-hello-script"
    local change_dir="openspec/changes/$change"

    run_openspec_auto_streaming "$change" --force --verbose --max-iterations 3 --timeout 600
    [ "$status" -eq 0 ]

    assert_file_exists "$change_dir/iterations.json"

    local count
    count=$(jq '. | length' "$change_dir/iterations.json")
    [[ "$count" -ge 7 ]]
}

@test "full-workflow: decision-log.json records agent reasoning" {
    local change="add-hello-script"
    local change_dir="openspec/changes/$change"

    run_openspec_auto_streaming "$change" --force --verbose --max-iterations 3 --timeout 600
    [ "$status" -eq 0 ]

    assert_file_exists "$change_dir/decision-log.json"

    local has_entries
    has_entries=$(jq '. | length > 0' "$change_dir/decision-log.json")
    [[ "$has_entries" == "true" ]]
}
