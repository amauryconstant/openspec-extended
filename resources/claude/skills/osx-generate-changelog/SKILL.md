---
name: osx-generate-changelog
description: Generate CHANGELOG.md from archived OpenSpec changes (Keep a Changelog format). Run via /osx-changelog [filter].
license: MIT
disable-model-invocation: true
compatibility: Requires openspec CLI.
---

Generate CHANGELOG.md from archived OpenSpec changes using Keep a Changelog format.

**IMPORTANT: This skill processes ARCHIVED changes only.** Changes must be archived via `osc-archive-change` (originally `openspec-archive-change`) before they appear in the changelog. Active (unarchived) changes are not included.

**Prerequisite**: Changes must be archived in `openspec/changes/archive/YYYY-MM-DD-<name>/`

---

## Input

Optionally specify filters. If omitted, processes all archived changes.

**Arguments**: `[filter]`

**Examples**:
- `/osx:changelog` - Generate from all archived changes
- `/osx:changelog --since 2025-01-01` - Changes after date
- `/osx:changelog add-dark-mode` - Only specific change(s)

---

## Steps

### 1. Discover archived changes

```bash
find openspec/changes/archive -type d -name "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*" | sort
```

Returns directories like `openspec/changes/archive/2026-02-12-add-dark-mode/`.

### 2. Apply filters

**Date filter** (`--since YYYY-MM-DD`): parse date from directory name (first 10 chars); include only changes after the specified date.

**Specific changes**: filter to only the named change(s); match against the `<name>` portion of directory.

### 3. Read proposal files

For each archived change, read `proposal.md`:

```
openspec/changes/archive/YYYY-MM-DD-<name>/proposal.md
```

Extract from each proposal:
- **## Summary**: First paragraph for changelog entry
- **## Proposed Change**: Detailed description for categorization

If `proposal.md` is missing, check for `design.md` or `tasks.md` as fallback context.

### 4. Categorise changes

Analyse the "## Proposed Change" section for keywords. Category priority (highest wins, first match within priority):

| Category | Keywords | Priority |
|----------|----------|----------|
| Security | security, vulnerability, CVE, critical, exploit | 1 (highest) |
| Breaking | BREAKING, breaking, incompatible, major change | 2 |
| Added | add, create, introduce, new, implement, feature | 3 |
| Changed | modify, update, change, refactor, improve, enhance | 4 |
| Fixed | fix, bug, resolve, correct, error, failure, patch | 5 |
| Removed | remove, delete, deprecate, drop | 6 |
| Deprecated | deprecate, obsolete | 7 |

Example categorisation:
- "Add dark mode support" → Added
- "Fix session timeout handling" → Fixed
- "BREAKING: Migrate to v2 API" → Breaking
- "Patch security vulnerability" → Security (not Fixed)

### 5. Read existing changelog

If `CHANGELOG.md` exists in project root, read current content and identify the latest version header (e.g., `## [1.2.3]`); preserve existing version history. If no changelog exists, will create new one.

### 6. Generate changelog entries

Format in Keep a Changelog structure:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Add dark mode support (add-dark-mode)
- Implement user authentication (add-user-auth)

### Fixed
- Fix session timeout handling (fix-session-timeout)

### Breaking
- **BREAKING**: Migrate to v2 API endpoints (migrate-api)

### Security
- Patch JWT token leak vulnerability (patch-jwt-leak)
```

**Entry format**: hyphen prefix `- `, brief summary from proposal, change reference `(<change-name>)` in parentheses.

### 7. Preview changes

Show user: number of changes processed; categorisation summary (X Added, Y Changed, Z Fixed); preview of generated/updated changelog; ask for confirmation before writing.

### 8. Write changelog

After confirmation:
- Create new `CHANGELOG.md` if it doesn't exist.
- Or update existing `CHANGELOG.md`: new entries go under `## [Unreleased]`; create new section if needed; preserve existing version history.

---

## Output

**Preview**:

```markdown
## Changelog Preview

**Changes to Process**: 5
- Added: 2
- Fixed: 2
- Breaking: 1

### Generated Entries

## [Unreleased]

### Added
- Add dark mode support (add-dark-mode)
- Implement user authentication (add-user-auth)

### Fixed
- Fix session timeout handling (fix-session-timeout)
- Resolve race condition in event handler (fix-race-condition)

### Breaking
- **BREAKING**: Migrate to v2 API endpoints (migrate-api)

---

Write to CHANGELOG.md? [Y/n]
```

**After Writing**:

```markdown
## Changelog Updated

**File**: CHANGELOG.md
**Changes Added**: 5
**Categories**:
- Added: 2
- Fixed: 2
- Breaking: 1

### Next Steps
- Review CHANGELOG.md for accuracy
- Update version header when ready to release
- Commit changelog with release
```

**No Archived Changes**:

```markdown
## No Archived Changes Found

No changes found in `openspec/changes/archive/`.

**To archive changes:**
1. Complete implementation: `/osc-apply-change <name>`
2. Verify implementation: `/osc-verify-change <name>`
3. Archive the change: `/osc-archive-change <name>`
4. Re-run changelog generation: `/osx:changelog`
```

---

## Version Header Guidance

When creating a release, update the version header. Before: `## [Unreleased]` followed by `### Added` etc. After: `## [Unreleased]` (kept empty), then `## [1.2.0] - 2026-02-14` followed by the categories. This skill does NOT automatically version — that's a manual release decision.

---

## Guardrails

- Only process ARCHIVED changes, never active ones
- Require user confirmation before writing to CHANGELOG.md
- Preserve existing changelog content and version history
- Use Keep a Changelog format consistently
- Include change name reference in parentheses for traceability
- If proposal.md is missing, use design.md or tasks.md as fallback
- Don't auto-version - that's a release-time decision
- Sort entries within categories by date (newest first)

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/osx-generate-changelog/SKILL.md
Regenerate: `mise run sync:mirrors`
-->
