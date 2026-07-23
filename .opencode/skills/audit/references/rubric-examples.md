# Rubric Examples

Project-specific anchors used by Phase E to classify findings. Refresh per audit: when prior findings no longer apply (fixed, drifted, or no longer reachable), remove or replace them. When new finding shapes appear, add them here.

## False-Positive Guards

These look like findings but are intentional. Do not flag:

- **Different version domains across files** — project version (`source/__init__.py`), installer version (`install.sh` `SCRIPT_VERSION`), resource versions (`resources/*/manifest.toml`). Separation is by design; do not flag the divergence.
- **Prefix collisions across surfaces** — distinct namespaces for upstream and local resources. Do not flag the collision; flag a missing or wrong prefix.
- **`mode` declarations in non-dispatched agents** — only flag when the orchestrator dispatches the agent (see engine dispatch table).
- **Shared or duplicated constants** — known MEDIUM at most; do not escalate.
- **Documentation that lists resource counts above the deployable manifest** — the picker may show fewer if delivery mode restricts it; user-controlled.
- **Skill references to taxonomy counts** — the count taxonomy is part of the contract; do not flag it as drift unless the count itself is wrong.

## Worked Findings

Anchors for assigning severity to new findings at the same shape.

### CRITICAL

1. **`osx store register --name` should be `--id`**
   `source/lib/osx.py` builds `["--name", name]`; upstream `openspec store register` accepts only `--id` (`openspec-core/source/src/commands/store.ts`). The unit test at `tests/unit/test_store_domain.py` cements the wrong behavior by mocking subprocess. Fix: rename flag; update test.

2. **PHASE2 / PHASE5 permission contradiction**
   `resources/opencode/agents/osx-analyzer.md` declares `edit: deny`, but PHASE2 and PHASE5 instruct the agent to write `verification-report.md`, `suggestions.md`, `reflections.md`, and commit. Fix: switch both phases to `osx-maintainer`, or introduce a reviewer agent with `edit: allow`.

3. **PHASE6 deletes the orchestrator's auto-log before the engine archives it**
   PHASE6 command does `rm -f .osx-orchestrate-$1.log` before the agent invokes the archive command. The engine then runs `archive_log_file`, which tries to move that file. Move fails; archive commit is not amended. Fix: drop the explicit `rm -f`; let engine own cleanup.

4. **Preflight only runs under `--clean`**
   `source/orchestrator/engine.py` wraps most preflight inside `if state.clean:`. Normal first-run with no flag skips skill/command/git/change-structure validation, binary probe, baseline recording. Fix: extract preflight out of the `clean` gate; always run.

5. **Cross-platform preflight checks the wrong binary**
   `source/orchestrator/engine.py` probes `opencode` even when Claude is the active platform. Fix: derive platform from `OrchestratorState.platform`; gate binary check accordingly.

6. **`osx state transition` positional binding wrong**
   `source/osx_cli.py` declares Typer positionals `action, change, phase, target, reason, details`; `transition` ignores `phase` so documented invocation passes the wrong arguments. Fix: refactor to `--target/--reason/--details` options.

### HIGH

7. **Three agents declare `mode: all` but convention says `mode: subagent`**
   `resources/opencode/agents/{analyzer,builder,maintainer}.md`; convention at `resources/opencode/agents/AGENTS.md`. Orchestrator-dispatched agents should not appear in user-driven pickers. Fix: `mode: subagent`; bump manifest versions.

8. **`REQUIRED_SKILLS` omits `osx-commit`**
   `source/lib/osx.py` declares 6 skills; manifest ships 8. `osx-commit` is referenced by every phase command but not preflight-required. Fix: include `osx-commit`; reconcile the doc; mark `osx-generate-changelog` optional.

9. **Stale command references in skills/commands**
   `skills/osx-generate-changelog/SKILL.md` references `/osx-apply`, `/osx-verify`, `/osx-archive` (do not exist; closest is `/osc-*`). Phase commands mix `/osx-modify` (extended) with `/opsx:update`/`/opsx:continue` (core, gets renamed). Fix: settle on `{{NAME}}` token resolved at install.

10. **`--with-core` non-destructive**
    `source/cli.py` runs `openspec init --force` without snapshotting prior state. Fix: snapshot global config; offer `--init-core` opt-in.

