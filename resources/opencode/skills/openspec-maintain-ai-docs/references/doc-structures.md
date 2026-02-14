# Documentation File Structures

This guide defines the expected structures for AGENTS.md and CLAUDE.md documentation files.

## AGENTS.md Structure

### Purpose

Project-level documentation for OpenSpec-extended. Serves as:
- Quick reference for available skills
- Project context and philosophy
- Development workflow documentation
- Troubleshooting and best practices

### Typical Sections

```markdown
# <Project Name> - OpenCode/Claude Code Reference

## Project Context & Philosophy

**Purpose**: Brief description of what this project does

**Core Philosophy**: Key principles guiding the project

**Project Scope**: What's in scope, what's out of scope

**Skills Distributed**:
- `skill-name-1`: Brief description
- `skill-name-2`: Brief description
- `skill-name-3`: Brief description

**Research Maintenance**: Notes on keeping documentation current

**Resource Creation**: References to platform-specific docs

---

## Quick Reference

| Command | Purpose |
|----------|----------|
| `command1` | Description |
| `command2` | Description |

---

## Running / Testing

**No automated tests** - Manual testing only.

```bash
# Example test command
./bin/openspecx install claude
```

---

## Code Style

### Language Requirements

**Header**: Always use shebang
**Strict Mode**: Set at top of all scripts

### Variables

**Constants**: UPPERCASE
**Local variables**: snake_case

### Key Patterns

[Code examples from project]

---

## Project Structure

```
directory/
├── file1
└── file2
```

---

## Adding New Skills

[Instructions for skill creation]

---

## Platform-Specific Details

**Claude Code Skills**: [Location]
**OpenCode Skills**: [Location]

---

## License

[License information]
```

## CLAUDE.md Structure

### Purpose

Claude Code-specific documentation when projects have both Claude Code and OpenCode skills. More focused than AGENTS.md.

### Typical Sections

```markdown
# Claude Code Configuration

## Project-Specific Skills

[Skills specific to Claude Code usage]

## Skill Configuration

How to configure Claude Code-specific behavior

## Integration with OpenSpec

How Claude Code interacts with OpenSpec workflow

## Claude-Specific Patterns

Patterns unique to Claude Code development
```

## Key Differences

| Aspect | AGENTS.md | CLAUDE.md |
|---------|-------------|-------------|
| Scope | Project-wide | Claude Code-specific |
| Skills | All skills | Claude Code-specific skills only |
| Audience | Any AI tool | Claude Code users only |
| Structure | Comprehensive | Focused on Claude Code features |

## Section Identification

### Skills Distributed Section

**Location**: After "Project Context & Philosophy" section

**Format**:
```markdown
**Skills Distributed**:
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifacts`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifacts`: Reviews OpenSpec artifacts for quality
```

**Entry format**:
- Skill name in backticks
- Brief description (1-2 lines)
- Sorted: Alphabetical or grouped by purpose

### Quick Reference Section

**Location**: After "Skills Distributed" or near top of file

**Format**:
```markdown
## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspecx install claude` | Install skills to `.claude/skills/` |
| `openspecx install opencode` | Install skills to `.opencode/skills/` |
```

**Properties**:
- Markdown table with Command and Purpose columns
- Commands relevant to the tool (Claude Code or OpenCode)
- Practical examples users can copy-paste

## Format Variations

### Minimal AGENTS.md

Some projects use minimal AGENTS.md with just:
- Skills Distributed section
- Basic project info
- No detailed sections

### Comprehensive AGENTS.md

Larger projects include:
- Code style guidelines
- Testing strategies
- CI/CD pipeline documentation
- Contributing guidelines

### Hybrid Documentation

Projects with both tools may have:
- Shared sections in AGENTS.md
- Tool-specific details in CLAUDE.md
- Cross-references between files

## Parsing Strategy

### Reading AGENTS.md

```python
# Extract skills list
def extract_skills_list(content):
    skills = []
    in_skills_section = False
    
    for line in content.split('\n'):
        if '**Skills Distributed**:' in line:
            in_skills_section = True
        elif in_skills_section and line.startswith('- '):
            skill_name = line.split(':`')[0].strip().strip(' -`')
            description = line.split(':', 1)[1].strip() if ':' in line else ''
            skills.append({'name': skill_name, 'description': description})
    
    return skills
```

### Reading CLAUDE.md

```python
# Extract Claude-specific sections
def extract_claude_sections(content):
    sections = {}
    current_section = None
    
    for line in content.split('\n'):
        if line.startswith('##'):
            current_section = line.strip('#')
            sections[current_section] = []
        elif current_section and line.startswith('- '):
            sections[current_section].append(line.strip('- '))
    
    return sections
```

## Writing Strategy

### Adding Skills

1. Find appropriate section (Skills Distributed or Project-Specific Skills)
2. Determine insertion point (alphabetical order or append)
3. Write skill entry with consistent format
4. Preserve surrounding content

### Updating Skills

1. Locate existing entry by skill name
2. Update description line while preserving skill name
3. Check if version needs updating
4. Preserve formatting (indentation, bullet style)

### Removing Skills

1. Find entry by skill name
2. Remove entire line
3. Remove trailing empty lines
4. Verify no orphaned references remain

## Validation Rules

### Required Sections

For AGENTS.md:
- Project Context & Philosophy
- Skills Distributed

For CLAUDE.md:
- Project-specific skills section (if any Claude-specific skills exist)

### Format Validation

- Markdown heading hierarchy (single # for title, ## for sections)
- Skill entries use consistent bullet style (- or *)
- Tables have proper syntax (| separators)
- No trailing whitespace
