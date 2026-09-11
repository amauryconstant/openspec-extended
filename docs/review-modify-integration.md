# Review/Modify × Core Pre-Implementation Integration

**Status**: Implemented + refreshed (Section A: orchestrator pre-flight consumes v1.11.0 contract)
**Last updated**: 2026-09-02
**Scope**: `osx-review-artifacts`, `osx-modify-artifacts`, and the orchestrator wiring; integrated against OpenSpec core v1.6.0 (initial design), v1.7.0 (`requires`, `instructions archive`, `skip_specs`, `defaultStore`), v1.8.0 (`isPlanningComplete`, `retire_capabilities`, `status` separation), v1.9.0 (`validate --archived`, `task-numbering`, `purpose-placeholder`, `SHALL`/`MUST` guidance), v1.10.0 (`init --language`), v1.11.0 (`status --all`, `show --diff`).

> **MIN_OPENSPEC_VERSION**: `(1, 11, 0)` (set in `source/lib/osx.py:66`). Orchestrator pre-flight exits 2 below that floor.

---

## 1. Context

### 1.1 The triggering change

OpenSpec core v1.6.0 introduced `openspec-update-change` (`/opsx:update`), a new pre-implementation skill that revises existing planning artifacts in place and reconciles them bidirectionally for coherence. v1.7.0 keeps this contract unchanged (still the recommended multi-artifact editor). This skill lives alongside four other pre-implementation skills:

| Core skill | Creates new? | Revises existing? | Granularity | Schema-agnostic? |
|---|---|---|---|---|
| `new` | dir only | — | — | yes |
| `continue` | next ready one | no | one per turn | yes |
| `propose` ≈ `ff` | all `applyRequires` | no | all at once | yes |
| `update` (v1.6.0; unchanged v1.7.0) | **forbidden** | yes | multi, bidirectional, per-artifact confirm | **strictly** |

`propose` and `ff` are ~95% duplicated (same `applyRequires` loop, different framing). Treat them as one capability. v1.7.0's `requires` field on `status --json` makes the loop converge on the full transitive required set instead of stopping at `tasks.md` (the bug fixed by upstream PR #1412).

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

### 1.4 v1.8.0–v1.11.0 contract additions (orchestrator now consumes)

The original design (v1.6.0/v1.7.0) focused on the pre-implementation *editor* family. Five later core contracts became load-bearing for the extended orchestrator:

| Contract | Source version | What the orchestrator does with it | Where wired |
|---|---|---|---|
| `isPlanningComplete` | v1.8.0 | Pre-flight `validate_change_dir` consults it before falling back to a local file check | `source/lib/osx.py` (validate_change_dir) + `source/orchestrator/engine.py:242` (wrapper) |
| `retire_capabilities: true` | v1.8.0 | `.openspec.yaml` is read once; orchestrator short-circuits PHASE0 → PHASE6 when set + planning complete | `source/orchestrator/engine.py` (`OrchestratorState.retire_capabilities`, declared at `:79`; set at `:262`/`:324`); `resources/opencode/commands/osx-phase0.md` (routing table at `:33-40`) |
| `operations.{apply,archive}.guidance` | v1.7.0 | Strings injected into PHASE1/PHASE6 prompts as `RunRequest.extra_prompt` | `source/lib/osx.py` (fetch_operation_guidance at `:2193`); `source/orchestrator/runner.py` (RunRequest.extra_prompt at `:47`); `source/orchestrator/engine.py:545` (build_run_request) |
| `show <change> --diff` | v1.11.0 | PHASE2 embeds the per-requirement diff as a `## Requirement diff` appendix in `verification-report.md` | `resources/opencode/commands/osx-phase2.md` (MANDATORY CHECKPOINT step 3 at `:23`; embed subsection at `:41`) |
| `validate --archived` | v1.9.0 | Non-fatal post-install/update sweep; opt-in strict via `--strict-archived` or `OPENSPEC_VALIDATE_ARCHIVED_STRICT=1` | `source/cli.py:_post_install_archived_sweep` at `:1214` (call sites at `:1071` and `:1898`) |

