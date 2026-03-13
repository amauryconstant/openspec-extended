# Semantic Extraction and Analysis

How to extract key behaviors from OpenSpec scenarios and test code for semantic similarity matching.

## Spec Behavior Extraction

### Parsing GIVEN/WHEN/THEN/AND Format

```python
def parse_scenario(content, scenario_name):
    """Extract behavior components from a scenario"""
    # Find scenario header
    lines = content.split('\n')
    in_scenario = False
    given = []
    when_ = []
    then_ = []
    and_ = []
    
    for line in lines:
        line = line.strip()
        
        if f'#### Scenario: {scenario_name}' in line:
            in_scenario = True
        elif in_scenario:
            if line.startswith('- **GIVEN**'):
                given.append(line.replace('- **GIVEN**', '').strip())
            elif line.startswith('- **WHEN**'):
                when_.append(line.replace('- **WHEN**', '').strip())
            elif line.startswith('- **THEN**'):
                then_.append(line.replace('- **THEN**', '').strip())
            elif line.startswith('- **AND**'):
                and_.append(line.replace('- **AND**', '').strip())
    
    return {
        'given': given,
        'when': when_,
        'then': then_,
        'and': and_
    }
```

**Components extracted**:
- **Actions**: Verbs - `submits`, `validates`, `returns`, `authenticates`, `checks`
- **Entities**: Nouns - `token`, `credentials`, `user`, `form`, `session`, `field`
- **Conditions**: - `valid`, `empty`, `null`, `invalid`, `missing`, `specified`
- **Outcomes**: - `SHALL have`, `must return`, `succeeds`, `errors`, `is issued`, `exists`

### Example Parsing

**Input**:
```markdown
#### Scenario: Valid credentials
- **GIVEN** a user with valid credentials
- **WHEN** user submits login form
- **THEN** a JWT token is returned
- **AND** user is redirected to dashboard
```

**Extracted behavior**:
```python
{
    'given': ['a user with valid credentials'],
    'when': ['user submits login form'],
    'then': ['a JWT token is returned', 'user is redirected to dashboard'],
    'and': []
}

# Keyword extraction
actions = ['submits']
entities = ['user', 'form', 'login']
conditions = []
outcomes = ['returned', 'redirected']
```

## Test Behavior Extraction

### Language-Agnostic Patterns

```python
def extract_test_behavior(test_content):
    """Extract behaviors from test code across languages"""
    behaviors = []
    
    # Action verbs (common across languages)
    action_patterns = [
        r'(\b(?:submit|click|call|invoke|request|get|post|put|delete)\b)',
        r'(?:assertEquals|assertEqual|t\.Equal|expect\(\.toEqual|toStrictEqual)\b)'
    ]
    
    # Entity keywords
    entity_patterns = [
        r'\b(token|credential|user|session|form|button|input|api|endpoint|response|data|model)\b'
    ]
    
    # Outcome keywords
    outcome_patterns = [
        r'(?:error|success|succeed|fail|return|result|throw|raise)\b'
    ]
```

### Go Test Patterns

```go
// Action verbs
t.Run("TestName", func(t *testing.T) {
    t.Errorf("expected %v, got %v", want, got)
    t.Fatal("unexpected error: %v", err)
    t.Equal(want, got)
}

// Assertions
t.Error()      // Indicates expected failure
t.Fatal()      // Stops test with error
t.Equal()      // Equality check
t.EqualError() // Error equality
t.Nil()        // Nil check
t.True()/t.False() // Boolean checks

// Common patterns
if tt.expectError {
    t.Errorf("expected error")
}
if !tt.expectError && err != nil {
    t.Errorf("unexpected error: %v", err)
}
```

### Python Test Patterns

```python
# Action verbs
assert response.status_code == 200
assert token is not None
user.submit_form(data)

# Assertions
assert condition
assertRaises(ExpectedException)
assertEqual(actual, expected)
assertTrue(condition)
assertFalse(condition)

# Common patterns
with self.assertRaises(ValueError):
    function_call()

with patch.object:
    mock_function()
```

### JavaScript/TypeScript Test Patterns

```javascript
// Action verbs
expect(user.submitForm(data)).resolves
expect(api.fetchUser(id)).rejects.toThrow()

// Assertions
expect(actual).toBe(expected)
expect(actual).toEqual(expected)
expect(actual).toBeNull()
expect(actual).toBeDefined()
expect(actual).toBeTruthy()

// Common patterns
expect(func).toThrow(Error)
expect(result).not.toBeNull()
```

## Semantic Similarity Scoring

### Confidence Calculation

```python
def calculate_confidence(spec_behavior, test_behavior):
    """Calculate confidence score 0-100%"""
    score = 0
    
    # Action verb similarity (30% max)
    spec_actions = extract_verbs(spec_behavior)
    test_actions = extract_verbs(test_behavior)
    action_overlap = set(spec_actions) & set(test_actions)
    if action_overlap:
        # Weight by overlap ratio
        weight = len(action_overlap) / max(len(spec_actions), len(test_actions))
        score += weight * 30
    
    # Entity overlap (30% max)
    spec_entities = extract_entities(spec_behavior)
    test_entities = extract_entities(test_behavior)
    entity_overlap = set(spec_entities) & set(test_entities)
    if entity_overlap:
        weight = len(entity_overlap) / max(len(spec_entities), len(test_entities))
        score += weight * 30
    
    # Outcome alignment (40% max)
    if has_outcome_match(spec_behavior, test_behavior):
        score += 40
    
    return min(score, 100)
```

