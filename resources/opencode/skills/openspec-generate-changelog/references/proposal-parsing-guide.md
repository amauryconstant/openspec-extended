# Proposal Parsing Guide

How to extract key information from OpenSpec proposal.md files for changelog generation.

## OpenSpec Proposal Format

### Standard Structure

```markdown
# Proposal: <Name>

## Summary
<brief description>

## Proposed Change
<detailed description>
```

## Sections to Extract

### ## Summary

**Purpose**: High-level overview of the change

**Content**: 1-3 sentences describing what this change accomplishes

**Use in changelog**: As the main entry description

Example from `2026-01-09-initialize-project-structure/proposal.md`:

```markdown
## Summary

Establishes Go project structure, tooling, and foundational configuration for germinator CLI tool.
```

**Changelog entry**: `- Establishes Go project structure, tooling, and foundational configuration for germinator CLI tool. (initialize-project-structure)`

### ## Proposed Change

**Purpose**: Detailed description of what will change

**Content**: Bullet points or paragraphs describing the changes

**Use in changelog**: For categorization and context

Example from `2026-01-09-initialize-project-structure/proposal.md`:

```markdown
## Proposed Change

Create a complete Go project structure following Standard Go Project Layout conventions...
Initialize Go modules with appropriate module path...
Set up Cobra CLI framework...
Create minimal placeholder files...
```

**Categorization analysis**:
- "Create" → Added category
- "Establishes" → Added category
- "Initialize" → Added category
- Multiple bullet points suggest multiple changes → categorize separately

## Alternative Sections

If proposal.md deviates from standard format, check these sections:

| Section | Use for Changelog | Notes |
|----------|---------------------|-------|
| ## What Changes | Categorization (alternative to Proposed Change) | Same as Proposed Change |
| ## Intent | Summary (alternative to Summary) | Use for main description |
| ## Motivation | Context (not user-facing) | Skip in changelog |
| ## Impact | Breaking change detection | Check for "**BREAKING**" markers |
| ## Capabilities | Feature list | Can be used for changelog |

## Parsing Strategy

### Line-by-Line Parsing

```python
def parse_proposal(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Initialize parser state
    in_summary = False
    in_proposed = False
    summary = []
    proposed_change = []
    
    for line in lines:
        line = line.strip()
        
        # Track sections
        if line.startswith('## Summary'):
            in_summary = True
            in_proposed = False
        elif line.startswith('## Proposed Change'):
            in_summary = False
            in_proposed = True
        elif line.startswith('##'):
            # Hit new section, stop parsing
            break
        
        # Extract content
        elif in_summary and line:
            summary.append(line)
        elif in_proposed and line:
            proposed_change.append(line)
    
    return {
        'summary': '\n'.join(summary).strip(),
        'proposed_change': '\n'.join(proposed_change).strip()
    }
```

### Keyword Detection

```python
def categorize_from_keywords(text):
    """Auto-categorize based on keywords"""
    text_lower = text.lower()
    
    # Category keywords
    categories = {
        'Added': ['add', 'create', 'introduce', 'new', 'implement', 'establish', 'initialize'],
        'Changed': ['modify', 'update', 'change', 'refactor', 'improve', 'enhance', 'adjust'],
        'Fixed': ['fix', 'bug', 'resolve', 'correct', 'error', 'failure', 'handle'],
        'Removed': ['remove', 'delete', 'deprecate', 'drop', 'remove legacy'],
        'Breaking': ['breaking', 'incompatible', 'major', 'api change']
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    return None  # No match
```

**Limitations**:
- Keyword-based is heuristic, can misclassify
- User should review categories before finalizing changelog
- Complex changes may need manual categorization

### Breaking Change Detection

```python
def detect_breaking_change(text):
    """Check if change is breaking"""
    text_upper = text.upper()
    
    breaking_indicators = [
        '**BREAKING**',
        'BREAKING',
        'incompatible',
        'breaking change'
    ]
    
    for indicator in breaking_indicators:
        if indicator in text_upper:
            return True, indicator
    
    return False, None
```

**Special case**: Security-related breaking changes

```python
def categorize_security_change(text):
    """Check if this is a security fix"""
    keywords = ['security', 'vulnerability', 'cve', 'patch', 'critical', 'jwt']
    text_lower = text.lower()
    
    for keyword in keywords:
        if keyword in text_lower:
            return True
    
    return False
```

If security fix detected → categorize as Security even if keywords suggest Fixed

## Processing Multiple Changes

### Split by Features

When proposal.md has multiple bullet points under "## Proposed Change":

```markdown
## Proposed Change

Create a complete Go project structure:
- Initialize Go modules with Cobra framework
- Add configuration management with mise
- Set up testing infrastructure

Implement user authentication:
- Add JWT token support
- Implement refresh token flow
- Add session management
```

