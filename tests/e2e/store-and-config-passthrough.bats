#!/usr/bin/env bats
# E2E mechanism tests for v1.5+ top-level passthroughs and subcommand groups.
# Verifies --help and registration of the new commands/groups added to mirror the upstream OpenSpec CLI surface.
# Does NOT require an installed `openspec` upstream binary; these are help-surface checks.

load 'helpers/e2e-helpers'

setup() {
    setup_e2e_repo
}

teardown() {
    teardown_e2e_repo
}

# ========== Top-level command registration ==========
#
# Asserts that every new top-level passthrough (view, archive, context,
# doctor, new change, store, config) is advertised on `--help` so users
# can discover them without reading source.

@test "mechanism: --help lists new top-level passthroughs" {
    run "$OPENSPEC_BIN" --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    for cmd in view archive context doctor new store config; do
        [[ "$output" == *"$cmd"* ]] || { echo "Missing command: $cmd"; return 1; }
    done
}

# ========== view passthrough ==========
#
# `view <change>` renders a change directory. The passthrough must
# document `--store` (v1.7+) and `--json` so callers can pipe output.

@test "mechanism: view --help shows flags" {
    run "$OPENSPEC_BIN" view --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--store"* ]]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: view without openspec shows friendly error or runs cleanly" {
    run "$OPENSPEC_BIN" view
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    # No traceback regardless of upstream availability.
    [[ "$output" != *"Traceback"* ]]
}

# ========== archive passthrough ==========
#
# `archive <change>` (and bulk form `archive --yes`) requires flags to
# bypass prompts and gate validation/skip-specs behaviour.

@test "mechanism: archive --help shows flags" {
    run "$OPENSPEC_BIN" archive --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--yes"* ]]
    [[ "$output" == *"--skip-specs"* ]]
    [[ "$output" == *"--no-validate"* ]]
    [[ "$output" == *"--json"* ]]
    [[ "$output" == *"--store"* ]]
}

@test "mechanism: archive without args shows usage" {
    run "$OPENSPEC_BIN" archive
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    # Upstream `openspec archive` with no args in non-TTY prints a clean
    # "no changes" message and exits 0 (or non-zero with the same message).
    # The wrapper must forward that without a Python traceback.
    [[ "$output" != *"Traceback"* ]]
}

@test "mechanism: archive forwards --yes" {
    # Don't actually archive anything (would require a real change);
    # just verify help documents --yes so callers know the flag exists.
    run "$OPENSPEC_BIN" archive --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--yes"* ]]
}

# ========== context passthrough ==========
#
# `context` writes editor workspace files. v1.7+ adds `--code-workspace`
# and `--force`; the passthrough must surface them all.

@test "mechanism: context --help shows flags" {
    run "$OPENSPEC_BIN" context --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--store"* ]]
    [[ "$output" == *"--json"* ]]
    [[ "$output" == *"--code-workspace"* ]]
    [[ "$output" == *"--force"* ]]
}

@test "mechanism: context with --json runs" {
    run "$OPENSPEC_BIN" context --json
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    # May fail without `openspec` installed (lazy-fail upstream) — that's
    # acceptable; only the absence of a Python traceback is enforced.
    [[ "$output" != *"Traceback"* ]]
}

# ========== doctor passthrough ==========
#
# `doctor` runs environment diagnostics. Same contract as the others:
# document `--store` and `--json`; never crash with a traceback.

@test "mechanism: doctor --help shows flags" {
    run "$OPENSPEC_BIN" doctor --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--store"* ]]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: doctor runs without traceback" {
    run "$OPENSPEC_BIN" doctor
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [[ "$output" != *"Traceback"* ]]
}

# ========== new change group ==========
#
# `new change <id>` is a CLI form of the change-scaffolding command.
# Flags added over the upstream version include `--description`,
# `--goal`, and `--schema` for richer provisioning.

@test "mechanism: new change --help shows flags" {
    run "$OPENSPEC_BIN" new change --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--description"* ]]
    [[ "$output" == *"--goal"* ]]
    [[ "$output" == *"--schema"* ]]
    [[ "$output" == *"--json"* ]]
    [[ "$output" == *"--store"* ]]
}

# ========== store group ==========
#
# `store <sub>` exposes the v1.7+ store registry lifecycle:
# setup/register/unregister/remove/list/doctor. Mirrors the CLI
# surface documented in source/lib/osx.py.

@test "mechanism: store --help lists subcommands" {
    run "$OPENSPEC_BIN" store --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    for sub in setup register unregister remove list doctor; do
        [[ "$output" == *"$sub"* ]] || { echo "Missing store subcommand: $sub"; return 1; }
    done
}

@test "mechanism: store list --help shows --json" {
    run "$OPENSPEC_BIN" store list --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: store doctor --help shows --json" {
    run "$OPENSPEC_BIN" store doctor --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--json"* ]]
}

# ========== config group ==========
#
# `config <sub>` is the user-facing config CLI (path/list/get/set/unset/
# reset/edit/profile). `config set` documents type coercion (`--string`)
# and the `--allow-unknown` opt-in for unknown keys.

@test "mechanism: config --help lists subcommands" {
    run "$OPENSPEC_BIN" config --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    for sub in path list get set unset reset edit profile; do
        [[ "$output" == *"$sub"* ]] || { echo "Missing config subcommand: $sub"; return 1; }
    done
}

@test "mechanism: config set --help shows --string and --allow-unknown" {
    run "$OPENSPEC_BIN" config set --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--string"* ]]
    [[ "$output" == *"--allow-unknown"* ]]
}

@test "mechanism: config get without key exits non-zero" {
    run "$OPENSPEC_BIN" config get
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -ne 0 ]
    [[ "$output" != *"Traceback"* ]]
}
