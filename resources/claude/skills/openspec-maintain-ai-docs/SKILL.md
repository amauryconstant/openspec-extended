---
name: openspec-maintain-ai-docs
description: Maintain AGENTS.md and CLAUDE.md documentation to keep synchronized with available skills. Use when adding new skills, updating existing ones, or ensuring documentation reflects current state.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec-extended
  version: "1.0"
---

# AI Documentation Maintenance

Maintain AI coding assistant documentation files (AGENTS.md, CLAUDE.md) to keep them synchronized with available skills.

## When to Use

- After creating new skills
- When skill metadata changes (name, description, version)
- Before releasing or publishing OpenSpec-extended
- As part of periodic documentation audits
- When documentation drifts from actual skills available

## Quick Reference

| Documentation File | Purpose | Key Sections | Location |
|------------------|---------|---------------|----------|
| `AGENTS.md` | Project context and skills list | Project root (OpenSpec-extended) |
| `CLAUDE.md` | Claude Code-specific documentation | Project root (if applicable) |

## Workflow

### 1. Detect Documentation Files

Scan current directory for documentation files:

```bash
# Check for AGENTS.md
test -f AGENTS.md && echo "AGENTS.md found" || echo "AGENTS.md not found"

# Check for CLAUDE.md  
test -f CLAUDE.md && echo "CLAUDE.md found" || echo "CLAUDE.md not found"
```

**Detected files**: Report which documentation files exist.

### 2. Read Current Documentation

For each detected file:

- Parse skills list sections
- Extract quick reference tables
- Preserve existing content structure

**Key sections to preserve**:
- Skills Distributed (list of skills with descriptions)
- Quick Reference (if exists)
- Project Context / Overview
- Any project-specific sections

### 3. Scan Available Skills

Discover skills in `.opencode/skills/openspec-*`:

```bash
# List OpenSpec skills
find .opencode/skills/openspec-* -type f -name "SKILL.md" | sort
```

For each skill:

- Parse SKILL.md frontmatter (name, description, license, version)
- Extract skill summary
- Build skills metadata

### 4. Identify Discrepancies

Compare detected skills vs documented skills:

**Types of discrepancies**:
- **Missing in docs**: Skill exists but not documented
- **Outdated entries**: Documented skill has wrong description or outdated info
- **Orphaned entries**: Documented skill no longer exists
- **Version mismatch**: Documented version doesn't match SKILL.md

**Discrepancy report format**:
```markdown
## Documentation Discrepancies

### Missing in Documentation
- `openspec-new-skill`: Not listed in Skills Distributed section

### Outdated Entries
- `openspec-review-artifacts`: Description needs update (current: "Reviews artifacts" - should be: "Reviews artifacts for quality...")

### Orphaned Entries
- `openspec-old-skill`: Documented but no longer exists
```

### 5. Update Documentation

For each discrepancy:

**For missing skills**:
- Add entry to Skills Distributed section
- Follow existing format (alphabetical or grouped)
- Include name, description, and brief purpose

**For outdated entries**:
- Update description to match SKILL.md frontmatter
- Update version if specified
- Preserve any notes or context

**For orphaned entries**:
- Remove entry from documentation
- Optionally archive to "Deprecated Skills" section

### 6. Validate Changes

Before writing:

- Check markdown formatting
- Verify no duplicate entries
- Confirm skill names are links to actual skill directories
- Ensure consistency across all documentation files

### 7. Preview and Confirm

Show user:

- Summary of changes (X added, Y updated, Z removed)
- Diff view (if supported) or detailed change list
- Ask for confirmation before writing

## Output

After confirmation, display:

```markdown
## Documentation Updated

**Files Modified**:
- `AGENTS.md`: X skills added, Y skills updated, Z skills removed

**Summary**:
- Skills Distributed section now reflects current state
- Quick Reference updated if applicable
- All discrepancies resolved

**Next Steps**:
- Run `openspecx init <tool>` to reinstall updated skills
- Commit changes to version control
```

## Advanced Usage

### Update specific documentation only

```bash
# Update only AGENTS.md
openspec-maintain-ai-docs --files AGENTS.md

# Update only CLAUDE.md
openspec-maintain-ai-docs --files CLAUDE.md
```

### Dry run mode

```bash
# Preview changes without writing
openspec-maintain-ai-docs --dry-run
```

### Custom skills directory

```bash
# Scan different directory
openspec-maintain-ai-docs --skills-dir /path/to/skills
```

## Troubleshooting

**No documentation files found**:
- Ensure you're in project root
- Create AGENTS.md if none exists (skill can provide template)

**Skills directory empty**:
- Check path is correct (`.opencode/skills/` or `.claude/skills/`)
- Verify permissions allow reading

**Duplicate entries**:
- Skill should detect duplicates during validation
- Manually review and remove duplicates if found

## Best Practices

- **Keep skills in sync**: Run this skill after adding/updating any skill
- **Preserve structure**: Don't reorganize entire documentation, update targeted sections
- **Add context**: Include brief descriptions for each skill's purpose
- **Version tracking**: Document skill versions if specified in frontmatter
- **Consistency**: Use same format across AGENTS.md and CLAUDE.md

## References

See `references/doc-structures.md` for:
- AGENTS.md section definitions
- CLAUDE.md section definitions
- Entry format specifications

See `references/update-rules.md` for:
- Rules for adding skills
- Rules for updating entries
- Rules for removing skills
