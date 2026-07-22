# Review/Modify × Core Pre-Implementation Integration

**Status**: Planning — ready for execution
**Last updated**: 2026-07-19
**Scope**: Rewrite of `osx-review-artifacts` and `osx-modify-artifacts`, plus orchestrator wiring updates, to integrate cleanly with OpenSpec core v1.6.0's pre-implementation workflow skills (`new`, `continue`, `propose`, `ff`, `update`).

---

## 1. Context

### 1.1 The triggering change

OpenSpec core v1.6.0 introduced `openspec-update-change` (`/opsx:update`), a new pre-implementation skill that revises existing planning artifacts in place and reconciles them bidirectionally for coherence. This skill lives alongside four other pre-implementation skills:

| Core skill | Creates new? | Revises existing? | Granularity | Schema-agnostic? |
|---|---|---|---|---|
| `new` | dir only | — | — | yes |
| `continue` | next ready one | no | one per turn | yes |
| `propose` ≈ `ff` | all `applyRequires` | no | all at once | yes |
| `update` (v1.6.0) | **forbidden** | yes | multi, bidirectional, per-artifact confirm | **strictly** |

`propose` and `ff` are ~95% duplicated (same `applyRequires` loop, different framing). Treat them as one capability.

### 1.2 The problem

Our local skills `osx-review-artifacts` and `osx-modify-artifacts` were designed before `update-change` existed. They:

- Hardcode artifact names (`proposal.md`, `specs/`, `design.md`, `tasks.md`) — breaks on custom schemas, violating the precedent `update` sets.
- Carry a 321-line `review-criteria.md` rubric encoding spec-driven format rules (scenario headers at H4, SHALL/MUST, checkbox format) that the schema's `template` field already encodes.
- Overlap with `update`'s reconciliation scope without a crisp division of labor.
- Wire into PHASE0 and PHASE2 of the orchestrator in ways that don't account for the new core skill.

### 1.3 What's actually unoccupied in core

Mapping the core surface against the full pre-implementation workflow reveals two empty cells:

1. **Pre-implementation artifact quality audit** — `verify-change` is post-impl (reads code/tests); `update` does coherence silently as edit proposals. Nobody emits a severity-ranked artifact-quality report before code is written.
2. **Single-artifact surgical edit** — `update` is multi-artifact bidirectional; `continue` only creates. Nobody edits one specific existing artifact in isolation with forward-only propagation.

These are precisely the cells our two skills should own.

---

## 2. Goals

1. **Clean composition with core**: review and modify adopt `update`'s schema-agnostic contract verbatim (status JSON as source of truth, glob safety, frontier discipline, no code edits, per-edit confirmation).
2. **Crisp division of labor**: each skill fills exactly one empty cell; no overlap with `new`/`continue`/`propose`/`ff`/`update`.
3. **Schema-driven, not rubric-driven**: review consumes `template` + `rules` + the `dependencies`/`unlocks` graph from the openspec CLI; it carries no hardcoded spec-driven assumptions.
4. **Smart routing**: review's hand-off knows the difference between single-artifact defects (→ `modify`), multi-artifact drift (→ `update`), missing artifacts (→ `continue`), and intent-level changes (→ `new`).
5. **Coherent orchestrator wiring**: PHASE0 picks the right editor per finding breadth; PHASE2 routes verify-blamed-artifact cases to `update` (not `modify`).
6. **Platform parity**: Claude tree tracks OpenCode tree; manifest drift reconciled.

### 2.1 Non-goals

- Rewriting `osx-review-test-compliance` (post-implementation, separate concern). Only stale slash-command references inside its body get fixed.
- Renaming slash commands (`/osx-review`, `/osx-modify`, `/osx-verify-tests` stay as-is).
- Building a `/osx-review-fix` wrapper command. PHASE0 owns the review→fix loop; ad-hoc users chain manually via smart routing.
- Touching the openspec CLI itself (all changes are at the skill/command layer).

---

## 3. Reasoning behind the design choices

### 3.1 Why keep `modify-artifacts` as a separate skill (vs. fold into `update`)?

`update` is multi-artifact bidirectional reconciliation. That's the right tool for "redesign the auth approach" — ripples everywhere. But the most common review-driven fix is narrow: "scenario in `specs/auth.md:42` uses wrong header level." Routing that through `update`'s full coherence sweep is overkill and forces the user through per-artifact confirmation on artifacts that didn't change.

Keeping `modify` as a **surgical single-artifact editor with forward-only `unlocks` propagation** gives:

- Smallest possible blast radius for targeted fixes.
- A 1:1 pairing with review findings ("fix issue N").
- Predictable forward-only semantics (no surprises from backward propagation).
- A simpler mental model: "modify = scalpel, update = reconciliation sweep."

The trade-off is maintaining two editing models, but they're clearly distinguished by trigger and scope.

### 3.2 Why keep cross-artifact consistency in `review` (vs. make it `update`'s exclusive domain)?

