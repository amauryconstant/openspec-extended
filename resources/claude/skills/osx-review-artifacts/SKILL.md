---
name: osx-review-artifacts
description: Schema-driven audit of planning artifacts before implementation. Validates each artifact against its schema template + rules, walks the dependency graph for cross-artifact consistency, and routes findings to the right editor (modify, update, continue, apply, archive). Never edits artifacts.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  audience: agents running pre-implementation artifact review (PHASE0, ad-hoc /osx:review)
  workflow: pre-implementation — between artifact creation and /opsx:apply
---

# osx-review-artifacts

Read-only, schema-driven audit of the planning artifacts in a change. Emits a
routing report — never edits artifacts. Reading is allowed on every concrete
file listed in `artifactPaths.<id>.existingOutputPaths`.

Adopted verbatim from core's `openspec-update-change` (`/opsx:update`):

- Schema is the source of truth. No hardcoded artifact names.
- Glob safety: write only to `existingOutputPaths`; never to a glob `resolvedOutputPath`.
- Read-only by design: any edit handoff points the user at `/osx:modify` or `/opsx:update`.
- Per-edit confirmation and severity calibration belong to the editing skills, not here.

This skill sits in the pre-implementation workflow between artifact creation
(`/opsx:continue`, `/opsx:propose`, `/opsx:ff`) and implementation (`/opsx:apply`).
Use it standalone via `/osx:review <change>` or as part of PHASE0.

---

## Store selection

If the user names a store (a store is a standalone OpenSpec repo registered on
this machine) or the work lives in one, run:

```bash
openspec store list --json
```

to discover registered store ids, then pass `--store <id>` on every command
that reads or writes specs and changes:

`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`,
`doctor`, `context`. Other commands do not take the flag.

Hints printed by commands already carry the flag; keep it on follow-ups.
Without a store, commands act on the nearest local `openspec/` root.

---

## Inputs

- Optional positional argument: `<change-name>`. If omitted or ambiguous, prompt.

---

## Workflow

### Step 1 — Select the change

Adopt the `openspec-update-change` policy: **never auto-select**. If the
argument is missing or matches more than one active change, ask the user
to choose (use the **`Ask`** tool). Mark the most-recently modified active
change as `(Recommended)`.

List candidates with:

```bash
openspec list --json
```

### Step 2 — Load schema state

Run:

```bash
openspec status --change "<name>" [--store "<id>"] --json
```

Capture:

- `schemaName` — the workflow schema id (e.g. `"spec-driven"`).
- `planningHome`, `changeRoot` — path context (do not assume repo-local paths).
- `artifactPaths.<id>.{outputPath, resolvedOutputPath, existingOutputPaths}`.
- `artifacts[]` — array of `{id, status, missingDeps?}` with status in `{done, ready, blocked}`.
- `isComplete`, `applyRequires`, `nextSteps`, `actionContext.allowedEditRoots`.

For each artifact with `status == "done"` and non-empty `existingOutputPaths`,
queue it for the per-artifact audit (Step 3). Skip `ready` and `blocked` —
those are frontier concerns, reported separately in Step 7.

If `isComplete` is already `true`, the schema is satisfied; the cross-artifact
audit (Step 4) is still worth running.

### Step 3 — Per-artifact compliance audit

For each queued artifact, run:

```bash
openspec instructions "<artifact-id>" --change "<name>" [--store "<id>"] --json
```

Then read each concrete file in `existingOutputPaths`. Validate against:

- **`template`** — structural conformance: required sections, header levels,
  required elements per the schema body. The template is what the file should
  conform to.
- **`instruction`** — schema-defined prose guidance (what to write). Use it
  to set expectations, not to copy into the file.
- **`rules`** — project-supplied overrides from `openspec/config.yaml`. These
  are constraints for the AI; surface them as additional checks but never copy
  them into artifact content.
- **`context`** — also a constraint; never copy into artifact content.

Report each violation with `file_path:line` (approximate line is fine) and a
concrete fix suggestion. Categorize each finding as one of:

- **Critical** — the artifact is invalid (missing required section, broken
  scenario format, content contradicts a hard rule).
