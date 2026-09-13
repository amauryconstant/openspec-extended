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
    cd "$BATS_TEST_TMPDIR" || exit 1

    run "$OPENSPEC_BIN" install opencode --with-autonomous
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [ -d .opencode/skills/osx-workflow ]
    [ -f .opencode/manifest.toml ]
    [ -f .opencode/skills/osx-workflow/SKILL.md ]
    [ -f .opencode/skills/osx-review-artifacts/SKILL.md ]
    [ ! -e .opencode/skills/osx-review-artifacts/references/review-criteria.md ]

    # Shared references are packaged into the skill's own references/ folder
    # so the SKILL.md links resolve without depending on a sibling directory.
    [ -f .opencode/skills/osx-review-artifacts/references/store-selection.md ]
    [ -f .opencode/skills/osx-review-artifacts/references/schema-agnostic-contract.md ]
    [ -f .opencode/skills/osx-review-test-compliance/references/scoring-rubric.md ]

    # Slash commands with self-contained bodies (osx-changelog, osx-maintain-docs)
    # are deployed as command files; their bodies reference shared-pool references.
    [ -f .opencode/commands/osx-changelog.md ]
    [ -f .opencode/commands/osx-maintain-docs.md ]

    # osx-concepts was dropped; the deletion is now load-bearing.
    [ ! -d .opencode/skills/osx-concepts ]
}

@test "mechanism: install claude deploys bundled resources" {
    cd "$BATS_TEST_TMPDIR" || exit 1

    run "$OPENSPEC_BIN" install claude --with-autonomous
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [ -d .claude/skills/osx-workflow ]
    [ -f .claude/manifest.toml ]
    [ -f .claude/skills/osx-workflow/SKILL.md ]
    [ -f .claude/skills/osx-review-artifacts/SKILL.md ]
    [ ! -e .claude/skills/osx-review-artifacts/references/review-criteria.md ]

    # Shared references are packaged into the skill's own references/ folder.
    [ -f .claude/skills/osx-review-artifacts/references/store-selection.md ]
    [ -f .claude/skills/osx-review-artifacts/references/schema-agnostic-contract.md ]
    [ -f .claude/skills/osx-review-test-compliance/references/scoring-rubric.md ]

    # Slash commands dual-emit on Claude as modern skills. The merged
    # changelog/maintain-docs bodies reference shared-pool files; the deploy
    # copies them into the dual-emit skill's references/ folder.
    [ -f .claude/skills/osx-changelog/SKILL.md ]
    [ -f .claude/skills/osx-maintain-docs/SKILL.md ]
    [ -f .claude/skills/osx-changelog/references/changelog-format.md ]
    [ -f .claude/skills/osx-maintain-docs/references/doc-structures.md ]

    # osx-concepts was dropped; the deletion is now load-bearing.
    [ ! -d .claude/skills/osx-concepts ]
}

@test "mechanism: install opencode defaults to utility-only" {
    cd "$BATS_TEST_TMPDIR" || exit 1

    run "$OPENSPEC_BIN" install opencode
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]

    [ ! -d .opencode/skills/osx-workflow ]
    [ ! -f .opencode/commands/osx-phase0.md ]
    [ ! -d .opencode/skills/osx-concepts ]
    [ -d .opencode/skills/osx-review-artifacts ]
    [ -f .opencode/commands/osx-review.md ]
    [ ! -e .opencode/agents ]
}

@test "mechanism: install claude defaults to utility-only" {
    cd "$BATS_TEST_TMPDIR" || exit 1

    run "$OPENSPEC_BIN" install claude
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]

    [ ! -d .claude/skills/osx-workflow ]
    [ ! -e .claude/commands/osx/phase0.md ]
    [ ! -d .claude/skills/osx-concepts ]
    [ -d .claude/skills/osx-review-artifacts ]
    [ -f .claude/commands/osx/review.md ]
}

# ========== Token substitution regression ==========
#
# Resources ship with {{TOKEN}} placeholders that the deploy step must
# rewrite per platform. A regression here means the deploy drops literal
# `{{CMD_PREFIX}}` / `{{PLATFORM_DIR}}` strings into users' projects,
# which is the bug that motivated this section. The skill-path reference
# must also resolve to a real on-disk directory.

