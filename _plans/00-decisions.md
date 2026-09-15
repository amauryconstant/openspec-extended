# 00 — Locked Decisions

Five architectural decisions locked before PR2. Each captures the question, the chosen option, and the rationale so future contributors understand *why* the plan took the shape it did.

## Decision 1 — Runner dispatch model

**Question:** Should `runner_kind` grow new literals (one per adapter shape) or absorb everything via `runner_args` + a new `plan_args` field?

**Locked:** Stay with the 3 existing literals (`opencode_run` / `claude_print` / `generic_print`). Add `plan_args: tuple[str, ...]` and `plan_args_position: Literal["flag","before_prompt","after_prompt"]` to `ToolAdapter` so per-tool flag differences land in registry data instead of new classes.

**Rationale:**

- The cost of a new `RunnerKind` literal is the `_runner_for` factory branch (`orchestrator/source/orchestrator/runner.py:117-142`) plus a new test class in `tests/unit/test_runner_abstraction.py::TestRunnerForFactory`. ~50 lines per new literal.
- `GenericPrintRunner`'s argv shape `[binary, *runner_args, --print, --dangerously-skip-permissions, prompt]` already handles Cursor, Qwen, Kimi, Kiro, Gemini, Cline, Devin, Claude Code, etc. once `runner_args` carries the per-tool flag set.
- The synthetic `claude_style` test in `test_runner_abstraction.py:946-993` proves `slash_prefix` does not affect the prompt — the prompt is always `/osx-phase0 <change_id>` regardless of `slash_prefix`.
- Promote to a new literal **only** when a tool's prompt shape genuinely diverges (e.g. a tool that takes the change id via `--change<id>` rather than as a positional arg). Until then, no new literal.

**Promotion criteria (write this into the PR2 review):**

1. The tool's prompt is not a positional argument but a flag value (e.g. `tool --prompt "<text>"`).
2. The tool requires a subcommand (e.g. `tool exec`, `tool chat`, `tool run`).
3. The tool consumes structured input (JSON / stdin pipe) rather than freeform text.

If any one of these is true, a new `RunnerKind` literal is warranted; otherwise use `runner_args`.

---

## Decision 2 — PR5 release shape

**Question:** Should the bulk-shipping of ~25 Low-effort adapters be one PR or three sub-PRs?

**Locked:** Three alphabet-split sub-PRs (PR5A / PR5B / PR5C).

**Rationale:**

- A 25-entry REGISTRY PR has ~750 lines of tests and ~750 lines of registry entries. Any test failure blocks all 25 adapters, even if the failure is in just one.
- Each sub-PR is ~250 lines and reviewable in 30 minutes.
- CI runs are cheaper because each sub-PR triggers one round of `mise run verify`.
- Partial rollback is possible (revert PR5C and ship a fix without disturbing PR5A/5B).

**Splits:**

- **PR5A** (~10 tools): `amazon-q`, `auggie`, `bob`, `cline`, `codeartsagent`, `codebuddy`, `command-code`, `continue`, `costrict`, `crush`.
- **PR5B** (~9 tools): `devin`, `factory`, `gemini`, `iflow`, `junie`, `kilocode`, `lingma`, `oh-my-pi`, `pi`, `codeassistant`.
- **PR5C** (~6 tools + zed + agents): `qoder`, `rovodev`, `roocode`, `trae`, `vibe`, `zcode`, `zed`, `agents` (vendor-neutral).

PR5C is the critical one for shared-root arbitration — `zed.detect_paths=(".zed", ".agents/skills")` must register BEFORE `codex.detect_paths=(".agents",)`. `TestDetectPlatformRegistrationOrderIsCanonical` (PR5C) walks every pair of shared-root adapters and asserts the more-specific one wins.

---

## Decision 3 — Legacy migration scope

**Question:** Should `legacy_skills_dirs` + the migration helper ship in PR6 (v1.12.0) or be deferred?

**Locked:** Ship in PR6 alongside the Medium-tier adapters.

**Rationale:**

- Antigravity users with pre-v1.20.5 `.agent/` get auto-migrated in v1.12.0.
- Windsurf users with `.windsurf/` get auto-migrated to `.devin/`.
- Codex users with `.codex/skills/` get auto-migrated to `.agents/skills/`.
- Kimi users with `.kimi/` get auto-migrated to `.kimi-code/`.

**Conservative migration contract** (write this into the PR6 review):

1. **Copy, not move.** Source files are preserved; if migration fails, the user's tree is intact.
2. **Refuse to overwrite.** If the destination file already exists and differs from the source, the migration helper logs the divergence and skips that file (no data loss).
3. **Idempotent.** A second run is a no-op.
4. **Snapshot.** Writes `.openspec-extended-migration.json` listing every file touched (matches `CORE_BASELINE_FILENAME` pattern at `cli.py:1131`).
5. **Dry-run by default.** The CLI surfaces the proposed migration as a yellow info line and asks for `--apply-migration` to actually run it. (Same UX pattern as `rename_core_resources:cli.py:1054-1128`.)

---

## Decision 4 — minimax-code timing

**Question:** Should `minimax-code` (the only Tier-3 adapter) ship in v1.11.0 or defer to v1.13.0?

**Locked:** Defer to v1.13.0 (PR7).

**Rationale:**

- The `global_skills_dir` field changes the deploy target for one tool to `~/.minimax/`, which means the binary writes outside the project root. That is a meaningful UX/security surface.
- v1.11.0 is already a meaty release (4-5 new adapters + 3 new fields + extension-aware deploy). Adding a home-relative deploy target would dilute the focus.
- v1.13.0 gives `global_skills_dir` its own release notes and design review.
- The 38 other adapters can ship in v1.11.0 + v1.12.0 without `minimax-code`.

**Design questions for v1.13.0 (deferred to PR7):**

- Should the manifest write at `~/.minimax/manifest.toml` follow the same `version` field as project-local manifests?
- Should the binary refuse to write to `~/.minimax/` without an explicit `--global` opt-in?
- Should `OPENSPEC_GLOBAL_SKILLS_HOME` env var override `Path.home()` for testability?

---

## Decision 5 — `setup_note` field timing

**Question:** Should `setup_note` (post-install hint) be a generic `ToolAdapter` field, or only added when a real consumer needs it?

**Locked:** Add in PR2 alongside `requires_ide_restart` and `shared_skills_root`.

**Rationale:**

- Only `hermes` and (potentially) `github-copilot` need a setup note today, but the field is small (one `str` field, one consumer in `deploy_all_resources`).
- Adding it now means PR2 ships 3 fields in one PR rather than 2 fields in PR2 and 1 field in PR6 — fewer review cycles.
- Locked by `TestAdapterFieldDefaults`. The default `""` preserves shipped behaviour byte-for-byte.

---

## What this means at a glance

| Decision | PR(s) affected | Code touched |
|---|---|---|
| Runner dispatch | PR2, PR3 | `tools.py` (new field), `runner.py` (consume `plan_args`) |
| PR5 split | PR5A, PR5B, PR5C | git history only; same code as one PR would have |
| Legacy migration | PR6 | `tools.py` (new field + `TOOL_ID_ALIASES`), `lib/osx.py` (migration helper) |
| minimax-code timing | PR7 only | `tools.py` (new field + 1 entry), `cli.py` (`_target_root` resolver) |
| `setup_note` | PR2 | `tools.py` (new field), `cli.py` (print in `deploy_all_resources`) |

## Retrospective (filled at end of each phase)

> Phase 2A — pending.
