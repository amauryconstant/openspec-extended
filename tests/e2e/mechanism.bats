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

# ========== Bundled resource deployment ==========
#
# These tests run against the built binary (built fresh by
# test:mechanism:bats) and assert the resources PyInstaller embeds
# actually reach the filesystem when the user runs `install <tool>`.
# The `setup_e2e_repo` helper pre-installs opencode for the
# orchestrator tests above, so these cases use a fresh tmpdir to
# observe a real install from a clean state.

@test "mechanism: install opencode deploys bundled resources" {
    local fresh_dir
    fresh_dir=$(mktemp -d)
    cd "$fresh_dir" || exit 1

    run "$OPENSPEC_BIN" install opencode
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [ -d .opencode/skills/osx-workflow ]
    [ -d .opencode/skills/osx-concepts ]
    [ -f .opencode/manifest.toml ]
    [ -f .opencode/skills/osx-workflow/SKILL.md ]

    rm -rf "$fresh_dir"
}

@test "mechanism: install claude deploys bundled resources" {
    local fresh_dir
    fresh_dir=$(mktemp -d)
    cd "$fresh_dir" || exit 1

    run "$OPENSPEC_BIN" install claude
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [ -d .claude/skills/osx-workflow ]
    [ -d .claude/skills/osx-concepts ]
    [ -f .claude/manifest.toml ]
    [ -f .claude/skills/osx-workflow/SKILL.md ]

    rm -rf "$fresh_dir"
}

# ========== osx subcommand surface ==========
#
# Round-trip the osx subcommand (the 10-domain CLI surface from
# source/osx_cli.py) against the built binary. Confirms the
# subcommand is mounted, every domain is reachable from --help,
# and the JSON output shapes match what osx.py documents.

@test "mechanism: --help lists osx subcommand alongside orchestrate" {
    run "$OPENSPEC_BIN" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"osx"* ]]
    [[ "$output" == *"orchestrate"* ]]
    [[ "$output" == *"install"* ]]
}

@test "mechanism: osx --help lists all 10 domains" {
    run "$OPENSPEC_BIN" osx --help
    [ "$status" -eq 0 ]
    for d in baseline ctx git phase state iterations log complete validate instructions; do
        [[ "$output" == *"$d"* ]]
    done
}

@test "mechanism: osx subcommand round-trip against built binary" {
    setup_minimal_change "smoke-change"

    run "$OPENSPEC_BIN" osx ctx get smoke-change
    [ "$status" -eq 0 ]
    echo "$output" | jq -e '.change == "smoke-change"'

    run "$OPENSPEC_BIN" osx state get smoke-change
    [ "$status" -eq 1 ]
    echo "$output" | jq -e '.error == "state_not_found"'

    run "$OPENSPEC_BIN" osx phase advance smoke-change
    [ "$status" -eq 0 ]
    echo "$output" | jq -e '.phase == "PHASE1"'

    run "$OPENSPEC_BIN" osx state complete smoke-change
    [ "$status" -eq 0 ]

    run "$OPENSPEC_BIN" osx state get smoke-change
    [ "$status" -eq 0 ]
    echo "$output" | jq -e '.phase_complete == true'

    run "$OPENSPEC_BIN" osx log append smoke-change \
        --phase PHASE1 --iteration 1 --summary "smoke"
    [ "$status" -eq 0 ]

    run "$OPENSPEC_BIN" osx iterations get smoke-change
    [ "$status" -eq 0 ]

    run "$OPENSPEC_BIN" osx validate change-dir smoke-change
    [ "$status" -eq 0 ]
    echo "$output" | jq -e '.valid == true'
}

# ========== v1.5.0 store subapp ==========
#
# The `osx store` Typer subapp (from source/osx_cli.py) is the user-facing
# CLI surface for the store_* library functions in source/lib/osx.py.
# These tests assert that:
#   - `osx --help` exposes the --store flag (the context-setting callback)
#   - `osx store --help` exposes the four store_* commands

@test "mechanism: osx store subapp is registered on built binary" {
    run "$OPENSPEC_BIN" osx --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--store"* ]]
    [[ "$output" == *"store"* ]]
}

@test "mechanism: osx store subcommands are registered" {
    run "$OPENSPEC_BIN" osx store --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"list"* ]]
    [[ "$output" == *"register"* ]]
    [[ "$output" == *"unregister"* ]]
    [[ "$output" == *"doctor"* ]]
}
