---
name: openspec-generate-changelog
description: Generate changelogs in Keep a Changelog format from archived OpenSpec changes. Use when publishing releases, generating user-facing documentation, or creating release notes.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec-extended
  version: "0.1.0"
---

# Changelog Generation

Generate changelogs from archived OpenSpec changes using Keep a Changelog format.

## When to Use

- Before publishing a release
- When generating release notes for users
- When creating version summaries
- After completing significant milestone
- As part of documentation generation workflow

## Quick Reference

| Option | Description | Example |
|---------|-------------|----------|
| `--all` | Process all archived changes | `openspec-generate-changelog --all` |
| `--since <date>` | Only changes after specified date | `openspec-generate-changelog --since 2025-01-01` |
| `--until <date>` | Only changes before specified date | `openspec-generate-changelog --until 2025-12-31` |
| `--changes <list>` | Specific changes by name | `openspec-generate-changelog --changes add-dark-mode,fix-login-bug` |
| `--output <path>` | Custom output file path | `openspec-generate-changelog --output docs/RELEASE_NOTES.md` |

## Workflow

### 1. Discover Archived Changes

Scan `openspec/changes/archive/` directory for archived changes:

```bash
# List archived changes (sorted by date)
find openspec/changes/archive -type d -name "YYYY-MM-DD-*" | sort
```

**Change directory format**: `YYYY-MM-DD-<change-name>/`

### 2. Parse Proposal Files

For each change, read `proposal.md` and extract:

```markdown
## Summary

<brief description>

## Proposed Change

<detailed description of what changed>
```

**Key sections to extract**:
- **## Summary** → Changelog entry summary
- **## Proposed Change** → Change details and categorization

### 3. Categorize Changes

Analyze "## Proposed Change" section for keywords:

**Default categorization** (auto):
```markdown
### Added
- Keywords: "add", "create", "introduce", "new", "implement"

### Changed
- Keywords: "modify", "update", "change", "refactor", "improve", "enhance"

### Fixed
- Keywords: "fix", "bug", "resolve", "correct", "error", "failure"

### Removed
- Keywords: "remove", "delete", "deprecate", "drop"

### Breaking
- Keywords: "BREAKING", "break", "breaking", "incompatible", "major"

### Security
- Keywords: "security", "vulnerability", "cve", "patch", "critical", "CVE"
```

**Multi-category detection**:
- Changes with multiple category keywords → Most significant category
- Example: "fix security vulnerability" → Security (not Fixed)

**User override**:
- Prompt for category confirmation if needed
- Provide option to reclassify manually

### 4. Generate Changelog

Use Keep a Changelog format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Add dark mode support (add-dark-mode)

### Changed
- Update API authentication flow (update-auth-flow)

### Fixed
- Fix session timeout handling (fix-session-timeout)

### Removed
- Remove legacy export feature (remove-legacy-export)

### Breaking
- **BREAKING**: API endpoint /v1/users is now /v2/users (migrate-users)

### Security
- **Security**: Patch JWT token leak vulnerability (patch-jwt-leak)
```

**Entry format**:
- Hyphen prefix (-) before each entry
- Change name in parentheses (optional, for reference)
- Description of the change
- References to related issues/PRs (optional)

### 5. Update Existing Changelog

If `CHANGELOG.md` exists:

1. **Detect current version**
   - Look for `## [Version]` headers
   - Identify latest version number

2. **Move unreleased to version**
   - If `## [Unreleased]` has entries
   - Create new version section: `## [1.2.3]`
   - Move unreleased entries to new version

3. **Update release date**
   - Add release date: `## [1.2.3] - 2026-02-12`

**If creating new changelog**:
- Start with `## [Unreleased]`
- No version header until first release

### 6. Write Output

Default output: `CHANGELOG.md` in project root

User-specified: Custom path via `--output`

### 7. Preview and Confirm

Show user:

- Number of changes processed
- Categorization summary (X Added, Y Changed, Z Fixed)
- Preview of generated changelog
- Ask for confirmation before writing

## Output

```markdown
## Changelog Generated

**Changes Processed**: 12
- Added: 5
- Changed: 3
- Fixed: 3
- Removed: 1

**Preview**:

# Changelog

## [Unreleased]

### Added
- Add dark mode support
- Implement user authentication

### Fixed
- Fix session timeout

**Output File**: CHANGELOG.md

Write to file? [y/N]
```

## Advanced Usage

### Dry Run

Preview changes without writing:

```bash
openspec-generate-changelog --all --dry-run
```

### Custom Templates

Use project-specific changelog format via references/ templates:

```bash
openspec-generate-changelog --template custom-changelog.md
```

### Date Filters

Process changes within date range:

```bash
# Changes from January 2026 only
openspec-generate-changelog --since 2026-01-01 --until 2026-01-31

# Changes since last release
openspec-generate-changelog --since $(git log -1 --format=%ai --date=short)
```

### Change Selection

Generate changelog for specific changes:

```bash
# Only specific changes
openspec-generate-changelog --changes add-dark-mode,update-auth-flow

# Combine with date filter
openspec-generate-changelog --changes add-dark-mode --since 2026-01-01
```

## Troubleshooting

**No archived changes found**:
- Check `openspec/changes/archive/` directory exists
- Verify changes are in `YYYY-MM-DD-<name>` format
- Run without `--all` flag for current changes

**Category seems wrong**:
- Manually reclassify using skill
- Override category by editing changelog after generation
- Check proposal.md "## Proposed Change" section for context

**Missing proposal.md**:
- Change may be infrastructure-only (no spec modifications)
- Use design.md or tasks.md for context
- Mark as "Infrastructure update" in changelog

## Best Practices

- **Release-driven**: Generate changelog as part of release process
- **One truth**: Keep CHANGELOG.md as source of truth, don't have multiple copies
- **Version tracking**: Follow semantic versioning when creating version headers
- **Breaking changes**: Highlight breaking changes prominently with `**BREAKING**` marker
- **Link references**: Include issue/PR numbers when possible
- **Concise entries**: Each entry should be 1-2 sentences for user-facing docs

## References

See `references/changelog-format.md` for detailed Keep a Changelog specification.

See `references/proposal-parsing-guide.md` for parsing guidelines based on OpenSpec proposal format.

See `references/example-output.md` for sample generated changelogs.
