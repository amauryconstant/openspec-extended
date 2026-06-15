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
    run "$OPENSPEC_BIN" --version
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^openspec-extended\ [0-9]+\.[0-9]+\.[0-9]+$ ]]
}

@test "mechanism: --help shows usage with all options" {
    run "$OPENSPEC_BIN" orchestrate --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"--max-phase-iterations"* ]]
    [[ "$output" == *"--timeout"* ]]
    [[ "$output" == *"--model"* ]]
    [[ "$output" == *"--verbose"* ]]
    [[ "$output" == *"--dry-run"* ]]
    [[ "$output" == *"--force"* ]]
    [[ "$output" == *"--clean"* ]]
    [[ "$output" == *"--from-phase"* ]]
    [[ "$output" == *"--list"* ]]
}

@test "mechanism: --list shows available changes" {
    setup_minimal_change "test-change"
    setup_minimal_change "another-change"

    run "$OPENSPEC_BIN" orchestrate --list test-change
    [ "$status" -eq 0 ]
    [[ "$output" == *"test-change"* ]]
}

@test "mechanism: --dry-run shows phases without execution" {
    setup_minimal_change "dry-test"

    run_osx_orchestrate dry-test --dry-run --max-phase-iterations 1
    [[ "$output" == *"[DRY RUN]"* ]]
    [[ "$output" == *"Would run command"* ]]
}

@test "mechanism: invalid change ID exits with error" {
    run_osx_orchestrate nonexistent-change
    [ "$status" -eq 1 ]
    [[ "$output" == *"not found"* ]] || [[ "$output" == *"Error"* ]] || [[ "$output" == *"Change"* ]]
}

@test "mechanism: invalid option exits with error" {
    run_osx_orchestrate --invalid-option
    [ "$status" -ne 0 ]
    [[ "$output" == *"Unknown option"* ]] || [[ "$output" == *"invalid"* ]]
}
