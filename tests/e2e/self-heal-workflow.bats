#!/usr/bin/env bats
# E2E self-heal PHASE0 tests — exercise the engine's auto-fix dispatch
# loop on a fixture that ships with deliberate PHASE0 findings. Catches
# the regression where the engine halted on `/osc-update-change`
# instead of self-dispatching.
#
# Scoped to PHASE0 via `--to-phase=PHASE0` to keep runtime short
# (~3-5 min vs ~20 min for the full 7-phase suite in
# full-workflow.bats). The PHASE0 audit + auto-fix dispatch is the
# regression; PHASE1+ don't add signal.
#
# Requires E2E_CONFIRM=1 to run (uses real AI calls).

load 'helpers/e2e-helpers'

# Per-phase AI subprocess timeout. PHASE0 with auto-fix dispatch and
# re-review fits comfortably under 1200s (20 min).
E2E_TIMEOUT=1200

# File-level shared state
SHARED_CHANGE_DIR=""
SHARED_CHANGE_NAME="add-self-heal-script"
SHARED_WORKFLOW_RAN=false
SHARED_ORCHESTRATE_LOG=""

setup_file() {
    require_e2e_confirm
    setup_shared_e2e_dir

    if [[ "${E2E_SKIP_ORCHESTRATOR:-}" == "1" ]]; then
        E2E_DIR="${E2E_DIR:?must set E2E_DIR when E2E_SKIP_ORCHESTRATOR=1}"
        cd "$E2E_DIR" || exit 1
        export E2E_DIR

        SHARED_CHANGE_NAME="${E2E_CHANGE_NAME:-add-self-heal-script}"
        SHARED_CHANGE_DIR="openspec/changes/$SHARED_CHANGE_NAME"
        if [[ ! -d "$SHARED_CHANGE_DIR" ]]; then
            echo "E2E_SKIP_ORCHESTRATOR=1: no active change dir at $SHARED_CHANGE_DIR" >&2
            exit 1
        fi
        save_e2e_state_phase0 "$SHARED_CHANGE_DIR" "$SHARED_CHANGE_NAME" "true"
        return 0
    fi

    setup_e2e_repo
    copy_fixture "$SHARED_CHANGE_NAME"

    # Run PHASE0 only (--to-phase=PHASE0 short-circuits the engine after
    # the audit + auto-fix dispatch + re-review completes successfully).
    run_osx_orchestrate_streaming "$SHARED_CHANGE_NAME" \
        --force \
        --clean \
        --verbose \
        --to-phase=PHASE0 \
        --max-phase-iterations=10 \
        --timeout="$E2E_TIMEOUT"

    SHARED_CHANGE_DIR="openspec/changes/$SHARED_CHANGE_NAME"

    # Validate success by checking actual outcome, not just exit status
    # (Exit status can be unreliable due to background tee process).
    local state_file="$SHARED_CHANGE_DIR/state.json"
    if [[ -f "$state_file" ]] \
        && jq -e '.phase_complete == true and .phase == "PHASE0"' "$state_file" >/dev/null 2>&1; then
        SHARED_WORKFLOW_RAN=true
    elif [[ "$status" -ne 0 ]]; then
        local log_file
        log_file=$(ls -t .osx-orchestrate-*.log 2>/dev/null | head -1)
        if [[ -n "$log_file" ]] && grep -q "Halted for routed commands" "$log_file"; then
            echo "REGRESSION: PHASE0 halted with routes_pending" >&2
            echo "  This fixture (add-self-heal-script) ships with findings" >&2
            echo "  on EXISTING artifacts that the orchestrator's auto-fix" >&2
            echo "  dispatch must self-resolve. A halt here means the" >&2
            echo "  engine reverted to halting on /osc-update-change." >&2
            echo "" >&2
            echo "  Routes listed in the log:" >&2
            grep -E '^\[[A-Z]+\][[:space:]]+-[[:space:]]+/' "$log_file" |
                sed 's/^/    /' >&2 || true
        else
            echo "PHASE0 did not complete (status=$status)." >&2
            if [[ -n "$log_file" ]]; then
                echo "See $log_file for the orchestrator's log." >&2
            fi
        fi
        exit 1
    else
        echo "Workflow exited 0 but state.json does not show PHASE0 complete." >&2
        exit 1
    fi

    # Save shared state to JSON file for test access
    save_e2e_state_phase0 "$SHARED_CHANGE_DIR" "$SHARED_CHANGE_NAME" "$SHARED_WORKFLOW_RAN"
}

setup() {
    load_e2e_state
}

teardown_file() {
    rm -f .e2e-state.json
    teardown_e2e_repo
    teardown_shared_e2e_dir
}

# ============================================================================
# Category 1: PHASE0 completion
# ============================================================================

