# 03 — Risk Register

Five concrete risks ranked by likelihood × impact. Each entry has: description, trigger conditions, mitigation already in the plan, and a residual risk rating.

## Risk 1 — Registration-order coupling when multiple adapters share `skills_dir`

**Likelihood:** high (codex, zed, antigravity, agents all use `.agents`).

**Impact:** medium (silently picks the wrong adapter when `.agents/` is present alongside another detection path).

**Trigger:** `detect_platform:lib/osx.py:205-221` walks `REGISTRY` in registration order. With `codex` registered before `zed`, a project with `.zed/` resolves to `codex` if both are present, because `codex.detect_paths=(".agents",)` matches `.agents/skills/` even when `.zed/` is the more specific signal.

**Mitigation in the plan:**

1. PR5C ships `TestDetectPlatformRegistrationOrderIsCanonical` (in `tests/unit/test_lib_registry_consumers.py`). The test walks every pair of shared-root adapters and asserts the more-specific one wins.
2. Registration order is canonical: `opencode` → `cursor` → `zed` → `codex` → `antigravity` → `agents`. Documented in [pr/PR5C-phase-3c-bulk-q-z.md](pr/PR5C-phase-3c-bulk-q-z.md) and `.opencode/rules/per-adapter-rendering.md`.
3. `orchestrator/source/lib/AGENTS.md` documents the registration-order invariant and explains why.

**Residual risk:** low. If a future contributor adds a new shared-root tool and forgets to register it before the broader-path tools, `TestDetectPlatformRegistrationOrderIsCanonical` catches it at PR time.

---

## Risk 2 — `commands_ext="toml"` / `".prompt.md"` substitution may collide with the host format's syntax

**Likelihood:** medium.

