---
name: osx-review-artifacts
description: Audit artifacts against schema + dependency graph before implementation. Use between artifact creation (/osc-continue-change, /osc-propose, /osc-ff-change) and /osc-apply-change. Emits a routing report only; never edits.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  author: openspec-extended
  audience: agents running pre-implementation artifact review (PHASE0, ad-hoc /osx-review)
  workflow: pre-implementation — between artifact creation and /osc-apply-change
---

# osx-review-artifacts

Read-only, schema-driven audit of the planning artifacts in a change. Emits a routing report — never edits artifacts. Reading is allowed on every concrete file listed in `artifactPaths.<id>.existingOutputPaths`.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `schemas`, `view`). Once selected, treat `--store <id>` as sticky for the rest of the workflow. Without a store, commands act on the nearest local `openspec/` root. Full flag matrix in `references/store-selection.md`.

> **Schema-agnostic contract** — see `references/schema-agnostic-contract.md`.

Sits in the pre-implementation workflow between artifact creation (`/osc-continue-change`, `/osc-propose`, `/osc-ff-change`) and implementation (`/osc-apply-change`). Use it standalone via `/osx-review <change>` or as part of PHASE0.

**Input**: Optionally specify `[<change-name>]` as `$1` (e.g., `/osx-review add-auth`). PHASE0 dispatches the change name automatically. For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. Mark the most-recently modified active change as `(Recommended)`. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

---

**Steps**