- **Warning** — the artifact has a fixable defect (wrong header level, missing
  optional-but-recommended element).
- **Suggestion** — a stylistic or clarity improvement.

Use the rule adopted from `openspec-verify-change`: **when uncertain, prefer
`Suggestion` over `Warning`, `Warning` over `Critical`**. Implementation-
readiness concerns (Step 5) are never `Critical` — they are explicitly human
judgment.

If the in-tree `spec-driven` schema's `template` field does not encode a format
rule we used to hardcode (H4 scenario headers, `#### Scenario:` shape, etc.),
file an upstream issue against `openspec-core/source` rather than re-adding a
local rubric.

### Step 4 — Cross-artifact consistency report

Build a graph from each artifact's `dependencies` + `unlocks` (both come from
`openspec instructions --json`). Skip `dependencies`/`unlocks` whose source
artifact has no `existingOutputPaths` — there is nothing to compare.

For each existing edge **A → B** (A depends on B, both with concrete files):

- **Entity coherence** — entities introduced in B that A consumes must be
  present in A; constraints declared in B must be honored by A; no orphan
  references.
- **Severity** — coherence-level findings follow the same calibration rule.

Do **not** hardcode any proposal↔specs↔design↔tasks pairs. The
`dependencies` / `unlocks` graph is fully schema-derived — never assume the
shape.

If an artifact in `unlocks` is missing concrete files (status `ready` or
`blocked`), it belongs to Step 7 routing, not here.

### Step 5 — Implementation-readiness

Stay clearly under `Suggestion` severity. Implementation readiness is human
judgment: feasibility, scope, dependency availability, ambiguous requirements.
Never `Critical`.

### Step 6 — Classify findings

Apply the verify calibration rule one more time across the whole report.
Severity buckets produce distinct routing paths:

- `Critical` / `Warning` → blocked; routing required before apply.
- `Suggestion` → optional; user may proceed.

### Step 7 — Smart routing recommendation

Produce one routing line per finding category. Pick the single best editor
for the aggregate finding set, following this matrix:

| Finding pattern | Recommended route |
|---|---|
| Single-artifact defect (1 artifact, format/content) | `/osx:modify <name> <artifact-id>` |
| Multi-artifact coherence drift (≥2 artifacts OR any coherence-level finding) | `/opsx:update <name>` |
| Missing artifact (referenced but not created) | `/opsx:continue <name>` |
| All clean, pre-impl (PHASE0) | `/opsx:apply <name>` (hand off to implementation) |
| Intent-level change detected (the change's purpose itself is wrong) | `/opsx:new <name>` (per "Update vs. Start Fresh" heuristic) |

The review skill never invokes the routed command itself. It only emits the
route so the user or the next orchestrator step can act.

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
  - Route: </osx:modify|/opsx:update|/opsx:continue|/opsx:apply|/opsx:new> <name> [<artifact-id>]

### Routing recommendation
<single sentence picking ONE of the routes from §Step 7>

### Next steps
- Address findings via the routed command above.
- Re-run review after fixes: `/osx:review <name>`
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

- **Read-only.** This skill emits findings; it never edits artifacts. The user
  (or a follow-up `/osx:modify` or `/opsx:update` invocation) writes.
- **No code edits.** If a finding implies code changes — for instance, a
  proposal that discovered the implementation contract is wrong — do not
  invent code diffs. Surface the issue and route the user to `/opsx:apply`.
- **No new artifacts.** Missing artifacts are reported; their creation is
  `/opsx:continue`'s job.
- **No hardcoded artifact names.** Schema is the source of truth.
- **Carry `--store <id>`** on every `openspec` command when the change is
  store-backed.

---

## Failure modes

- **`openspec status` returns no change** — confirm the change name (and
  `--store` if applicable); offer `openspec list --json` to help the user.
- **`openspec instructions` errors mid-audit** — report which artifact failed
  and stop; do not invent instructions from the schema body.
- **`isComplete` is false and no `ready` artifact exists** — unusual state;
  surface as `Suggestion` and ask the user whether they want to archive or
  start a new change.