**Impact:** medium (deployed file fails to parse on the target tool, which surfaces as a "command not found" or runtime error in the user's session).

**Trigger:** `_substitute_tokens:cli.py:99-137` uses a `\{\{([A-Z_]+)\}\}` regex — only uppercase ASCII letters and underscores. But the host format may use a similar placeholder syntax (e.g. Jinja-style `{{ var }}` with spaces, TOML's `[section]` syntax, YAML's `{key: value}` braces). Unknown tokens are left verbatim per `cli.py:128-129`, which is safe for unknown TOML keys but may collide with the host format's own placeholder grammar.

**Specific concerns:**

- **Qwen Code TOML:** TOML's basic string syntax is `key = "value"`. A leftover `{{TOKEN}}` inside a value would be a literal string — safe, but ugly. A leftover `{{TOKEN}}` inside a key would be a syntax error.
- **Kiro `.prompt.md`:** Markdown with YAML frontmatter. The frontmatter is YAML, the body is Markdown. Same risk as opencode's `.md` (already known-safe).
- **GitHub Copilot `.prompt.md`:** same as Kiro.

**Mitigation in the plan:**

1. PR4 extends `_substitute_tokens_in_file` to `.toml` and `.prompt.md` (the substitution is format-agnostic).
2. Before PR4 lands, run a contract test against the live Qwen / Kiro CLIs: deploy a known-shape file and assert the target tool parses it.
3. Document the format-specific concerns in the per-tool adapter docstrings (e.g. `# Qwen: deploys .toml command files; {{TOKEN}} placeholders must be uppercase ASCII to avoid TOML syntax errors`).

**Residual risk:** low-medium. The contract tests catch the worst-case issues; minor cosmetic leftovers are tolerable.

---

## Risk 3 — `legacy_skills_dirs` migration is destructive

**Likelihood:** medium (PR6 only).

**Impact:** high (silent loss of user-authored customisations if migration is too aggressive).

**Trigger:** `migrate_legacy_skills_dirs` (proposed for PR6) moves files from a legacy root to the new tool's skills_dir. If the migration is too aggressive — e.g. moves instead of copies, overwrites destination files without consent, runs without a dry-run preview — the user loses their customisations.

**Mitigation in the plan (locked in [00-decisions.md](00-decisions.md) Decision 3):**

1. **Copy, not move.** Source files are preserved; if migration fails, the user's tree is intact.
2. **Refuse to overwrite.** If the destination file already exists and differs from the source, the migration helper logs the divergence and skips that file (no data loss).
3. **Idempotent.** A second run is a no-op.
4. **Snapshot.** Writes `.openspec-extended-migration.json` listing every file touched (matches `CORE_BASELINE_FILENAME` pattern at `cli.py:1131`).
5. **Dry-run by default.** The CLI surfaces the proposed migration as a yellow info line and asks for `--apply-migration` to actually run it. (Same UX pattern as `rename_core_resources:cli.py:1054-1128`.)

**Residual risk:** low. The conservative contract + dry-run-by-default + snapshot pattern matches the project's existing baseline machinery. If the migration helper is too conservative (e.g. refuses to migrate anything that diverges), users can `--apply-migration --force` after reviewing.

---

## Risk 4 — Bulk-shipping 25 adapters in one release is a review and CI hazard

**Likelihood:** high.

**Impact:** medium (merge conflicts with other work, slower CI, larger blast radius if a regression lands).

**Trigger:** A 25-entry REGISTRY PR has ~750 lines of tests and ~750 lines of registry entries. Any test failure blocks all 25 adapters, even if the failure is in just one. Review bandwidth is limited; a 1500-line PR takes longer to review than 3 × 500-line PRs.

**Mitigation in the plan (locked in [00-decisions.md](00-decisions.md) Decision 2):**

1. Split Phase 3 into 3A / 3B / 3C sub-PRs by alphabet.
2. Each sub-PR is ~250 lines and reviewable in 30 minutes.
3. CI runs are cheaper because each sub-PR triggers one round of `mise run verify`.
4. Partial rollback is possible (revert PR5C and ship a fix without disturbing PR5A/5B).

**Splits:**

- **PR5A** (~10 tools): `amazon-q`, `auggie`, `bob`, `cline`, `codeartsagent`, `codebuddy`, `command-code`, `continue`, `costrict`, `crush`.
- **PR5B** (~9 tools): `devin`, `factory`, `gemini`, `iflow`, `junie`, `kilocode`, `lingma`, `oh-my-pi`, `pi`, `codeassistant`.
- **PR5C** (~6 tools + zed + agents): `qoder`, `rovodev`, `roocode`, `trae`, `vibe`, `zcode`, `zed`, `agents`.

**Residual risk:** low. The split is mechanical (alphabet) and the per-tool entries are independent. A regression in one tool does not block the others.

---

## Risk 5 — Upstream renames keep happening

**Likelihood:** high.

**Impact:** low-medium (a renamed tool needs a fresh alias + a fresh detection path + possibly a legacy-skills-dir entry).

**Trigger:** Upstream moves fast — every release of OpenSpec Core can rename tools, change detection paths, or move legacy directories. Examples already in scope:

- **Windsurf → Devin** (2026-06-02). Aliases `windsurf → devin`; `.windsurf/` is the legacy root for `.devin/`.
- **Antigravity `.agent` → `.agents`** (upstream v1.20.5). `legacy_skills_dirs=(".agent",)` covers this.
- **CoStrict `.costrict` → `.cospec`** (per `config.ts:59`). The shipped directory name is `.cospec`, not `.costrict` — easy typo.

**Mitigation in the plan:**

1. **PR6 ships `TOOL_ID_ALIASES`** (per Decision 3) — a forward-compat dictionary that resolves aliases before unknown-id checks. Adding a new alias is one line.
2. **PR6 ships `legacy_skills_dirs`** — a per-adapter tuple of former roots. Adding a new legacy root for a renamed tool is one field value.
3. **Add a rebrand audit step to `mise run sync-core`** — diff `orchestrator/core/source/src/core/config.ts` against the previous sync, flag any `value` change or any new `legacySkillsDirs` entry, surface a warning in the sync-core task output.

The rebrand audit is the cheapest way to stay current without manual tracking. Implementation:

```bash
# In .mise/tasks/sync-core (post-sync step):
diff <previous-sync-config.ts> <new-config.ts> | grep -E "value:|legacySkillsDirs"
# If non-empty, emit a yellow warning:
echo "⚠️  Upstream AI_TOOLS changed; review docs/plans/upstream-parity/02-coverage-matrix.md"
```

**Residual risk:** low. The rebrand audit is mechanical; the alias + legacy_skills_dirs machinery absorbs future renames.

---

## Risks NOT in the plan (and why)

| Concern | Why not in the plan |
|---------|---------------------|
| New upstream `CommandsStyle` literal | Upstream uses only `flat`, `namespaced`, `skills-only` — all already covered. A 4th would be a major upstream architectural change, not just a new tool. |
| New upstream `RunnerKind` literal | Per Decision 1, `runner_args` absorbs flag differences. A new literal would only be needed for a tool whose prompt shape genuinely diverges (none in the current 39). |
| `commands_ext` other than `.md`/`.toml`/`.prompt.md`/`.prompt` | Upstream only uses these four. |
| Loss of `OpencodeRunner` shape (the bespoke `opencode run --command X --agent Y change`) | OpencodeRunner is unique to opencode; no third tool replicates it. Future third-party tools that want a similar shape would need their own bespoke runner, but that's not in scope for the current 39. |
| Wire format drift (upstream changes the `.toml` escape algorithm) | Upstream's escape algorithm is locked by `test/core/command-generation/adapters.test.ts`. Drift would surface as upstream test failures, not our problem. |

## Tracking

Add new risks to this file as they emerge during execution. Format:

```
## Risk N — <one-line summary>
**Likelihood:** <low|medium|high>
**Impact:** <low|medium|high>
**Trigger:** <what would surface this risk>
**Mitigation:** <what the plan does about it>
**Residual risk:** <low|medium|high>
```
