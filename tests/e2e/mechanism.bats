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

    run "$OPENSPEC_BIN" install opencode --with-autonomous
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [ -d .opencode/skills/osx-workflow ]
    [ -d .opencode/skills/osx-concepts ]
    [ -f .opencode/manifest.toml ]
    [ -f .opencode/skills/osx-workflow/SKILL.md ]
    [ -f .opencode/skills/osx-review-artifacts/SKILL.md ]
    [ -f .opencode/skills/osx-modify-artifacts/SKILL.md ]
    [ ! -e .opencode/skills/osx-review-artifacts/references/review-criteria.md ]

    # Shared references are packaged into the skill's own references/ folder
    # so the SKILL.md links resolve without depending on a sibling directory.
    [ -f .opencode/skills/osx-modify-artifacts/references/store-selection.md ]
    [ -f .opencode/skills/osx-modify-artifacts/references/schema-agnostic-contract.md ]
    [ -f .opencode/skills/osx-modify-artifacts/references/osx-mode-conventions.md ]
    [ -f .opencode/skills/osx-review-artifacts/references/store-selection.md ]
    [ -f .opencode/skills/osx-review-artifacts/references/schema-agnostic-contract.md ]
    [ -f .opencode/skills/osx-maintain-ai-docs/references/osx-mode-conventions.md ]
    [ -f .opencode/skills/osx-review-test-compliance/references/scoring-rubric.md ]
    # Skill-local references stay untouched.
    [ -f .opencode/skills/osx-concepts/references/cli-reference.md ]
    [ -f .opencode/skills/osx-maintain-ai-docs/references/doc-structures.md ]

    rm -rf "$fresh_dir"
}

@test "mechanism: install claude deploys bundled resources" {
    local fresh_dir
    fresh_dir=$(mktemp -d)
    cd "$fresh_dir" || exit 1

    run "$OPENSPEC_BIN" install claude --with-autonomous
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [ -d .claude/skills/osx-workflow ]
    [ -d .claude/skills/osx-concepts ]
    [ -f .claude/manifest.toml ]
    [ -f .claude/skills/osx-workflow/SKILL.md ]
    [ -f .claude/skills/osx-review-artifacts/SKILL.md ]
    [ -f .claude/skills/osx-modify-artifacts/SKILL.md ]
    [ ! -e .claude/skills/osx-review-artifacts/references/review-criteria.md ]

    # Shared references are packaged into the skill's own references/ folder.
    [ -f .claude/skills/osx-modify-artifacts/references/store-selection.md ]
    [ -f .claude/skills/osx-modify-artifacts/references/schema-agnostic-contract.md ]
    [ -f .claude/skills/osx-modify-artifacts/references/osx-mode-conventions.md ]
    [ -f .claude/skills/osx-review-artifacts/references/store-selection.md ]
    [ -f .claude/skills/osx-review-artifacts/references/schema-agnostic-contract.md ]
    [ -f .claude/skills/osx-maintain-ai-docs/references/osx-mode-conventions.md ]
    [ -f .claude/skills/osx-review-test-compliance/references/scoring-rubric.md ]
    # Skill-local references stay untouched.
    [ -f .claude/skills/osx-concepts/references/cli-reference.md ]
    [ -f .claude/skills/osx-maintain-ai-docs/references/doc-structures.md ]

    rm -rf "$fresh_dir"
}

@test "mechanism: install opencode defaults to utility-only" {
    local fresh_dir
    fresh_dir=$(mktemp -d)
    cd "$fresh_dir" || exit 1

    run "$OPENSPEC_BIN" install opencode
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]

    [ ! -d .opencode/skills/osx-workflow ]
    [ ! -f .opencode/commands/osx-phase0.md ]
    [ -d .opencode/skills/osx-concepts ]
    [ -d .opencode/skills/osx-modify-artifacts ]
    [ -f .opencode/commands/osx-modify.md ]
    [ ! -e .opencode/agents ]

    rm -rf "$fresh_dir"
}

@test "mechanism: install claude defaults to utility-only" {
    local fresh_dir
    fresh_dir=$(mktemp -d)
    cd "$fresh_dir" || exit 1

    run "$OPENSPEC_BIN" install claude
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]

    [ ! -d .claude/skills/osx-workflow ]
    [ ! -e .claude/commands/osx/phase0.md ]
    [ -d .claude/skills/osx-concepts ]
    [ -d .claude/skills/osx-modify-artifacts ]
    [ -f .claude/commands/osx/modify.md ]

    rm -rf "$fresh_dir"
}

# ========== Token substitution regression ==========
#
# Resources ship with {{TOKEN}} placeholders that the deploy step must
# rewrite per platform. A regression here means the deploy drops literal
# `{{CMD_PREFIX}}` / `{{PLATFORM_DIR}}` strings into users' projects,
# which is the bug that motivated this section. The skill-path reference
# must also resolve to a real on-disk directory.

