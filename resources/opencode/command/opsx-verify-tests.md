---
description: Review test coverage for OpenSpec changes to ensure spec requirements have tests
---

Review test coverage for OpenSpec changes, ensuring spec requirements have corresponding tests.

**Input**: Specify change to review with optional flags:

Required:
- `[change-name]`: Change to review (infer from context if omitted)

Optional:
- `--specs <path>`: Custom specs path to check
- `--test-dir <path>`: Explicit test directory
- `--test-pattern <glob>`: Test file pattern
- `--report <path>`: Custom report output path
- `--json`: JSON output format for CI integration
- `--dry-run`: Preview without writing

**Steps**

1. **Select change**
   - If name provided: use it
   - Otherwise: infer from conversation context
   - If only one active change: auto-select it
   - If multiple changes: run `openspec list --json` and use **AskUserQuestion** to let user select

   Always announce: "Reviewing tests for change: <name>" and how to override.

2. **Get project context** from `openspec/config.yaml`:
   ```bash
   cat openspec/config.yaml
   ```

   **Extract from context**:
   - Testing framework conventions
   - Test directory structure patterns
   - Project-specific validation rules

3. **Read specs** for the change:
   Parse OpenSpec specification files:
   ```markdown
   ## ADDED Requirements

   ### Requirement: User Authentication
   The system SHALL issue a JWT token upon successful login.

   #### Scenario: Valid credentials
   - **GIVEN** a user with valid credentials
   - **WHEN** user submits login form
   - **THEN** a JWT token is returned
   - **AND** user is redirected to dashboard
   ```

   **Extract**:
   - Requirement names (### Requirement: ...)
   - Scenario names (#### Scenario: ...)
   - Scenario content (GIVEN/WHEN/THEN/AND clauses)

4. **Discover tests** using project context:

   **Auto-discovery** (default): Framework-specific patterns from `config.yaml`, multi-language support.

   **Test file patterns** (by language):
   | Language | Default Patterns | Examples |
   |-----------|----------------|----------|
   | Go | `**/*_test.go` | `internal/core/loader_test.go`, `pkg/models_test.go` |
   | Python | `**/test_*.py` | `tests/test_auth.py`, `test_user.py` |
   | JavaScript/TypeScript | `**/*.test.{js,ts,jsx,tsx}` | `auth.test.js`, `user.test.ts` |
   | Java | `**/*Test.java` | `AuthTest.java`, `UserTest.java` |
   | Ruby | `**/*_spec.rb` | `auth_spec.rb`, `user_spec.rb` |

   **Override**: User can specify `--test-dir` or `--test-pattern`.

5. **Semantic extraction** from both specs and tests:

   **From specs** (GIVEN/WHEN/THEN/AND):
   - **Actions**: verbs - `submits`, `validates`, `returns`, `authenticates`
   - **Entities**: nouns - `token`, `credentials`, `user`, `session`, `form`
   - **Conditions**: - `valid`, `empty`, `null`, `invalid`, `missing`
   - **Outcomes**: - `SHALL have`, `must return`, `succeeds`, `errors`

   **From tests** (agnostic parsing): Match patterns like:
   - Go: `t.Errorf("expected non-nil, got %v", actual)`
   - Python: `assert response.status_code == 200`
   - JavaScript: `expect(result).toBe(expectedValue)`, `expect(error).toBeNull()`

6. **Semantic similarity scoring** to match spec scenarios to test implementations:

   **Confidence levels**:

   | Score | Description | Example Match |
   |--------|-------------|----------------|
   | 100% | Exact scenario name match | Scenario: "Valid credentials" ↔ Test: `TestValidCredentials` |
   | 85-95% | Strong semantic match | Scenario mentions "token" and test checks JWT behavior |
   | 60-84% | Partial semantic match | Both mention "user" but in different contexts |
   | 30-59% | Weak keyword overlap | Both mention "valid" but unrelated |
   | 0% | No match | No common keywords or behavior overlap |

7. **Gap analysis** to identify missing test coverage:

   **Requirement coverage**:
   ```markdown
   ## Uncovered Requirements

   | Requirement | Scenario | Why No Match |
   |-------------|-----------|---------------|
   | User Authentication | Valid credentials | No test covers credential validation |
   | Session Expiration | Idle timeout | Tests use fixed 30min timeout, not dynamic |
   ```

   **Test gaps**:
   ```markdown
   ## Gaps Analysis

   | Gap Type | Count | Examples |
   |-----------|-------|----------|
   | Untested scenarios | 3 | No tests for: valid credentials, invalid credentials, token expiry |
   | Partially covered | 2 | Tests cover happy path only |
   | Orphaned tests | 5 | Tests not matching any scenario |
   ```

8. **Generate report** (Markdown or JSON based on `--json` flag):

   **Markdown format**:
   ```markdown
   ## Test Compliance Report: <change-name>

   ### Summary
   - Total requirements: 12
   - Requirements with tests: 9
   - Requirements without tests: 3
   - Overall coverage: 75%

   ### Coverage Details

   | Requirement | Scenario | Coverage | Tests | Notes |
   |-------------|-----------|------------|--------|--------|
   | User Authentication | Valid credentials | Partial (60%) | TestLoadDocumentIntegration covers loading, no specific credential test |
   | Session Expiration | Idle timeout | None | No test for session expiry |

   ### Recommendations
   - Add test `TestValidCredentials()` to cover credential validation
   - Consider adding test for session expiry edge cases
   - Document test `TestLoadDocumentIntegration()` as integration utility in tests

   ### Gaps Analysis

   | Gap Type | Count |
   |-----------|-------|
   | Untested scenarios | 3 |
   | Partially covered | 2 |
   | Orphaned tests | 5 |
   ```

   **JSON output format**:
   ```json
   {
     "change": "add-dark-mode",
     "summary": {
       "totalRequirements": 12,
       "testedRequirements": 9,
       "untestedRequirements": 3,
       "overallCoverage": 75
     },
     "coverageDetails": [...],
     "recommendations": [...]
   }
   ```

9. **Write to file**:
   - Default: save to change directory
   - Custom: use `--report <path>` path
   - Preview if `--dry-run` specified
   - Verify file was written successfully

**Output**

Display summary and ask for confirmation before writing.

**Advanced Usage**

- **Dry run**: Preview report without writing: `openspec-review-test-compliance --dry-run`
- **Focus on specific requirements**: Check single requirement only: `openspec-review-test-compliance --change add-dark-mode --requirement "Session Expiration"`
- **Compare multiple changes**: Review changes in date range: `openspec-review-test-compliance --since 2024-01-01 --until 2024-03-31`

**Guardrails**

- Gap-focused reporting: Report what's missing, not coverage percentages
- Explain context: Provide "why no match" explanations, not just "no match"
- Project-aware: Use `openspec/config.yaml` for test patterns
- Actionable recommendations: Suggest specific test additions
- Handle reality: Acknowledge unit tests ≠ scenario tests
- Multiple evidence sources: Combine semantic + structural matching
- Confidence transparency: Show scores and explain matching logic

Load the corresponding skill for detailed implementation:

See `.opencode/skills/openspec-review-test-compliance/SKILL.md` for:
- Semantic similarity scoring algorithm details
- Multi-language test discovery patterns
- Gap analysis methodology
- Report generation specifications