@test "phase0: completed successfully despite initial findings" {
    # Direct regression sentinel for the `library-state-status` bug.
    # If the engine halted on /osc-update-change instead of self-fixing,
    # state.json would not show phase_complete=true.
    [ "$SHARED_WORKFLOW_RAN" = "true" ]
    [ -n "$SHARED_CHANGE_DIR" ]
    [ -d "$SHARED_CHANGE_DIR" ]
    local state_file="$SHARED_CHANGE_DIR/state.json"
    [ -f "$state_file" ]
    jq -e '.phase_complete == true' "$state_file" >/dev/null
    jq -e '.phase == "PHASE0"' "$state_file" >/dev/null
}

# ============================================================================
# Category 2: PHASE0 self-healing (regression sentinels)
# ============================================================================

@test "phase0: no halt-for-routed-commands for autofixable route" {
    # THE regression sentinel for the `library-state-status` bug.
    #
    # The fixture ships with PHASE0 findings on existing artifacts that
    # resolve to /osc-update-change. The engine MUST auto-dispatch the
    # fix (not halt). If the engine ever reverts to halt-on-every-route,
    # this test fails with a clear message.
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    [ -f "$log_file" ]

    if grep -q "Halted for routed commands" "$log_file"; then
        echo "REGRESSION: PHASE0 halted with routes_pending" >&2
        echo "  The orchestrator should have auto-dispatched the fix" >&2
        echo "  instead of halting. See engine._run_auto_fix and" >&2
        echo "  engine.AUTO_FIXABLE_ROUTES for the contract." >&2
        grep -E '^\[[A-Z]+\][[:space:]]+-[[:space:]]+/' "$log_file" |
            sed 's/^/    /' >&2 || true
        return 1
    fi
}

@test "phase0: routed to osc-update-change (autofixable route)" {
    # Confirms the fixture actually triggered the auto-fixable route.
    # If the audit produced no findings, this fixture would be testing
    # nothing — we want at least one /osc-update-change route emission
    # to prove the auto-fix dispatch was exercised.
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    [ -f "$log_file" ]

    # The route should appear in the log either as a set-routes call
    # (initial PHASE0 audit) or as an auto-fix invocation.
    if ! grep -qE "(set-routes.*osc-update-change|Auto-fix invocation.*osc-update-change)"; then
        echo "EXPECTED: PHASE0 should emit /osc-update-change (auto-fixable)" >&2
        echo "  for this fixture's findings. If no such route is in the" >&2
        echo "  log, the fixture may need findings seeded differently" >&2
        echo "  to exercise the auto-fix path." >&2
        return 1
    fi
}

@test "phase0: auto-fix dispatch logged" {
    # Proves the engine actually invoked the auto-fix, not just emitted
    # the route. The "Auto-fix invocation" log line is emitted by
    # engine._run_auto_fix when it spawns the subprocess.
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    [ -f "$log_file" ]

    if ! grep -qE "Auto-fix invocation.*osc-update-change"; then
        echo "EXPECTED: engine._run_auto_fix should log an 'Auto-fix" >&2
        echo "  invocation' line for /osc-update-change. If missing, the" >&2
        echo "  engine's auto-fix dispatch did not fire." >&2
        return 1
    fi
}

@test "phase0: slash command resolved by pre-check" {
    # The engine's pre-check (added to fix the airk regression)
    # logs "Slash command resolved to <path>" before spawning. If the
    # pre-check fails, the engine halts with a clear error message
    # naming the missing file — that's the failure mode we want to
    # surface here.
    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    [ -f "$log_file" ]

    if grep -qE "slash command file not found"; then
        echo "FAIL: engine pre-check reports missing slash command." >&2
        echo "  This is the regression where the deployed slash command" >&2
        echo "  is named differently from what the engine routes to." >&2
        echo "  Re-run \`openspec-extended install opencode\` to deploy" >&2
        echo "  the canonical slash commands." >&2
        return 1
    fi
}

# ============================================================================
# Category 3: Iterations tracking (multiple PHASE0 entries = re-review)
# ============================================================================

@test "iterations: PHASE0 ran multiple times (auto-fix re-review)" {
    # The auto-fix dispatch is followed by a re-entry into PHASE0 to
    # verify the change is now coherent. We expect at least 2
    # ARTIFACT_REVIEW entries: the initial audit + the post-fix re-audit.
    local iterations_file="$SHARED_CHANGE_DIR/iterations.json"
    [ -f "$iterations_file" ]
    local count
    count=$(jq '[.[] | select(.phase == "ARTIFACT_REVIEW")] | length' "$iterations_file")
    [[ "$count" -ge 2 ]] || {
        echo "Expected ≥2 ARTIFACT_REVIEW entries (initial audit + re-audit after auto-fix); got $count"
        return 1
    }
}

@test "iterations: respects max-phase-iterations limit" {
    # Auto-fix loop must not run unbounded. Cap is set to 10 via the
    # bats invocation; PHASE0 should not exceed it.
    local iterations_file="$SHARED_CHANGE_DIR/iterations.json"
    [ -f "$iterations_file" ]
    local count
    count=$(jq '[.[] | select(.phase == "ARTIFACT_REVIEW")] | length' "$iterations_file")
    [[ "$count" -le 10 ]] || {
        echo "PHASE0 exceeded max iterations: $count"
        return 1
    }
}

