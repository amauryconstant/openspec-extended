---
name: osx-phase6
description: PHASE6 — archive a completed change with full audit trail. Use when dispatched by the orchestrator after self-reflection, or ad-hoc via `/osc-archive-change` once verification is clean.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
agent: osx-maintainer
metadata:
  audience: PHASE6 archive (dispatched by orchestrator)
  workflow: post-implementation — archive completed change
---

# PHASE6: Archive Change

Change: $1

> **Protocol spine** — see `references/phase-protocol-common.md`. **Blocker semantics** — `references/blocker-semantics.md`. **Decision-log schema** — `references/osx-decision-logging.md`. **Shell-arg safety** — `references/shell-argument-safety.md`. **Tools** — `osx-workflow` §1. **Store selection** — `references/store-selection.md`.

**Input**: The orchestrator dispatches `<change-name>` as `$1` (e.g., `/osx-phase6 add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` (filtered to active, non-archived changes) and prompt via `{{ASK_TOOL}}`. PHASE6 also reads `.openspec.yaml` (for `retire_capabilities`), `state.json`, and `complete.json`; optional advisory guidance from `operations.archive.guidance` in `openspec/config.yaml` is injected via `RunRequest.extra_prompt`.

## Mandatory start

```bash
# Pre-validation
openspec validate --change "$1" --type all --strict --json
# Context load
openspec-extended osx ctx get "$1"
```

## Mandatory end (no `osx state complete`)

```bash
# Decision log
openspec-extended osx log append "$1" --phase ARCHIVE --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"archive_path":"openspec/changes/archive/<dir>/","retire_capabilities":false}'
openspec-extended osx iterations append "$1" --phase ARCHIVE --iteration N \
  --commit-hash "<hash or null>" --notes "..."
# Archive command
openspec archive "$1" --yes
# Orchestrator detects completion by archive directory existing.
```

## Steps

1. **Select the change**

   If a name is provided (the orchestrator dispatches `<change-name>` as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` (filtered to active, non-archived changes) and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-phase6 <other>`).

2. **ATOMIC EXECUTION REQUIREMENT.** All archive steps must run in a single uninterrupted sequence. The orchestrator detects completion by the archive directory existing; do not split into separate transactions.

3. Load context per protocol spine.

4. **Step 0 — Precondition.** Confirm `openspec validate --change "$1" --type all --strict --json` exits 0. If non-zero, halt and signal `BLOCKED` with `validation_failed` (do not archive an invalid change).

5. **Step 1 — Archive.** Load skill:

   ```bash
   # Single change
   openspec archive "$1" --yes
   ```

   For multi-change contexts, `osc-bulk-archive-change` runs the per-change archive inline (do not delegate to a background task — the sync would race the archive).

6. **Step 2 — Decision log.** Append a final `decision_log` entry summarising what was archived. Reference `.openspec-baseline.json` if `retire_capabilities: true` was set.

7. **Step 3 — Iterations log.** Append the final `iterations.json` entry marking archive complete.

8. **Step 4 — Commit.** Commit via `osx-commit`. Capture the commit hash in `state.json.last_archive_commit`.

9. **Step 5 — Detect completion.** The orchestrator checks for the archive directory at `openspec/changes/archive/`. PHASE6 **does not call `osx state complete`** — completion is inferred.

## Output

`openspec/changes/archive/YYYY-MM-DD-<name>/` populated with `proposal.md`, `design.md` (if present), `tasks.md`, and `specs/<cap>/spec.md` (if delta specs exist). `decision-log.json` and `iterations.json` updated. Commit hash recorded in `state.json.last_archive_commit`.

## Post-archive hand-off

After archive succeeds, consider generating a release note:

- **`/osx-changelog`** — process the just-archived changes (or all archived changes since `--since YYYY-MM-DD`) into `CHANGELOG.md` using Keep a Changelog format. Run after a release cutoff or when updating version headers. See `references/changelog-format.md` and `references/proposal-parsing-guide.md` for the contract.
- **`/osx-changelog <change-name>`** — single-change preview before adding to the next release section.

## Guardrails

- **Agent**: `osx-maintainer` (`edit: allow`).
- **Atomic** — all steps run in one uninterrupted sequence. Never split across separate transactions.
- **Never call `osx state complete`** — the orchestrator detects completion by archive directory existence.
- **Pre-validation required** — `openspec validate --strict` must exit 0 before archive. A non-strict-valid change must not be archived.
- **`retire_capabilities: true`** — check `.openspec.yaml`; if set, baseline specs at `.openspec-baseline.json` before archive.
- **Max 10 iterations** per phase. If exceeded, signal `BLOCKED` with `iteration_budget_exceeded`.
- **Failure modes**:
  - Pre-validation fails → halt, signal `BLOCKED`.
  - Archive command errors → halt, signal `BLOCKED`; do not retry blindly.
  - `--store <id>` was used and the store is unreachable → halt, signal `BLOCKED` with `store_unreachable`.
