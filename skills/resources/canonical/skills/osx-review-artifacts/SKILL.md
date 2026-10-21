---
name: osx-review-artifacts
description: Schema-driven audit of OpenSpec change artifacts before implementation, mirroring the three-dimension report (Completeness / Correctness / Coherence) and the CRITICAL / WARNING / SUGGESTION severity scale of openspec-verify-change. Read-only — emits a routing report and never edits artifacts. Trigger words: "review artifacts", "osx review", "opsx review", "audit planning".
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  author: openspec-extended
  version: "0.5.0"
---

# osx-review-artifacts

Read-only, schema-driven audit of the planning artifacts in a change. Emits a routing report that points at the next editor — never edits artifacts directly. Reading is allowed on every concrete file listed in `artifactPaths.<id>.existingOutputPaths`.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `schemas`, `view`). Once selected, treat `--store <id>` as sticky for the rest of the workflow. Full flag matrix in the shared `references/store-selection.md`.

> **Schema-agnostic contract** — see the shared `references/schema-agnostic-contract.md` for the upstream contract this skill consumes.

Sits in the pre-implementation workflow between artifact creation (`/osc-continue-change`, `/osc-propose`, `/osc-ff-change`) and implementation (`/osc-apply-change`). Use it standalone via `/osx-review <change>` or as part of PHASE0.

**Input**: Optionally specify `[<change-name>]` as `$1` (e.g., `/osx-review add-auth`). PHASE0 dispatches the change name automatically. For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. Mark the most-recently modified active change as `(Recommended)`. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

---

**Steps**

