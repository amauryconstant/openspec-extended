---
name: openspec-review-test-compliance
description: Analyze spec-to-test alignment for OpenSpec changes. Use after implementation to identify test gaps, verify coverage of spec requirements, or understand test/spec alignment. Performs semantic matching between spec scenarios and test implementations.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec-extended
  version: "0.2.0"
---

Analyze spec-to-test alignment to identify missing test coverage for OpenSpec changes.

**IMPORTANT: This is a semantic analysis skill, not a CLI tool.** You will read spec files, discover test files, and analyze coverage by comparing scenarios to test implementations.

---

## Input

Optionally specify a change name. If omitted, the skill will infer from context or prompt for selection.

**Arguments**: `[change-name]`

**Examples**:
- `/opsx:test-compliance add-auth` - Analyze test coverage for "add-auth"
- "Check test coverage" - Infer change from context

---

## When to Use

| Timing | Use Case |
|--------|----------|
| After `apply-change` | Deep test coverage analysis when implementation is done |
| Before `verify-change` | Get detailed test gaps before general verification |
| During code review | Check spec/test alignment for PRs |
| Periodic maintenance | Audit test coverage quality over time |

---

## Steps

1. **Select the change**

    If a name is provided, use it. Otherwise:
    - Infer from conversation context
    - Auto-select if only one active change exists
    - If ambiguous: run `openspec list --json` to get available changes and prompt the user to select

   Always announce: "Analyzing test compliance for: <name>"

2. **Check change status**

   ```bash
   openspec status --change "<name>" --json
   ```

   Parse the JSON to identify the change directory path.

3. **Read spec files**

    Read all spec files from `openspec/changes/<name>/specs/`:

    Use the Glob tool to find spec files:
    ```bash
    openspec/changes/<name>/specs/**/*.md
    ```

   For each spec file, extract:
   - **Requirement names**: Lines matching `### Requirement: <name>`
   - **Scenario names**: Lines matching `#### Scenario: <name>`
   - **Scenario content**: GIVEN/WHEN/THEN/AND clauses following each scenario

4. **Discover test files**

   Use the Glob tool to find test files. Start with common patterns:

   | Language | Pattern |
   |----------|---------|
   | Go | `**/*_test.go` |
   | Python | `**/test_*.py`, `**/*_test.py` |
   | JavaScript/TypeScript | `**/*.test.{js,ts,jsx,tsx}`, `**/*.spec.{js,ts,jsx,tsx}` |
   | Java | `**/*Test.java` |
   | Ruby | `**/*_spec.rb` |

    If `openspec/config.yaml` exists, check the `context` field for project-specific test patterns.

5. **Extract test behaviors**

   For each test file, read its contents and extract:
   - **Test function names**: e.g., `TestLoginFlow`, `test_user_authentication`
   - **Assertion patterns**: Look for `assert`, `expect`, `should`, `t.Error`
   - **Test descriptions**: Describe blocks, docstrings, comments

   Identify what behavior each test validates based on its name and assertions.

6. **Match scenarios to tests**

   For each spec scenario, find matching tests by comparing:

   **Semantic similarity factors**:
   - **Action alignment**: Does the test name/description contain verbs from the scenario? (e.g., "submits", "validates", "returns")
   - **Entity overlap**: Do both reference the same domain objects? (e.g., "token", "credentials", "user")
   - **Outcome correspondence**: Does the test verify the expected outcome?

   **Confidence levels**:

   | Score | Match Quality | Interpretation |
   |--------|---------------|----------------|
   | High (80%+) | Strong match | Scenario clearly covered |
   | Medium (50-79%) | Partial match | Some coverage, gaps noted |
   | Low (<50%) | Weak/No match | Coverage gap |

7. **Generate gap analysis**

   Compile findings:

   **Coverage by requirement**:
   - For each requirement, list its scenarios
   - For each scenario, show match status and confidence
   - Note what's missing or partially covered

   **Orphaned tests**:
   - Tests that don't match any scenario
   - May indicate missing specs or utility tests

8. **Output compliance report**

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
- Re-run compliance: `/opsx:test-compliance <name>`
- Verify implementation: `/opsx:verify <name>`
```

**Quick Summary** (for clean changes):

```markdown
## Test Compliance: <change-name>

✅ **All scenarios covered**

- 5 requirements, 12 scenarios
- All scenarios have corresponding tests
- 0 coverage gaps

Ready to verify: `/opsx:verify <name>`
```

---

## Matching Heuristics

Use these patterns when analyzing test-to-spec correspondence:

**Strong indicators of coverage**:
- Test name contains scenario name keywords
- Test asserts the exact outcome specified in THEN clause
- Test sets up the exact GIVEN conditions

**Partial coverage indicators**:
- Test covers happy path but not error cases
- Test validates subset of scenario conditions
- Test has similar name but different scope

**No coverage indicators**:
- No test names match scenario keywords
- No assertions for expected outcomes
- Scenario describes feature not in test suite

---

## Guardrails

- Read actual test files - don't assume coverage from names alone
- Report gaps, not just percentages - focus on what's missing
- Acknowledge utility tests that don't map to scenarios (orphaned tests)
- Consider partial coverage valid for complex scenarios
- Don't require 100% coverage - focus on critical path scenarios
- Confidence scores are subjective - explain reasoning
- If no tests exist, report that clearly rather than failing