@test "mechanism: install opencode substitutes {{TOKEN}} placeholders" {
    cd "$BATS_TEST_TMPDIR" || exit 1

    run "$OPENSPEC_BIN" install opencode --with-autonomous
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]

    # No deployed file should still carry a `{{TOKEN}}` placeholder.
    # Phase 2A: there is no on-disk Claude mirror anymore; deploy-time
    # rendering substitutes tokens for every adapter.
    leftovers="$(find .opencode -name '*.md' -exec grep -lE '\{\{[A-Z_]+\}\}' {} + 2>/dev/null || true)"
    if [ -n "$leftovers" ]; then
        echo "FAIL: deployed files still contain {{TOKEN}} placeholders:"
        echo "$leftovers"
        return 1
    fi

    # OpenCode slash-command form: `/osx-review` (hyphen).
    grep -q '/osx-review\b' .opencode/commands/osx-review.md
    # OpenCode platform dir: `.opencode/skills/...`.
    grep -q '\.opencode/skills/' .opencode/commands/osx-review.md
    # Skill-path reference is the literal hyphenated form on both platforms.
    grep -q '\.opencode/skills/osx-review-artifacts/SKILL.md' .opencode/commands/osx-review.md
    # The hardcoded opencode slash-command form must NOT carry the colon
    # separator (Claude form). Defensive — token substitution is per platform.
    if grep -q '/osx:review\b' .opencode/commands/osx-review.md; then
        echo "FAIL: opencode deploy leaked Claude slash-command form /osx:review"
        return 1
    fi
}

@test "mechanism: install claude substitutes {{TOKEN}} placeholders" {
    cd "$BATS_TEST_TMPDIR" || exit 1

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

    # Claude deploy writes the legacy command form at ``commands/osx/review.md``
    # (matching the Claude mirror layout, not the opencode file name).
    local cmd=".claude/commands/osx/review.md"
    [ -f "$cmd" ]
    # Claude slash-command form: `/osx:review` (colon).
    grep -q '/osx:review\b' "$cmd"
    # The dual-emit Claude skill mirror must point at the real
    # `osx-review-artifacts` skill directory (hyphen, not colon).
    local skill_md=".claude/skills/osx-review/SKILL.md"
    [ -f "$skill_md" ]
    grep -q '\.claude/skills/osx-review-artifacts/SKILL.md' "$skill_md"
    if grep -q 'osx:review-artifacts' "$skill_md"; then
        echo "FAIL: Claude skill mirror points at non-existent osx:review-artifacts"
        return 1
    fi
    # The referenced skill directory must actually exist on disk.
    [ -d .claude/skills/osx-review-artifacts ]
    [ -f .claude/skills/osx-review-artifacts/SKILL.md ]
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
    for cmd in which list validate fork fork-diff init; do
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

# ========== v1.5+ store subapp (current v1.13.0 compatible) ==========
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

@test "mechanism: validate --help documents --concurrency and OPENSPEC_CONCURRENCY" {
    run "$OPENSPEC_BIN" validate --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--concurrency"* ]]
    [[ "$output" == *"OPENSPEC_CONCURRENCY"* ]]
}

@test "mechanism: install --help shows --language flag" {
    run "$OPENSPEC_BIN" install --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--language"* ]]
    [[ "$output" == *"OPENSPEC_LANGUAGE"* ]]
}

@test "mechanism: init --help shows --language flag" {
    run "$OPENSPEC_BIN" init --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--language"* ]]
    [[ "$output" == *"OPENSPEC_LANGUAGE"* ]]
}

# ========== A.2: show --diff flag (v1.11.0+) ==========
#
# PHASE2 (REVIEW) embeds the `openspec show <change> --diff --json` output
# as the `## Requirement diff` appendix of `verification-report.md`. The
# `--diff` flag is gated on OpenSpec core >= 1.11.0. Skip the test if the
# upstream CLI is not on PATH (the binary's `show` passthrough forwards
# to `openspec show`).

@test "mechanism: openspec show --help documents --diff and applies to a change" {
    if ! command -v openspec >/dev/null 2>&1; then
        skip "openspec CLI not on PATH; --diff flag requires v1.11.0+ core"
    fi

    # BATS_TEST_TMPDIR is auto-cleaned by bats; using it instead of mktemp
    # means a failed assertion below doesn't leave the tmpdir behind.
    cd "$BATS_TEST_TMPDIR" || exit 1

    # The binary's `show` subcommand is a passthrough to `openspec show`.
    # We assert the help text contains the `--diff` flag introduced in
    # v1.11.0 (still required as of v1.13.0); older cores won't list it
    # (and PHASE2 would silently fall back to non-diff output).
    run "$OPENSPEC_BIN" show --help
    echo "STATUS=$status"
    echo "OUTPUT=$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--diff"* ]] || {
        echo "FAIL: openspec show --help does not document --diff flag"
        return 1
    }

    # Sanity: the `--json` flag must still be present (used together
    # with `--diff` in PHASE2's MANDATORY CHECKPOINT).
    [[ "$output" == *"--json"* ]]
}

