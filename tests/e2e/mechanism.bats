#!/usr/bin/env bats
# E2E mechanism tests - no AI calls, safe to run anytime
# Tests CLI options and error handling

load 'helpers/e2e-helpers'

setup() {
    setup_e2e_repo
}

teardown() {
    teardown_e2e_repo
}

@test "mechanism: --version returns version string" {
    run_openspec_auto --version
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^0\.7\.0$ ]]
}

@test "mechanism: --help shows usage with all options" {
    run_openspec_auto --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"--max-iterations"* ]]
    [[ "$output" == *"--timeout"* ]]
    [[ "$output" == *"--model"* ]]
    [[ "$output" == *"--verbose"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"--force"* ]]
    [[ "$output" == *"--clean"* ]]
    [[ "$output" == *"--from-phase"* ]]
    [[ "$output" == *"--version"* ]]
    [[ "$output" == *"--list"* ]]
}

@test "mechanism: --list shows available changes" {
    setup_minimal_change "test-change"
    setup_minimal_change "another-change"

    run_openspec_auto --list
    [ "$status" -eq 0 ]
    [[ "$output" == *"test-change"* ]]
    [[ "$output" == *"another-change"* ]]
}

@test "mechanism: --dry-run shows phases without execution" {
    setup_minimal_change "dry-test"

    run_openspec_auto dry-test --dry-run --max-iterations 1
    [[ "$output" == *"[DRY RUN]"* ]]
    [[ "$output" == *"Would run command"* ]]
}

@test "mechanism: invalid change ID exits with error" {
    run_openspec_auto nonexistent-change
    [ "$status" -eq 1 ]
    [[ "$output" == *"not found"* ]] || [[ "$output" == *"Error"* ]] || [[ "$output" == *"Change"* ]]
}

@test "mechanism: invalid option exits with error" {
    run_openspec_auto --invalid-option
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]] || [[ "$output" == *"invalid"* ]]
}
