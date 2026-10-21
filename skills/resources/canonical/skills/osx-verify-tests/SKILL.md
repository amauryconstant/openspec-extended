---
name: osx-verify-tests
description: Verify that implementation tests cover every scenario in an OpenSpec change. Use after implementation, between /osc-apply-change and /osc-verify-change. Mirrors the three-dimension report (Completeness / Correctness / Coherence) and the CRITICAL / WARNING / SUGGESTION severity scale of openspec-verify-change. Trigger words: "verify tests", "osx verify tests", "opsx verify tests", "test compliance".
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  author: openspec-extended
  version: "0.4.0"
---

# osx-verify-tests

Surface spec-to-test alignment for an OpenSpec change. Complements `openspec-verify-change` by going one layer deeper — instead of asking "does the implementation touch this scenario?", it asks "does a test exercise this scenario?". The report shape matches `openspec-verify-change` (three dimensions, CRITICAL / WARNING / SUGGESTION tiers, Not applicable / Not verified semantics) so the two skills compose into a single review.

> **IMPORTANT**: This is a semantic analysis skill, not a CLI tool. Read spec files, discover test files, analyse coverage by comparing scenarios to test implementations.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `schemas`, `view`). Once selected, treat `--store <id>` as sticky for the rest of the workflow. Without a store, commands act on the nearest local `openspec/` root.

**Project check:** Before the first step that reads changes or artifacts, confirm the project has a root by running `openspec list --json` (with `--store <id>` when a store is selected). A root object means the project is set up. `"root": null` means it is not — stop and ask the user to either run `openspec init`, target a registered store with `--store <id>`, or continue without OpenSpec. Never create the root as a side effect.

