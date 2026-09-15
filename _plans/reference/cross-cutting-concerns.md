# Cross-Cutting Concerns

Things that span multiple PRs and aren't captured in any single PR file. Read this before starting any of PR2 through PR7.

---

## 1. Registration order invariants

`detect_platform:lib/osx.py:218-220` walks `REGISTRY` in registration order, matching `(project_root / p).is_dir()` for any path in `detect_paths`. After PR5C, `detect_platform` is split into two passes:

1. **First pass**: non-shared-root adapters in registration order.
2. **Second pass**: shared-root adapters sorted by specificity (sub-paths first).

### Canonical registration order (after v1.13.0+)

```
Phase 1A (shipped):
  opencode
  claude

PR3 (Phase 2B main, v1.11.0):
  cursor
  codex         # .agents — must be registered before zed/antigravity/agents
  kimi
  forgecode

PR4 (Phase 2C, v1.11.x):
  qwen
  kiro

PR5A (Phase 3a, v1.12.0):
  amazon-q, auggie, bob, cline, codeartsagent, codebuddy, command-code,
  continue, costrict, crush

PR5B (Phase 3b, v1.12.0):
  devin, factory, gemini, iflow, junie, kilocode, lingma, oh-my-pi, pi,
  codeassistant

PR5C (Phase 3c, v1.12.0):
  qoder, rovodev, roocode, trae, vibe, zcode, zed, agents
  # ↑ zed MUST be after codex in iteration order, with more specific paths
  # ↑ agents MUST be last (vendor-neutral fallback)

PR6 (Phase 3 part 2, v1.12.x):
  antigravity   # .agent + .agents/workflows — must be after zed, before agents
  github-copilot
  hermes

PR7 (Phase 4, v1.13.0+):
  minimax-code  # global_skills_dir — separate detection path
```

### Shared-root pairs (must satisfy specificity invariant)

| Specific tool | Less-specific tool | Resolution |
|---------------|-------------------|-----------|
| `zed` (`detect_paths=(".zed", ".agents/skills")`) | `codex` (`detect_paths=(".agents",)`) | `.zed/` present → zed wins. `.agents/skills/` only → zed wins (more specific). `.agents/` only → codex wins. |
| `antigravity` (`detect_paths=(".agent", ".agents/workflows")`) | `codex` (`detect_paths=(".agents",)`) | `.agent/` (singular) present → antigravity wins. |
| `agents` (`detect_paths=(".agents/skills",)`) | `codex` (`detect_paths=(".agents",)`) | `.agents/skills/` only → agents wins. `.agents/` only → codex wins. |

Locked by `TestDetectPlatformRegistrationOrderIsCanonical` (PR5C).

---

## 2. Hardcode-check guard

The pre-commit hook `.opencode/scripts/check-platform-hardcodes.sh` rejects per-tool hardcodes in `cli.py`, `runner.py`, `engine.py`, `lib/osx.py`. The regexes:

```bash
'if[[:space:]].*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
'elif[[:space:]].*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
'[[:space:]]!=[^=].*["'"'"'](opencode|claude)["'"'"']'
'[[:space:]]in[[:space:]]+\[(.*["'"'"'](opencode|claude)["'"'"'])'
'TOOL_DIRS\[["'"'"'](opencode|claude)["'"'"']\]'
'PLATFORM_TOKENS\[["'"'"'](opencode|claude)["'"'"']\]'
'adapter\.commands_style[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
'adapter\.skill_prefix[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
'adapter\.runner_kind[[:space:]]*==[[:space:]]*["'"'"'](opencode|claude)["'"'"']'
```

**Implication for the rollout:**

- Every new `REGISTRY` entry is one literal value (not a branch) — no risk of tripping the regex.
- `if adapter.commands_style == "skills-only":` is legitimate (axis-value comparison, not per-tool).
- `if adapter.tool_id == "kimi":` would trip the regex — the hook does NOT allow per-tool branches even for new tools.

