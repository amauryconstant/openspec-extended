---
name: openspec-review-artifacts
description: Review OpenSpec artifacts (proposal.md, design.md, tasks.md, specs/) for quality, completeness, consistency, and alignment with schema requirements. Use when validating artifacts before archiving, checking consistency across change artifacts, or identifying issues that prevent successful archiving.
license: MIT
compatibility: opencode
metadata:
  author: openspec-extended
  version: "0.1.0"
---

# Artifact Review

Review OpenSpec artifacts for quality, completeness, and consistency.

## When to Use

- Reviewing artifacts before archiving a change
- Validating artifact quality during change creation
- Checking consistency across all artifacts in a change
- Identifying issues that would prevent successful archiving
- Reviewing individual artifacts for best practices

## Artifact Quick Reference

| Artifact | Purpose | Key Sections | Common Issues |
|-----------|----------|---------------|---------------|
| proposal.md | Why and what | Why, What Changes, Capabilities, Impact | Missing Why, vague What Changes |
| specs/ | Requirements | ADDED/MODIFIED/REMOVED, scenarios | Wrong scenario header level |
| design.md | How | Context, Decisions, Trade-offs | Missing rationale |
| tasks.md | Checklist | Numbered ## sections, checkboxes | Wrong checkbox format |

## Review Workflow

### Single Artifact Review

1. Identify artifact type (proposal/spec/design/tasks)
2. Read the artifact file
3. Load `references/review-criteria.md` for that artifact type
4. Check each required section exists
5. Validate format (headers, scenario levels, checkbox format)
6. Review content quality (specificity, clarity)
7. Reference `references/common-issues.md` for known problems
8. Report issues with actionable feedback (line numbers, examples)

### Entire Change Review

1. List artifacts: `openspec status --change <name> --json`
2. Review each artifact using single artifact workflow
3. **Cross-artifact consistency checks**:
   - proposal Capabilities match specs/ folder structure
   - proposal What Changes covered by tasks.md
   - design.md decisions referenced in tasks
   - All proposal Capabilities have corresponding specs
4. **Schema compliance**:
   - Validate against schema.yaml requirements
   - Check template format adherence
5. Prioritize issues: critical (blocking), warning (should fix), suggestion (nice to have)

## Consistency Checks

### proposal → specs
- New Capabilities in proposal = specs/ directory names
- Modified Capabilities in proposal = existing spec names in openspec/specs/
- Use kebab-case names consistently

### specs → design
- All ADDED/MODIFIED requirements addressed in design
- REMOVED requirements with Migration have migration plan in design

### design → tasks
- Decisions in design.md have corresponding tasks
- Risks in design.md have mitigation tasks
- Non-goals in design.md not in tasks.md

### proposal → tasks
- What Changes items covered by task sections
- Impact items considered in tasks

## Common Issues by Artifact

### proposal.md
- Missing Why section
- Vague "improve X" in What Changes
- Inconsistent capability naming
- Missing Impact section

### specs/
- Wrong scenario header (3 # instead of 4 #)
- MODIFIED with partial content
- Missing scenarios for requirements
- SHALL/MUST not used

### design.md
- Implementation details (belongs in tasks)
- Decisions without rationale
- Missing alternatives considered

### tasks.md
- Non-checkbox format breaks apply tracking
- Tasks too large/vague
- Wrong dependency order
- Missing numbered ## sections

## Report Format

```
## Artifact Review: [artifact-name.md]

### ✅ Format: Valid
- All required sections present
- Header format correct

### ⚠️ Issues Found

#### Critical (Must Fix Before Archive)
- **Line X**: [Description]
  - Fix: [Specific action]
  
#### Warnings (Should Fix)
- **Line X**: [Description]
  - Better: [Suggestion]

#### Suggestions (Nice to Have)
- **Line X**: [Description]
  - Consider: [Alternative]

### Consistency Check
- ✅/❌ [Cross-artifact validation result]

See references/review-criteria.md for detailed criteria.
```

## References

- **Detailed criteria**: See `references/review-criteria.md` for comprehensive review criteria per artifact type
- **Common issues**: See `references/common-issues.md` for catalog of frequent problems with examples
- **Schema validation**: Run `openspec validate` for automated checks
