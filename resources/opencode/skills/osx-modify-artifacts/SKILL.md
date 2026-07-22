---
name: osx-modify-artifacts
description: Surgical single-artifact edit with forward-only dependent propagation. Use for targeted fixes (typically from review findings). For multi-artifact reconciliation use /opsx:update; for new artifacts use /opsx:continue.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
---

# osx-modify-artifacts

Single-artifact surgical editor. Walks downstream `unlocks` for forward-only
propagation, **never** rewrites a `dependencies` artifact (that is
`openspec-update-change`'s job).

Adopted verbatim from core's `openspec-update-change` (`/opsx:update`):

- Schema is the source of truth. No hardcoded artifact names.
- Glob safety: write only to `existingOutputPaths`; never to a glob `resolvedOutputPath`.
- Frontier discipline: refuse to create new artifacts or new files under glob artifacts.
- No code edits — plan-only.
- Per-edit confirmation. Rejected revisions are left unchanged.
- Severity calibration does not apply (this skill makes edits, not findings).

Triggered by `/osx-modify <change> [artifact-id]` or as a routing target from
`osx-review-artifacts`. Multi-artifact drift is out of scope — route to
`/opsx:update` instead.

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

- Positional `<change-name>` (required).
- Optional positional `<artifact-id>`. When provided as the second argument it
  is the **root artifact** to edit. When omitted, prompt.
- Optional `--intent-flag <flag>` to surface a deliberate intent change when
  the requested edit cannot be a refinement.

---

## Workflow

### Step 1 — Select the change

Adopt the `openspec-update-change` policy: **never auto-select**. If the
argument matches multiple active changes, ask the user
(`AskUserQuestion` / `**Ask**`) with the most-recently modified active change
marked `(Recommended)`.

### Step 2 — Load schema state

```bash
openspec status --change "<name>" [--store "<id>"] --json
```

Capture `schemaName`, `planningHome`, `changeRoot`, every
`artifactPaths.<id>`, and `actionContext.allowedEditRoots`. Reject the request
if the change's `allowedEditRoots` does not include the current project root.

### Step 3 — Select the root artifact

If `<artifact-id>` was not supplied, prompt. Show for each candidate:

- artifact id
- `status`
- `unlocks` count (downstream blast radius)

Sort candidates by `unlocks` ascending — pick the smallest blast-radius
artifact first. Skip `ready`/`blocked` candidates for selection (they are
uncreated); they belong in `/opsx:continue`'s domain.

Refuse the request if the candidate set is empty or if every artifact is
`ready`/`blocked`. Route to `/opsx:continue <name>` instead.

### Step 4 — Load artifact context

```bash
openspec instructions "<root-id>" --change "<name>" [--store "<id>"] --json
```

Capture `template`, `instruction`, `context`, `rules`, `dependencies[]`,
`unlocks[]`, `existingOutputPaths`. Read the current concrete file(s) from
`existingOutputPaths` (never from `resolvedOutputPath` — for glob artifacts
that is still a pattern).

Stop if `existingOutputPaths` is empty. That means the artifact has not been
created yet — `/osx-modify` cannot create it; route the user to
`/opsx:continue`.

### Step 5 — Surface constraints

Show the user, in this order:

1. The artifact's **root constraints**: `template` skeleton, `instruction`
   prose, `rules` (each rule is a project-supplied constraint from
   `openspec/config.yaml`), and `context`.
2. The **upstream** facts pulled in: `dependencies[]` summaries.
3. The **downstream** blast radius: `unlocks[]` with each artifact's current
   status and `existingOutputPaths` size.

Wait for the user to acknowledge (or adjust scope) before proposing edits.

### Step 6 — Propose and confirm the root edit

Based on the user's intent (natural language from the slash command, or by
inferring from a review finding id), propose a single edit to the root
artifact. Compose the proposal by:

- Reading the current file(s).
- Composing the new content per `template` + `rules`.
- Showing the diff (`file_path:line` ranges and the new content) inline.

**Confirm with `AskUserQuestion` / `**Ask**` before writing.**

If the user rejects, leave the file untouched and exit. Do not cascade.

### Step 7 — Forward-only propagation

For each artifact id in `unlocks` of the root, run:

```bash
openspec instructions "<dependent-id>" --change "<name>" [--store "<id>"] --json
```

Read the dependent's `existingOutputPaths` and check whether the root edit
breaks anything downstream (entities consumed by the dependent, constraints
declared on the root that the dependent must honor). Compose a propagation
proposal for that dependent only.

**Forward-only.** Never edit an artifact in `dependencies`. Editing an
upstream dep is `openspec-update-change`'s job; reject the request and route
to `/opsx:update`.

**Confirmation model.** Confirm every dependent proposal **individually**:

- For each dependent: show the diff, propose the change with `AskUserQuestion`
  / `**Ask**`, write only after confirmation.
- Provide an explicit "cascade all" affordance: a single confirmation that
  then walks each dependent through its own confirmation in sequence.
- A rejected dependent is left unchanged; remaining dependents are still
  proposed.

If `unlocks` is empty, the work is done after the root edit. Otherwise the
skill keeps proposing dependents until each is confirmed or rejected.

If a dependent's contents strongly suggest it should change because of the
root edit but the schema's `requires` does not declare a dependency (i.e.
the schema declaration is incomplete), surface a `Suggestion` finding and
recommend `/opsx:update`. Do not auto-edit.

### Step 8 — Inherit "Update vs. Start Fresh"

If the requested edit changes the change's **intent** rather than refining
its execution, refuse the in-place edit. Detect intent-level changes by:
- The user explicitly says "we want a different feature now" or equivalent.
- The proposed edit rewrites the proposal section that defines the change's
  purpose (read the proposal section, not file name).
- The user passes `--intent-flag`.

Refuse the modification, explain the signal, and recommend `/opsx:new
<new-name>`. Stop cleanly.

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
- Re-review: `/osx-review <name>`
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
- Or override: re-run `/osx-modify <name> <artifact-id>` and explicitly confirm the intent change.
```

---

## Guardrails

- **Schema-agnostic.** Never assume `proposal.md`/`specs/`/`design.md`/`tasks.md`
  or any other hardcoded artifact name. Read ids and paths from CLI JSON.
- **Glob safety.** Read from and write to `existingOutputPaths` only. Never
  to a glob `resolvedOutputPath`.
- **Frontier discipline.** A missing artifact is not an editing target.
  Route to `/opsx:continue <name>`.
- **Forward-only propagation.** Never edit an artifact in `dependencies`.
- **No code edits.** If the user asks to change code, refuse and point to
  `/opsx:apply <name>`.
- **Per-edit confirmation.** Show each proposed revision (root + each
  dependent). Write only after the user confirms. Rejected revisions are
  left unchanged.
- **Carry `--store <id>`** on every `openspec` command when the change is
  store-backed.

---

## Failure modes

- **`unlocks` is non-empty but no dependent should change** — accept each as
  "unchanged"; that is a valid terminal state.
- **`existingOutputPaths` reads as glob pattern, not a file** — you read the
  wrong field. Re-read `existingOutputPaths`.
- **`openspec instructions` errors mid-cascade** — stop the cascade, report
  which dependent failed, leave prior confirmed writes in place.
- **`actionContext.allowedEditRoots` is empty** — refuse with a clear
  message and recommend `/opsx:update` (which validates its own context).
