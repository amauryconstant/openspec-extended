# Documentation Update Rules

Rules for updating AGENTS.md and CLAUDE.md documentation files when adding, updating, or removing skills.

## General Principles

1. **Preserve existing structure** - Don't reorganize entire file, update targeted sections
2. **Maintain consistency** - Use same format across all entries
3. **Add context, not clutter** - Include brief, meaningful descriptions
4. **Keep it alphabetical** - Skills distributed in alphabetical order unless grouped by purpose
5. **Version awareness** - Track skill versions if specified in SKILL.md frontmatter
6. **Don't duplicate** - Check for existing entries before adding
7. **Clean removal** - When removing skills, ensure no orphaned references remain

## Adding Skills

### When to Add

- After creating a new skill with skill-creator
- After manually creating a skill
- When skill metadata changes (name, description, version updated)

### Entry Format

```markdown
- `openspec-new-skill`: Start a new OpenSpec change
- `openspec-review-artifacts`: Review artifacts for quality and consistency
```

**Components**:
- Skill name in backticks (e.g., `openspec-new-skill`)
- Colon separator (space before and after)
- Brief description (30-60 characters)
- Sentence case for first letter
- Active voice ("Teaches AI agents" not "AI agents are taught by")

### Insertion Order

**Default**: Alphabetical order

**Grouped by purpose** (if applicable):
```markdown
**Core Skills**:
- `openspec-concepts`: Framework understanding
- `openspec-modify-artifact`: Artifact modification

**Quality Skills**:
- `openspec-review-artifacts`: Artifact review
- `openspec-verify-change`: Implementation verification

**Utility Skills**:
- `openspec-new-change`: Change creation
- `openspec-apply-change`: Implementation
```

**Grouping rules**:
- Keep groups small (3-5 skills per group)
- Clearly label groups with descriptive names
- Within groups, maintain alphabetical order

### Verification Before Adding

**Check for duplicates**:
```python
def is_duplicate_skill(skills_list, new_skill_name):
    for skill in skills_list:
        if skill['name'].lower() == new_skill_name.lower():
            return True
    return False
```

**Check for similar names**:
```python
def find_similar_skills(skills_list, new_skill_name):
    similar = []
    for skill in skills_list:
        if skill['name'].lower().replace('-', '') in new_skill_name.lower().replace('-', ''):
            similar.append(skill['name'])
    return similar
```

**Action**: If similar names found, ask user for confirmation before adding.

## Updating Skills

### When to Update

- Skill description changes in SKILL.md
- Skill version changes in SKILL.md
- Skill purpose or scope changes

### Update Rules

**1. Locate existing entry**
```python
def find_skill_entry(content, skill_name):
    for line in content.split('\n'):
        if line.strip().startswith(f'- `{skill_name}`:'):
            return line
    return None
```

**2. Update description only**
- Keep skill name unchanged
- Replace description after colon
- Preserve formatting (bullet style, indentation)

**3. Update description and version**
- If version specified in SKILL.md frontmatter
- Append version to description
- Format: `- `skill-name`: Description (v1.0.0)`

**4. Update with metadata changes**
- If license, compatibility, or author changes
- Add relevant metadata tags
- Update description accordingly

### What NOT to Change

- Don't change skill name (requires removing and re-adding)
- Don't change entry format (bullet style, indentation)
- Don't reposition entries unless user requests

## Removing Skills

### When to Remove

- Skill file deleted
- Skill deprecated and removed
- Skill merged into another skill

### Removal Process

**1. Locate entry**
```python
def find_and_remove_skill(content, skill_name):
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if not line.strip().startswith(f'- `{skill_name}`:'):
            new_lines.append(line)
    
    return '\n'.join(new_lines)
```

**2. Handle adjacent blank lines**
```python
# Remove extra blank lines after removal
def cleanup_blank_lines(content):
    lines = content.split('\n')
    cleaned = []
    prev_was_blank = False
    
    for line in lines:
        is_blank = line.strip() == ''
        if not (is_blank and prev_was_blank):
            cleaned.append(line)
        prev_was_blank = is_blank
        else:
            cleaned.append(line)
    
    return '\n'.join(cleaned)
```

**3. Verify no orphaned references**
- Search file for skill name mentions outside of Skills Distributed section
- If found, update those references or remove them

