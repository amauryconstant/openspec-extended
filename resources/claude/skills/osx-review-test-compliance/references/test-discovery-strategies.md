# Test Discovery Strategies

How to discover test files across different project structures and languages.

## Auto-Discovery Patterns

### Project-Agnostic

```bash
# Find test files by common patterns
find . -type f \( -name "*_test.go" -o -name "*_test.py" -o -name "*.test.ts" -o -name "*.test.js" \)
```

**Coverage**: Go, Python, JavaScript, TypeScript, Java, Ruby

### Language-Specific

| Language | Pattern | Example Match | Notes |
|-----------|----------|---------------|-------|
| Go | `**/*_test.go` | `internal/core_test.go`, `pkg/models_test.go` | Scattered in internal/ and pkg/ |
| Go | `**/test/` | `test/` directory | Standard Go test directory |
| Python | `**/test_*.py` | `tests/test_auth.py` | Common Python pattern |
| Python | `tests/test_*.py` | `tests/test_user.py` | Tests directory |
| JavaScript | `**/*.test.js` | `auth.test.js` | Node.js pattern |
| JavaScript | `**/*.spec.js` | `auth.spec.js` | Jest/Mocha pattern |
| TypeScript | `**/*.test.ts` | `auth.test.ts` | TS test files |
| TypeScript | `**/*.test.tsx` | `auth.test.tsx` | TSX test files |
| Java | `**/*Test.java` | `AuthTest.java` | JUnit pattern |
| Ruby | `**/*_spec.rb` | `auth_spec.rb` | RSpec pattern |

### Framework-Specific

| Framework | Pattern | Notes |
|----------|----------|-------|
| Jest | `**/*.test.{js,ts}` or `**/*.spec.{js,ts}` | JavaScript/TypeScript |
| Mocha | `**/*.test.js` | JavaScript |
| Pytest | `**/test_*.py` | Python |
| unittest | `**/test_*.py` | Python (alternative) |
| JUnit | `**/*Test.java` | Java |
| Go testing | `**/*_test.go` | Go built-in |

## User-Specified Paths

### Explicit Directory

```bash
# Specify test directory
openspec-review-test-compliance --test-dir ./tests
```

### Custom Pattern

```bash
# Use custom glob pattern
openspec-review-test-compliance --test-pattern "**/*_spec.go"
```

### Multiple Sources

```bash
# Search multiple directories
openspec-review-test-compliance --test-dir src/tests --test-dir lib/tests
```

## Using openspec config.yaml

### Get Testing Framework

```bash
# Read project context
cat openspec/config.yaml
```

### Extract Test Patterns

**Example config.yaml**:
```yaml
context: |
  Tech stack: Go 1.21, Cobra CLI
  Testing: Go testing package with table-driven tests in internal/ and pkg/
  Test location: Scattered tests (*_test.go) in code directories
  Test patterns: Table-driven with fixtures in test/fixtures/
```

**Parse framework**:
- Extract "Testing:" section
- Identify patterns from description
- Use as default discovery strategy

### Override Default Patterns

User can always override with `--test-dir` or `--test-pattern` flags.

## Language Detection

### From File Extensions

```python
def detect_language_from_extension(filename):
    """Detect programming language from file extension"""
    mapping = {
        '.go': 'go',
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.rb': 'ruby'
    }
    ext = os.path.splitext(filename)[1].lower()
    return mapping.get(ext, 'unknown')
```

### From Directory Structure

```python
def detect_project_language(project_root):
    """Detect project language from directory structure"""
    # Go
    if os.path.exists('go.mod') and os.path.exists('internal/'):
        return 'go'
    # Python
    if os.path.exists('setup.py') or os.path.exists('requirements.txt'):
        return 'python'
    # JavaScript/TypeScript
    if os.path.exists('package.json') and os.path.exists('node_modules/'):
        return 'javascript'
    return 'unknown'
```

## Exclusion Patterns

### Files to Exclude

```bash
# Exclude vendor directories
find . -type f -name "*_test.go" ! -path "*/vendor/*"

# Exclude node_modules
find . -type f -name "*.test.js" ! -path "*/node_modules/*"

# Exclude build artifacts
find . -type f -name "*_test.go" ! -path "*/bin/*" ! -path "*/dist/*"
```

### Exclude Flags

```bash
# Combined exclusions
find . -type f \( -name "*_test.go" \) \
    ! -path "*/vendor/*" \
    ! -path "*/node_modules/*" \
    ! -path "*/.git/*"
```

## Test Organization Analysis

### Monorepo Detection

```python
def is_monorepo(root_path):
    """Detect if project is a monorepo"""
    # Check for common monorepo patterns
    indicators = [
        'packages/',
        'apps/',
        'apps/',
        'services/',
        os.path.join(root_path, 'lerna.json')
    ]
    
    for indicator in indicators:
        if os.path.exists(os.path.join(root_path, indicator)):
            return True
    return False
```

### Workspace Detection

```bash
# Check for Go workspaces
grep "module " path " go.work

# Check for npm workspaces
grep "workspaces" package.json
```

**Monorepo strategy**: Scan each workspace/package directory independently

## Performance Considerations

### Large Codebases

**Optimization for 10,000+ test files**:
```bash
# Limit concurrent file reads
find . -type f -name "*_test.go" -print0 | head -100
```

### Caching

```python
def cache_test_discovery(project_root):
    """Cache test file list for faster subsequent runs"""
    cache_file = os.path.join(project_root, '.test_cache.json')
    
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)
    
    # Discover and cache
    test_files = discover_tests(project_root)
    with open(cache_file, 'w') as f:
        json.dump(test_files, f)
    
    return test_files
```

**Invalidate cache**:
```bash
# Clear cache when codebase changes
rm .test_cache.json
```

## Common Patterns

### Go Projects

**Table-driven tests**:
- Test fixtures in `test/fixtures/`
- Golden files in `test/golden/`
- Tests named `Test<Feature><Case>()` - **not** scenario names

**Integration tests**:
- May cover scenarios more directly
- Named like `TestLoadDocumentIntegration`

### Python Projects

**Pytest**:
- Test files in `tests/` directory
- Named `test_<feature>()` - not scenario names

**unittest**:
- Test files anywhere
- Named `Test<Feature>()` - not scenario names

### JavaScript/TypeScript

**Jest/Mocha**:
- Tests in `__tests__/` or `tests/` directories
- Named `describe('<feature>')` blocks - scenarios nested inside
- Named with `test` or `spec` suffix - not direct scenario matches

## Best Practices

1. **Start with defaults**: Use project context from `openspec/config.yaml`
2. **Be explicit**: Tell user which test patterns discovered
3. **Allow overrides**: `--test-dir` and `--test-pattern` for custom setups
4. **Handle monorepos**: Scan each package/workspace separately
5. **Cache wisely**: For large codebases, cache discovery results
6. **Exclude appropriately**: vendor/, node_modules/, build artifacts
7. **Multi-language support**: Handle mixed-language projects