`update` already does coherence reconciliation silently — its findings become edit proposals without ever being surfaced as a report. This is fine when the user knows what they want to change. It's bad when the user wants to know **what's wrong before deciding what to change**.

A standalone consistency report (the kind `review` produces) is a different mode of use:

- "Audit my plan and tell me what's broken" → review.
- "Fix the broken thing I already know about" → modify or update.

Keeping the report function in `review` and the reconciliation function in `update` is intentional overlap: **one reports, one fixes**. The user-facing distinction is "do you want a diagnosis or a procedure?"

### 3.3 Why drop the 321-line rubric?

The rubric (`review-criteria.md`) encodes spec-driven format rules: H4 scenario headers, SHALL/MUST keyword rules, `- [ ]` checkbox format, decision rationale requirements, etc. These are valuable, but they are **already encoded in the spec-driven schema's `template` field**, which `openspec instructions <id> --json` returns. Carrying a parallel hardcoded rubric:

- Duplicates what the schema already declares.
- Breaks on custom schemas (where the template legitimately differs).
- Requires manual sync when upstream evolves the spec-driven format.
- Violates the schema-agnostic precedent `update` sets.

Going schema-only means review validates the artifact against the `template` and `rules` the CLI hands it. When the schema is spec-driven, review still catches H4-vs-H3 errors — because the spec-driven template says so. When the schema is custom, review adapts automatically.

**Verification gate** (Phase B): during execution, run `openspec instructions <id> --json` against the spec-driven schema and confirm the template actually encodes the format rules we care about. If gaps surface, raise an upstream issue against `openspec-core` rather than re-adding a local rubric.

### 3.4 Why route PHASE2 Case A to `update` (not `modify`)?

Post-implementation verify-blamed-artifact cases are almost always multi-artifact: when code drift reveals that the plan was wrong, it's typically the specs + tasks + maybe the design that all need to move together. `modify`'s single-artifact surgical scope is the wrong fit; `update`'s bidirectional reconciliation is.

If verify identifies a clearly isolated single-artifact defect, PHASE2 *may* still delegate to `modify`. But the default flips from `modify` to `update`.

### 3.5 Why adopt `verify`'s severity calibration in `review`?

`verify-change` uses the rule "when uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL." Adopting the same rule in `review` keeps the experience consistent: a user moving from pre-impl review to post-impl verify sees the same severity discipline. Inconsistency here would erode trust in both reports.

---

## 4. Target architecture

### 4.1 Composition diagram

```
GREENFIELD ENTRY
  ├── new ──► continue* ──┐
  ├── propose ────────────┤
  └── ff ─────────────────┤
                          ▼
                  ┌── review (audit) ──┐
                  │   schema-driven    │
                  │   findings + route │
                  └────────────────────┘
                          │
              ┌───────────┼───────────┬─────────────┐
              ▼           ▼           ▼             ▼
        single-art    multi-art    missing      intent-level
          defect       drift       artifact      change
              │           │           │             │
          modify        update     continue        new
              │           │           │
              └───── re-review ───────┘
                          │
                          ▼
                       apply → verify → archive

ADJUST EXISTING (any time after ≥1 artifact exists)
  └── update (reconcile) ──► continue/apply/archive
```

### 4.2 The integration contract (non-negotiable)

Both `review` and `modify` adopt these six rules, drawn from `update-change`'s precedents:

1. **Schema source of truth** — read `artifactPaths.<id>.existingOutputPaths` from `openspec status --change <name> --json`; never hardcode `proposal.md`/`specs/`/`design.md`/`tasks.md`.
2. **Glob safety** — write only to concrete files in `existingOutputPaths`; never to a glob `resolvedOutputPath` (which is still a glob pattern, not a real file).
3. **Frontier discipline** — both refuse to create new artifacts or new files under glob artifacts. Route to `/opsx:continue`.
4. **No code edits** — both refuse to touch implementation code; point to `/opsx:apply` if code changes are implied.
5. **Per-edit confirmation** — proposed edits are shown and confirmed per artifact before writing. Rejected revisions are left unchanged. (Review findings can be auto-emitted; only edit proposals require confirmation.)
6. **Severity calibration** — adopt `verify`'s rule: "when uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL."

### 4.3 CLI JSON shapes (reference)

Both skills consume these CLI outputs. These are the field contracts.