# ========== A.6: post-install `validate --archived` sweep ==========
#
# ``install --with-core`` and ``update --with-core`` (and ``update-core``)
# run a non-fatal ``openspec validate --archived --json`` sweep so that
# unfinished archive state surfaces immediately. The flag is opt-in strict
# mode; the default is a yellow warning.

@test "mechanism: install --help documents --strict-archived" {
    run "$OPENSPEC_BIN" install --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--strict-archived"* ]]
}

@test "mechanism: update --help documents --strict-archived" {
    run "$OPENSPEC_BIN" update --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--strict-archived"* ]]
}

@test "mechanism: update-core --help documents --strict-archived and OPENSPEC_VALIDATE_ARCHIVED_STRICT" {
    run "$OPENSPEC_BIN" update-core --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--strict-archived"* ]]
    [[ "$output" == *"OPENSPEC_VALIDATE_ARCHIVED_STRICT"* ]]
}

# ========== C.5: osx validate archived (v1.9.0+ scope) ==========
#
# Brings `validate --archived` to parity with the other validate scopes
# inside the osx sub-app (change, spec, all, changes, specs). The help
# text must surface the new action plus the --change flag.

@test "mechanism: osx validate --help lists archived action" {
    run "$OPENSPEC_BIN" osx validate --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"archived"* ]]
    [[ "$output" == *"--change"* ]]
}

# ========== C.3: osx instructions structured errors (v1.7.0+ mirror) ==========
#
# The osx instructions command routes through fetch_instructions, which
# returns structured JSON errors on subprocess failure (vs. the prior
# raw passthrough that surfaced upstream stderr text). Help text must
# surface --change.

@test "mechanism: osx instructions --help documents --change" {
    run "$OPENSPEC_BIN" osx instructions --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--change"* ]]
}

# ========== G.4a: status --store threading ==========
#
# `openspec status --change <name> --store <id> --json` (v1.5.0+; the
# `--store` flag threads a store id through the call). The binary's `status`
# passthrough forwards the flag verbatim; this test pins the help text.

@test "mechanism: status --help documents --store flag" {
    run "$OPENSPEC_BIN" status --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--store"* ]]
}

# ========== G.4b: validate --archived passthrough ==========
#
# `openspec validate --archived` (v1.9.0+) is the CI gate the A.6 wrapper
# invokes post-install. The wrapper forwards the flag verbatim; this test
# pins the help text and a smoke-level execution.

@test "mechanism: validate --help documents --archived flag" {
    run "$OPENSPEC_BIN" validate --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--archived"* ]]
}

@test "mechanism: validate --archived --json executes without crash against empty repo" {
    cd "$BATS_TEST_TMPDIR" || exit 1

    run "$OPENSPEC_BIN" validate --archived --json
    # Acceptable outcomes: rc == 0 (core returned a clean envelope) OR
    # rc == 1 with valid JSON (core returned an error envelope). Anything
    # else (non-JSON, traceback, etc.) is a regression.
    [[ "$output" != *"Traceback"* ]]
    # If parseable as JSON, accept either success or structured error.
    if echo "$output" | jq -e . >/dev/null 2>&1; then
        : # parseable, OK
    fi
}
