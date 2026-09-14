# Schema-Agnostic Contract

The six rules every pre-implementation review / modify / update skill must honour. Adopted verbatim from core's `openspec-update-change`.

## The six rules

1. **Schema source of truth** — read artifact ids, descriptions, and paths from `openspec status --change <name> --json` and `openspec instructions <id> --change <name> --json`. Never hardcode `proposal.md`/`specs/`/`design.md`/`tasks.md`. v1.7.0 status adds a `requires` array per artifact — prefer it over a separate `instructions` call when building the dependency graph.
2. **Glob safety** — write only to concrete files in `existingOutputPaths`. Never write to a glob `resolvedOutputPath` (it is still a pattern).
3. **Frontier discipline** — refuse to create new artifacts or new files under glob artifacts. Route missing-artifact cases to `/osc-continue-change <name>`.
4. **No code edits** — refuse to touch implementation code. If a finding implies code changes, stop and point to `/osc-apply-change <name>`.
5. **Per-edit confirmation** — show each proposed revision and write only after the user confirms. Rejected revisions are left unchanged.
6. **Severity calibration** — adopt the same rule as `openspec-verify-change`: when uncertain, prefer `Suggestion` over `Warning`, `Warning` over `Critical`. Implementation-readiness issues are never `Critical`.

## Carry `--store <id>` on every command

When the change lives in a registered store, pass `--store <id>` on every `openspec` command that accepts the flag. See `references/store-selection.md` for the full list.

## v1.7.0+ additions (unchanged through v1.13.0)

- Each artifact entry in `status --json` carries a `requires` array of artifact ids it directly depends on. Prefer it over `instructions --json`'s `dependencies`/`unlocks` for the dependency graph.
- `openspec instructions archive` is a read-only mirror of the proposal/apply variants — use it for archive-readiness pre-checks.
- `operations.apply.guidance` and `operations.archive.guidance` in `openspec/config.yaml` are per-operation text surfaced through the `instructions` surface — escape hatches for project-specific guidance.

## v1.8.0+ additions

- `status --json` adds `isPlanningComplete` distinct from `isComplete`. Use `isPlanningComplete` when verifying the plan is finished before triggering apply/archive; treat `isComplete` as the legacy alias. `osx-review-artifacts` Step 2 and the orchestrator pre-flight consult this field directly; the local file-existence check is a fallback only.
- `retire_capabilities: true` change metadata (v1.8.0+) — archive can delete a capability whose last requirement is removed. The orchestrator's PHASE0 pre-flight reads this marker; when set, the routing report points to `/osc-archive-change <name>` instead of `/osc-apply-change`. Coordinate with any in-flight MODIFIED change against the retired capability (it will refuse to archive cleanly).

## v1.11.0 additions

- `status --all` returns a single envelope of every active change across all stores in one process; use it when the orchestrator wants the full set without per-store subprocess fan-out.
- `show <change> --diff` renders requirement-level diffs (added/removed/renamed/modified) against the main spec — prefer it for review-time diff context over manual file comparison.

## v1.12.0 additions

- `openspec validate --report findings` — opt-in bulk-scope flag. Returns only items with errors / warnings / informational findings while keeping full-run totals and exit codes. The default full report is unchanged; default callers (and `osx validate *`) keep using the full report.

## v1.13.0 additions

- `openspec instructions apply --json` adds a `missingPrerequisites` array — the full build-order chain, not just the first hop. The text response remedies now name `openspec instructions <artifact> --change <name>` commands rather than the `openspec-continue-change` skill (which the `core` profile never installs). PHASE1 consumers should prefer the structured `missingPrerequisites` field over parsing the text remedies; `osx.fetch_apply_prerequisites` is the in-process reader.
- `openspec list --specs` is a first-class spec-inventory command (parallel to `openspec list` for changes). The filtered read is `openspec show <id> --type spec --json --no-scenarios`; `--no-scenarios` keeps the read small enough to enumerate on every capability. PHASE0 spec-aware review can use it to detect "capability already exists" drift before approving an `ADDED Requirements` block.
- Delta sections accept `[-*+]` as bullet markers, not just `-`. Duplicate section titles (e.g., two `## ADDED Requirements` headers, or `## ADDED Requirements` beside `## Added Requirements`) now read every body, not just the first. The schema-agnostic contract already derives parsing from `template`/`rules` rather than hardcoded markers, so no orchestrator-side change is needed.
- `openspec archive` preserves the inside of fenced code blocks (blank-line collapsing now runs through `buildCodeFenceMask`). Samples inside fence boundaries — YAML block scalars, Python, expected-output fixtures, Markdown-inside-Markdown — keep their internal whitespace. No orchestrator change.
- `retire_capabilities` no longer refuses specs whose scenario bullets wrap onto a second line, nor specs whose scenarios use `+`-marker bullets. `osx-phase6`'s precondition check relaxes accordingly.

## See also

- `references/store-selection.md`
- `references/osx-mode-conventions.md`