---
name: osx-review-artifacts
description: Audit artifacts against schema + dependency graph before implementation. Use between artifact creation (/opsx:continue, /opsx:propose, /opsx:ff) and /opsx:apply. Emits a routing report only; never edits.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  audience: agents running pre-implementation artifact review (PHASE0, ad-hoc /{{CMD_PREFIX}}review)
  workflow: pre-implementation — between artifact creation and /opsx:apply
---

# osx-review-artifacts

Read-only, schema-driven audit of the planning artifacts in a change. Emits a routing report — never edits artifacts. Reading is allowed on every concrete file listed in `artifactPaths.<id>.existingOutputPaths`.

> **Schema-agnostic contract** — see `references/schema-agnostic-contract.md`.
> **Store selection** — see `references/store-selection.md`.

Sits in the pre-implementation workflow between artifact creation (`/opsx:continue`, `/opsx:propose`, `/opsx:ff`) and implementation (`/opsx:apply`). Use it standalone via `/{{CMD_PREFIX}}review <change>` or as part of PHASE0.

---

## Inputs

- Optional positional argument: `<change-name>`. If omitted or ambiguous, prompt.

---

## Workflow

### Step 1 — Select the change

Adopt the `openspec-update-change` policy: **never auto-select**. If the argument is missing or matches more than one active change, ask the user to choose with `{{ASK_TOOL}}`. Mark the most-recently modified active change as `(Recommended)`.

List candidates with:

```bash
openspec list --json
```

### Step 2 — Load schema state

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

### Step 3 — Per-artifact compliance audit

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

If the in-tree `spec-driven` schema's `template` field does not encode a format rule we used to hardcode (H4 scenario headers, `#### Scenario:` shape, etc.), file an upstream issue against `openspec-core/source` rather than re-adding a local rubric.

### Step 4 — Cross-artifact consistency report

Build a graph from each artifact's `requires` array (v1.7.0+, captured in Step 2 from `openspec status --json`). When a `requires` value is missing, fall back to that artifact's `dependencies` + `unlocks` from `openspec instructions --json`. Skip edges whose source artifact has no `existingOutputPaths`.

For each existing edge **A → B** (A depends on B, both with concrete files):

- **Entity coherence** — entities introduced in B that A consumes must be present in A; constraints declared in B must be honored by A; no orphan references.
- **Severity** — coherence-level findings follow the same calibration rule.

Do **not** hardcode any proposal↔specs↔design↔tasks pairs. The `requires` (or `dependencies` / `unlocks`) graph is fully schema-derived.

If an artifact in the edge target has no concrete files (status `ready` or `blocked`), it belongs to Step 7 routing, not here.

### Step 5 — Implementation-readiness

Stay under `Suggestion` severity. Implementation readiness is human judgment: feasibility, scope, dependency availability, ambiguous requirements. Never `Critical`.

### Step 6 — Classify findings

Apply the verify calibration rule once more across the whole report. Severity buckets produce distinct routing paths:

- `Critical` / `Warning` → blocked; routing required before apply.
- `Suggestion` → optional; user may proceed.

### Step 7 — Smart routing recommendation

Produce one routing line per finding category. Pick the single best editor for the aggregate finding set:

| Finding pattern | Recommended route |
|---|---|
| Single-artifact defect (1 artifact, format/content) | `/{{CMD_PREFIX}}modify <name> <artifact-id>` |
| Multi-artifact coherence drift (≥2 artifacts OR any coherence-level finding) | `/opsx:update <name>` |
| Missing artifact (referenced but not created) | `/opsx:continue <name>` |
| All clean, pre-impl (PHASE0) | `/opsx:apply <name>` |
| Intent-level change detected | `/opsx:new <name>` (per "Update vs. Start Fresh" heuristic) |

Exactly one routing line, matching this matrix.

The review skill never invokes the routed command itself. It only emits the route so the user or the next orchestrator step can act.

---

## Output formats

### Issues found

```
## Artifact Review: <change-name>

**Schema**: <schemaName>
**Artifacts audited**: <count>

### <Severity> findings
- **<artifact-id>:<file:line>**: <issue>
  - Fix: <concrete fix>
  - Route: </{{CMD_PREFIX}}modify|/opsx:update|/opsx:continue|/opsx:apply|/opsx:new> <name> [<artifact-id>]

### Routing recommendation
<single sentence picking ONE of the routes from §Step 7>

### Next steps
- Address findings via the routed command above.
- Re-run review after fixes: `/{{CMD_PREFIX}}review <name>`
```

### All checks passed

```
## Artifact Review: <change-name>

### All checks passed

**Schema compliance**: All artifacts conform to their templates and rules.
**Cross-artifact consistency**: No drift detected across the dependency graph.
**Implementation readiness**: <brief judgment>

### Next steps
- Start (or resume) implementation: `/opsx:apply <name>`
```

---

## Guardrails

- **Read-only.** Emits findings; never edits artifacts.
- **No code edits.** Surface issues, route the user to `/opsx:apply`.
- **No new artifacts.** Missing artifacts are reported; their creation is `/opsx:continue`'s job.
- **No hardcoded artifact names.** Schema is the source of truth.

---

## Failure modes

- **`openspec status` returns no change** — confirm the change name (and `--store` if applicable); offer `openspec list --json` to help the user.
- **`openspec instructions` errors mid-audit** — report which artifact failed and stop; do not invent instructions from the schema body.
- **`isComplete` is false and no `ready` artifact exists** — unusual state; surface as `Suggestion` and ask the user whether they want to archive or start a new change.