1. **Select the change** — If a name is provided (as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and ask the user to select one with `{{ASK_TOOL}}`. Mark the most-recently modified active change as `(Recommended)`.

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-review <other>`).

2. **Load schema state**

   ```bash
   openspec status --change "<name>" [--store "<id>"] --json
   ```

   Capture:

   - `schemaName` — the workflow schema id (e.g. `"spec-driven"`).
   - `planningHome`, `changeRoot` — path context (do not assume repo-local paths).
   - `artifactPaths.<id>.{outputPath, resolvedOutputPath, existingOutputPaths}`.
   - `artifacts[]` — array of `{id, status, missingDeps?, requires?}` with status in `{done, ready, blocked}`.
   - `isComplete`, `applyRequires`, `nextSteps`, `actionContext.allowedEditRoots`.

   > **v1.7.0 contract**: each entry in `artifacts[]` carries a `requires` array of the artifact ids it directly depends on. This is the preferred input for Step 4's dependency graph. Fall back to `instructions --json` `dependencies`/`unlocks` only when `requires` is absent.

   For each artifact with `status == "done"` and non-empty `existingOutputPaths`, queue it for the per-artifact audit (Step 3). Skip `ready` and `blocked` — those are frontier concerns, reported in Step 7.

   If `isComplete` is already `true`, the schema is satisfied; the cross-artifact audit (Step 4) is still worth running.

   a. **Build spec inventory (v1.13.0+, additive)**

   ```bash
   openspec list --specs [--store "<id>"] --json
   # for each spec id in the response:
   openspec show "<spec-id>" --type spec --json --no-scenarios [--store "<id>"]
   ```

   Capture:

   - The full spec inventory as `{spec_id -> {path, purpose, requirements_count}}`.
   - The filtered read for each spec keeps the bulk read small enough to enumerate on every capability (the `--no-scenarios` flag).

   > **v1.13.0 contract**: `openspec list --specs` is the first-class spec-inventory command (parallel to `openspec list` for changes). The filtered read `openspec show <id> --type spec --json --no-scenarios` is what generated guidance uses. PHASE0 spec-aware review builds the inventory here and consumes it in Step 4's "Capability-already-exists" check.

   If the inventory can't be built (older core, missing `--specs` flag, CLI failure), skip Step 2b and the new Step 4 check — backwards-compatible with v1.11.0 cores. Do not raise.

3. **Per-artifact compliance audit**

   For each queued artifact, run:

   ```bash
   openspec instructions "<artifact-id>" --change "<name>" [--store "<id>"] --json
   ```

   Read each concrete file in `existingOutputPaths`. Validate against:

   - **`template`** — structural conformance: required sections, header levels, required elements per the schema body.
   - **`instruction`** — schema-defined prose guidance. Sets expectations, not copy-source.
   - **`rules`** — project-supplied overrides from `openspec/config.yaml`. Surface as additional checks; never copy into artifact content.
   - **`context`** — also a constraint; never copy into artifact content.

   Report each violation with `file_path:line` (approximate line is fine) and a concrete fix suggestion. Categorize each finding as one of:

   - **Critical** — the artifact is invalid (missing required section, broken scenario format, content contradicts a hard rule).
   - **Warning** — the artifact has a fixable defect (wrong header level, missing optional-but-recommended element).
   - **Suggestion** — a stylistic or clarity improvement.

   Use the rule adopted from `openspec-verify-change`: **when uncertain, prefer `Suggestion` over `Warning`, `Warning` over `Critical`**. Implementation-readiness concerns (Step 5) are never `Critical`.

   If the in-tree `spec-driven` schema's `template` field does not encode a format rule we used to hardcode (H4 scenario headers, `#### Scenario:` shape, etc.), file an upstream issue against the upstream OpenSpec project rather than re-adding a local rubric.

4. **Cross-artifact consistency report**

   Build a graph from each artifact's `requires` array (v1.7.0+, captured in Step 2 from `openspec status --json`). When a `requires` value is missing, fall back to that artifact's `dependencies` + `unlocks` from `openspec instructions --json`. Skip edges whose source artifact has no `existingOutputPaths`.

   For each existing edge **A → B** (A depends on B, both with concrete files):

   - **Entity coherence** — entities introduced in B that A consumes must be present in A; constraints declared in B must be honored by A; no orphan references.
   - **Severity** — coherence-level findings follow the same calibration rule.

   Do **not** hardcode any proposal↔specs↔design↔tasks pairs. The `requires` (or `dependencies` / `unlocks`) graph is fully schema-derived.

   If an artifact in the edge target has no concrete files (status `ready` or `blocked`), it belongs to Step 7 routing, not here.

   a. **Capability-already-exists (v1.13.0+, additive)**

   For each delta `ADDED Requirements` capability path:

   ```bash
   # Walk the inventory built in Step 2b:
   for spec_id in spec_inventory.keys(): ...
   # If the ADDED capability path is already in the inventory, flag it.
   ```

   If the spec inventory (Step 2b) has an existing capability at the same path as the delta's `ADDED Requirements` block, emit a `Warning` finding naming the existing spec id and pointing to `/osc-update-change <name>` — the right way to MODIFY/extend an existing capability is `update`, not a fresh `ADDED Requirements` block in a new change. The `Suggestion` ↔ `Warning` ↔ `Critical` calibration rule applies (prefer `Suggestion`).

   Skip Step 4b when the spec inventory is unavailable (older core, CLI failure) — backwards-compatible with v1.11.0 cores. Do not raise.

5. **Implementation-readiness** — Stay under `Suggestion` severity. Implementation readiness is human judgment: feasibility, scope, dependency availability, ambiguous requirements. Never `Critical`.

6. **Classify findings** — Apply the verify calibration rule once more across the whole report. Severity buckets produce distinct routing paths:
   - `Critical` / `Warning` → blocked; routing required before apply.
   - `Suggestion` → optional; user may proceed.

7. **Smart routing recommendation** — Produce one routing line per finding category. Pick the single best editor for the aggregate finding set:

   | Finding pattern | Recommended route |
   |---|---|
   | Findings on existing artifacts (single- or multi-artifact) | `/osc-update-change <name>` — `osc-update-change` reconciles any combination |
   | Missing artifact (referenced but not created) | `/osc-continue-change <name>` |
   | All clean, pre-impl (PHASE0) | `/osc-apply-change <name>` |
   | Intent-level change detected | `/osc-new-change <name>` (per "Update vs. Start Fresh" heuristic) |

   Exactly one routing line, matching this matrix.

   The review skill never invokes the routed command itself. It only emits the route so the user or the next orchestrator step can act.

---

**Output**

**Issues found**:

```
## Artifact Review: <change-name>

**Schema**: <schemaName>
**Artifacts audited**: <count>

### <Severity> findings
- **<artifact-id>:<file:line>**: <issue>
  - Fix: <concrete fix>
  - Route: </osc-update-change|/osc-continue-change|/osc-apply-change|/osc-new-change> <name>

### Routing recommendation
<single sentence picking ONE of the routes from §Step 7>

### Next steps
- Address findings via the routed command above.
- Re-run review after fixes: `/osx-review <name>`
```

**All checks passed**:

```
## Artifact Review: <change-name>

### All checks passed

**Schema compliance**: All artifacts conform to their templates and rules.
**Cross-artifact consistency**: No drift detected across the dependency graph.
**Implementation readiness**: <brief judgment>

### Next steps
- Start (or resume) implementation: `/osc-apply-change <name>`
```

---

**Guardrails**

- **Read-only.** Emits findings; never edits artifacts.
- **No code edits.** Surface issues, route the user to `/osc-apply-change`.
- **No new artifacts.** Missing artifacts are reported; their creation is `/osc-continue-change`'s job.
- **No hardcoded artifact names.** Schema is the source of truth.

---

## Failure modes

- **`openspec status` returns no change** — confirm the change name (and `--store` if applicable); offer `openspec list --json` to help the user.
- **`openspec instructions` errors mid-audit** — report which artifact failed and stop; do not invent instructions from the schema body.
- **`isComplete` is false and no `ready` artifact exists** — unusual state; surface as `Suggestion` and ask the user whether they want to archive or start a new change.
