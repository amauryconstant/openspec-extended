# AI-Optimized Structure Standards

## Document Header Format

```markdown
# [Platform Name] Documentation

[One-line subtitle explaining purpose]

## Official Documentation Sources

[List all official sources with links]

---
```

## Section Ordering (must follow exactly)

1. Official Documentation Sources
2. Document Types
3. [Platform-specific sections in alphabetical order]
4. Examples
5. Validation Constraints
6. Comparison (if comparing platforms)

## Table Format Standard

Frontmatter tables MUST use this exact column order:
`Field | Type | Required | Default | Description`

Built-in entities tables MUST use:
`[Entity Name] | [Description]` or `[Entity Name] | [Field 2] | ...`

## Hierarchy Rules

- H1: Document title only (appears once)
- H2: Major section separators
- H3: Subsections within major sections
- H4: Detail subsections (rare, use sparingly)

## Section Templates

### New Document Type Section

```markdown
### [Document Type Name]

**File:** `[file path]`

**Frontmatter Fields:**

| Field | Type | Required | Default | Description |
| ----- | ---- | -------- | ------- | ----------- |

**Body:** [content description]

[Additional subsections as needed]
```

### New Functional Section

```markdown
## [Section Name]

**Description:** Brief purpose

[Content]

**Examples:**

[Code examples]

**Edge Cases:** [if applicable]
```
