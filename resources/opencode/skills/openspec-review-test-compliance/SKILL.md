---
name: openspec-review-test-compliance
description: Review test coverage for OpenSpec changes, ensuring spec requirements have corresponding tests. Use when verifying implementation completeness, identifying test gaps, or understanding test/spec alignment.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec-extended
  version: "1.0"
---

# Test Compliance Review

Review test coverage for OpenSpec changes to ensure spec requirements have corresponding tests.

## When to Use

- Before archiving changes to verify completeness
- After implementation to identify gaps
- During code review to check spec/test alignment
- Periodically to maintain test coverage quality

## Quick Reference

| Option | Description | Example |
|---------|-------------|----------|
| `--change <name>` | Specific change to review | `openspec-review-test-compliance --change add-dark-mode` |
| `--specs <path>` | Custom specs path to check | `openspec-review-test-compliance --specs ./custom-specs/` |
| `--test-dir <path>` | Explicit test directory | `openspec-review-test-compliance --test-dir test/` |
| `--test-pattern <glob>` | Test file pattern | `openspec-review-test-compliance --test-pattern "**/*_test.go"` |
| `--report <path>` | Custom report output | `openspec-review-test-compliance --report coverage-report.md` |
| `--json` | JSON output format | `openspec-review-test-compliance --json` |

## Workflow

### 1. Get Project Context

Read `openspec/config.yaml` for project context:

```bash
# Get project context
cat openspec/config.yaml
```

**Extract from context**:
- Testing framework conventions
- Test directory structure patterns
- Project-specific validation rules

### 2. Read Specs

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

### 3. Discover Tests

Use project context to find test files:

**Auto-discovery** (default):
- Framework-specific patterns from `config.yaml`
- Multi-language support for mixed projects

**Test file patterns** (by language):

| Language | Default Patterns | Examples |
|-----------|----------------|----------|
| Go | `**/*_test.go` | `internal/core/loader_test.go`, `pkg/models_test.go` |
| Python | `**/test_*.py` | `tests/test_auth.py`, `test_user.py` |
| JavaScript/TypeScript | `**/*.test.{js,ts,jsx,tsx}` | `auth.test.js`, `user.test.ts` |
| Java | `**/*Test.java` | `AuthTest.java`, `UserTest.java` |
| Ruby | `**/*_spec.rb` | `auth_spec.rb`, `user_spec.rb` |

**Override**: User can specify `--test-dir` or `--test-pattern`

### 4. Semantic Extraction

Extract key behaviors from both specs and tests:

**From specs** (GIVEN/WHEN/THEN/AND):
- **Actions**: verbs - `submits`, `validates`, `returns`, `authenticates`
- **Entities**: nouns - `token`, `credentials`, `user`, `session`, `form`
- **Conditions**: - `valid`, `empty`, `null`, `invalid`, `missing`
- **Outcomes**: - `SHALL have`, `must return`, `succeeds`, `errors`

**From tests** (agnostic parsing):
```javascript
// Go
t.Errorf("expected non-nil, got %v", actual)

// Python
assert response.status_code == 200

// JavaScript
expect(result).toBe(expectedValue)
expect(error).toBeNull()
```

### 5. Semantic Similarity Scoring

Match spec scenarios to test implementations:

**Confidence levels**:

| Score | Description | Example Match |
|--------|-------------|----------------|
| 100% | Exact scenario name match | Scenario: "Valid credentials" ↔ Test: `TestValidCredentials` |
| 85-95% | Strong semantic match | Scenario mentions "token" and test checks JWT behavior |
| 60-84% | Partial semantic match | Both mention "user" but in different contexts |
| 30-59% | Weak keyword overlap | Both mention "valid" but unrelated |
| 0% | No match | No common keywords or behavior overlap |

**Scoring algorithm**:

```python
def calculate_similarity(spec_behavior, test_behavior):
    """Calculate semantic similarity score 0-100%"""
    score = 0
    
    # Action verb match (30% max)
    spec_actions = extract_verbs(spec_behavior)
    test_actions = extract_verbs(test_behavior)
    common_actions = set(spec_actions) & set(test_actions)
    if common_actions:
        score += min(30, (len(common_actions) / len(spec_actions)) * 30)
    
    # Entity overlap (30% max)
    spec_entities = extract_entities(spec_behavior)
    test_entities = extract_entities(test_behavior)
    common_entities = set(spec_entities) & set(test_entities)
    if common_entities:
        score += min(30, (len(common_entities) / len(spec_entities)) * 30)
    
    # Outcome alignment (40% max)
    if has_outcome_match(spec_behavior, test_behavior):
        score += 40
    
    return min(score, 100)
```

### 6. Gap Analysis

Identify missing test coverage:

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

**Key insight**: Gap-focused reporting, not coverage percentages

### 7. Generate Report

Default format (Markdown):

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

### 8. Save Report Options

```bash
# Save markdown to change directory
openspec-review-test-compliance --change add-dark-mode

# Save to custom location
openspec-review-test-compliance --change add-dark-mode --report /path/to/report.md

# JSON output for CI integration
openspec-review-test-compliance --change add-dark-mode --json
```

## Advanced Usage

### Dry Run

Preview report without writing:

```bash
openspec-review-test-compliance --dry-run
```

### Focus on Specific Requirements

```bash
# Check single requirement only
openspec-review-test-compliance --change add-dark-mode --requirement "Session Expiration"
```

### Compare Multiple Changes

```bash
# Review changes in date range
openspec-review-test-compliance --since 2024-01-01 --until 2024-03-31
```

## Troubleshooting

### No Tests Found

**Possible causes**:
- `--test-dir` path incorrect
- Test files don't match expected patterns
- Project is early in development

**Solutions**:
1. Use `--test-dir` to specify correct location
2. Check test file patterns in `openspec/config.yaml`
3. Verify tests exist at expected paths

### Low Coverage

**Common causes**:
- Tests are unit tests, specs expect integration tests
- Tests are utility functions, not feature tests
- Scenario granularity doesn't match test granularity

**Solutions**:
1. Clarify scope in specs vs test intent
2. Add integration tests for scenario-level coverage
3. Document utility/test functions separately
4. Use partial coverage category appropriately

### High False Positives

**Symptoms**:
- Test matches scenario but doesn't actually test it
- Confidence scores inflated by keyword overlap

**Solutions**:
1. Review actual test content for scenario correspondence
2. Lower confidence threshold for weaker matches
3. Add manual review for borderline cases
4. Refine semantic extraction heuristics

## Best Practices

1. **Gap-focused, not coverage**: Report what's missing, not percentages
2. **Explain context**: Provide "why no match" explanations, not just "no match"
3. **Project-aware**: Use `openspec/config.yaml` for test patterns
4. **Actionable recommendations**: Suggest specific test additions
5. **Handle reality**: Acknowledge unit tests ≠ scenario tests
6. **Multiple evidence sources**: Combine semantic + structural matching
7. **Confidence transparency**: Show scores and explain matching logic