**`openspec status --change <name> --json`** returns:
- `schemaName`: workflow schema id (e.g., `"spec-driven"`)
- `artifacts[]`: array of `{ id, status }` where status ∈ `{done, ready, blocked}`
- `isComplete`: boolean
- `planningHome`, `changeRoot`: path context (use these, don't assume repo-local paths)
- `artifactPaths.<id>.existingOutputPaths`: concrete on-disk files (glob-expanded for glob artifacts)
- `artifactPaths.<id>.resolvedOutputPath`: the declared path or glob pattern (do NOT write to this for glob artifacts)
- `actionContext`: scope context
- `nextSteps`: hints

**`openspec instructions <artifact-id> --change <name> --json`** returns:
- `template`: structural template the artifact should conform to (this is where spec-driven format rules live — H4 scenarios, checkbox format, etc.)
- `context`: project background (constraint for the LLM, never copied into artifact files)
- `rules`: project-supplied overrides from `openspec/config.yaml` (per-artifact, free-form strings)
- `dependencies`: completed artifacts to read for context
- `unlocks`: reverse-deps — artifacts that depend on this one
- `resolvedOutputPath`, `existingOutputPaths`: file paths
- `instruction`: schema-specific guidance
- `references?`: optional upstream-store index (only when declared)

**Schema-declared artifact graph**: the schema itself declares `requires` relationships between artifacts (validated for cycles by the CLI). This means the `dependencies`/`unlocks` graph is fully schema-derived — no hardcoded proposal↔specs↔design↔tasks pairs needed.

---

## 5. Current-state inventory

For implementation reference, here is where review/modify currently touch the codebase. All file paths are repo-relative.

### 5.1 Skills (OpenCode canonical)

| Skill | Path | Current version |
|---|---|---|
| `osx-review-artifacts` | `resources/opencode/skills/osx-review-artifacts/SKILL.md` | 0.2.6 |
| `osx-review-artifacts` rubric | `resources/opencode/skills/osx-review-artifacts/references/review-criteria.md` (321 lines) | (part of skill) |
| `osx-modify-artifacts` | `resources/opencode/skills/osx-modify-artifacts/SKILL.md` | 0.2.3 |
| `osx-review-test-compliance` | `resources/opencode/skills/osx-review-test-compliance/SKILL.md` | 0.2.1 (out of scope; stale-ref fix only) |

Claude mirrors live under `resources/claude/skills/<name>/SKILL.md`.

### 5.2 Slash commands

| Command | Path | Wraps | Version |
|---|---|---|---|
| `/osx-review` | `resources/opencode/commands/osx-review.md` | `osx-review-artifacts` | 0.1.3 |
| `/osx-modify` | `resources/opencode/commands/osx-modify.md` | `osx-modify-artifacts` | 0.1.4 |
| `/osx-verify-tests` | `resources/opencode/commands/osx-verify-tests.md` | `osx-review-test-compliance` | 0.1.1 |

Claude mirrors: `resources/claude/commands/osx/{review,modify,verify-tests}.md`. Note Claude uses `/osx:` prefix and `**Ask**` tool (vs OpenCode's `/osx-` prefix and `AskUserQuestion`).

### 5.3 Orchestrator wiring

- `source/orchestrator/engine.py` — never names review/modify skills directly; only knows phase → command → agent mappings. `PHASE_NAMES` at `engine.py:31-39`, `PHASE_COMMANDS` at `:41-49`, `PHASE_AGENTS` at `:51-59`. PHASE0 and PHASE2 both dispatch `osx-analyzer`.
- `source/lib/osx.py:67-74` — `REQUIRED_SKILLS` enforces presence of `osx-review-artifacts`, `osx-modify-artifacts`, `osx-review-test-compliance` at pre-flight. `validate_skills()` at `osx.py:1107-1121`.
- `osx-phase0.md` — PHASE0 details. `:35` loads `osx-review-artifacts`; `:44` invokes `osx-modify-artifacts` for each issue; `:46` re-reviews after fixes; `:114` caps at 10 review iterations.
- `osx-phase1.md` — PHASE1 (implementation). `:94` runs `osx-review-test-compliance` at end. Does not touch review/modify.
- `osx-phase2.md` — PHASE2 (post-impl verify). `:43` loads `osc-verify-change`. `:60` invokes `osx-modify-artifacts` for Case A (artifacts wrong) with `artifacts_modified` transition at `:64`. `:69` forbids artifact modification for Case B (implementation wrong).
- `osx-phase5.md` — reflection only. `:34` asks "How well did the artifact review process work?" No skill invocation.

### 5.4 Conceptual narrative touchpoints

These docs describe the review→modify cycle and need rewriting:

- `osx-workflow/SKILL.md:16-22` — 7-phase TL;DR diagram
- `osx-workflow/SKILL.md:98-106` — phase detail table (lists skills per phase)
- `osx-workflow/SKILL.md:108` — disambiguation: "PHASE0 = ARTIFACT_REVIEW (engine) = osx-review-artifacts (skill)"
- `osx-workflow/SKILL.md:378-383` — workflow patterns (Enhanced manual vs Autonomous)
- `osx-workflow/SKILL.md:318-319` — blocker routing for "unclear specs"
- `osx-workflow/SKILL.md:185-189` — transition reasons including `artifacts_modified`
- `osx-concepts/SKILL.md:104-117` — skill taxonomy table
- `osx-concepts/SKILL.md:132` — command grouping
- `osx-concepts/references/anti-patterns.md:65, :75, :277` — references to review-test-compliance and modify-artifacts
- `osx-concepts/references/cli-reference.md:437-440` — transition reasons

### 5.5 Manifests

| Resource | OpenCode version | Claude version | Drift? |
|---|---|---|---|
| `osx-review-artifacts` (skill) | 0.2.6 | 0.2.0 | yes |
| `osx-modify-artifacts` (skill) | 0.2.3 | 0.2.3 | no |
| `osx-review-test-compliance` (skill) | 0.2.1 | 0.2.0 | yes |
| `osx-review` (command) | 0.1.3 | 0.2.0 | yes (different scheme) |
| `osx-modify` (command) | 0.1.4 | 0.2.0 | yes |
| `osx-verify-tests` (command) | 0.1.1 | 0.2.0 | yes |

Open paths: `resources/opencode/manifest.toml`. Claude paths: `resources/claude/manifest.toml`.

---

## 6. Execution plan

### Suggested execution order

A → B → C → (D parallel with E) → F → G.

Phases B and C are independent and can run in parallel. D and E both depend on B and C. F depends on B–E. G is the gate.

### Phase A — Establish the integration contract (docs only)

**Goal**: lock the schema-agnostic contract that review, modify, and PHASE0/PHASE2 will honor.

**Changes**:
- New section "Schema-agnostic contract for review/modify skills" in `resources/opencode/skills/AGENTS.md` and `resources/claude/skills/AGENTS.md` — codifies the six rules from §4.2 above.
- `resources/opencode/skills/osx-concepts/SKILL.md:104-117` taxonomy table: relabel entries to:
  - `osx-review-artifacts` → "Pre-implementation schema-driven audit"
  - `osx-modify-artifacts` → "Single-artifact surgical editor (forward-only)"
- Mirror in Claude.

**No version bumps** in this phase (docs-only framing).

### Phase B — Rewrite `osx-review-artifacts` (the big one)

**Goal**: schema-driven audit, drop hardcoded names, drop rubric, keep severity + coherence report + smart routing.

**New body structure** (replaces current 7 steps):

1. **Select change** — adopt `update`'s prompt-always policy (never auto-select; mark most-recent as "(Recommended)").
2. **Load schema state** — `openspec status --change <name> --json`; capture `schemaName`, `artifacts`, `artifactPaths`.
3. **Per-artifact compliance audit** (replaces steps 4 + the rubric):
   - For each existing artifact (skip "blocked"/missing), run `openspec instructions <id> --change <name> --json`.
   - Validate the artifact file(s) at `existingOutputPaths` against:
     - `template` — structural conformance (sections present, header levels, required elements).
     - `rules` — project-supplied overrides from `openspec/config.yaml`.
   - Report violations with `file_path:line` + concrete fix.
4. **Cross-artifact consistency report** (replaces step 5, schema-driven):
   - Build the dependency graph from each artifact's `dependencies` + `unlocks` (queried via `openspec instructions`).
   - For each edge A→B (A depends on B), check that A's references to B's content are coherent: every entity introduced in B that A consumes is present; every constraint declared in B is honored by A; no orphan references.
   - **No hardcoded proposal↔specs↔design↔tasks pairs** — derived purely from the graph.
5. **Implementation-readiness** (kept, labeled "Suggestions"): feasibility, scope, dependency availability. Explicitly human judgment; never Critical severity.
6. **Classify findings** — Critical/Warning/Suggestion with `verify`'s calibration rule.
7. **Smart routing** (new — see §6.B.1 below).

**Delete**:
- `resources/opencode/skills/osx-review-artifacts/references/review-criteria.md`
- `resources/claude/skills/osx-review-artifacts/references/review-criteria.md`

If the `references/` directory is then empty, remove it.

**Update frontmatter description** to: `"Schema-driven audit of planning artifacts before implementation. Validates each artifact against its schema template + rules, walks the dependency graph for cross-artifact consistency, and routes findings to the right editor (modify, update, continue, apply, archive)."`

**Verification gate** (must pass before completing Phase B):
```bash
# In a scratch change with spec-driven schema:
openspec instructions <id> --change <scratch> --json | jq '.template'
```
Confirm the template field actually encodes the format rules we used to hardcode (H4 scenarios, checkbox format, SHALL/MUST, etc.). If gaps, raise upstream issue against `openspec-core/source` — do NOT re-add a local rubric.

#### 6.B.1 Smart routing table (for step 7)

| Finding pattern | Route to |
|---|---|
| Single-artifact defect (1 artifact, format/content) | `/osx-modify <name> <artifact-id>` |
| Multi-artifact coherence drift (≥2 artifacts OR any coherence-level finding) | `/opsx:update <name>` |
| Missing artifact (referenced but not created) | `/opsx:continue <name>` |
| Code drift detected (post-impl review only) | `/opsx:apply <name>` |
| All clean, pre-impl | `/opsx:apply <name>` |
| All clean, post-impl | `/opsx:archive <name>` |
| Intent-level change (the change's purpose itself is wrong) | `/opsx:new <name>` (per `update`'s "Update vs. Start Fresh" heuristic) |

The routing is **guidance only** — review never invokes the routed command itself.

**Files**:
- `resources/opencode/skills/osx-review-artifacts/SKILL.md` (rewrite)
- `resources/opencode/skills/osx-review-artifacts/references/review-criteria.md` (delete)
- `resources/claude/skills/osx-review-artifacts/SKILL.md` (rewrite)
- `resources/claude/skills/osx-review-artifacts/references/review-criteria.md` (delete)

**Manifest bumps**: `osx-review-artifacts` 0.2.6 → **0.3.0** (breaking: schema-driven rewrite, rubric removed). Bump Claude to match.

### Phase C — Rewrite `osx-modify-artifacts` (narrow to surgical)

**Goal**: single-artifact surgical editor, forward-only propagation, schema-agnostic, drop dual-mode.

**New body structure**:

1. **Select change** — adopt `update`'s prompt-always policy.
2. **Load schema state** — `openspec status --json`; capture `artifactPaths`.
3. **Select artifact** — from argument or prompt. When prompting:
   - Show: artifact id, status, `unlocks` count (downstream blast radius).
   - Sort by `unlocks` ascending (smallest blast radius first).
4. **Load artifact context** — `openspec instructions <id> --change <name> --json`; capture `template`, `rules`, `dependencies`, `unlocks`, `existingOutputPaths`. **Read the current file(s) from `existingOutputPaths`** (never `resolvedOutputPath`).
5. **Surface constraints** — show the user `rules`, `dependencies`, `unlocks` before editing.
6. **Apply edit** — Edit tool for targeted changes, Write tool for full rewrites. Validate the result against `template` + `rules`.
7. **Forward-only propagation** — for each artifact in `unlocks`:
   - Run `openspec instructions <dependent-id> --change <name> --json`.
   - Read the dependent's file(s).
   - Check whether the edit breaks anything downstream.
   - **Decision rule**:
     - 0–1 affected dependents → auto-update with explanation (no prompt).
     - 2+ affected dependents → list them and prompt for confirmation.
     - User says "cascade" → auto-update all regardless of count.
   - **Never edit backward** (i.e., never revise an artifact in `dependencies`). That's `update`'s job.
8. **Per-artifact confirmation** — show each proposed revision and why; write only after user confirms. Rejected revisions are left unchanged (matches `update`'s contract).
9. **Inherit "Update vs. Start Fresh"** — if the requested edit changes the change's *intent* (rather than refining it), redirect to `/opsx:new`.
10. **Hand-off routing**:
    - Re-review: `/osx-review <name>`
    - Multi-artifact drift: `/opsx:update <name>`
    - Missing artifacts: `/opsx:continue <name>`
    - Code implications: `/opsx:apply <name>`

**Drop**: dual-mode decision (Review Iteration / Amendment). The skill is single-purpose: surgical single-artifact edit. Amendment cases (requirements discovered during coding that ripple through multiple artifacts) route to `update`.

**Update frontmatter description** to: `"Surgical single-artifact edit with forward-only dependent propagation. Use for targeted fixes (typically from review findings). For multi-artifact reconciliation use /opsx:update; for new artifacts use /opsx:continue."`

**Files**:
- `resources/opencode/skills/osx-modify-artifacts/SKILL.md` (rewrite)
- `resources/claude/skills/osx-modify-artifacts/SKILL.md` (rewrite)

**Manifest bumps**: `osx-modify-artifacts` 0.2.3 → **0.3.0** (breaking: schema-driven rewrite, dual-mode dropped). Bump Claude to match.

### Phase D — Rewire the orchestrator

**Goal**: PHASE0 picks the right editor per finding; PHASE2 routes Case A to `update`; workflow docs reflect the new model.

#### D.1 — `resources/opencode/commands/osx-phase0.md`

Current loop: `review → modify → re-review` (max 10). New loop: `review → route-to-editor → re-review`.

- After review produces findings, **classify finding breadth** with this crisp rule:
  - All findings target a single artifact AND no coherence-level findings → `/osx-modify <name> <artifact-id>`
  - Findings span ≥2 artifacts OR any coherence-level finding → `/opsx:update <name>`
  - Findings indicate missing artifacts → `/opsx:continue <name>`
- Keep the max-10-iterations guardrail.
- Keep "fix CRITICAL/WARNING immediately"; Suggestions can be deferred.

**Manifest bump**: `osx-phase0` 0.2.11 → **0.3.0** (breaking: editor routing logic).

#### D.2 — `resources/opencode/commands/osx-phase2.md`

Current Case A (`:60`): verify blames artifacts → `osx-modify-artifacts` + `artifacts_modified` transition.

New Case A: verify blames artifacts → **`osc-update-change`** + `artifacts_modified` transition.

Refinement: if verify identifies a clearly isolated single-artifact defect, PHASE2 *may* delegate to `osx-modify-artifacts`. But the default is `update`.

**Manifest bump**: `osx-phase2` 0.2.13 → **0.3.0** (breaking: Case A → update).

#### D.3 — `resources/opencode/skills/osx-workflow/SKILL.md`

- `:16-22` (TL;DR diagram) — redraw to show `update` as primary editor in PHASE0/PHASE2, with `modify` as surgical fallback.
- `:98-106` (phase table):
  - PHASE0 skills: `osx-review-artifacts` + `osc-update-change` (primary editor) + `osx-modify-artifacts` (surgical fallback).
  - PHASE2 skills: `osc-verify-change` + `osc-update-change` (Case A).
- `:108` — keep the PHASE0 ≠ PHASE2 disambiguation.
- `:378-383` (workflow patterns) — Enhanced manual chain becomes `review → {modify | update} → apply → test-compliance → verify`.

**Manifest bump**: `osx-workflow` 0.2.0 → **0.3.0** (breaking: phase table change).

#### D.4 — `resources/opencode/skills/osx-concepts/` references

- `osx-concepts/SKILL.md:104-117` taxonomy — update labels (done in Phase A, but verify here).
- `references/anti-patterns.md:277` — update "Missing spec updates → Use `osx-modify-artifacts`" to: route via review first, or directly to `update` for multi-artifact cases.
- `references/cli-reference.md:437-440` — keep `artifacts_modified` transition reason; add note that PHASE2 now invokes `osc-update-change` for Case A.

**Manifest bump**: `osx-concepts` 0.8.0 → **0.9.0** (additive).

**Files**: all listed above plus Claude mirrors.

### Phase E — Slash commands catch-up

**Goal**: `/osx-review` and `/osx-modify` match their rewritten skills; hygiene fix on `/osx-verify-tests`.

- `resources/opencode/commands/osx-review.md`:
  - Drop hardcoded proposal/specs/design/tasks references.
  - Route to `openspec status`/`instructions` JSON.
  - Tail pointer to rewritten skill (unchanged path).
- `resources/opencode/commands/osx-modify.md`:
  - Drop dual-mode language.
  - Document forward-only `unlocks` propagation.
  - Tail pointer to rewritten skill.
- `resources/opencode/commands/osx-verify-tests.md`:
  - Hygiene only: fix any stale `/osx-test-compliance` / `/osx-verify` references inside the skill body (the slash command is `/osx-verify-tests`; verify does not exist).
- `resources/opencode/skills/osx-review-test-compliance/SKILL.md`:
  - Stale-ref fix only at `:174-176, :189` (referenced `/osx-test-compliance` and `/osx-verify` — replace with `/osx-verify-tests` and `/opsx:verify`).

**Manifest bumps**:
- `osx-review` 0.1.3 → **0.2.0** (rewritten to schema-driven)
- `osx-modify` 0.1.4 → **0.2.0** (rewritten, dual-mode dropped)
- `osx-verify-tests` 0.1.1 → **0.1.2** (hygiene fix)
- `osx-review-test-compliance` 0.2.1 → **0.2.2** (stale-ref fix)

**Files**: all listed above plus Claude mirrors.

### Phase F — Reconcile Claude manifest drift

**Goal**: Claude tree matches OpenCode tree after the rewrite.

- Walk `resources/claude/manifest.toml`. For each resource touched in Phases B–E, set the Claude version equal to the OpenCode post-rewrite version.
- Verify all rewritten `SKILL.md` files have platform-correct frontmatter per `openspec-core/AGENTS.md:62-69`:
  - **Claude**: full YAML with `metadata` + `allowed-tools` (e.g., `allowed-tools: Bash(openspec:*)`).
  - **OpenCode**: `description` only.
- Confirm Claude slash-command bodies use `**Ask**` (not `AskUserQuestion`) per platform convention.
- Confirm Claude command naming uses `/osx:` prefix and lives at `resources/claude/commands/osx/<name>.md`.

**Files**: `resources/claude/manifest.toml`, plus any Claude mirrors whose frontmatter drifted.

### Phase G — Verification

Run in order:

1. `mise run version:check` — confirm all manifest bumps are detected and consistent. **This is a pre-commit hook** (`.pre-commit-config.yaml`) — staged changes to resource files and `install.sh` are gated by it.
2. `pytest -m unit` — fast smoke.
3. `pytest -m mechanism` — CLI validation, orchestrator wiring sanity, no AI calls.
4. `mise run test:mechanism:bats` — bats mechanism tests against the built binary. Runs `build` first.
5. `mise run verify` — full check pipeline (lint, typecheck, tests).

**Optional manual spot-check** (requires AI; slow):
- Scaffold a scratch change with `openspec new`.
- Draft artifacts via `continue`.
- Run `/osx-review` — confirm:
  - Findings are schema-driven (not hardcoded to proposal/specs/design/tasks names).
  - Routing hints point to the right editor per §6.B.1.
- Run `/osx-modify` on a single-artifact finding — confirm forward-only propagation works.
- Force multi-artifact drift — confirm `/opsx:update` is suggested.

**Do not run** `E2E_CONFIRM=1 mise run test:e2e` unless full AI-driven validation is explicitly required.

---

## 7. Risks and mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Loss of spec-format expertise**: dropping the rubric means review relies entirely on what the spec-driven schema's `template` encodes. If the template doesn't say "scenarios use `#### Scenario:`", H3-vs-H4 errors slip through. | Medium | High | Phase B verification gate (§6.B): run `openspec instructions <id> --json` and confirm template encodes format rules. If gaps, raise upstream issue against `openspec-core/source` — do NOT re-add a local rubric. |
| 2 | **PHASE0 routing complexity**: phase command now classifies finding breadth. Misjudging routes users to `update` for trivial fixes or `modify` for cascading ones. | Medium | Medium | Phase D.1 crisp classification rule: "≥2 artifacts OR any coherence-level finding → update". Make the rule literal in the phase command body. |
| 3 | **Schema-agnostic breakage on custom schemas**: both rewrites must work on schemas we haven't seen. | Low | High | Phase G manual spot-check on at least one custom schema if feasible. Otherwise document the assumption that custom schemas provide sane `template`/`rules` in the skill body's "Limitations" section. |
| 4 | **Backward compatibility for users**: existing muscle memory (`/osx-modify <name> proposal` to do an amendment) breaks. | High | Low | Add a CHANGELOG entry naming the routing explicitly: "amendments now route through `/opsx:update`; `/osx-modify` is for surgical single-artifact fixes only." Phase F version bumps (0.3.0) signal the breaking change. |
| 5 | **Version drift recurrence**: Claude manifest has drifted before. | High | Low | Phase F reconciles. Consider a follow-up issue to add a cross-platform consistency assertion in `mise run version:check`. Out of scope for this effort. |
| 6 | **`unlocks` graph incompleteness**: if a custom schema doesn't declare `requires` correctly, modify's forward propagation may miss downstream artifacts. | Low | Medium | Modify should warn when `unlocks` is empty for an artifact that clearly has content others depend on. Document this as a schema-quality issue, not a modify bug. |

---

## 8. Hand-off language templates

These literal phrases should appear in the rewritten skills' output sections to keep the user-facing voice consistent with `update` and `verify`.

### 8.1 `osx-review-artifacts` output (issues found)

```
## Artifact Review: <change-name>

**Schema**: <schemaName>
**Artifacts audited**: <count>

### <severity> findings
- **<artifact-id>:<file:line>**: <issue>
  - Fix: <concrete fix>
  - Route: </osx-modify|/opsx:update|/opsx:continue> <name> [<artifact-id>]

### Routing recommendation
<single sentence picking ONE of the routes from §6.B.1>

### Next steps
- Address findings via the routed command above.
- Re-run review after fixes: `/osx-review <name>`
```

### 8.2 `osx-review-artifacts` output (clean)

```
## Artifact Review: <change-name>

### All checks passed

**Schema compliance**: All artifacts conform to their templates and rules.
**Cross-artifact consistency**: No drift detected across the dependency graph.
**Implementation readiness**: <brief judgment>

### Next steps
- Start (or resume) implementation: `/opsx:apply <name>`
```

### 8.3 `osx-modify-artifacts` output (success)

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

### 8.4 `osx-modify-artifacts` output (intent-level change detected)

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

## 9. Version summary (target state)

After all phases complete, the manifests should read:

### OpenCode (`resources/opencode/manifest.toml`)

| Resource | Current | Target | Change type |
|---|---|---|---|
| `osx-review-artifacts` (skill) | 0.2.6 | **0.3.0** | breaking (schema-driven rewrite) |
| `osx-modify-artifacts` (skill) | 0.2.3 | **0.3.0** | breaking (surgical narrowing) |
| `osx-review-test-compliance` (skill) | 0.2.1 | **0.2.2** | hygiene (stale-ref fix) |
| `osx-phase0` (command) | 0.2.11 | **0.3.0** | breaking (editor routing) |
| `osx-phase2` (command) | 0.2.13 | **0.3.0** | breaking (Case A → update) |
| `osx-workflow` (skill) | 0.2.0 | **0.3.0** | breaking (phase table) |
| `osx-concepts` (skill) | 0.8.0 | **0.9.0** | additive (labels + refs) |
| `osx-review` (command) | 0.1.3 | **0.2.0** | rewritten |
| `osx-modify` (command) | 0.1.4 | **0.2.0** | rewritten |
| `osx-verify-tests` (command) | 0.1.1 | **0.1.2** | hygiene |

### Claude (`resources/claude/manifest.toml`)

All resources listed above get the **same target versions** as OpenCode, eliminating the existing drift.

---

## 10. Key references

### Files this plan modifies (creation order)

```
resources/opencode/skills/AGENTS.md                                    # Phase A
resources/opencode/skills/osx-concepts/SKILL.md                        # Phase A, D.4
resources/opencode/skills/osx-review-artifacts/SKILL.md                # Phase B (rewrite)
resources/opencode/skills/osx-review-artifacts/references/review-criteria.md  # Phase B (delete)
resources/opencode/skills/osx-modify-artifacts/SKILL.md                # Phase C (rewrite)
resources/opencode/commands/osx-phase0.md                              # Phase D.1
resources/opencode/commands/osx-phase2.md                              # Phase D.2
resources/opencode/skills/osx-workflow/SKILL.md                        # Phase D.3
resources/opencode/skills/osx-concepts/references/anti-patterns.md     # Phase D.4
resources/opencode/skills/osx-concepts/references/cli-reference.md     # Phase D.4
resources/opencode/commands/osx-review.md                             # Phase E
resources/opencode/commands/osx-modify.md                             # Phase E
resources/opencode/commands/osx-verify-tests.md                       # Phase E
resources/opencode/skills/osx-review-test-compliance/SKILL.md         # Phase E (stale-ref fix)
resources/opencode/manifest.toml                                       # all phases
resources/claude/skills/AGENTS.md                                      # Phase A mirror
resources/claude/skills/osx-concepts/SKILL.md                          # Phase A, D.4 mirror
resources/claude/skills/osx-review-artifacts/SKILL.md                  # Phase B mirror
resources/claude/skills/osx-review-artifacts/references/review-criteria.md  # Phase B delete
resources/claude/skills/osx-modify-artifacts/SKILL.md                  # Phase C mirror
resources/claude/commands/osx/phase0.md                                # Phase D.1 mirror
resources/claude/commands/osx/phase2.md                                # Phase D.2 mirror
resources/claude/skills/osx-workflow/SKILL.md                          # Phase D.3 mirror
resources/claude/skills/osx-concepts/references/anti-patterns.md       # Phase D.4 mirror
resources/claude/skills/osx-concepts/references/cli-reference.md       # Phase D.4 mirror
resources/claude/commands/osx/review.md                                # Phase E mirror
resources/claude/commands/osx/modify.md                                # Phase E mirror
resources/claude/commands/osx/verify-tests.md                          # Phase E mirror
resources/claude/skills/osx-review-test-compliance/SKILL.md           # Phase E mirror
resources/claude/manifest.toml                                         # Phase F
```

### Key upstream sources (read-only, do not modify)

- `openspec-core/AGENTS.md` — sync strategy, platform differences (Claude vs OpenCode frontmatter).
- `openspec-core/source/dist/core/templates/workflows/update-change.js` — the canonical schema-agnostic editor; `getUpdateChangeSkillTemplate()` and `getOpsxUpdateCommandTemplate()`.
- `openspec-core/source/dist/core/templates/workflows/continue-change.js` — schema-agnostic creator (one per turn).
- `openspec-core/source/dist/core/templates/workflows/propose.js` — schema-agnostic creator (all at once).
- `openspec-core/source/dist/core/artifact-graph/instruction-loader.js` — defines the JSON shape returned by `openspec instructions` (fields: `template`, `context`, `rules`, `dependencies`, `unlocks`, `references?`).
- `openspec-core/source/dist/core/project-config.js` — defines `rules` field semantics (per-artifact, project-supplied via `openspec/config.yaml`).

### In-repo wiring references

- `source/orchestrator/engine.py:31-59` — phase → command → agent mappings.
- `source/lib/osx.py:67-74` — `REQUIRED_SKILLS` pre-flight enforcement.
- `source/lib/osx.py:1107-1121` — `validate_skills()`.
- `.pre-commit-config.yaml` — `version:check` gating.
- `.mise/tasks/version/` — bash tasks for `version:check` and `version:update`.

---

## 11. Glossary

- **Frontier**: the boundary between created and not-yet-created artifacts in a change. `continue` advances it; `update` is forbidden from advancing it; `modify` is forbidden from advancing it.
- **`existingOutputPaths`**: concrete on-disk files for an artifact (glob-expanded for glob artifacts). Safe to read and write.
- **`resolvedOutputPath`**: the declared path or glob pattern. For glob artifacts, this is still a pattern — never write to it directly.
- **Coherence**: cross-artifact consistency — content in one artifact correctly references and aligns with content in its dependencies/dependents.
- **Surgical edit**: a single-artifact edit with forward-only dependent propagation, as distinct from `update`'s multi-artifact bidirectional reconciliation.
- **Update vs. Start Fresh**: `update`'s heuristic — if a requested edit changes the change's *intent* (rather than refining its execution), recommend `/opsx:new` rather than mutating in place. `modify` inherits this.
- **Case A / Case B** (PHASE2): when `verify` finds post-impl drift, Case A = "artifacts are wrong" (route to editor), Case B = "implementation is wrong" (route back to `apply`).

---

## 12. Open questions for follow-up (out of scope)

1. **Cross-platform version consistency assertion**: should `mise run version:check` enforce that Claude and OpenCode manifests don't drift? Currently it doesn't. Worth a separate issue.
2. **Slash command naming cleanup**: `/osx-verify-tests` ↔ skill `osx-review-test-compliance` stem mismatch. Defer to a separate naming pass.
3. **`/osx-review-fix` wrapper**: should there be a single command that wraps the review→fix loop for ad-hoc (non-orchestrator) users? Currently out of scope; PHASE0 owns the loop.
4. **Review-cache for re-runs**: when review runs after modify fixes, does it need to re-query `openspec instructions` for unchanged artifacts, or can it cache? Out of scope; treat as stateless for now.