**Strategy**: Create separate changelog entries per feature:

1. "Create a complete Go project structure" → Added: Project setup
2. "Initialize Go modules with Cobra framework" → Added: Project setup
3. "Implement user authentication" → Added: User authentication

### Split by Type

When bullets mix different types:

```python
def split_by_type(proposed_text):
    """Split proposed change into separate entries by type"""
    lines = proposed_text.split('\n')
    entries = []
    current_entry = {'bullet': '', 'content': []}
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('- '):
            if current_entry['content']:
                entries.append({
                    'content': ' '.join(current_entry['content']),
                    'bullet': current_entry['bullet']
                })
            current_entry = {'bullet': stripped, 'content': []}
        elif stripped:
            current_entry['content'].append(stripped)
    
    # Don't forget last entry
    if current_entry['content']:
        entries.append({
            'content': ' '.join(current_entry['content']),
            'bullet': current_entry['bullet']
        })
    
    return entries
```

## Change Name Extraction

### From Directory Path

```python
def extract_change_name(directory_path):
    """Extract change name from YYYY-MM-DD-<name> format"""
    # Path: openspec/changes/archive/2026-01-09-initialize-project-structure
    parts = directory_path.split('/')
    if len(parts) > 0:
        name_with_date = parts[-1]
        # Remove date prefix: 2026-01-09-initialize-project-structure
        # Expected: initialize-project-structure
        if len(name_with_date) >= 11:  # YYYY-MM-DD- is 11 chars
            return name_with_date[11:]
    return None
```

**Use**: For referencing change in changelog entry

Example:
```markdown
### Added
- Establishes Go project structure, tooling, and foundational configuration (initialize-project-structure)
```

## Complex Scenarios

### Infrastructure Changes

Changes with no user-facing impact:

```markdown
## Proposed Change

Update CI/CD pipeline for better performance
- Add caching to reduce build times
- Optimize test suite execution
- Update deployment process
```

**Strategy**:
- Categorize as "Changed" or "Infrastructure"
- Group under single entry: "Update CI/CD pipeline"
- Add note: "(infrastructure-only)"

### Multi-Category Changes

Changes affecting multiple aspects:

```markdown
## Proposed Change

Add user authentication with OAuth2 support:
- Implement login flow with Google provider
- Add GitHub OAuth2 provider
- Update session management for multiple providers
- **BREAKING**: Legacy OAuth1 is deprecated

### Strategy**:
1. "Add user authentication with OAuth2 support" → Added
2. "Implement login flow with Google provider" → Added (same entry)
3. "Update session management" → Changed (same entry)
4. Legacy OAuth1 deprecated → Removed (separate entry)
5. Breaking change → Breaking (separate entry or emphasize with **BREAKING**)

## Integration with Other Skills

### Using openspec-explore

Before generating changelog, user may want to explore context:

```bash
# Understand recent changes
openspec-explore "What were the main changes in Q1 2026?"

# Then generate changelog
openspec-generate-changelog --since 2026-01-01 --until 2026-03-31
```

### Using openspec-verify

Verify changes are complete before changelog:

```bash
# Verify implementation
openspec-verify <change-name>

# Then generate changelog for verified changes
openspec-generate-changelog --changes <verified-changes>
```

## Error Handling

### Missing Proposal File

```python
def handle_missing_proposal(change_path):
    """Use alternative sources when proposal.md doesn't exist"""
    # Try design.md
    design_path = os.path.join(os.path.dirname(change_path), 'design.md')
    if os.path.exists(design_path):
        return parse_design_summary(design_path)
    
    # Try tasks.md
    tasks_path = os.path.join(os.path.dirname(change_path), 'tasks.md')
    if os.path.exists(tasks_path):
        return parse_tasks_summary(tasks_path)
    
    # Fallback
    return {
        'summary': 'Infrastructure update',
        'proposed_change': 'Configuration changes'
    }
```

### Malformed Proposal

```python
def validate_proposal_structure(content):
    """Check if proposal.md has expected structure"""
    required_sections = ['## Summary', '## Proposed Change']
    
    for section in required_sections:
        if section not in content:
            return False, f"Missing required section: {section}"
    
    return True, None
```

## Best Practices

1. **Preserve context**: Keep enough detail in changelog entries for users to understand changes
2. **Be specific**: Avoid vague descriptions like "various improvements"
3. **Categorize correctly**: Wrong category leads to user confusion
4. **Highlight breaking**: Use `**BREAKING**` prefix for breaking changes
5. **Group related changes**: Multiple bullets about one feature → single entry
6. **Include migration links**: For breaking changes, link to migration guide
7. **Version appropriately**: Use semantic versioning based on change impact
