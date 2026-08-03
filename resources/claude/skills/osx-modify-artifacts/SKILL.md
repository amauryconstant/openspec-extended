---
name: osx-modify-artifacts
description: Single-artifact edit with forward-only dependent propagation. Use for targeted fixes from review findings. Route multi-artifact drift to /opsx:update; missing artifacts to /opsx:continue.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  audience: agents making single-artifact edits before implementation (PHASE0 fallback, ad-hoc /{{CMD_PREFIX}}modify)
  workflow: pre-implementation — surgical edit; multi-artifact drift routes to /opsx:update
---

# osx-modify-artifacts

Single-artifact surgical editor. Walks downstream `unlocks` for forward-only propagation, **never** rewrites a `dependencies` artifact (that is `openspec-update-change`'s job).

> **Schema-agnostic contract** — see `references/schema-agnostic-contract.md`.
> **Store selection** — see `references/store-selection.md`.
> **Mode** — see `references/osx-mode-conventions.md`. When `OSX_AUTONOMOUS=1` is set, skip interactive confirmation and proceed with reasonable defaults.

Triggered by `/{{CMD_PREFIX}}modify <change> [artifact-id]` or as a routing target from `osx-review-artifacts`. Multi-artifact drift is out of scope — route to `/opsx:update` instead.

---

## Inputs

- Positional `<change-name>` (required).
- Optional positional `<artifact-id>`. When provided as the second argument it is the **root artifact** to edit. When omitted, prompt.
- Optional `--intent-flag <flag>` to surface a deliberate intent change when the requested edit cannot be a refinement.

---

## Workflow

### Step 1 — Select the change

Adopt the `openspec-update-change` policy: **never auto-select**. If the argument matches multiple active changes, auto-select the most-recently modified under `OSX_AUTONOMOUS=1`; otherwise ask the user with `{{ASK_TOOL}}` marked `(Recommended)`.

### Step 2 — Load schema state

```bash
openspec status --change "<name>" [--store "<id>"] --json
```

Capture `schemaName`, `planningHome`, `changeRoot`, every `artifactPaths.<id>`, and `actionContext.allowedEditRoots`. Reject the request if the change's `allowedEditRoots` does not include the current project root.

> **v1.7.0 contract**: also capture `artifacts[].requires` per artifact. The root's `requires` list enumerates the artifacts that **must not** be edited here; `unlocks` from `instructions` covers the forward direction.

### Step 3 — Select the root artifact

If `<artifact-id>` was not supplied, auto-select the first candidate under `OSX_AUTONOMOUS=1`; otherwise prompt. Show for each candidate:

- artifact id
- `status`
- `unlocks` count (downstream blast radius)

Sort candidates by `unlocks` ascending — pick the smallest blast-radius artifact first. Skip `ready`/`blocked` candidates for selection (they are uncreated); they belong in `/opsx:continue`'s domain.

Refuse the request if the candidate set is empty or if every artifact is `ready`/`blocked`. Route to `/opsx:continue <name>` instead.

### Step 4 — Load artifact context

```bash
openspec instructions "<root-id>" --change "<name>" [--store "<id>"] --json
```

Capture `template`, `instruction`, `context`, `rules`, `dependencies[]`, `unlocks[]`, `existingOutputPaths`. Read the current concrete file(s) from `existingOutputPaths` (never from `resolvedOutputPath` — for glob artifacts that is still a pattern).

Stop if `existingOutputPaths` is empty. That means the artifact has not been created yet — `/{{CMD_PREFIX}}modify` cannot create it; route the user to `/opsx:continue`.

### Step 5 — Surface constraints

Show the user, in this order:

1. The artifact's **root constraints**: `template` skeleton, `instruction` prose, `rules`, and `context`.
2. The **upstream** facts pulled in: `dependencies[]` summaries.
3. The **downstream** blast radius: `unlocks[]` with each artifact's current status and `existingOutputPaths` size.

Wait for the user to acknowledge (or adjust scope) before proposing edits.

### Step 6 — Propose and confirm the root edit

Based on the user's intent (natural language from the slash command, or by inferring from a review finding id), propose a single edit to the root artifact:

- Read the current file(s).
- Compose the new content per `template` + `rules`.
- Show the diff (`file_path:line` ranges and the new content) inline.

Auto-accept under `OSX_AUTONOMOUS=1`. Otherwise, confirm with `{{ASK_TOOL}}` before writing.

If the user rejects, leave the file untouched and exit. Do not cascade.

### Step 7 — Forward-only propagation

**v1.7.0 cross-artifact re-read requirement**: before proposing a propagation edit for any dependent, **re-read the dependent's current file(s) from disk**. The conversation context may carry a stale version; the actual on-disk content is the source of truth for downstream edits.

For each artifact id in `unlocks` of the root, run:

```bash
openspec instructions "<dependent-id>" --change "<name>" [--store "<id>"] --json
```

Read the dependent's `existingOutputPaths` and check whether the root edit breaks anything downstream (entities consumed by the dependent, constraints declared on the root that the dependent must honor). Compose a propagation proposal for that dependent only.

**Forward-only.** Never edit an artifact in `dependencies` (use the root's `requires` array from `status --json`, v1.7.0+, to enumerate them defensively). Editing an upstream dep is `openspec-update-change`'s job; reject the request and route to `/opsx:update`.

Confirm every dependent proposal individually (auto-accept under `OSX_AUTONOMOUS=1`):

- For each dependent: show the diff, propose with `{{ASK_TOOL}}`, write only after confirmation.
- Provide an explicit "cascade all" affordance: one confirmation that walks each dependent through its own confirmation in sequence.
- A rejected dependent is left unchanged; remaining dependents are still proposed.

Every dependent in `unlocks` is either confirmed or marked unchanged — both are valid terminal states.

If a dependent's contents strongly suggest it should change because of the root edit but the schema's `requires` does not declare a dependency (i.e. the schema declaration is incomplete), surface a `Suggestion` finding and recommend `/opsx:update`. Do not auto-edit.

### Step 8 — Inherit "Update vs. Start Fresh"

If the requested edit changes the change's **intent** rather than refining its execution, refuse the in-place edit. Detect intent-level changes by:
- The user explicitly says "we want a different feature now" or equivalent.
- The proposed edit rewrites the proposal section that defines the change's purpose (read the proposal section, not file name).
- The user passes `--intent-flag`.

Refuse the modification, explain the signal, and recommend `/opsx:new <new-name>`. Stop cleanly.

### Step 9 — Hand-off

After all proposed edits are confirmed (or rejected), surface:

```
## Modification Complete

**Change**: <name>
**Artifact**: <artifact-id>
**Files edited**: <list of existingOutputPaths written>

### Changes applied
- <section>: <action> — <summary>

### Forward propagation
- [x] <dependent-id>: <auto-updated | unchanged | prompted>
- [ ] <dependent-id>: <rejected by user>

### Next steps
- Re-review: `/{{CMD_PREFIX}}review <name>`
- Multi-artifact drift: `/opsx:update <name>`
- Code implications: `/opsx:apply <name>`
```

If the request was rejected as intent-level:

```
## Modification declined

The requested edit changes the change's intent rather than refining it.
This is better handled by starting a fresh change.

**Detected signal**: <why we classified this as intent-level>

### Recommendation
- Start fresh: `/opsx:new <new-name>`
- Or override: re-run `/{{CMD_PREFIX}}modify <name> <artifact-id>` and explicitly confirm the intent change.
```

---

## Guardrails

- **Schema-agnostic.** Never assume `proposal.md`/`specs/`/`design.md`/`tasks.md` or any other hardcoded artifact name. Read ids and paths from CLI JSON.
- **Glob safety.** Read from and write to `existingOutputPaths` only.
- **Frontier discipline.** A missing artifact is not an editing target. Route to `/opsx:continue <name>`.
- **Forward-only propagation.** Never edit an artifact in `dependencies`.
- **No code edits.** If the user asks to change code, refuse and point to `/opsx:apply <name>`.
- **Per-edit confirmation.** Show each proposed revision (root + each dependent). Write only after the user confirms. Rejected revisions are left unchanged.

---

## Failure modes

- **`unlocks` is non-empty but no dependent should change** — accept each as "unchanged"; valid terminal state.
- **`existingOutputPaths` reads as glob pattern, not a file** — you read the wrong field. Re-read `existingOutputPaths`.
- **`openspec instructions` errors mid-cascade** — stop the cascade, report which dependent failed, leave prior confirmed writes in place.
- **`actionContext.allowedEditRoots` is empty** — refuse with a clear message and recommend `/opsx:update` (which validates its own context).
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/osx-modify-artifacts/SKILL.md
Regenerate: `mise run sync:mirrors`
-->