1. **Select the change**

   If a name is provided (as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and ask the user to select one with `{{ASK_TOOL}}`. Mark the most-recently modified active change as `(Recommended)`.

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-review <other>`).

2. **Check status to understand the schema**

   ```bash
   openspec status --change "<name>" [--store "<id>"] --json
   ```

   Parse the JSON to capture:
   - `schemaName` — the workflow schema id (e.g., `"spec-driven"`).
   - `planningHome`, `changeRoot` — path context (do not assume repo-local paths).
   - `artifactPaths.<id>.{outputPath, resolvedOutputPath, existingOutputPaths}`.
   - `artifacts[]` — array of `{id, status, missingDeps?, requires?}` with status in `{done, ready, blocked}`.
   - `isComplete`, `applyRequires`, `nextSteps`, `actionContext.allowedEditRoots`.

   > **v1.7.0 contract**: each entry in `artifacts[]` carries a `requires` array of the artifact ids it directly depends on. This is the preferred input for Step 4's dependency graph. Fall back to `instructions --json` `dependencies`/`unlocks` only when `requires` is absent.

   For each artifact with `status == "done"` and non-empty `existingOutputPaths`, queue it for the per-artifact audit (Step 5). Skip `ready` and `blocked` — those are frontier concerns, reported in Step 7.

   If `isComplete` is already `true`, the schema is satisfied; the cross-artifact audit (Step 6) is still worth running.

   a. **Build spec inventory (v1.13.0+, additive)**

   ```bash
   openspec list --specs [--store "<id>"] --json
   # for each spec id in the response:
   openspec show "<spec-id>" --type spec --json --no-scenarios [--store "<id>"]
   ```

   Capture the full spec inventory as `{spec_id -> {path, purpose, requirements_count}}`.

   > **v1.13.0 contract**: `openspec list --specs` is the first-class spec-inventory command (parallel to `openspec list` for changes). The filtered read `openspec show <id> --type spec --json --no-scenarios` is what generated guidance uses. Step 6 (Cross-artifact consistency) consumes the inventory for its "Capability-already-exists" check.

   If the inventory can't be built (older core, missing `--specs` flag, CLI failure), skip Step 6b and its check — backwards-compatible with v1.11.0 cores. Do not raise.

3. **Get planning context** (per-artifact instructions + change context)

   ```bash
   openspec instructions apply --change "<name>" --json
   openspec context --change "<name>" [--store "<id>"] --json
   ```

   Capture:
   - Per-artifact `instructions` for the queued artifact ids (loaded in Step 5 alongside concrete files).
   - Top-level `contextFiles` per artifact id, used to bound what we read.
   - Aggregated `tasks` and `progress` from the schema's `apply.tracks` configuration.

   Treat `state` and `instruction` as context, not a verdict. Step 8's routing recommendation is this skill's verdict; do not let apply's verdict leak in.

4. **Initialize audit report structure**

   Create a report skeleton with three dimensions matching `openspec-verify-change`:
   - **Completeness**: every required artifact exists and tracks a file (artifact presence and dependency readiness).
   - **Correctness**: every artifact conforms to its schema `template`, follows `instruction` guidance, and respects project `rules` from `openspec/config.yaml`.
   - **Coherence**: cross-artifact graph is consistent (entity coherence, capability-already-exists) and the change is implementation-ready (feasibility, scope, dependency availability).

   Each finding uses a severity tier in `{CRITICAL, WARNING, SUGGESTION}`:
   - **CRITICAL** — must fix before /osc-apply-change (missing required section, broken scenario format, content contradicts a hard rule, artifact absent against schema requirement).
   - **WARNING** — should fix (wrong header level, missing optional-but-recommended element, capability-already-exists collision when the wrong editor was chosen).
   - **SUGGESTION** — nice to fix (stylistic improvement, implementation-readiness note, routing hint).

   Apply the calibration rule borrowed from `openspec-verify-change`: **when uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL**. Implementation-readiness concerns (Step 8) are **never** CRITICAL.

   Mark checks the schema does not define, or artifacts the status reports as intentionally skipped (e.g., `skip_specs: true`), as **Not applicable**. Mark checks whose evidence is missing or unusable as **Not verified** with the reason. Distinguish **Not applicable** from **Not verified** the same way `openspec-verify-change` does. Never score a skipped check as passing.

5. **Verify Completeness — Per-artifact presence + readiness**

   For each queued artifact (status `done` with concrete files), run:

   ```bash
   openspec instructions "<artifact-id>" --change "<name>" [--store "<id>"] --json
   ```

   Read each concrete file in `existingOutputPaths`. Validate against:
   - **`template`** — structural conformance: required sections, header levels, required elements per the schema body. Missing required sections or breaks in scenario format are CRITICAL.
   - **`instruction`** — schema-defined prose guidance. Sets expectations; never copy its text into the artifact.

   For each artifact, also confirm that the file actually exists and is non-empty. Missing or empty `existingOutputPaths` is a CRITICAL finding for that artifact.

   Surface facts, do not copy. Categorize each finding as:
   - **Critical** — the artifact is invalid or absent against schema.
   - **Warning** — the artifact has a fixable defect (wrong header level, missing optional-but-recommended element).
   - **Suggestion** — stylistic or clarity improvement.

   Use the calibration rule already noted above. Implementation-readiness concerns never escalate to CRITICAL — that test belongs in Step 8.

   If the in-tree `spec-driven` schema's `template` field does not encode a format rule we used to hardcode (H4 scenario headers, `#### Scenario:` shape, etc.), file an upstream issue against the OpenSpec project rather than re-adding a local rubric.

6. **Verify Correctness + Coherence — Cross-artifact consistency**

   Build a graph from each artifact's `requires` array (v1.7.0+, captured in Step 2 from `openspec status --json`). When a `requires` value is missing, fall back to that artifact's `dependencies` + `unlocks` from `openspec instructions --json`. Skip edges whose source artifact has no `existingOutputPaths`.

   For each existing edge **A → B** (A depends on B, both with concrete files):
   - **Entity coherence** — entities introduced in B that A consumes must be present in A; constraints declared in B must be honored by A; no orphan references.
   - **Constraint propagation** — forward-only unlocks propagation: if A satisfies a constraint for B, do not duplicate or rewrite B's content.
   - **Severity** — coherence-level findings follow the same calibration rule.

   Do **not** hardcode any proposal↔specs↔design↔tasks pairs. The `requires` (or `dependencies` / `unlocks`) graph is fully schema-derived.

   If an artifact in the edge target has no concrete files (status `ready` or `blocked`), it belongs to Step 8 routing, not here.

   a. **Capability-already-exists (v1.13.0+, additive)**

   For each delta `ADDED Requirements` capability path, walk the spec inventory built in Step 2a. If the inventory already has a spec at the same path as the delta's `ADDED Requirements` block, emit a WARNING naming the existing spec id and pointing to `/osc-update-change <name>` — the right way to MODIFY / extend an existing capability is `update`, not a fresh `ADDED Requirements` block in a new change.

   Skip Step 6b when the spec inventory is unavailable (older core, CLI failure) — backwards-compatible with v1.11.0 cores. Mark that specific check as **Not verified** with the reason "spec inventory unavailable"; do not raise it as a finding.

7. **Verify Coherence — Implementation-readiness**

   Stay under SUGGESTION severity. Implementation readiness is human judgment: feasibility, scope, dependency availability, ambiguous requirements. Never CRITICAL. Findings here surface as the "Readiness" row of the summary scorecard.

8. **Generate audit report + Routing recommendation**

   **Summary Scorecard**:

   ```markdown
   ## Artifact Review: <change-name>

   **Schema**: <schemaName>
   **Artifacts audited**: <count>

   ### Summary
   | Dimension    | Status |
   |--------------|--------|
   | Completeness | <done / N ready / M blocked> |
   | Correctness  | <conforming / N warnings / N criticals> |
   | Coherence    | <consistent / N warnings / readiness notes> |
   ```

   Each Status cell reports the results of checks that ran and `Not verified (<reason>)` for every skipped check. If all checks in a dimension were skipped, start the cell with `Not verified`. Never score a skipped check as passing.

   **Issues by Priority**:

   1. **CRITICAL** (must fix before /osc-apply-change):
      - Required artifacts absent or empty
      - Required sections broken
      - Content contradicts a hard rule
      - Each with `file_path:line` and a concrete fix suggestion
   2. **WARNING** (should fix before /osc-apply-change):
      - Fixable defects, cross-artifact inconsistencies
      - Capability-already-exists collisions
      - Each with file:line and concrete fix
   3. **SUGGESTION** (nice to fix; user may proceed):
      - Stylistic improvements
      - Implementation-readiness notes
      - Orphan-reference cleanups

   **Routing recommendation** — Produce one routing line per finding category. Pick the single best editor for the aggregate finding set. The route shape depends on whether the audit was dispatched by the orchestrator (`OSX_AUTONOMOUS=1` — the engine handles `/osc-update-change` itself and re-enters PHASE0 to verify) or invoked ad-hoc by a user (`OSX_AUTONOMOUS` unset — the user must run the slash command themselves):

   | Finding pattern | In-orchestration route | Ad-hoc route |
   |---|---|---|
   | Findings on existing artifacts (single- or multi-artifact) | `auto-fix:osc-update-change` (engine handles) | `/osc-update-change <name>` (user runs) |
   | Missing artifact (referenced but not created) | `/osc-continue-change <name>` (halt + surface) | `/osc-continue-change <name>` |
   | All clean, pre-impl (PHASE0) | `advance-to PHASE1` (no slash needed) | `/osc-apply-change <name>` |
   | Intent-level change detected | `/osc-new-change <name>` (halt + surface) | `/osc-new-change <name>` (per "Update vs. Start Fresh" heuristic) |
   | Ambiguous finding needing thinking time | `/osc-explore <name>` (halt + surface) | `/osc-explore <name>` |

   Exactly one routing line, matching this matrix.

   The review skill never invokes the routed command itself. It only emits the route so the engine (in `OSX_AUTONOMOUS=1` context) or the user (ad-hoc) can act.

   **Final Assessment** (mirrors the wording of `openspec-verify-change`):
   - If CRITICAL issues: "X critical issue(s) found. Fix before /osc-apply-change." If any check was skipped, also name every skipped check and its reason.
   - If no CRITICAL issues, one or more warnings, and no checks were skipped: "No critical issues. Y warning(s) to consider. Ready for /osc-apply-change (with noted improvements)."
   - If only suggestions and no checks were skipped: "No critical issues or warnings. Z suggestion(s) to consider. Ready for /osc-apply-change (with noted improvements)."
   - If no issues and no checks were skipped: "All checks passed. Ready for /osc-apply-change."
   - If any check was skipped and there are no CRITICAL issues: do not claim readiness. Say "No critical issues found in the checks that ran. <check(s)> not verified: <reason>." Include the warning count when nonzero. Include the suggestion count when nonzero.

---

**Verification Heuristics**

- **Completeness**: Objective checklist — artifact status (`done`/`ready`/`blocked`), presence of `existingOutputPaths`, required sections per the schema `template`.
- **Correctness**: Use `instruction` prose from `openspec instructions` for expectations; use `rules` from `openspec/config.yaml` for project overrides. Surface as findings; never copy into artifact content.
- **Coherence**: Look for glaring cross-artifact drift, not stylistic micro-edits. Apply the calibration rule: **when uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL**.
- **Actionability**: Every finding carries a `file_path:line` reference (approximate line is fine) and a concrete fix suggestion. Implementation-readiness findings stay under SUGGESTION and route forward.

**Output Format**

Use clean markdown with:
- Schema, dimensions, and artifacts-audited in the header
- Summary scorecard table
- Grouped lists for CRITICAL / WARNING / SUGGESTION
- One routing line per finding category
- File references in format `path/to/file.md:42`
- Specific, actionable recommendations
- No vague suggestions like "consider reviewing"

---

**Guardrails**

- **Read-only.** Emits findings; never edits artifacts.
- **No code edits.** Surface issues, route the user to `/osc-apply-change`.
- **No new artifacts.** Missing artifacts are reported; their creation is `/osc-continue-change`'s job.
- **No hardcoded artifact names.** Schema is the source of truth.
- **Mode detection via `OSX_AUTONOMOUS` env var.** When set (orchestrator-dispatched PHASE0), the routing table's "in-orchestration" column applies — `auto-fix:osc-update-change` is emitted and the engine reconciles. When unset (ad-hoc `/osx-review <change>`), the "ad-hoc" column applies — slash-command forms are emitted for the user.
- **Calibration rule.** When uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL. Implementation-readiness never escalates above SUGGESTION.

---

## Failure modes

- **`openspec status` returns no change** — confirm the change name (and `--store` if applicable); offer `openspec list --json` to help the user.
- **`openspec instructions` errors mid-audit** — report which artifact failed and stop; do not invent instructions from the schema body.
- **`isComplete` is false and no `ready` artifact exists** — unusual state; surface as SUGGESTION and ask the user whether they want to archive or start a new change.