### Score Ranges

| Score | Meaning | Action |
|--------|---------|---------|
| 0-29% | No match or weak keyword overlap | Report as "No match" |
| 30-59% | Weak match (some keyword overlap, different context) | Include note explaining low confidence |
| 60-84% | Partial match (actions or entities match, outcomes differ) | "Partial coverage" label |
| 85-95% | Strong match (semantic alignment, minor differences) | High confidence match |
| 96-100% | Excellent match (direct scenario name or perfect semantic alignment) | Near-perfect correspondence |

### Outcome Matching

```python
def has_outcome_match(spec_behavior, test_behavior):
    """Check if test outcomes align with spec expectations"""
    spec_outcomes = set()
    for clause in spec_behavior['then'] + spec_behavior['and']:
        outcome = extract_outcome(clause)
        if outcome:
            spec_outcomes.add(outcome)
    
    test_outcomes = set(extract_outcomes(test_behavior))
    
    # Check for overlap
    overlap = spec_outcomes & test_outcomes
    
    # If any outcome matches
    return len(overlap) > 0
    
    # Negative outcomes
    negative_spec = any(out in spec_outcomes for out in ['error', 'fail', 'exception'])
    negative_test = any(out in test_outcomes for out in ['error', 'fail', 'exception'])
    
    if negative_spec and negative_test:
        return True
    
    return False
```

### Keyword Extraction Functions

```python
import re

def extract_verbs(text):
    """Extract action verbs from text"""
    verb_patterns = [
        r'\b(submit|click|call|invoke|request|get|post|put|delete|add|remove|create|update|modify|validate|check|assert|expect)\b',
        r'\b(\w+(?:ing|ed))\b'
    ]
    verbs = set()
    for pattern in verb_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get base verb without ing/ed
            verb = re.sub(r'(ing|ed)$', '', match)
            verbs.add(verb.lower())
    return verbs

def extract_entities(text):
    """Extract entity nouns from text"""
    # Common software entities
    entity_keywords = [
        'token', 'credential', 'user', 'session', 'form', 'button', 'input',
        'api', 'endpoint', 'response', 'data', 'model', 'field', 'property'
    ]
    entities = set()
    for keyword in entity_keywords:
        if keyword in text.lower():
            entities.add(keyword)
    return entities

def extract_outcomes(text):
    """Extract expected outcomes from text"""
    outcome_patterns = [
        r'(?:return|result|output)\s+(?:\w+)',
        r'(?:error|fail|exception|success|succeed)\w*',
        r'(?:assert|expect|check|verify)\w+'
    ]
    outcomes = set()
    for pattern in outcome_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get the key word
            outcome = re.sub(r'(?:return|result|output)\s+', '', match.lower())
            outcome = re.sub(r'(?:error|fail|exception|success|succeed)\w*', '', match.lower())
            outcomes.add(outcome)
    return outcomes
```

## Examples

### Example 1: Direct Match

**Spec scenario**:
```markdown
#### Scenario: Valid credentials
- **GIVEN** a user with valid credentials
- **WHEN** user submits login form
- **THEN** a JWT token is returned
- **AND** user is redirected to dashboard
```

**Test**:
```go
func TestValidCredentials(t *testing.T) {
    user := User{Email: "test@example.com", Password: "valid123"}
    token, err := Authenticate(user)
    
    assert.NoError(err)
    assert.Equal("jwt-token-xyz", token)
}
```

**Confidence calculation**:
- Spec actions: `submits`
- Test actions: `assert.NoError`, `assert.Equal`
- Outcome match: `assert.NoError` ↔ `token is returned`
- Score: 85% (strong match)

### Example 2: Partial Coverage

**Spec scenario**:
```markdown
#### Scenario: Session timeout

- **GIVEN** an authenticated session
- **WHEN** 30 minutes pass without activity
- **THEN** session is invalidated
- **AND** user must re-authenticate
```

**Test**:
```go
func TestSessionTimeout(t *testing.T) {
    session := CreateSession("user123")
    SetExpiry(session, 30*time.Minute)
    
    // Tests expiry, but not re-authentication requirement
    assert.True(IsExpired(session))
}
```

**Confidence calculation**:
- Spec actions: `invalidate`
- Test actions: (none - doesn't test invalidation directly)
- Outcome match: Partial - `IsExpired` covers `session is invalidated`
- Score: 60% (partial - missing re-authentication test)

**Result**: "Partial coverage" with note about missing scenario

### Example 3: No Match

**Spec scenario**:
```markdown
#### Scenario: Token refresh

- **GIVEN** a user with an expired token
- **WHEN** user makes authenticated request
- **THEN** system automatically refreshes token
- **AND** user session continues
```

**Test coverage**: None found

**Confidence calculation**:
- No common keywords
- No semantic overlap
- Score: 0% (no match)

**Result**: "No match" - gap reported

## Best Practices

1. **Multi-factor scoring**: Combine action, entity, and outcome matching
2. **Context awareness**: Consider test context (unit vs integration)
3. **Language flexibility**: Support multiple test frameworks
4. **Confidence transparency**: Explain scoring logic to users
5. **Threshold configuration**: Allow adjusting confidence thresholds
6. **Explain gaps**: Provide specific reasons for "no match" results
