---
description: Review test coverage for OpenSpec changes to ensure spec requirements have tests
---

Review test coverage for OpenSpec changes, ensuring spec requirements have corresponding tests.

**IMPORTANT**: This is an AI-guided analysis workflow. It does not use any CLI flags.

---

## Input

Optionally specify `[change-name]` after `/opsx:verify-tests`. If omitted, the AI will infer from context or prompt for selection.

---

## Steps

1. **Select the change**

   If name provided: use it. Otherwise:
   - Infer from conversation context
   - Auto-select if only one active change
   - If ambiguous: run `openspec list --json` and use **Ask** to prompt

   Announce: "Reviewing tests for change: <name>" and how to override.

2. **Get project context**

   Check for `openspec/config.yaml`:
   ```bash
   cat openspec/config.yaml
   ```
   
   Extract if present:
   - Testing framework conventions
   - Test directory patterns
   - Project-specific rules

   If no config: use sensible defaults based on project structure.

3. **Read specs for the change**

   Find and read spec files:
   ```bash
   ls openspec/changes/<name>/specs/
   ```
   
   Parse each spec for:
   - Requirement names (`### Requirement: ...`)
   - Scenario names (`#### Scenario: ...`)
   - Scenario content (GIVEN/WHEN/THEN/AND clauses)

4. **Discover tests**

   Use Glob tool with language-appropriate patterns:

   | Language | Patterns |
   |----------|----------|
   | Go | `**/*_test.go` |
   | Python | `**/test_*.py`, `**/*_test.py` |
   | JavaScript/TS | `**/*.test.{js,ts,jsx,tsx}` |
   | Java | `**/*Test.java` |
   | Ruby | `**/*_spec.rb` |

   Auto-detect language from project if not specified.

5. **Extract semantics from specs and tests**

   **From specs** (GIVEN/WHEN/THEN/AND):
   - Actions: verbs - submits, validates, returns
   - Entities: nouns - token, credentials, user
   - Conditions: valid, empty, null, invalid
   - Outcomes: SHALL have, must return, succeeds

   **From tests** (language-agnostic):
   - Test function names
   - Assertion patterns
   - Setup/teardown context

6. **Match scenarios to tests**

   Semantic similarity scoring:

   | Score | Description |
   |-------|-------------|
   | 100% | Exact name match |
   | 85-95% | Strong semantic match |
   | 60-84% | Partial match |
   | 30-59% | Weak keyword overlap |
   | 0% | No match |

7. **Analyze gaps**

   Identify:
   - **Untested scenarios**: No matching tests found
   - **Partially covered**: Happy path only, edge cases missing
   - **Orphaned tests**: Tests not matching any scenario

8. **Generate report**

   Ask user for confirmation using **Ask** before saving.

   Default output: `openspec/changes/<name>/test-compliance-report.md`

---

## Output

```
## Test Compliance Report: <change-name>

### Summary
- Total requirements: 12
- Requirements with tests: 9
- Requirements without tests: 3
- Overall coverage: 75%

### Coverage Details

| Requirement | Scenario | Coverage | Tests | Notes |
|-------------|----------|----------|-------|-------|
| User Auth | Valid credentials | Partial | TestLoadDocument... | No credential test |

### Gaps Analysis

| Gap Type | Count |
|----------|-------|
| Untested scenarios | 3 |
| Partially covered | 2 |
| Orphaned tests | 5 |

### Recommendations
- Add test `TestValidCredentials()` to cover credential validation
- Document test `TestLoadDocumentIntegration()` as integration utility
```

---

## Guardrails

- Gap-focused: Report what's missing, not just percentages
- Explain context: Provide "why no match" explanations
- Project-aware: Use config.yaml for patterns if available
- Actionable: Suggest specific test additions
- Reality check: Acknowledge unit tests != scenario tests
- Confidence transparency: Show scores and explain matching

---

See `.claude/skills/openspec-review-test-compliance/SKILL.md` for detailed semantic matching and gap analysis methodology.
