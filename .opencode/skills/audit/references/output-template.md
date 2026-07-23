# Output Template

Phase E writes the final report following this structure. Sections appear only when findings exist for that category. Variable substitutions use `<…>` notation.

```markdown
# Integration Audit — <upstream-label> vs <local-label> — <UTC-date>

## Metadata

| <upstream-label> | <local-label> |
| --- | --- |
| commit `<hash>` <date> | commit `<hash>` <date> |
| <file count> files | <file count> files |
| v<X.Y.Z> | v<A.B.C> |

## Executive Summary

- ≤10 bullets covering severity counts, top findings, blast radius
- One bullet per CRITICAL finding (filename + one-line issue)

## Key Findings (CRITICAL + HIGH only)

One paragraph per finding: file:line, issue, concrete fix, blast radius.

## Detailed Findings

### Naming & Taxonomy
### CLI / JSON / Schema Drift
### Manifest / Resource Parity
### Skill Quality
### Agent Quality
### Command Quality
### Phase Workflow Quality
### Documentation Drift

Each section: list of findings as `file:line — issue — fix` tuples, grouped by sub-area.

## Prioritized Backlog

| # | Severity | File:line | Issue | Suggested fix |
|---|----------|-----------|-------|---------------|
| 1 | … | … | … | … |

## Out of Scope / Deferred

Items that look like findings but are intentional (different version domains by design, intentional prefix collisions, etc.).
```
