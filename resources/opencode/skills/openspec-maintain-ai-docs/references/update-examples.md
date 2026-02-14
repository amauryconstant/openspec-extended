# Documentation Update Examples

Before and after examples showing how AGENTS.md and CLAUDE.md are updated.

## Example 1: Adding a New Skill

### Before

```markdown
# OpenSpec-extended - OpenCode Reference

## Project Context & Philosophy

**Purpose**: Bridge AI coding assistants with OpenSpec - spec-driven development framework.

**Core Philosophy**: Agree on WHAT to build before writing code.

**Project Scope**: This is a rough, minimal project.

**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking

## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspecx install claude` | Install skills to `.claude/skills/` |
| `openspecx install opencode` | Install skills to `.opencode/skills/` |
```

### After

```markdown
# OpenSpec-extended - OpenCode Reference

## Project Context & Philosophy

**Purpose**: Bridge AI coding assistants with OpenSpec - spec-driven development framework.

**Core Philosophy**: Agree on WHAT to build before writing code.

**Project Scope**: This is a rough, minimal project. No deep infrastructure, CI, or complex install scripts needed.

**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifacts`: Reviews OpenSpec artifacts for quality, completeness, and consistency
```

### After

```markdown
**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifacts`: Reviews OpenSpec artifacts for quality, completeness, and consistency
```

**Changes**:
- Removed `openspec-old-parser` entry
- Maintained alphabetical order
- No orphaned references found

---

## Example 4: Updating Quick Reference Table

### Before

```markdown
## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspecx install claude` | Install skills |
```

### After

```markdown
## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspecx install claude` | Install skills to `.claude/skills/` |
| `openspecx install opencode` | Install skills to `.opencode/skills/` |
```

**Changes**:
- Added command for `openspecx install opencode`
- Maintained table format and alignment
- Sorted commands alphabetically

---

## Example 5: Handling Version Information

### Before

```markdown
**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts
- `openspec-review-artifacts`: Reviews OpenSpec artifacts
```

### After (with version update)

```markdown
**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking (v1.0)
- `openspec-review-artifacts`: Reviews OpenSpec artifacts for quality and consistency
```

**Changes**:
- Added version (v1.0) to `openspec-modify-artifacts` entry
- Preserved other entries unchanged
- Version format consistent across all skills

---

## Example 6: Grouping Skills by Category

### Before (flat alphabetical list)

```markdown
**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts
- `openspec-review-artifacts`: Reviews OpenSpec artifacts
- `openspec-new-change`: Start a new OpenSpec change
- `openspec-apply-change`: Implement tasks from an OpenSpec change
```

### After (categorized)

```markdown
**Skills Distributed**:

**Core Skills**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework

**Artifact Management**:
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifacts`: Reviews OpenSpec artifacts for quality

**Workflow Skills**:
- `openspec-new-change`: Start a new OpenSpec change
- `openspec-apply-change`: Implement tasks from an OpenSpec change
```

**Changes**:
- Grouped related skills into categories
- Added category headers for clarity
- Maintained alphabetical order within categories

---

## Example 7: AGENTS.md vs CLAUDE.md Updates

### AGENTS.md Update (general skill)

```markdown
# OpenSpec-extended - OpenCode Reference

**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifacts`: Reviews OpenSpec artifacts
- `openspec-maintain-ai-docs`: Maintain AGENTS.md and CLAUDE.md documentation
```

**Changes**:
- Added skill entry in AGENTS.md (general purpose skill)
- Updated skills count (4 skills)

### CLAUDE.md Update (not needed)

**Action**: No update to CLAUDE.md
**Reason**: `openspec-maintain-ai-docs` is a general-purpose skill, not Claude Code-specific

---

## Example 8: Resolving Duplicate Entries

### Before (duplicate detected)

```markdown
**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifacts`: Reviews OpenSpec artifacts
- `openspec-review-artifacts`: Reviews OpenSpec artifacts for quality
```

**Changes**:
- Removed duplicate `openspec-review-artifacts` entry
- Verified only one entry remains
- Maintained alphabetical order

---

## Example 9: Full File Reorganization

### Before (scattered structure)

```markdown
# OpenSpec-extended - OpenCode Reference

## Project Context

**Purpose**: Bridge AI coding assistants with OpenSpec

**Skills Distributed**:
- `openspec-concepts`: Framework understanding
- `openspec-modify-artifacts`: Artifact modification

## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspecx install claude` | Install skills |
```

### After (organized structure)

```markdown
# OpenSpec-extended - OpenCode Reference

## Project Context & Philosophy

**Purpose**: Bridge AI coding assistants with OpenSpec - spec-driven development framework.

**Core Philosophy**: Agree on WHAT to build before writing code.

**Project Scope**: This is a rough, minimal project.

**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifacts`: Reviews OpenSpec artifacts for quality, completeness, and consistency

## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspecx install claude` | Install skills to `.claude/skills/` |
| `openspecx install opencode` | Install skills to `.opencode/skills/` |

## Running / Testing

**No automated tests** - Manual testing only.

---

## Code Style

[Code style sections preserved]

---

## Project Structure

[Project structure sections preserved]
```

**Changes**:
- Restored proper section hierarchy
- Added missing Core Philosophy subsections
- Added Quick Reference table entries

---

## Edge Cases

### Empty Skills Directory

**Before**: Skills Distributed section lists 5 skills

**After**: Skills Distributed section lists 3 skills

**Action**: 
1. Scan actual skills directory
2. Report discrepancy: "2 documented skills no longer exist"
3. Ask user whether to remove entries or investigate

### Malformed Skill Entry

**Before**: 
```markdown
- openspec-concepts Teaches AI agents about OpenSpec framework
```

**After**:
```markdown
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
```

**Action**: Fix formatting (add backticks, add colon separator)

### Missing Frontmatter in SKILL.md

**Before**: Cannot read skill version

**After**: Document skill without version

**Action**: 
1. Report "SKILL.md missing frontmatter" in discrepancy report
2. Add entry anyway with note: "(version unknown)"
3. Ask user to fix SKILL.md frontmatter for future runs
