# Formatting Guide

## Code Blocks

- YAML frontmatter examples: ```yaml
- JSON configuration examples: ```json
- Inline code: Use backticks for field names, file paths, keywords

## Separators

Use `---` between major sections only. Never use between subsections.

## Lists

- Numbered lists (1., 2., 3.) for sequences
- Bulleted lists for groups
- Nested bullets: use `  -` (two-space indent)

## Links

- Official docs: [Description](URL) in "Official Documentation Sources"
- Section cross-refs: Use `### [Section Name]` format
- Avoid relative links

## AI-Optimized Patterns

### Frontmatter Tables
```markdown
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
```

### Code Pattern
```markdown
Use `Bash(git *)` format for tool permission specifiers.
```

### File Path Pattern
```markdown
**File:** `.claude/skills/<name>/SKILL.md`
```

### Heading Pattern
```markdown
## [Major Section]

[Content]

---

## [Next Major Section]
```
