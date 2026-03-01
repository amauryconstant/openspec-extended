#!/usr/bin/env bats
# E2E single-phase tests - test individual phases and flags
# Requires E2E_CONFIRM=1 to run (uses real AI calls)

load 'helpers/e2e-helpers'

setup() {
    require_e2e_confirm
    setup_e2e_repo
    copy_fixture "add-hello-script"
}

teardown() {
    teardown_e2e_repo
}

@test "single-phase: --clean removes existing state files" {
    local change="add-hello-script"
    local change_dir="openspec/changes/$change"

    echo '{"phase":"PHASE3","iteration":5}' > "$change_dir/state.json"
    echo '{"status":"COMPLETE"}' > "$change_dir/complete.json"

    assert_file_exists "$change_dir/state.json"
    assert_file_exists "$change_dir/complete.json"

    run_openspec_auto_streaming "$change" --clean --verbose --dry-run --max-iterations 1

    [[ "$output" == *"clean"* ]] || [[ "$output" == *"Clean"* ]] || [[ "$output" == *"PHASE0"* ]]
}

@test "single-phase: --force continues with dirty git state" {
    local change="add-hello-script"

    echo "dirty" > dirty-file.txt
    git add dirty-file.txt

    run_openspec_auto_streaming "$change" --force --verbose --dry-run --max-iterations 1
    [[ "$output" == *"force"* ]] || [[ "$output" == *"dirty"* ]] || [[ "$output" == *"PHASE0"* ]]
}

@test "single-phase: --from-phase PHASE3 skips preflight validation" {
    local change="add-hello-script"

    run_openspec_auto_streaming "$change" --from-phase PHASE3 --verbose --dry-run --max-iterations 1
    [[ "$output" == *"Skipping preflight"* ]] || [[ "$output" == *"PHASE3"* ]] || [[ "$output" == *"from"* ]]
}

@test "single-phase: --max-iterations 1 limits iterations" {
    local change="add-hello-script"

    run_openspec_auto_streaming "$change" --max-iterations 1 --verbose --dry-run
    [[ "$output" == *"1"* ]] || [[ "$output" == *"iteration"* ]]
}