**Input**: Optionally specify a change name as `$1` (e.g., `/osx-verify-tests add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. PHASE1 end-of-iteration dispatches the change name automatically. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

---

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and ask the user to select one

   When prompting, show all active changes returned by the list, including changes with `status: "no-tasks"`. Include the schema used for each change if available. Mark changes with incomplete tasks as "(In Progress)".

   Always announce: "Using test-compliance for: <name>" and how to override (e.g., `/osx-verify-tests <other>`).

2. **Check status to understand the schema**

   ```bash
   openspec status --change "<name>" --json
   ```

   Parse the JSON to understand:
   - `schemaName`: the workflow being used (e.g., "spec-driven")
   - `planningHome`, `changeRoot`, `artifactPaths`, `actionContext`: path and scope context
   - Which artifacts exist for this change and which spec artifacts contain ADDED / MODIFIED requirements

3. **Get planning context and load artifacts**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   This returns the change directory, `contextFiles` (artifact ID -> array of concrete file paths), `taskTrackingConfigured`, and top-level `tasks` and `progress` aggregated from every concrete file matched by the schema's `apply.tracks` configuration that could be read. Read the spec artifacts from `contextFiles` and extract:
   - **Requirement names**: Lines matching `### Requirement: <name>` under `## ADDED Requirements` or `## MODIFIED Requirements`. Note which delta section each requirement sits under.
   - **Scenario names**: Lines matching `#### Scenario: <name>`
   - **Scenario content**: GIVEN / WHEN / THEN / AND clauses

   For REMOVED / RENAMED requirements there is no positive test-coverage ask; mark them **Not applicable** under the test-coverage dimensions. Do not invent test targets for them.

   If the spec artifact's `contextFiles.<id>` is absent or empty, mark **Requirement Coverage**, **Scenario Coverage**, and **Implementation Match** as **Not verified** with the reason; continue checks supported by other evidence.

   Treat apply `state` and `instruction` as context, not a compliance verdict.

4. **Initialize compliance report structure**

   Create a report structure with three dimensions mirroring `openspec-verify-change`:
   - **Completeness**: Track test-inventory and requirement coverage.
   - **Correctness**: Track scenario coverage and implementation match.
   - **Coherence**: Track project-pattern consistency and orphan classification.

   Each finding uses a severity tier in `{CRITICAL, WARNING, SUGGESTION}`:
   - **CRITICAL** — must fix before /osc-verify-change (missing tests for required scenarios, missing tests for ADDED / MODIFIED requirements).
   - **WARNING** — should fix (partial coverage, weak semantic match).
   - **SUGGESTION** — nice to fix (orphaned tests, project-style deviations).

   Apply the calibration rule borrowed from `openspec-verify-change`: **when uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL**. Read actual test files before scoring — do not infer coverage from names alone.

   Mark checks the schema does not define (e.g., no spec artifact, no scenarios, or a change with no testable delta) as **Not applicable**. Mark checks whose evidence is missing or unusable as **Not verified** with the reason. Distinguish **Not applicable** (no test expected) from **Not verified** (test expected, evidence missing). Never score a skipped check as passing.

5. **Verify Completeness**

   **Test Inventory**:
   - Skip on changes where no spec artifacts exist (no delta specs and not `skip_specs: true`); mark **Test Inventory** as **Not applicable**. Otherwise report the count of test files discovered.
   - Start with language-conventional globs:

     | Language | Pattern |
     | --- | --- |
     | Go | `**/*_test.go` |
     | Python | `**/test_*.py`, `**/*_test.py` |
     | JavaScript / TypeScript | `**/*.test.{js,ts,jsx,tsx}`, `**/*.spec.{js,ts,jsx,tsx}` |
     | Java | `**/*Test.java` |
     | Ruby | `**/*_spec.rb` |

   - If `openspec/config.yaml` is present, read `context` for project-specific globs and overrides (Rust, Kotlin, Swift). Honour them before the language defaults.
   - When the change has testable scenarios and no tests were discovered: emit `CRITICAL: No test files discovered for change "<name>". Add at least one test before /osc-verify-change.` and stop the per-test checks with the reason "no test files".

   **Requirement Coverage**:
   - For each ADDED or MODIFIED requirement (RENAMED is checked under Coherence / orphan-classification instead), search the discovered tests for direct references. Matches in `openspec/` artifacts or docs alone are not evidence.
   - For each ADDED or MODIFIED requirement with no matching test:
     - Add CRITICAL: "Requirement has no test: <requirement name>".
     - Recommendation: "Add at least one test exercising <requirement name>: <description>."

6. **Verify Correctness**

   **Scenario Coverage** (the meat of this skill):
   - For each scenario under an ADDED or MODIFIED requirement (extract the actions, entities, conditions, and outcomes per the GIVEN / WHEN / THEN / AND clauses):
     - **Action alignment** — does the test name or description contain the scenario's verbs (e.g., "submits", "validates", "returns", "expires", "refreshes")?
     - **Entity overlap** — do both reference the same domain objects (e.g., "token", "credentials", "user", "session")?
     - **Outcome correspondence** — does the test assert the scenario's expected outcome (the `THEN` clause)?
   - Score the match:

     | Confidence | Tier | Verdict |
     | --- | --- | --- |
     | 85–100 | Strong | All three factors align; behaviour is exercised directly. |
     | 60–84 | Partial | Action + entity align; some gaps (missing assertions, happy-path-only). |
     | 30–59 | Weak | Keyword overlap; different context. |
     | 0–29 | None | No semantic overlap. |

   - Map tiers to severity:

     | Confidence tier | Severity emitted |
     | --- | --- |
     | None (0–29) | **CRITICAL** |
     | Weak (30–59) | **WARNING** (when no Partial-match test exists) |
     | Partial (60–84) | **WARNING** |
     | Strong (85–100) | (no finding) |

   - For each scenario not covered by a Strong / Partial match:
     - CRITICAL finding: "Scenario not covered: <scenario name>". Recommendation: "Add test for scenario: <description>." (Weak / None tiers.)
     - WARNING finding: "Scenario weakly covered: <scenario name>". Recommendation: "Tighten assertions to cover <THEN clause>." (Partial tier.)
   - Skip scenarios under REMOVED requirements: that behaviour is meant to be gone. Orphans belong under Coherence.

   **Implementation Match**:
   - For each scenario covered by a test, read the test body and check that the assertions actually exercise the scenario's `SHALL` / `THEN` clauses. A test whose name matches but whose assertions cover only the happy path yields a WARNING recommending the addition of the missing assertions.

7. **Verify Coherence**

   **Pattern Consistency**:
   - Compare discovered tests against project conventions (test file naming, `tests/` vs `__tests__` vs co-located, table-driven vs scenario-driven). Significant deviations get a SUGGESTION pointing to an existing file that follows the convention.

   **Orphaned Tests**:
   - Tests that exist in the discovered corpus but do not map to any scenario in the change's spec artifacts:
     - Add SUGGESTION: "Orphaned test: <name>". Recommendation: "Either add a scenario for this test or document it as a utility / helper."
   - Orphaned tests are not gaps by themselves; utility tests are expected. They become SUGGESTIONs only when the user's `openspec/config.yaml` `context` does not list them as utilities.

   **Capability-already-exists (v1.13.0+, additive)**:
   - When `openspec list --specs` is available, walk the spec inventory for each ADDED requirement's capability path. If the inventory already has a spec at that path, emit WARNING: "Capability already exists: <path>" with recommendation to use `/osc-update-change <name>` instead of adding new ADDED requirements. Skip on older cores.

8. **Generate compliance report**

   **Summary Scorecard**:

   ```markdown
   ## Test Compliance Report: <change-name>

   ### Summary
   | Dimension    | Status |
   |--------------|--------|
   | Completeness | X/Y requirements have tests |
   | Correctness  | M/N scenarios have strong matches |
   | Coherence    | Z orphans / pattern suggestions |
   ```

   Each Status cell reports the results of checks that ran and `Not verified (<reason>)` for every skipped check. If all checks in a dimension were skipped, start the cell with `Not verified`. Never score a skipped check as passing. Count only ADDED and MODIFIED requirements; REMOVED and RENAMED requirements are reported separately (for example, "1 removal confirmed (Not applicable under test coverage)", "1 rename verified").

   **Issues by Priority**:

   1. **CRITICAL** (must fix before /osc-verify-change):
      - No test files for testable changes
      - ADDED / MODIFIED requirement with no test
      - Scenarios with None-tier confidence
      - Each with specific, actionable recommendation with `file:line` references where applicable

   2. **WARNING** (should fix):
      - Partial / Weak scenario coverage
      - Implementation match mismatches
      - Capability-already-exists collision
      - Each with specific recommendation

   3. **SUGGESTION** (nice to fix):
      - Pattern deviations
      - Orphaned tests
      - Each with specific recommendation

   **Final Assessment** (mirrors the wording of `openspec-verify-change`):
   - If CRITICAL issues: "X critical issue(s) found. Fix before /osc-verify-change." If any check was skipped, also name every skipped check and its reason.
   - If no CRITICAL issues, one or more warnings, and no checks were skipped: "No critical issues. Y warning(s) to consider. Ready for /osc-verify-change (with noted improvements)."
   - If only suggestions and no checks were skipped: "No critical issues or warnings. Z suggestion(s) to consider. Ready for /osc-verify-change (with noted improvements)."
   - If no issues and no checks were skipped: "All checks passed. Ready for /osc-verify-change."
   - If any check was skipped and there are no CRITICAL issues: do not claim readiness. Say "No critical issues found in the checks that ran. <check(s)> not verified: <reason>." Include the warning count when nonzero.
   - Include the suggestion count when nonzero in every final assessment.

---

**Verification Heuristics**

- **Completeness**: Objective checklist — file existence, requirement -> test presence.
- **Correctness**: Use keyword search, file path analysis, and reasonable inference; do not require perfect certainty. When uncertain about a scenario match, downgrade the severity (CRITICAL → WARNING → SUGGESTION) rather than upgrade it.
- **Coherence**: Look for obvious pattern deviations; do not nitpick style.
- **Actionability**: Every finding has a specific recommendation with `file:line` references where applicable. Never "consider reviewing".
- **Confidence calibration**: A Strong tier match (85–100) is a high bar — it requires action alignment, entity overlap, AND outcome correspondence. A name-only match is Partial (60–84) at best.

**Output Format**

Use clean markdown with:
- Table for summary scorecard
- Grouped lists for issues (CRITICAL / WARNING / SUGGESTION)
- Code references in format `file.test:123` (test-file path with line number where possible)
- Specific, actionable recommendations
- No vague suggestions like "consider reviewing"

---

**Guardrails**

- Read actual test files — don't assume coverage from names alone.
- Report gaps, not just percentages — focus on what's missing.
- Acknowledge utility tests that don't map to scenarios (orphaned tests) without escalating them above SUGGESTION.
- Don't require 100% coverage — focus on critical-path scenarios. A test covering one scenario is sufficient for that scenario unless the scenario has multiple distinct `THEN` clauses.
- Confidence scores are subjective — explain reasoning per the tier table above; **when uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL** (calibration rule from `openspec-verify-change`).
- If no tests exist for a change, report that clearly rather than failing silently.
- Use **Not applicable** when a check has no expected target (no spec, no scenarios, REMOVED requirements). Use **Not verified** when a check has an expected target but evidence is missing. Never count Not-verified checks as passing.

---

## Tips

- Run on a single change at a time — multi-change compliance analysis bloats the report and dilutes per-change findings.
- For languages not in the discovery table (Rust, Kotlin, Swift), override via `openspec/config.yaml` `context` rather than inline regex hunting.
- Re-run after fixes to confirm previously-missing scenarios now have tests; the report does not store incremental state.
- This skill is a complement to `openspec-verify-change` (/osc-verify-change) — run it as a stepping stone *before* the upstream verify when you want deeper test-coverage signal. The two reports share severity vocabulary so a single triage works.
- PHASE1 dispatches this skill at the end of each iteration; for ad-hoc runs use `/osx-verify-tests <change-name>`.