The full per-contract operational notes (and how they interact with the schema-agnostic contract in §4.2) live in §13 below. The broader context — what these contracts mean in upstream OpenSpec, and the changelog entries that introduced them — lives in `orchestrator/core/AGENTS.md` (v1.7.0–v1.11.0 highlights) and `orchestrator/core/source/CHANGELOG.md`.

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
- `artifacts[]`: array of `{ id, status, requires }` where status ∈ `{done, ready, blocked}` and `requires` (v1.7.0+) is the dependency list preferred over `dependencies`/`unlocks` for graph construction
- `isPlanningComplete`: boolean (v1.8.0+) — true when every non-skipped planning artifact exists. Distinct from `isComplete`. Orchestrator pre-flight (`validate_change_dir`) consults this field; treat `isComplete` as deprecated for new consumers.
- `isComplete`: boolean — v1.8.0 backward-compatibility alias folded from planning and implementation. Kept through v1.11.0.
- `planningHome`, `changeRoot`: path context (use these, don't assume repo-local paths)
- `root.{kind, root, source}`: project context (v1.7.0+). `source` ∈ `{project, defaultStore, global_default, store}` distinguishes resolution provenance — `global_default` is the v1.7.0+ machine-level fallback.
- `artifactPaths.<id>.existingOutputPaths`: concrete on-disk files (glob-expanded for glob artifacts)
- `artifactPaths.<id>.resolvedOutputPath`: the declared path or glob pattern (do NOT write to this for glob artifacts)
- `actionContext`: scope context
- `nextSteps`: hints

**`openspec instructions <artifact-id> --change <name> --json`** returns:
- `template`: structural template the artifact should conform to (this is where spec-driven format rules live — H4 scenarios, checkbox format, etc.)
- `context`: project background (constraint for the LLM, never copied into artifact files)
- `rules`: project-supplied overrides from `openspec/config.yaml` (per-artifact, free-form strings; added to that artifact's built-in guidance)
- `operationGuidance`: array of strings (v1.7.0+) — present on `instructions apply` and `instructions archive` envelopes. Project-level advisory from `operations.{apply|archive}.guidance` in `openspec/config.yaml`. Consumed via `osx_lib.fetch_operation_guidance` for PHASE1/PHASE6 prompts only. Not present on other operation envelopes (`proposal`, `update`, etc.).
- `dependencies`: completed artifacts to read for context
- `unlocks`: reverse-deps — artifacts that depend on this one
- `resolvedOutputPath`, `existingOutputPaths`: file paths
- `instruction`: schema-specific guidance
- `references?`: optional upstream-store index (only when declared)

**`openspec show <change> --diff --json`** returns (v1.11.0+):
- `changeName`, `schemaName`: identity
- `deltas[]`: each delta carries `diff` and `warning` fields for MODIFIED requirements (plain unified-diff on `--json`; colorized on terminal)
- ADDED requirements print in full (no `diff` block)
- REMOVED requirements carry authored Reason/Migration
- RENAMED requirements carry FROM/TO (a delta that RENAMEs and MODIFIES in the same change is diffed against its old name)

The PHASE2 review embeds this payload as a `## Requirement diff` appendix in `verification-report.md`. See `osx-phase2` MANDATORY CHECKPOINT step 3 for the protocol; §13.4 for the consumer contract.

**Schema-declared artifact graph**: the schema itself declares `requires` relationships between artifacts (validated for cycles by the CLI). This means the `dependencies`/`unlocks` graph is fully schema-derived — no hardcoded proposal↔specs↔design↔tasks pairs needed.

---

## 5. Current-state inventory

For implementation reference, here is where review/modify currently touch the codebase. All file paths are repo-relative.

### 5.1 Skills (OpenCode canonical)

| Skill | Path | Current version |
|---|---|---|
| `osx-review-artifacts` | `resources/opencode/skills/osx-review-artifacts/SKILL.md` | 0.3.3 |
| `osx-modify-artifacts` | `resources/opencode/skills/osx-modify-artifacts/SKILL.md` | 0.3.4 |
| `osx-review-test-compliance` | `resources/opencode/skills/osx-review-test-compliance/SKILL.md` | 0.2.6 (out of scope; stale-ref fix only) |
| `osx-workflow` | `resources/opencode/skills/osx-workflow/SKILL.md` | 0.3.6 — gated by `install --with-autonomous`; absent from `REQUIRED_SKILLS` (see `source/lib/osx.py:AUTONOMOUS_RESOURCE_NAMES`) |
| `osx-concepts` | `resources/opencode/skills/osx-concepts/SKILL.md` | 0.9.6 — taxonomy reference (no pre-flight gate) |
| `osx-commit` | `resources/opencode/skills/osx-commit/SKILL.md` | 0.1.2 — required by pre-flight, but not part of review/modify scope |

The legacy `osx-review-artifacts/references/review-criteria.md` (321-line rubric) was deleted in Phase B in favour of the schema-driven contract.

Claude mirrors live under `resources/claude/skills/<name>/SKILL.md`. Slash-command bodies (`osx-changelog`, `osx-maintain-docs`) are *not* skills — they live as flat files and are deliberately absent from `REQUIRED_SKILLS`.

### 5.2 Slash commands

| Command | Path | Wraps | Version |
|---|---|---|---|
| `/osx-review` | `resources/opencode/commands/osx-review.md` | `osx-review-artifacts` | 0.2.2 |
| `/osx-modify` | `resources/opencode/commands/osx-modify.md` | `osx-modify-artifacts` | 0.2.2 |
| `/osx-verify-tests` | `resources/opencode/commands/osx-verify-tests.md` | `osx-review-test-compliance` | 0.1.4 |
| `/osx-changelog` | `resources/opencode/commands/osx-changelog.md` | (self-contained) | 0.2.0 |
| `/osx-maintain-docs` | `resources/opencode/commands/osx-maintain-docs.md` | (self-contained) | 0.3.0 |

Phase commands (`/osx-phase0` … `/osx-phase6`) live in `resources/opencode/commands/osx-phase{0..6}.md`; their versions live in `manifest.toml`. Claude mirrors: `resources/claude/commands/osx/{review,modify,verify-tests,changelog,maintain-docs}.md`. Note Claude uses `/osx:` prefix and `**Ask**` tool (vs OpenCode's `/osx-` prefix and `AskUserQuestion`).

### 5.3 Orchestrator wiring

- `source/orchestrator/engine.py` — never names review/modify skills directly; only knows phase → command → agent mappings. `PHASE_NAMES`, `PHASE_COMMANDS`, `PHASE_AGENTS` near the top of the module. PHASE0 and PHASE2 dispatch different agents (`osx-analyzer` and `osx-reviewer`, respectively). Section A wiring points:
  - `validate_change_dir` engine wrapper at `engine.py:242` (A.1 — consults `isPlanningComplete`)
  - `OrchestratorState.retire_capabilities` declared at `engine.py:79`; stamped in the `validate_change_dir` wrapper at `:262` and in `validate_archive` at `:324` (A.3)
  - `build_run_request(state, phase, *, on_pid)` helper at `engine.py:545` (A.4 — factors out the `extra_prompt` plumbing)
- `source/lib/osx.py` — change-management library. Key anchors:
  - `MIN_OPENSPEC_VERSION = (1, 11, 0)` at `:66`; `REQUIRED_SKILLS` at `:122-128`
  - `_fetch_planning_status(change_id, *, store=None)` at `:254` (A.1 helper)
  - `validate_change_dir(target, *, store=None)` at `:1450` (A.1)
  - `_resolve_concurrency(explicit)` at `:1921` (OPENSPEC_CONCURRENCY env-var plumbing)
  - `validate_archived(...)` at `:1990` (A.6 — `validate --archived` first-class scope)
  - `read_change_metadata(change_dir)` at `:2037` (A.3 — reads `.openspec.yaml`)
  - `fetch_operation_guidance(operation, project_root, store=None)` at `:2193` (A.4 — reads `openspec/config.yaml`)
- `source/cli.py` — top-level CLI. Key anchors:
  - `_resolve_language(arg)` at `:135` (OPENSPEC_LANGUAGE env-var plumbing for `init --language`)
  - `_post_install_archived_sweep(strict=False, timeout=30)` at `:1214` (A.6 — non-fatal sweep; called from `deploy_core` at `:1071` and from `update-core_cmd` at `:1898`; `--strict-archived` flag at `:1162`/`:1332`/`:1881`; `OPENSPEC_VALIDATE_ARCHIVED_STRICT=1` env honoured inside the function)
- `source/orchestrator/runner.py` — AI-runner abstraction. `RunRequest.extra_prompt: str` at `:47` (A.4 — OpenCode attaches via `--file` at `:134`; Claude prepends to the prompt at `:179`).
- `resources/opencode/commands/osx-phase0.md` — PHASE0 details. Loads `osx-review-artifacts` at `:28`. Routing table at `:33-40` — the `retire_capabilities` row (line 39) is the A.3 short-circuit. PHASE1–PHASE5 are skipped on retirement (PHASE6 runs directly).
- `resources/opencode/commands/osx-phase2.md` — PHASE2 (post-impl verify). MANDATORY CHECKPOINT step 3 at `:23` fetches `openspec show "$1" --diff --json`; the `## Requirement diff` embed subsection at `:35-49` writes the per-requirement diff into `verification-report.md` (A.2). Case A at `:55` routes verify-blamed-artifact defects to `/opsx:update` (with `osx-modify-artifacts` only for clearly isolated single-artifact defects); `artifacts_modified` transition at `:61`.
- `resources/opencode/commands/osx-phase5.md` — reflection only. No skill invocation.

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
Confirm the template field actually encodes the format rules we used to hardcode (H4 scenarios, checkbox format, SHALL/MUST, etc.). If gaps, raise upstream issue against `orchestrator/core/source` — do NOT re-add a local rubric.

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
- Verify all rewritten `SKILL.md` files have platform-correct frontmatter per `orchestrator/core/AGENTS.md:62-69`:
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

### Phase H — Adopt post-v1.7.0 contracts (Section A, completed)

Six contracts from v1.8.0–v1.11.0 were wired across Section A. Each is documented in §13 with its consumer and reference:

- A.1 → `isPlanningComplete` (see §13.1) — orchestrator pre-flight consults the v1.8.0+ field before the local file-existence fallback
- A.2 → `show <change> --diff` appendix in PHASE2 (see §13.4) — per-requirement diff embeds into `verification-report.md`
- A.3 → `retire_capabilities` marker (see §13.2) — `.openspec.yaml` flag short-circuits PHASE0 → PHASE6
- A.4 → `operations.{apply,archive}.guidance` (see §13.3) — project-level advisory injected as `RunRequest.extra_prompt` on PHASE1/PHASE6 spawns only
- A.5 → `OPENSPEC_LANGUAGE` / `--language` plumbing (informational; not a core contract — see `source/cli.py:_resolve_language:135` and `init --language` in v1.10.0)
- A.6 → `validate --archived` post-install sweep (see §13.5) — non-fatal by default; `--strict-archived` / `OPENSPEC_VALIDATE_ARCHIVED_STRICT=1` opts in to fail-on-warning
- A.7 → `OPENSPEC_CONCURRENCY` plumbing (informational; not a core contract — see `_resolve_concurrency` at `source/lib/osx.py:1921`)

The post-A Phase H verification addendum (run alongside Phase G):

6. `pytest tests/unit/test_validation_translator.py::TestValidateChangeDirPlanning -m unit` — A.1 contract: validate_change_dir consults `isPlanningComplete` before falling back.
7. `pytest tests/unit/test_schema_resolution.py::TestFetchOperationGuidance -m unit` — A.4 contract: guidance strings round-trip from `openspec/config.yaml` to the `RunRequest.extra_prompt` field.
8. `pytest tests/unit/test_validation_translator.py::TestReadChangeMetadata -m unit` — A.3 contract: `retire_capabilities` (and `skip_specs`, `schema`) parse from `.openspec.yaml`.
9. `pytest tests/integration/test_install_flow.py::TestValidateArchivedSweep -m integration` — A.6 contract: non-fatal sweep on default; `strict=True` exits non-zero.
10. `pytest tests/contract/test_upstream_envelopes.py -m contract` — live `openspec` envelope shape for `isPlanningComplete` (`TestStatusPlanning`) and `show --diff` (`TestShowDiffEnvelope`). `operationGuidance` and `validate --archived` are not in this live suite (they are covered by in-process unit/integration tests); the contract tests guard only what they can probe against a real installed `openspec`.

---

## 7. Risks and mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Loss of spec-format expertise**: dropping the rubric means review relies entirely on what the spec-driven schema's `template` encodes. If the template doesn't say "scenarios use `#### Scenario:`", H3-vs-H4 errors slip through. | Medium | High | Phase B verification gate (§6.B): run `openspec instructions <id> --json` and confirm template encodes format rules. If gaps, raise upstream issue against `orchestrator/core/source` — do NOT re-add a local rubric. |
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

## 9. Version summary

> Current as of OpenSpec core v1.11.0 (`MIN_OPENSPEC_VERSION = (1, 11, 0)`). Per-resource versions tracked in `resources/opencode/manifest.toml` and `resources/claude/manifest.toml`; both files are regenerated by `mise run sync:mirrors`. This section records the per-resource **post-rewrite** versions (the table below is the manifest as it stands today, not the plan-time targets).

### OpenCode (`resources/opencode/manifest.toml`)

| Resource | Version |
|---|---|
| `osx-review-artifacts` (skill) | 0.3.3 |
| `osx-modify-artifacts` (skill) | 0.3.4 |
| `osx-review-test-compliance` (skill) | 0.2.6 |
| `osx-concepts` (skill) | 0.9.6 |
| `osx-workflow` (skill) | 0.3.6 |
| `osx-commit` (skill) | 0.1.2 |
| `osx-phase0` (command) | 0.3.2 |
| `osx-phase1` (command) | 0.3.6 |
| `osx-phase2` (command) | 0.3.3 |
| `osx-phase3` (command) | 0.3.6 |
| `osx-phase4` (command) | 0.2.14 |
| `osx-phase5` (command) | 0.3.6 |
| `osx-phase6` (command) | 0.3.9 |
| `osx-review` (command) | 0.2.2 |
| `osx-modify` (command) | 0.2.2 |
| `osx-verify-tests` (command) | 0.1.4 |
| `osx-changelog` (command) | 0.2.0 |
| `osx-maintain-docs` (command) | 0.3.0 |
| `osx-analyzer` / `osx-builder` / `osx-maintainer` (agent) | 0.2.3 each |
| `osx-reviewer` (agent) | 0.1.0 |

### Claude (`resources/claude/manifest.toml`)

`resources/claude/manifest.toml` mirrors the OpenCode versions listed above (the auto-generated manifest keeps them in lockstep; `mise run sync-mirrors --check` enforces parity as a pre-commit hook).

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

- `orchestrator/core/AGENTS.md` — sync strategy, platform differences (Claude vs OpenCode frontmatter).
- `orchestrator/core/source/dist/core/templates/workflows/update-change.js` — the canonical schema-agnostic editor; `getUpdateChangeSkillTemplate()` and `getOpsxUpdateCommandTemplate()`.
- `orchestrator/core/source/dist/core/templates/workflows/continue-change.js` — schema-agnostic creator (one per turn).
- `orchestrator/core/source/dist/core/templates/workflows/propose.js` — schema-agnostic creator (all at once).
- `orchestrator/core/source/dist/core/artifact-graph/instruction-loader.js` — defines the JSON shape returned by `openspec instructions` (fields: `template`, `context`, `rules`, `dependencies`, `unlocks`, `references?`).
- `orchestrator/core/source/dist/core/project-config.js` — defines `rules` field semantics (per-artifact, project-supplied via `openspec/config.yaml`).

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
- **`isPlanningComplete`**: v1.8.0+ `openspec status --change <name> --json` boolean — true when every non-skipped planning artifact exists. Distinct from `isComplete` (kept as a back-compat alias that folds planning and implementation). The orchestrator's pre-flight consults this field; treat `isComplete` as deprecated.
- **`retire_capabilities`**: v1.8.0+ change metadata in `.openspec.yaml`. Set to `true` (alongside the mandatory `schema:`) to allow `openspec archive` to delete a capability's main spec when its last requirement is REMOVED. Without the marker, archive aborts with "Spec must have at least one requirement". Stamped on `OrchestratorState.retire_capabilities` (`engine.py:79`) and read by PHASE0's routing table.
- **`operationGuidance`**: v1.7.0+ project-level advisory returned on `openspec instructions apply|archive --json`. Sourced from `operations.{apply|archive}.guidance` in `openspec/config.yaml`. Injected as `RunRequest.extra_prompt` on PHASE1/PHASE6 spawns only; advisory, never authoritative. Do not copy verbatim into artifact files.
- **`isComplete`** *(deprecated)*: v1.8.0 backward-compatibility alias for the folded planning-and-implementation boolean. Prefer `isPlanningComplete` for any new consumer. Kept through v1.11.0.
- **Operation guidance vs. artifact rules**: similar YAML shape but distinct meaning — `operationGuidance` (operations.{apply|archive}.guidance) is project-level advisory for an entire operation; `rules` (config.yaml's per-artifact block) is per-artifact content guidance that gets appended to that artifact's built-in template. Both are advisory; neither is an enforceable check.

---

## 12. Open questions for follow-up (out of scope)

1. **Cross-platform version consistency assertion**: should `mise run version:check` enforce that Claude and OpenCode manifests don't drift? Currently it doesn't. Worth a separate issue.
2. **Slash command naming cleanup**: `/osx-verify-tests` ↔ skill `osx-review-test-compliance` stem mismatch. Defer to a separate naming pass.
3. **`/osx-review-fix` wrapper**: should there be a single command that wraps the review→fix loop for ad-hoc (non-orchestrator) users? Currently out of scope; PHASE0 owns the loop.
4. **Review-cache for re-runs**: when review runs after modify fixes, does it need to re-query `openspec instructions` for unchanged artifacts, or can it cache? Out of scope; treat as stateless for now.
5. **Should `osx review` consume `isPlanningComplete` directly?** Today the orchestrator pre-flight consumes it, but the standalone `/osx-review` slash command (`osx-review.md`) does not. Inconsistency: standalone users see the local-fallback behavior; orchestrator users see the core signal. Either route both through the same helper or document the difference.
6. **Should `osx review` short-circuit on `retire_capabilities: true`?** Same question — orchestrator's PHASE0 does, but the standalone slash command does not. PHASE0's routing table is in `osx-phase0.md:33-40`; the slash command is in `osx-review.md`.
7. **Should `osx modify` log `operationGuidance`?** The orchestrator injects guidance as `extra_prompt` on PHASE1/PHASE6 spawns. The standalone `/osx-modify` slash command does not. Decide whether standalone `/osx-modify` is for "edit an artifact" (which the user is doing manually) or "implement an apply change" (which deserves guidance).

---

## 13. Post-v1.7.0 contract additions

This section catalogues every v1.8.0–v1.11.0 contract the extended orchestrator depends on. Each entry has: (1) the contract, (2) the source version, (3) the consumer, (4) the operational note. Upstream context (changelog entries, design intent) lives in `orchestrator/core/AGENTS.md` and `orchestrator/core/source/CHANGELOG.md`; this section is the extended-side mirror.

### 13.1 `isPlanningComplete` (v1.8.0+)

**Contract**: `openspec status --change <name> --json` returns `isPlanningComplete: bool` distinct from `isComplete`. `isPlanningComplete` is true when every non-skipped planning artifact exists; `isComplete` is a backward-compatibility alias that folds planning and implementation together (kept through v1.11.0). See `orchestrator/core/source/CHANGELOG.md` PR #1518 for the v1.8.0 introduction.

**Consumer**: `validate_change_dir` library helper (`source/lib/osx.py:1450`) reads the field via `_fetch_planning_status` (`source/lib/osx.py:254`); the engine wrapper at `source/orchestrator/engine.py:242` logs the source (`core` or `local-heuristic`) on success. Falls back to `_validate_change_dir_local` (`source/lib/osx.py:1559`) when the CLI is missing, the call fails, the version is below v1.8.0, or `OPENSPEC_EXTENDED_NO_PLANNING_CORE=1` is set.

**Operational note**: When the AI sees a pre-flight failure citing specific missing artifact ids, the agent should fetch those artifacts via `/opsx:continue <name>` — the local file check is a fallback, not the source of truth. The pre-flight surface is `planning_complete` (a tri-state field: `True` / `False` / `None` for "unknown"), not the raw core boolean; callers should treat `None` as "we couldn't reach core; local-heuristic result follows in `missing`".

**Reference**: `source/lib/osx.py:1450` (library), `source/orchestrator/engine.py:242` (engine wrapper). Tests: `tests/unit/test_validation_translator.py::TestValidateChangeDirPlanning` (line 843) for the engine-level behaviour, plus `tests/contract/test_upstream_envelopes.py::TestStatusPlanning::test_status_includes_isPlanningComplete` (line 185) for the live-`openspec` envelope shape. Authoritative core reference: `orchestrator/core/AGENTS.md:38` and `orchestrator/core/source/CHANGELOG.md` 1.8.0.

### 13.2 `retire_capabilities: true` (v1.8.0+)

**Contract**: A change with `retire_capabilities: true` in `.openspec.yaml` (alongside the mandatory `schema:`) declares that `openspec archive` may delete the capability's main spec if its last requirement is REMOVED. Without the marker, archive aborts with "Spec must have at least one requirement". Core additionally aborts when the emptied spec also holds content the merge cannot account for — the abort names the blocking lines and reports the marker as the way out (PR #1699, v1.10.0). See `orchestrator/core/source/CHANGELOG.md` PR #1484.

**Consumer**: `osx.read_change_metadata(change_dir)` (`source/lib/osx.py:2037`) reads `.openspec.yaml` once during pre-flight. The result is stashed on `OrchestratorState.retire_capabilities` (declared at `source/orchestrator/engine.py:79`; set in the `validate_change_dir` wrapper at `:262` and in `validate_archive` at `:324`). PHASE0's routing table (`resources/opencode/commands/osx-phase0.md:33-40`, line 39 specifically) routes the change to `/opsx:archive <name>` (skipping PHASE1–PHASE5) when the marker is set *and* planning is complete. The orchestrator's `--from-phase` resume path checks the marker and short-circuits to PHASE6 on the next invocation.

**Operational note**: An in-flight MODIFIED change against the retired capability will keep validating clean and then refuse to archive ("target spec does not exist; only ADDED requirements are allowed for new specs"). Close or rework that change alongside the retirement. The retirement is whole-file deletion: the marker is honored only when the emptied spec has nothing left but its title, `## Purpose`, and its requirement blocks — any `## Notes` section or comment under a requirement causes the abort to name those lines.

**Reference**: `source/lib/osx.py:2037` (read_change_metadata), `source/orchestrator/engine.py` (OrchestratorState.retire_capabilities), `resources/opencode/commands/osx-phase0.md` (routing table). Tests: `tests/unit/test_validation_translator.py::TestReadChangeMetadata` for the parser, `tests/integration/test_phase_workflow.py::test_validate_change_dir_stamps_retire_capabilities` for the engine wrapper, `tests/contract/test_upstream_envelopes.py::TestArchiveWithRetireCapabilities` for live-core support.

### 13.3 `operations.{apply,archive}.guidance` (v1.7.0+)

**Contract**: `openspec/config.yaml` may declare per-operation advisory strings:

```yaml
schema: spec-driven
operations:
  apply:
    guidance:
      - "Always run unit tests after a milestone commit."
      - "Prefer composition over inheritance."
  archive:
    guidance:
      - "Move CHANGELOG.md entry above the v-next header."
```

The strings surface as `operationGuidance: string[]` in `openspec instructions apply|archive --json`. The operations supported are exactly `apply` and `archive` (no `update`, `propose`, `continue`, etc.). Core docs (`orchestrator/core/source/docs/agent-contract.md:69-72`) make the contract precise: both `context` and `operationGuidance` are read from the selected root on every invocation; `context` is a required prompt-level input (project facts, conventions, constraints); `operationGuidance` is advisory input whose entries are followed only when applicable and compatible with the built-in workflow. Neither field is an enforceable check. Note: `orchestrator/core/AGENTS.md` does **not** name this contract in its synopsis — it lives in the changelog and `docs/agent-contract.md` only.

**Consumer**: `osx.fetch_operation_guidance(operation, project_root, store=None)` (`source/lib/osx.py:2193`) reads `openspec/config.yaml` (or `.yml`) directly and returns the list. The orchestrator's `build_run_request` (`source/orchestrator/engine.py:545`) calls this helper only for PHASE1 (`operation="apply"`) and PHASE6 (`operation="archive"`) and passes the joined strings as `RunRequest.extra_prompt` (`source/orchestrator/runner.py:47`). Other phases ignore the guidance (the field stays `""`). The OpenCode runner attaches the prompt via `--file` (`runner.py:134`); the Claude runner prepends it to the slash-command prompt (`runner.py:179`).

**Operational note**: The guidance is **advisory**, not authoritative. Treat it as project context that shapes implementation choices; do not copy it verbatim into artifact files or commit messages. Core's apply/archive skills explicitly warn: "Do not copy runtime context or operation guidance into implementation files or planning artifacts" (see `orchestrator/core/source/skills/openspec-apply-change/SKILL.md` and `orchestrator/core/source/skills/openspec-archive-change/SKILL.md`). Don't confuse `operationGuidance` with `rules` — they share a YAML shape but mean different things (see glossary).

**Reference**: `source/lib/osx.py:2193` (fetch_operation_guidance), `source/orchestrator/runner.py:47` (RunRequest.extra_prompt), `source/orchestrator/engine.py:545` (build_run_request). Tests: `tests/unit/test_schema_resolution.py::TestFetchOperationGuidance` (line 168) covers parser behaviour; `tests/integration/test_phase_workflow.py` line 1231 covers the orchestrator integration. There is no live-`openspec` contract test for the `operationGuidance` envelope — it's verified through the in-process helper because the envelope is identical to the file contents.

### 13.4 `show <change> --diff` (v1.11.0+)

**Contract**: `openspec show <change> --diff --json` renders each MODIFIED requirement as a unified diff against the requirement it replaces in the main spec; ADDED requirements print in full (no `diff` block); REMOVED print authored Reason/Migration; RENAMED print FROM/TO (a delta that RENAMEs and MODIFIES in the same change is diffed against its old name). `--json --diff` keeps the existing payload shape and adds `diff` and `warning` fields to MODIFIED deltas only. Main specs resolve against the same root as the change, so `--store <id>` diffs against that store. See `orchestrator/core/source/CHANGELOG.md` PR #980.

**Consumer**: PHASE2 (REVIEW) fetches this payload during its MANDATORY CHECKPOINT step 3 (`resources/opencode/commands/osx-phase2.md:23`) and embeds it as a `## Requirement diff` appendix in `verification-report.md`. ADDED/REMOVED/RENAMED deltas appear in a separate `## Delta inventory` section above the diff (`osx-phase2.md:37-40`); MODIFIED deltas with a `warning` field get a `## Verification warnings` section (`osx-phase2.md:47-49`). The Claude mirror (`resources/claude/skills/osx-phase2/SKILL.md`) carries the same protocol.

**Operational note**: The diff payload replaces the hand-rolled "what changed in this requirement?" prose that earlier versions of PHASE2 produced. Reviewers should still write their own narrative — the diff is supplementary context, not the report. When a MODIFIED requirement is renamed-and-modified in the same delta, the diff is against the pre-rename version; if you'd prefer the new-name header, sort the delta in your head before quoting.

**Reference**: `resources/opencode/commands/osx-phase2.md` (MANDATORY CHECKPOINT step 3 + the `### Embed requirement-level diff in verification-report.md` sub-section). Tests: `tests/contract/test_upstream_envelopes.py::TestShowDiffEnvelope` (line 259) for live-core envelope shape, `tests/integration/test_phase_workflow.py` line 962 for the orchestrator recording, `tests/e2e/mechanism.bats` line 462 for the built-binary smoke.

### 13.5 `validate --archived` (v1.9.0+)

**Contract**: `openspec validate --archived` is an opt-in CI/pre-commit gate that every change under `changes/archive/` has all `tasks.md` checkboxes ticked. Exits non-zero if any are unchecked. Standalone scope — does not alter any other `validate` invocation and does not re-validate already-applied spec deltas. See `orchestrator/core/source/CHANGELOG.md` PR #1604 and `orchestrator/core/AGENTS.md:25`.

**Consumer**: `source/cli.py._post_install_archived_sweep(strict=False, timeout=30)` (`source/cli.py:1214`) runs `openspec validate --archived --json` after `deploy_core` finishes (`source/cli.py:1071`) and after `update-core_cmd` returns (`source/cli.py:1898`). Default is non-fatal: a yellow warning names the remediation (`openspec validate --archived --strict --json`). Opt-in to fail-on-warning via `--strict-archived` (CLI flag, declared at `cli.py:1162`, `:1332`, `:1881`) or `OPENSPEC_VALIDATE_ARCHIVED_STRICT=1` (env var, honoured inside the function at `cli.py:1222`).

**Operational note**: The sweep is a CI hygiene check, not a regression test. It catches the case where someone archived a change with unfinished work — exactly the audit trail `osc-bulk-archive-change` later relies on. The function also bridges the broader `validate --archived` envelope into the `osx validate archived` subcommand (`source/lib/osx.py:1990` — `validate_archived`) for in-process callers.

**Reference**: `source/cli.py:1214` (_post_install_archived_sweep), `source/lib/osx.py:1990` (validate_archived). Tests: `tests/integration/test_install_flow.py::TestValidateArchivedSweep` (line 1011) and `TestValidateArchivedSweepInProcess` (line 1125), `tests/unit/test_no_double_json.py` line 172, `tests/unit/test_validate_subcommands.py:164`, `tests/e2e/mechanism.bats:501`. There is no live-`openspec` contract test for `validate --archived` — the contract is narrow enough that the integration tests cover the round-trip.

### 13.6 Related v1.7.0+ contracts (informational)

These were adopted in v1.7.0 but not separately wired in the extended system (already covered by existing passthroughs):

- **`requires: string[]`** on each `artifacts[]` entry — used by `osx-review-artifacts` Step 4 to build the dependency graph (the v1.6.0 `dependencies`/`unlocks` graph derived via `openspec instructions` still works, but `requires` is the preferred signal). See `resources/opencode/skills/osx-review-artifacts/SKILL.md`.
- **`skip_specs: true`** change metadata — zero-delta changes (pure refactors). Honoured by core's validator; extended side surfaces it in `read_change_metadata` (`source/lib/osx.py:2037`) so the orchestrator can log it.
- **`defaultStore` machine-level fallback** — `openspec config set defaultStore <id>` sets a per-machine fallback. The status `root` block reports `source: "global_default"` when used. See `resources/opencode/skills/osx-concepts/references/cli-reference.md` ("openspec store and the --store flag" section, line 444+) for the full precedence table. Not separately wired in the orchestrator; resolution flows through `current_store.get()`.
- **`instructions archive`** — read-only mirror of `instructions apply`. Returns `{ "changeName", "context"?, "operationGuidance"?, "root" }` per `orchestrator/core/source/docs/agent-contract.md:72`. Surfaces archive-specific guidance without requiring a change to be in apply state. (Note: this is the same v1.7.0 PR #1062 that introduced `operationGuidance`.)

### 13.7 Interaction with the §4.2 schema-agnostic contract

The six rules in §4.2 (Schema source of truth, Glob safety, Frontier discipline, No code edits, Per-edit confirmation, Severity calibration) were authored at v1.6.0. Two rules are now load-bearing beyond their original scope:

- **Rule 1 (Schema source of truth)** — extended to include `isPlanningComplete` (for the planning-complete signal), `retire_capabilities` (for routing), and `operationGuidance` (for prompt injection). Review and modify skills must consume all three when present. The `existingOutputPaths` discipline (write only to concrete files) is unchanged but now stricter: a MODIFIED requirement delta that an agent is editing under `osx-modify-artifacts` should never re-write the file paths the `show --diff` envelope already pinned.
- **Rule 2 (Glob safety)** — unchanged. The new `requires` field (v1.7.0+) does not change which paths are safe to write.

The other four rules are unchanged. The `Severity calibration` rule (adopt `verify`'s "prefer SUGGESTION over WARNING, WARNING over CRITICAL") is reinforced by `validate --archived` findings: an archived change with unfinished `tasks.md` is a hygiene defect, not a regression, so it surfaces as a warning in the post-install sweep unless `--strict-archived` is set.