11. **No upstream version floor**
    `source/orchestrator/engine.py` only checks exit code of `openspec --version`, not version. With v1.4.x, `openspec-update-change` (v1.6.0) is absent and a phase command silently no-ops. Fix: parse version, enforce `>=1.6.0`.

12. **No live contract tests for upstream JSON shapes**
    Unit tests mock subprocess and never hit real upstream. Fix: `tests/contract/test_upstream_envelopes.py` snapshotting each `--json` shape.

13. **`state.child_pid` set after `runner.run()` returns**
    `source/orchestrator/engine.py`. SIGINT during AI subprocess may survive. Fix: capture PID before `wait()`.

14. **PHASE0 has no follow-through dispatch**
    `source/orchestrator/engine.py` reads `routed_to` from completion but does not call the routed command. Fix: when `state.complete.json.blocker=False` and `routed_to` is set, dispatch automatically.

### MEDIUM

15. **Phase constants duplicated**
    `source/lib/osx.py` and `source/orchestrator/engine.py` both define `PHASES`, `PHASE_NAMES`, `PHASE_COMMANDS`. Fix: single home in `lib/osx.py`; engine imports.

16. **Double `--json` in callers**
    `source/lib/osx.py` adds it; many callers also include it. Works today; fragile w.r.t. upstream Commander. Fix: audit each caller; remove literal `--json`.

17. **README counts and version literals stale**
    `README.md` lists counts and version numbers that have drifted. Fix: recount and refresh.

18. **`install.sh` example uses stale version**
    `install.sh` install example uses an outdated version pin. Fix: refresh to current version.

19. **`SCRIPT_VERSION` literal not alias of `__version__`**
    `source/cli.py` declares a literal `SCRIPT_VERSION`. Fix: `from source import __version__ as SCRIPT_VERSION`.

20. **`get_version()` reads nonexistent key**
    `source/orchestrator/engine.py` reads `resources.scripts.osx-orchestrate`. Fix: parse `pyproject.toml`.

21. **`.gitignore` patterns shadow archive**
    `source/cli.py` adds patterns that match `openspec/changes/*/iterations.json` even after archive. Fix: prefix archived paths with `!`.

22. **`complete_set` accepts BLOCKED without reason**
    `source/lib/osx.py` silently passes `BLOCKED` with no reason as `{status: "BLOCKED", with_blocker: false}`. Fix: raise `OSXError` when status=`BLOCKED` and no reason.

23. **Doc drift in skill references**
    `resources/opencode/skills/osx-concepts/references/cli-reference.md` pinned to old versions. Fix: refresh.

24. **Workflow skill stale**
    `resources/opencode/skills/osx-workflow/SKILL.md` lists `REQUIRED_SKILLS` and `validate` actions at outdated counts. Fix: sync with code.

### LOW

25. **Stale `osc log` references in agent prompts**
    `agents/osx-analyzer.md` and `agents/osx-builder.md` say `osc log`. Should be `openspec-extended osx log`. Fix: replace.

26. **PHASE0/PHASE2 "read-only" wording in `osx-workflow`**
    `resources/opencode/skills/osx-workflow/SKILL.md` says PHASE0/PHASE2 are "read-only routing phases" but PHASE2 writes `verification-report.md` and `suggestions.md`. Fix: mark PHASE2 as write-capable via delegated role.

27. **Engine reads/writes state.json directly**
    `source/orchestrator/engine.py` reads/writes state directly, contradicting `source/orchestrator/AGENTS.md`. Fix: pick a story; route all engine reads/writes through `osx_lib.state_*` or document the dual-write contract.

28. **`started_at` resets every write**
    `source/orchestrator/engine.py`. Should only set on first write. Fix.

29. **Iteration counter resets on resume**
    `source/orchestrator/engine.py`. Local iteration resets to 1; persisted iteration lives in `phase_iterations[phase]` only. Fix: read from state at phase start.

## Maintenance notes

- Refresh per audit. When a finding is fixed, move it here to "## Resolved History" or delete; do not leave stale anchors in the active list.
- When a new finding shape appears that does not fit any existing example, add it under the appropriate tier with a one-line summary and a citation.
- Keep citations to canonical file paths only. Line numbers drift; resolve them at audit time, not when writing this file.
