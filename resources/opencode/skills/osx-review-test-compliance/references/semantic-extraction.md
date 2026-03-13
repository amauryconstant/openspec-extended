# Semantic Extraction and Analysis

How to extract key behaviors from OpenSpec scenarios and test code for semantic similarity matching.

## Spec Behavior Extraction

### Parsing GIVEN/WHEN/THEN/AND Format

Extract behavior components from scenario content:

**Components to extract**:
- **Actions**: Verbs - `submits`, `validates`, `returns`, `authenticates`, `checks`
- **Entities**: Nouns - `token`, `credentials`, `user`, `form`, `session`, `field`
- **Conditions**: Adjectives - `valid`, `empty`, `null`, `invalid`, `missing`, `specified`
- **Outcomes**: Results - `SHALL have`, `must return`, `succeeds`, `errors`, `is issued`, `exists`

### Example Extraction

**Input**:
```markdown
#### Scenario: Valid credentials
- **GIVEN** a user with valid credentials
- **WHEN** user submits login form
- **THEN** a JWT token is returned
- **AND** user is redirected to dashboard
```

**Extracted behavior**:
- Actions: `submits`
- Entities: `user`, `form`, `login`
- Conditions: `valid`
- Outcomes: `returned`, `redirected`

## Test Behavior Extraction

### Language-Agnostic Patterns

Look for common patterns across test frameworks:

**Assertion patterns**:
- `assert`, `expect`, `should`, `must`
- `Equal`, `NotEqual`, `True`, `False`, `Nil`, `NotNull`
- `toThrow`, `toThrowError`, `raises`

**Test naming conventions**:
- Function names: `TestValidCredentials`, `test_valid_credentials`
- Describe blocks: `describe('valid credentials', ...)`
- Test annotations: `@Test`, `func TestX(t *testing.T)`

**Action indicators**:
- HTTP verbs: `GET`, `POST`, `PUT`, `DELETE`
- User actions: `submit`, `click`, `enter`, `select`
- System actions: `create`, `update`, `delete`, `fetch`

## Similarity Matching Approach

### Matching Strategy

1. **Name similarity**: Does test name match scenario name?
2. **Action alignment**: Do spec and test describe the same action?
3. **Entity overlap**: Do they reference the same domain objects?
4. **Outcome correspondence**: Does the test verify the spec's expected outcome?

### Confidence Levels

| Score | Description | Action |
|--------|-------------|--------|
| 85-100% | Strong match | High confidence correspondence |
| 60-84% | Partial match | Some alignment, gaps noted |
| 30-59% | Weak match | Keyword overlap, different context |
| 0-29% | No match | Report as gap |

### Matching Examples

**Strong match (85-100%)**:
- Spec: "Valid credentials" scenario
- Test: `TestValidCredentials` or `test_valid_credentials`
- Same actions, entities, and outcomes verified

**Partial match (60-84%)**:
- Spec: "Session timeout" scenario
- Test: Tests session expiry but not re-authentication
- Some scenarios covered, others missing

**Weak match (30-59%)**:
- Spec: "Token refresh" scenario
- Test: Tests authentication but not specifically refresh
- Related but different focus

**No match (0-29%)**:
- Spec: "Password reset" scenario
- Test: No test covering password functionality
- Gap to report
