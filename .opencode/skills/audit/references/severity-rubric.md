# Severity Rubric

Use this rubric in Phase E (Synthesize) to assign severity to each finding. Tiers are ordered by blast radius: CRITICAL findings break the autonomous loop or produce silent failures; LOW findings are polish.

## Contents

- [Severity Tiers](#severity-tiers)
- [Worked Examples (anchored to prior audits)](#worked-examples-anchored-to-prior-audits)
- [False-Positive Guards](#false-positive-guards)
- [Citation Discipline](#citation-discipline)

## Severity Tiers

| Tier | Definition | Blast radius |
|------|------------|--------------|
| **CRITICAL** | Silent failure · autonomous-loop break · test cements wrong behavior · production bug | Users hit it on every run; orchestrator halts or loops forever |
| **HIGH** | Drift · dead references · version-gated silent no-op · missing contract test · permission contradiction · agent permission vs command body mismatch | Users hit it on edge cases; certain schema/version combos break |
| **MEDIUM** | Doc drift · version literal mismatch · missing preflight · double-flag · duplicated constants · verbosity | Confusing or wasteful; rarely breaks |
| **LOW** | Terminology · redundant comment · layout polish · style nit | Cosmetic; never breaks |

## Worked Examples (anchored to prior audits)

These are real findings from prior audits. Use them as anchors when classifying new findings. New findings at the same shape should receive the same tier.

### CRITICAL

1. **`osx store register --name` should be `--id`**
   `source/lib/osx.py:1076` builds `["--name", name]`; upstream `openspec store register` accepts only `--id` (`openspec-core/source/src/commands/store.ts:543-580`). The unit test at `tests/unit/test_store_domain.py:78-91` cements the wrong behavior by mocking subprocess. Fix: rename flag; update test.

2. **PHASE2 / PHASE5 permission contradiction**
   `resources/opencode/agents/osx-analyzer.md:7` declares `edit: deny`, but PHASE2 (`commands/osx-phase2.md:53-137`) and PHASE5 (`commands/osx-phase5.md:76-142`) instruct the agent to write `verification-report.md`, `suggestions.md`, `reflections.md`, and commit. Fix: switch both phases to `osx-maintainer`, or introduce an `osx-reviewer` with `edit: allow`.

3. **PHASE6 deletes the orchestrator's auto-log before the engine archives it**
   `commands/osx-phase6.md:50` does `rm -f .osx-orchestrate-$1.log` before the agent invokes `osc-archive-change`. The engine then runs `archive_log_file` at `engine.py:659-714`, which tries to `shutil.move` that file. Move fails; archive commit is not amended. Fix: drop the explicit `rm -f`; let engine own cleanup.

4. **Preflight only runs under `--clean`**
   `source/orchestrator/engine.py:930-989` wraps most preflight inside `if state.clean:`. Normal first-run with no flag skips skill/command/git/change-structure validation, jq/openspec/opencode probe, baseline recording. Fix: extract preflight out of the `clean` gate; always run.

5. **Claude preflight checks for `opencode`**
   `source/orchestrator/engine.py:975-979` calls `shutil.which("opencode")` even when Claude is the active platform. Fix: derive platform from `OrchestratorState.platform`; gate binary check accordingly.

6. **`osx state transition` positional binding wrong**
   `source/osx_cli.py:125-152` declares Typer positionals `action, change, phase, target, reason, details`; `transition` ignores `phase` so documented invocation `state transition <change> PHASE1 artifacts_modified "details"` passes `target=artifacts_modified, reason=details, details=None`. Fix: refactor to `--target/--reason/--details` options.

### HIGH

7. **Three agents declare `mode: all` but convention says `mode: subagent`**
   `resources/opencode/agents/{analyzer,builder,maintainer}.md:4`; convention at `resources/opencode/agents/AGENTS.md:34`. Orchestrator-dispatched agents should not appear in user-driven pickers. Fix: `mode: subagent`; bump manifest versions.

8. **`REQUIRED_SKILLS` omits `osx-commit`**
   `source/lib/osx.py:67-74`; `source/lib/AGENTS.md:60-66` lists 5, code declares 6, manifest ships 8. `osx-commit` is referenced by every phase command but not preflight-required. Fix: include `osx-commit`; reconcile the doc; mark `osx-generate-changelog` optional.

9. **Stale command references in skills/commands**
   `skills/osx-generate-changelog/SKILL.md:218-220` references `/osx-apply`, `/osx-verify`, `/osx-archive` (don't exist; closest is `/osc-*`). `commands/osx-phase0.md:48-49, 118-119` mixes `/osx-modify` (extended) with `/opsx:update`/`/opsx:continue` (core, gets renamed). Fix: settle on `{{NAME}}` token resolved at install.

10. **`--with-core` non-destructive**
    `source/cli.py:430-485` runs `openspec init --force` without snapshotting prior state. Fix: snapshot global config; offer `--init-core` opt-in.

11. **No upstream version floor**
    `source/orchestrator/engine.py:970` only checks exit code of `openspec --version`, not version. With v1.4.x, `openspec-update-change` (v1.6.0) is absent and `osx-phase2.md` Case A routing silently no-ops. Fix: parse version, enforce `>=1.6.0`.

12. **No live contract tests for upstream JSON shapes**
    Unit tests mock subprocess and never hit real upstream. Fix: `tests/contract/test_upstream_envelopes.py` snapshotting each `--json` shape.

13. **`state.child_pid` set after `runner.run()` returns**
    `source/orchestrator/engine.py:553` vs `engine.py:719-735`. SIGINT during AI subprocess may survive. Fix: capture PID before `wait()`.

14. **PHASE0 has no follow-through dispatch**
    `source/orchestrator/engine.py:578-607` reads `routed_to` from completion but does not call the routed command. Fix: when `state.complete.json.blocker=False` and `routed_to` is set, dispatch automatically.

### MEDIUM

15. **Phase constants duplicated 3×**
    `source/lib/osx.py:30-50` and `source/orchestrator/engine.py:29-49` both define `PHASES`, `PHASE_NAMES`, `PHASE_COMMANDS`. Fix: single home in `lib/osx.py`; engine imports.

16. **Double `--json` in 11 callers**
    `source/lib/osx.py:141` adds it; callers at `lib/osx.py:1410, 1431, 1455, 1472, 1482, 1558, 1601, 1619, 1638, 1654, 1673` also include it. Works today; fragile w.r.t. upstream Commander. Fix: audit each caller; remove literal `--json`.

17. **README "11 commands" / "6 extension skills" / "0.19.0"**
    `README.md:13, 78, 96, 230, 67`. Fix: recount to 12 / 8 / 1.2.1.

18. **`install.sh` example uses stale `v0.19.0`**
    `install.sh:6, 70, 85`. Fix: replace with `v1.2.1`.

19. **`SCRIPT_VERSION` literal not alias of `__version__`**
    `source/cli.py:22` declares a literal `SCRIPT_VERSION = "1.2.1"`. Fix: `from source import __version__ as SCRIPT_VERSION`.

20. **`get_version()` reads nonexistent key**
    `source/orchestrator/engine.py:71-84` reads `resources.scripts.osx-orchestrate`. Fix: parse `pyproject.toml:7`.

21. **`.gitignore` patterns shadow archive**
    `source/cli.py:322-349` adds patterns that match `openspec/changes/*/iterations.json` even after archive. Fix: prefix archived paths with `!`.

22. **`complete_set` accepts BLOCKED without reason**
    `source/lib/osx.py:1024-1056` silently passes `BLOCKED` with no reason as `{status: "BLOCKED", with_blocker: false}`. Fix: raise `OSXError` when status=`BLOCKED` and no reason.

23. **Doc drift in `osx-concepts/references/cli-reference.md`**
    `resources/opencode/skills/osx-concepts/references/cli-reference.md:3, 331` pinned to `@fission-ai/openspec@1.5.0` and `openspec-extended@0.19.x`. Fix: refresh to 1.6.0 / 1.2.1.

24. **`osx-workflow` skill stale**
    `resources/opencode/skills/osx-workflow/SKILL.md:42-50, 241-251` lists `REQUIRED_SKILLS` as 5 (actually 6 in code, 8 in manifest) and `validate` actions as 7 (actually 11). Fix: sync with code.

### LOW

25. **Stale `osc log` references in agent prompts**
    `agents/osx-analyzer.md:31` and `agents/osx-builder.md:32` say `osc log`. Should be `openspec-extended osx log`. Fix: replace.

26. **PHASE0/PHASE2 "read-only" wording in `osx-workflow`**
    `resources/opencode/skills/osx-workflow/SKILL.md` says PHASE0/PHASE2 are "read-only routing phases" but PHASE2 writes `verification-report.md` and `suggestions.md`. Fix: mark PHASE2 as write-capable via delegated role.

27. **Engine reads/writes state.json directly**
    `source/orchestrator/engine.py:368-407` (and many other places) read/write state directly, contradicting `source/orchestrator/AGENTS.md:47`. Fix: pick a story; route all engine reads/writes through `osx_lib.state_*` or document the dual-write contract.

28. **`started_at` resets every write**
    `source/orchestrator/engine.py:368-407`. Should only set on first write. Fix.

29. **Iteration counter resets on resume**
    `source/orchestrator/engine.py:578-584`. Local iteration resets to 1; persisted iteration lives in `phase_iterations[phase]` only. Fix: read from state at phase start.

## False-Positive Guards

These look like findings but are intentional. Do not flag:

- **Different version domains across files** — `source/__init__.py` (project version), `install.sh` `SCRIPT_VERSION` (installer version), `resources/*/manifest.toml` (resource version). Separation is documented at root `AGENTS.md:79-85` and is by design.
- **`osc-*` vs `osx-*` prefix collision** — `osc-*` = renamed core surfaces; `osx-*` = extended's own. Disjoint namespaces, intentional. Documented at `resources/AGENTS.md`.
- **`mode: all` in non-orchestrator-dispatched agents** — only flag when the agent is dispatched by the orchestrator (`engine.py` PHASE_AGENTS map).
- **Duplicated phase constants** — known MEDIUM; not HIGH. Don't escalate.
- **`tools.AGENTS.md` mentions skills that aren't in the deployable manifest** — the project ships 12 commands but the OpenCode picker may show fewer if `--delivery=skills` is set; that's user-controlled.
- **`osx-workflow` skill saying "core skills are 12"** — correct taxonomy: 12 core workflows, 8 extended skills, 3 agents.

## Citation Discipline

- **Every claim**: `file:line` format.
- **Group related findings** under one header. Don't split one issue across multiple bullets.
- **No paraphrasing.** Quote the actual line when ambiguity is possible.
- **Use absolute paths from repo root.** `source/lib/osx.py:1076`, not `lib/osx.py:1076` (the latter is ambiguous with `openspec-core/source/lib/...`).
- **Cite the source AND the target** for drift findings: `source/lib/osx.py:1076` ↔ `openspec-core/source/src/commands/store.ts:543`.
- **Mark unverified** if you cannot confirm from source alone. Do not infer.