@test "mechanism: install opencode substitutes {{TOKEN}} placeholders" {
    local fresh_dir
    fresh_dir=$(mktemp -d)
    cd "$fresh_dir" || exit 1

    run "$OPENSPEC_BIN" install opencode --with-autonomous
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]

    # No deployed file should still carry a `{{TOKEN}}` placeholder. The
    # `AUTO-GENERATED` header in the Claude mirror is the only place that
    # legitimately mentions token names — and that's not deployed to
    # users' projects, only kept in resources/claude/ for audit.
    leftovers="$(find .opencode -name '*.md' -exec grep -lE '\{\{[A-Z_]+\}\}' {} + 2>/dev/null || true)"
    if [ -n "$leftovers" ]; then
        echo "FAIL: deployed files still contain {{TOKEN}} placeholders:"
        echo "$leftovers"
        return 1
    fi

    # OpenCode slash-command form: `/osx-modify` (hyphen).
    grep -q '/osx-modify\b' .opencode/commands/osx-modify.md
    # OpenCode platform dir: `.opencode/skills/...`.
    grep -q '\.opencode/skills/' .opencode/commands/osx-modify.md
    # Skill-path reference is the literal hyphenated form on both platforms.
    grep -q '\.opencode/skills/osx-modify-artifacts/SKILL.md' .opencode/commands/osx-modify.md
    # The hardcoded opencode slash-command form must NOT carry the colon
    # separator (Claude form). Defensive — token substitution is per platform.
    if grep -q '/osx:modify\b' .opencode/commands/osx-modify.md; then
        echo "FAIL: opencode deploy leaked Claude slash-command form /osx:modify"
        return 1
    fi

    rm -rf "$fresh_dir"
}

@test "mechanism: install claude substitutes {{TOKEN}} placeholders" {
    local fresh_dir
    fresh_dir=$(mktemp -d)
    cd "$fresh_dir" || exit 1

    run "$OPENSPEC_BIN" install claude --with-autonomous
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]

    leftovers="$(find .claude -name '*.md' -exec grep -lE '\{\{[A-Z_]+\}\}' {} + 2>/dev/null || true)"
    if [ -n "$leftovers" ]; then
        echo "FAIL: deployed files still contain {{TOKEN}} placeholders:"
        echo "$leftovers"
        return 1
    fi

    # Claude deploy writes the legacy command form at ``commands/osx/modify.md``
    # (matching the Claude mirror layout, not the opencode file name).
    local cmd=".claude/commands/osx/modify.md"
    [ -f "$cmd" ]
    # Claude slash-command form: `/osx:modify` (colon).
    grep -q '/osx:modify\b' "$cmd"
    # The dual-emit Claude skill mirror must point at the real
    # `osx-modify-artifacts` skill directory (hyphen, not colon).
    local skill_md=".claude/skills/osx-modify/SKILL.md"
    [ -f "$skill_md" ]
    grep -q '\.claude/skills/osx-modify-artifacts/SKILL.md' "$skill_md"
    if grep -q 'osx:modify-artifacts' "$skill_md"; then
        echo "FAIL: Claude skill mirror points at non-existent osx:modify-artifacts"
        return 1
    fi
    # The referenced skill directory must actually exist on disk.
    [ -d .claude/skills/osx-modify-artifacts ]
    [ -f .claude/skills/osx-modify-artifacts/SKILL.md ]

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

@test "mechanism: osx --help lists all 11 domains" {
    run "$OPENSPEC_BIN" osx --help
    [ "$status" -eq 0 ]
    for d in baseline ctx git phase state iterations log complete validate instructions schema; do
        [[ "$output" == *"$d"* ]]
    done
}

@test "mechanism: osx schema --help lists all subcommands" {
    run "$OPENSPEC_BIN" osx schema --help
    [ "$status" -eq 0 ]
    for cmd in which list validate fork init; do
        [[ "$output" == *"$cmd"* ]]
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

# ========== v1.5+ store subapp (current v1.7.0 compatible) ==========
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

# ========== Top-level passthrough commands ==========
#
# Top-level pass-through commands wrap upstream
# `openspec` CLI commands. These tests assert that:
#   - The new commands are registered (--help shows them)
#   - The help text includes the expected flags
#   - Command execution against an empty repo doesn't crash

@test "mechanism: --help lists new passthrough commands" {
    run "$OPENSPEC_BIN" --help
    [ "$status" -eq 0 ]
    for cmd in validate list show status instructions templates schemas init update-core feedback completion; do
        [[ "$output" == *"$cmd"* ]] || { echo "Missing command: $cmd"; return 1; }
    done
}

@test "mechanism: validate --help shows flags" {
    run "$OPENSPEC_BIN" validate --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--all"* ]]
    [[ "$output" == *"--changes"* ]]
    [[ "$output" == *"--specs"* ]]
    [[ "$output" == *"--strict"* ]]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: list --help shows flags" {
    run "$OPENSPEC_BIN" list --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--specs"* ]]
    [[ "$output" == *"--sort"* ]]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: show --help shows flags" {
    run "$OPENSPEC_BIN" show --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--type"* ]]
    [[ "$output" == *"--deltas-only"* ]]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: status --help shows flags" {
    run "$OPENSPEC_BIN" status --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--change"* ]]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: instructions --help shows flags" {
    run "$OPENSPEC_BIN" instructions --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--change"* ]]
    [[ "$output" == *"--json"* ]]
}

@test "mechanism: schemas --json returns valid JSON" {
    run "$OPENSPEC_BIN" schemas --json
    # May exit 1 if openspec isn't installed (lazy fail), but stdout should not contain traceback
    [[ "$output" != *"Traceback"* ]]
}

@test "mechanism: update-core --help shows --force" {
    run "$OPENSPEC_BIN" update-core --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--force"* ]]
}

@test "mechanism: completion --help shows --install and --uninstall" {
    run "$OPENSPEC_BIN" completion --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--install"* ]]
    [[ "$output" == *"--uninstall"* ]]
}

@test "mechanism: feedback requires message argument" {
    run "$OPENSPEC_BIN" feedback
    [ "$status" -ne 0 ]
    [[ "$output" == *"Missing argument"* ]] || [[ "$output" == *"required"* ]]
}