# ============================================================================
# Category 4: Decision log (auto-fix bookkeeping)
# ============================================================================

@test "decision-log: contains auto-fix iteration entry" {
    # The auto-fix dispatch writes a decision-log entry summarizing
    # what changed. Without this entry, the auto-fix happened silently.
    local decision_log="$SHARED_CHANGE_DIR/decision-log.json"
    [ -f "$decision_log" ]
    local count
    count=$(jq '[.[] | select(.phase == "ARTIFACT_REVIEW")] | length' "$decision_log")
    [[ "$count" -ge 2 ]] || {
        echo "Expected ≥2 ARTIFACT_REVIEW entries in decision-log (initial + post-fix); got $count"
        return 1
    }
}

@test "decision-log: last entry mentions auto-fix or reconciliation" {
    # The post-fix decision-log entry should mention the reconciliation
    # action. This is a heuristic — it accepts any of the standard
    # phrasings the osx-editor agent might use.
    local decision_log="$SHARED_CHANGE_DIR/decision-log.json"
    [ -f "$decision_log" ]
    local last_entry
    last_entry=$(jq '.[-1]' "$decision_log")
    local summary
    summary=$(echo "$last_entry" | jq -r '.summary // ""')

    if ! echo "$summary" | grep -qiE "(auto.?fix|reconcil|osc-update-change|fix and re-review|re-review)"; then
        echo "Expected last decision-log summary to mention auto-fix/reconciliation." >&2
        echo "  Got: $summary" >&2
        return 1
    fi
}

# ============================================================================
# Category 5: Auto-fix actually changed things
# ============================================================================

@test "auto-fix: proposal.md exit-code mismatch was corrected" {
    # The fixture's proposal.md says "code 0 on invalid flags" (wrong).
    # design.md and spec.md say "code 1" (correct). The auto-fix must
    # edit proposal.md so all three artifacts agree on the exit code.
    #
    # We assert the post-fix proposal.md says "code 1 on invalid flags"
    # at the relevant section. If this fails, the auto-fix did NOT
    # reconcile the contradiction (or didn't fire at all).
    local proposal="$SHARED_CHANGE_DIR/proposal.md"
    [ -f "$proposal" ]
    if ! grep -qE "code.*1.*invalid|exit.*1.*invalid|invalid.*code.*1|invalid.*exit.*1" "$proposal"; then
        echo "Auto-fix did not reconcile the exit-code contradiction in proposal.md" >&2
        echo "  Expected proposal.md to consistently say 'code 1 on invalid flags'" >&2
        echo "  (matching design.md and spec.md). Got:" >&2
        grep -E "exit|invalid" "$proposal" | sed 's/^/    /' >&2 || true
        return 1
    fi
}

@test "auto-fix: design.md exit-code policy was not regressed" {
    # Symmetric sentinel: design.md should still say "code 1 on invalid
    # flags" in its Decisions section. If the auto-fix accidentally
    # regressed design.md while reconciling, this fails.
    local design="$SHARED_CHANGE_DIR/design.md"
    [ -f "$design" ]
    if ! grep -qE "Exit code 1 on invalid flags|code 1.*invalid" "$design"; then
        echo "design.md no longer states the correct exit code policy." >&2
        echo "  This is a regression of the design itself, not the auto-fix." >&2
        return 1
    fi
}

# ============================================================================
# Category 6: Git history
# ============================================================================

@test "git: at least one commit during PHASE0 auto-fix loop" {
    # The auto-fix dispatch writes a milestone commit via osx-commit.
    # If no commits exist for this change, the auto-fix didn't actually
    # apply changes.
    local commits
    commits=$(git log --oneline -- openspec/changes/add-self-heal-script/ 2>/dev/null | wc -l)
    [[ "$commits" -ge 2 ]] || {
        echo "Expected ≥2 commits (fixture copy + auto-fix milestone); got $commits"
        return 1
    }
}

# ============================================================================
# Category 7: --to-phase short-circuit (PHASE1 not entered)
# ============================================================================

@test "to-phase: PHASE1 was not entered" {
    # --to-phase=PHASE0 must short-circuit the engine after PHASE0.
    # If PHASE1 ran, the iterations.json would have IMPLEMENTATION
    # entries and the log would not show the to-phase completion banner.
    local iterations_file="$SHARED_CHANGE_DIR/iterations.json"
    [ -f "$iterations_file" ]
    local count
    count=$(jq '[.[] | select(.phase == "IMPLEMENTATION")] | length' "$iterations_file")
    [[ "$count" -eq 0 ]] || {
        echo "PHASE1 ran despite --to-phase=PHASE0 (IMPLEMENTATION entries: $count)"
        return 1
    }

    local log_file
    log_file=$(get_log_file "$SHARED_CHANGE_NAME")
    [ -n "$log_file" ]
    [ -f "$log_file" ]
    grep -q "PHASE0 completed (to-phase reached)" "$log_file" || {
        echo "Log missing to-phase completion banner; engine may not be honoring --to-phase"
        return 1
    }
}
