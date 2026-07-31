---
name: osx-review-test-compliance
description: Surface test coverage gaps and orphaned tests for OpenSpec changes. Use after implementation, between /opsx:apply and /opsx:archive. Pair with /osc-verify-change for full verification.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  audience: agents running post-implementation spec-to-test alignment review (PHASE1 end, ad-hoc /osx:verify-tests)
  workflow: post-implementation — after `osc-apply-change` and before `osc-verify-change`
---

Surface spec-to-test alignment to identify gaps for OpenSpec changes.

**IMPORTANT: This is a semantic analysis skill, not a CLI tool.** Read spec files, discover test files, analyse coverage by comparing scenarios to test implementations.

---

## Input

Optionally specify a change name. If omitted, the skill will infer from context or prompt for selection.

**Arguments**: `[change-name]`

**Examples**:
- `/osx:verify-tests add-auth` — analyse test coverage for "add-auth"
- "Check test coverage" — infer change from context

---

## When to Use

After implementation, between `/opsx:apply` and `/opsx:archive`.

---

## Steps

### 1. Select the change

If a name is provided, use it. Otherwise:
- Infer from conversation context.
- Auto-select if only one active change exists.
- If ambiguous, run `openspec list --json` to get available changes and prompt the user to select.

Always announce: "Analysing test compliance for: <name>"

### 2. Check change status

```bash
openspec status --change "<name>" --json
```

Parse the JSON to identify the change directory path.

### 3. Read spec files

Read all spec files from `openspec/changes/<name>/specs/`:

```bash
openspec/changes/<name>/specs/**/*.md
```

For each spec file, extract:
- **Requirement names**: Lines matching `### Requirement: <name>`
- **Scenario names**: Lines matching `#### Scenario: <name>`
- **Scenario content**: GIVEN/WHEN/THEN/AND clauses following each scenario

### 4. Discover test files

Use Glob to find test files. Start with common patterns:

| Language | Pattern |
|----------|---------|
| Go | `**/*_test.go` |
| Python | `**/test_*.py`, `**/*_test.py` |
| JavaScript/TypeScript | `**/*.test.{js,ts,jsx,tsx}`, `**/*.spec.{js,ts,jsx,tsx}` |
| Java | `**/*Test.java` |
| Ruby | `**/*_spec.rb` |

If `openspec/config.yaml` exists, check the `context` field for project-specific test patterns.

### 5. Extract test behaviours

For each test file, read its contents and extract:
- **Test function names**: e.g., `TestLoginFlow`, `test_user_authentication`
- **Assertion patterns**: Look for `assert`, `expect`, `should`, `t.Error`
- **Test descriptions**: Describe blocks, docstrings, comments

Identify what behaviour each test validates based on its name and assertions.

### 6. Match scenarios to tests

For each spec scenario, find matching tests by comparing:

**Semantic similarity factors**:
- **Action alignment** — does the test name/description contain verbs from the scenario? (e.g., "submits", "validates", "returns")
- **Entity overlap** — do both reference the same domain objects? (e.g., "token", "credentials", "user")
- **Outcome correspondence** — does the test verify the expected outcome?

**Confidence scoring** — see `references/scoring-rubric.md` for tier definitions and worked examples.

### 7. Generate gap analysis

Compile findings into two sections: **Coverage by requirement** (each scenario's match status and confidence, with notes for missing or partial coverage) and **Orphaned tests** (tests that don't match any scenario — may indicate missing specs or utility tests).

### 8. Output compliance report

Present the analysis with actionable recommendations.

---

## Output

**Full Compliance Report**:

```markdown
## Test Compliance Report: <change-name>

### Summary
- Total requirements: 5
- Total scenarios: 12
- Scenarios with tests: 9
- Scenarios without tests: 3
- Orphaned tests: 2

### Coverage by Requirement

#### Requirement: User Authentication
| Scenario | Coverage | Matching Tests | Notes |
|----------|----------|----------------|-------|
| Valid credentials | High (85%) | `TestLoginFlow` | Happy path covered |
| Invalid credentials | None | — | Missing: add negative test |
| Token expiry | Partial (60%) | `TestTokenRefresh` | Missing: expired token handling |

#### Requirement: Session Management
| Scenario | Coverage | Matching Tests | Notes |
|----------|----------|----------------|-------|
| Session timeout | None | — | No test for timeout |
| Concurrent sessions | High (90%) | `TestConcurrentLogin` | Covered |

### Gaps Analysis

| Gap Type | Count | Examples |
|----------|-------|----------|
| Untested scenarios | 3 | "Invalid credentials", "Token expiry", "Session timeout" |
| Partially covered | 2 | Token refresh missing expired token case |
| Orphaned tests | 2 | `TestHelperFunction`, `TestLoadFixture` |

### Recommendations
1. Add test `TestInvalidCredentials()` to cover negative auth case
2. Add test `TestExpiredToken()` to cover token expiry scenario
3. Add test `TestSessionTimeout()` to cover session timeout
4. Document orphaned tests `TestHelperFunction` as utility functions

### Next Steps
- Address gaps: Add recommended tests
- Re-run compliance: `/osx:verify-tests <name>`
- Verify implementation: `/osc-verify <name>`
```

**Quick Summary** (for clean changes):

```markdown
## Test Compliance: <change-name>

✅ **All scenarios covered**

- 5 requirements, 12 scenarios
- All scenarios have corresponding tests
- 0 coverage gaps

Ready to verify: `/osc-verify <name>`
```

---

## Guardrails

- Read actual test files — don't assume coverage from names alone.
- Report gaps, not just percentages — focus on what's missing.
- Acknowledge utility tests that don't map to scenarios (orphaned tests).
- Don't require 100% coverage — focus on critical path scenarios.
- Confidence scores are subjective — explain reasoning per the scoring rubric.
- If no tests exist, report that clearly rather than failing.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/osx-review-test-compliance/SKILL.md
Regenerate: `mise run sync:mirrors`
-->