If a future PR needs a per-tool branch (e.g. codex's dual-syntax body rewrite), it must be expressed via a field on `ToolAdapter` (e.g. `cross_ref_prefix="$"`) and a single branch on the field, not on the tool id.

---

## 3. Test refactor is mostly removal

The synthetic fixtures in:
- `tests/unit/test_runner_abstraction.py:240-274` (cursor / codex / kimi)
- `tests/unit/test_cli_registry_consumers.py:599-651` (cursor / codex / kimi)
- `tests/unit/test_lib_registry_consumers.py:36-70` (kimi)

…become real `REGISTRY` entries at PR3. The fixture-monkeypatching code (e.g. `monkeypatch.setitem(REGISTRY, "cursor", ToolAdapter(...))` inside test methods) goes away. Per-tool snapshot tests for the real entries replace it.

The diff in each test file is therefore:
- ~-30 lines of fixture setup (removed)
- ~+30 lines of real per-tool snapshot test (added)
- Net: roughly zero change per test file at PR3.

For PR5A/5B/5C the pattern repeats:
- ~+30 lines of new per-tool snapshot test per new adapter
- No fixture-monkeypatching (those were already removed at PR3)

---

## 4. Per-tool preflight binary probe

`orchestrator/source/orchestrator/engine.py:1262` runs `[runner_binary, "--version"]` to confirm the CLI binary is on PATH. This is per-adapter and gated on `runner_binary`.

Tools with `runner_binary=""` (Continue, rovodev when invoked as `acli rovodev run`, github-copilot when no CLI is installed, agents, zed) **skip the probe**:

```python
# In validate_skills or wherever the probe lives:
if not adapter.runner_binary:
    log_verbose(state, f"Skipping binary probe for {tool_id} (no runner_binary)")
    return
```

This change ships in PR5A. Subsequent PRs (PR5B, PR5C, PR6) inherit the change.

Tools with `runner_binary="acli"` (rovodev) should run `[acli, --version]` which works (acli has a top-level `--version` flag). The actual rovodev invocation is `acli rovodev run --yolo "<prompt>"` via `runner_args` — the preflight probe confirms `acli` exists, the actual run uses the full subcommand.

---

## 5. Shared references packaging

Cross-cutting material lives once at `orchestrator/resources/canonical/skills/references/` and is copied into each consuming skill's `references/` subdir at deploy time. The mechanism (per `orchestrator/source/AGENTS.md` "Shared references packaging"):

1. `orchestrator/resources/canonical/skills/references/` is the canonical pool.
2. Each consuming skill declares `references = [...]` in its manifest entry.
3. `deploy_skills` (post-PR6 unchanged) copies each named reference into `<target>/<skills_dir>/skills/<skill>/references/`.

This is unrelated to the adapter rollout — no changes to the shared-references machinery in any PR.

---

## 6. Manifest format

Two manifests ship at the target after install:
- `<target>/manifest.toml` — orchestrator-side resources (orchestrator + agents + phase commands + osx-changelog + osx-maintain-docs).
- `<target>/skills-manifest.toml` — skills-side resources (commit / review / verify-tests / etc.).

The two manifests are disjoint (locked by `tests/unit/test_resource_contract.py::TestManifestParity`).

For the adapter rollout, no manifest changes are needed. Each `REGISTRY` entry is metadata, not a manifest entry. The manifest tracks **what openspec-extended shipped**, not **which AI tools are supported**.

A user's installed tool registry (`openspec config show` or equivalent) is a separate concern handled by upstream OpenSpec, not openspec-extended.

---

## 7. Vendored OpenSpec Core sync

`orchestrator/core/` is the vendored upstream OpenSpec source tree. It is **read-only** and synced via `mise run sync-core`. The adapter rollout does not modify `orchestrator/core/`.

Implication: if upstream changes the `AI_TOOLS` registry between our releases, our `REGISTRY` may diverge from upstream's. This is fine — openspec-extended supports the synthesised upstream catalogue, not the live upstream catalogue. The `mise run sync-core` task should be extended (post-rollout) to flag `value` and `legacySkillsDirs` changes — see [03-risks.md](../03-risks.md) Risk 5.

---

## 8. PyInstaller bundle layout

PyInstaller's `openspec.spec` collects each side's files under a specific path prefix:
- Orchestrator-side: `resources/`
- Skills-side: `skills/resources/`

After PR7, the bundled binary writes to `~/.minimax/` when `global_skills_dir` is set. This is a runtime concern, not a bundling concern — the binary reads/writes outside the bundle as expected.

---

## 9. Test markers

The pytest markers (`unit`, `integration`, `mechanism`, `e2e`) are unchanged. The new tests added in each PR should use:

- `unit` — for `test_tool_registry.py`, `test_runner_abstraction.py`, `test_cli_registry_consumers.py`, `test_lib_registry_consumers.py` (no subprocess).
- `integration` — for `test_install_flow.py` (subprocess / file system side effects).
- `mechanism` — `tests/e2e/mechanism.bats` for CLI surface checks.

`tests/conftest.py` skips `e2e` tests unless `E2E_CONFIRM=1`. None of the rollout PRs add `e2e` tests.

---

## 10. Backwards compatibility

Every default value on every new field preserves shipped behaviour byte-for-byte:

| Field | Default | Behaviour preserved |
|-------|---------|---------------------|
| `requires_ide_restart` | `False` | No IDE-restart hint printed for shipped opencode / claude |
| `shared_skills_root` | `False` | Existing "no other adapter uses this dir" check fires as before |
| `setup_note` | `""` | No setup note printed for shipped opencode / claude |
| `legacy_skills_dirs` | `()` | No migration runs for shipped opencode / claude |
| `global_skills_dir` | `None` | Project-local deploy target as before |
| `TOOL_ID_ALIASES` | `{"windsurf": "devin"}` | Existing `windsurf` was an unknown tool; now resolves to `devin` (a benign alias addition) |

The single user-visible behaviour change for `TOOL_ID_ALIASES`: a user who passed `--tool windsurf` before v1.12.x would have gotten "Unknown tool: windsurf". After v1.12.x, it resolves to `devin` and the install proceeds. This is the correct behaviour — the alias is forward-compat for users migrating from Windsurf to Devin.

---

## 11. AGENTS.md updates per PR

| PR | Files updated |
|----|---------------|
| PR1 | none |
| PR2 | `orchestrator/source/AGENTS.md`, `.opencode/rules/per-adapter-rendering.md` |
| PR3 | `orchestrator/source/AGENTS.md`, `orchestrator/source/lib/AGENTS.md`, `.opencode/rules/per-adapter-rendering.md` |
| PR4 | `.opencode/rules/per-adapter-rendering.md` |
| PR5A | `.opencode/rules/per-adapter-rendering.md` |
| PR5B | `.opencode/rules/per-adapter-rendering.md` |
| PR5C | `orchestrator/source/lib/AGENTS.md`, `orchestrator/source/orchestrator/AGENTS.md`, `.opencode/rules/per-adapter-rendering.md` |
| PR6 | `orchestrator/source/AGENTS.md`, `orchestrator/source/lib/AGENTS.md`, root `AGENTS.md`, `.opencode/rules/per-adapter-rendering.md` |
| PR7 | `orchestrator/source/AGENTS.md`, `orchestrator/source/lib/AGENTS.md`, `.opencode/rules/per-adapter-rendering.md` |

The AGENTS.md accumulation is intentional — every PR adds the per-field documentation that a future contributor needs to add a new tool without re-discovering the field's purpose.

---

## 12. PRs and their dependencies

```
PR1 (Phase 2A) ─ no dependencies
   ↓
PR2 (Phase 2B prep) ─ depends on PR1
   ↓
PR3 (Phase 2B main) ─ depends on PR1, PR2
   ↓
PR4 (Phase 2C) ─ depends on PR1, PR2, PR3
   ↓
PR5A (Phase 3a) ─ depends on PR1, PR2, PR3, PR4
   ↓
PR5B (Phase 3b) ─ depends on PR5A
   ↓
PR5C (Phase 3c) ─ depends on PR5B
   ↓
PR6 (Phase 3 part 2) ─ depends on PR5C
   ↓
PR7 (Phase 4) ─ depends on PR6
```

Linear dependency chain. PR5A/5B/5C could in principle run in parallel (different files in `REGISTRY`), but the sequential order keeps PR review focused and CI runs deterministic.