## Section Updates

### Skills Distributed Section

**Complete replacement** (if all skills reorganized):
```markdown
**Skills Distributed**:
[New skill list in correct order]
```

**Incremental update** (if adding/updating specific skills):
```python
def update_skills_distributed(content, skill_name, new_description):
    lines = content.split('\n')
    updated = []
    
    for line in lines:
        if line.strip().startswith(f'- `{skill_name}`:'):
            updated.append(f'- `{skill_name}`: {new_description}')
        else:
            updated.append(line)
    
    return '\n'.join(updated)
```

### Quick Reference Section

**Add new command**:
```markdown
## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspec-maintain-ai-docs`: Maintain AGENTS.md and CLAUDE.md |
| `openspec-new-skill`: Start a new OpenSpec change |
```

**Update command description**:
- Locate row in table
- Update purpose column
- Keep table formatting (| separators, alignment)

### Project Context Section

**When to update**:
- Skills count changes significantly
- New skill categories added
- Project scope expands

**Update approach**:
- Update skills count if specified
- Add new category descriptions if needed
- Keep existing context unless user requests change

## AGENTS.md vs CLAUDE.md

### Shared Updates

Some changes should apply to both files:

- Core framework skills (openspec-concepts, openspec-modify-artifact)
- General utility skills
- Project configuration changes

### AGENTS.md-Specific

Only update AGENTS.md for:

- OpenCode-specific skills
- Tool configuration changes
- CI/CD pipeline documentation
- Code style specific to project structure

### CLAUDE.md-Specific

Only update CLAUDE.md for:

- Claude Code-specific skills
- Claude Code configuration
- Claude Code integration patterns
- Claude Code-specific limitations or features

## Conflict Resolution

### Version Mismatch

**Scenario**: SKILL.md frontmatter has version v1.2 but docs say v1.0

**Resolution**:
1. Ask user which version is correct
2. Update docs to match SKILL.md (recommended, as source of truth)
3. Optionally add note: "(See SKILL.md for current version)"

### Duplicate Entries

**Scenario**: Same skill name found in two sections

**Resolution**:
1. Determine which section is correct location
2. Remove from incorrect section
3. Keep in correct section with consolidated description

### Orphaned References

**Scenario**: Description mentions `openspec-deprecated-skill` in Quick Reference but skill doesn't exist

**Resolution**:
1. Remove reference from Quick Reference table
2. Check if other orphaned references exist
3. Clean up all references to removed skills

## Backup Strategy

### Before Major Updates

1. Backup current file
2. Apply updates
3. Verify correctness
4. Keep backup until confirmed

### Backup Method

```bash
# Create timestamped backup
cp AGENTS.md AGENTS.md.backup.$(date +%Y%m%d_%H%M%S)
```

### Rollback

If updates introduce errors, restore from backup:
```bash
# Restore from backup
cp AGENTS.md.backup.YYYYMMDD_HHMMSS AGENTS.md
```

## Formatting Standards

### Markdown Consistency

- Use consistent heading levels (# for title, ## for sections)
- Use consistent bullet style (all - or all *)
- Use consistent code block formatting (```language or indented)
- No trailing whitespace on any line

### Skill Entry Consistency

- All skill names in backticks (`)
- Single space after colon in description
- Descriptions start with capital letter
- No period at end of description (unless multiple sentences)

### Table Consistency

- Left column aligned, right column left-aligned
- Consistent column headers (Command | Purpose)
- No empty rows in tables

## Testing Updates

### Manual Validation Checklist

Before finalizing updates:

- [ ] File parses correctly (check with markdown parser)
- [ ] No duplicate skill entries
- [ ] All skill names match actual skill directories
- [ ] Descriptions are concise and meaningful
- [ ] Tables have proper syntax
- [ ] No broken links or references
- [ ] Consistent formatting throughout

### Test Scenarios

**Add new skill**:
1. Run skill to add entry
2. Verify entry appears in correct location
3. Check alphabetical order maintained
4. Verify no duplicates introduced

**Update existing skill**:
1. Run skill to update entry
2. Verify description changed correctly
3. Verify skill name unchanged
4. Verify no unintended changes to other entries

**Remove skill**:
1. Run skill to remove entry
2. Verify entry removed cleanly
3. Verify no orphaned references remain
4. Check formatting preserved
