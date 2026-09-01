# Schema-Agnostic Contract

The six rules every pre-implementation review / modify / update skill must honour. Adopted verbatim from core's `openspec-update-change`.

## The six rules

1. **Schema source of truth** — read artifact ids, descriptions, and paths from `openspec status --change <name> --json` and `openspec instructions <id> --change <name> --json`. Never hardcode `proposal.md`/`specs/`/`design.md`/`tasks.md`. v1.7.0 status adds a `requires` array per artifact — prefer it over a separate `instructions` call when building the dependency graph.
2. **Glob safety** — write only to concrete files in `existingOutputPaths`. Never write to a glob `resolvedOutputPath` (it is still a pattern).
3. **Frontier discipline** — refuse to create new artifacts or new files under glob artifacts. Route missing-artifact cases to `/opsx:continue <name>`.
4. **No code edits** — refuse to touch implementation code. If a finding implies code changes, stop and point to `/opsx:apply <name>`.
5. **Per-edit confirmation** — show each proposed revision and write only after the user confirms. Rejected revisions are left unchanged.
6. **Severity calibration** — adopt the same rule as `openspec-verify-change`: when uncertain, prefer `Suggestion` over `Warning`, `Warning` over `Critical`. Implementation-readiness issues are never `Critical`.

## Carry `--store <id>` on every command

When the change lives in a registered store, pass `--store <id>` on every `openspec` command that accepts the flag. See `references/store-selection.md` for the full list.

## v1.7.0+ additions (unchanged through v1.11.0)

- Each artifact entry in `status --json` carries a `requires` array of artifact ids it directly depends on. Prefer it over `instructions --json`'s `dependencies`/`unlocks` for the dependency graph.
- `openspec instructions archive` is a read-only mirror of the proposal/apply variants — use it for archive-readiness pre-checks.
- `operations.apply.guidance` and `operations.archive.guidance` in `openspec/config.yaml` are per-operation text surfaced through the `instructions` surface — escape hatches for project-specific guidance.

## v1.8.0+ additions

- `status --json` adds `isPlanningComplete` distinct from `isComplete`. Use `isPlanningComplete` when verifying the plan is finished before triggering apply/archive; treat `isComplete` as the legacy alias.
- `retire_capabilities: true` change metadata — archive can delete a capability whose last requirement is removed. Coordinate with any in-flight MODIFIED change against the retired capability (it will refuse to archive cleanly).

## v1.11.0 additions

- `status --all` returns a single envelope of every active change across all stores in one process; use it when the orchestrator wants the full set without per-store subprocess fan-out.
- `show <change> --diff` renders requirement-level diffs (added/removed/renamed/modified) against the main spec — prefer it for review-time diff context over manual file comparison.

## See also

- `references/store-selection.md`
- `references/osx-mode-conventions.md`
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/references/schema-agnostic-contract.md
Regenerate: `mise run sync:mirrors`
-->
