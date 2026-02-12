---
description: Generate changelogs in Keep a Changelog format from archived OpenSpec changes
---

Generate changelogs from archived OpenSpec changes.

**Input**: Specify scope with one of:

Required (if no flags, defaults to `--all`):
- `--all`: Process all archived changes
- `--since <date>`: Only changes after specified date
- `--until <date>`: Only changes before specified date
- `--changes <list>`: Specific changes by name (comma-separated)

Optional:
- `--output <path>`: Custom output file path
- `--dry-run`: Preview without writing

**Steps**

1. **Discover archived changes** from `openspec/changes/archive/`:
   ```bash
   find openspec/changes/archive -type d -name "YYYY-MM-DD-*" | sort
   ```

   **Change directory format**: `YYYY-MM-DD-<change-name>/`

2. **Filter changes** based on input flags:
   - `--all`: Include all archived changes
   - `--since <date>`: Filter by date prefix (YYYY-MM-DD)
   - `--until <date>`: Filter by date prefix (YYYY-MM-DD)
   - `--changes <list>`: Match specific change names after date prefix

3. **Parse proposal files** for each selected change and extract:
   ```markdown
   ## Summary

   <brief description>

   ## Proposed Change

   <detailed description of what changed>
   ```

   **Key sections to extract**:
   - **## Summary** → Changelog entry summary
   - **## Proposed Change** → Change details and categorization

4. **Categorize changes** by analyzing "## Proposed Change" section for keywords:

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

   **User override**: Prompt for category confirmation if needed, provide option to reclassify manually.

5. **Generate changelog** in Keep a Changelog format:

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

6. **Update existing CHANGELOG.md**:
   1. **Detect current version**: Look for `## [Version]` headers, identify latest version number
   2. **Move unreleased to version**: If `## [Unreleased]` has entries, create new version section `## [1.2.3]`, move unreleased entries to new version
   3. **Update release date**: Add release date: `## [1.2.3] - 2026-02-12`

   **If creating new changelog**: Start with `## [Unreleased]`, no version header until first release.

7. **Preview and confirm**:
   Show user:
   - Number of changes processed
   - Categorization summary (X Added, Y Changed, Z Fixed)
   - Preview of generated changelog
   - Ask for confirmation using AskUserQuestion before writing

8. **Write to file**:
   - Default output: `CHANGELOG.md` in project root
   - User-specified: Custom path via `--output`
   - Verify file was written successfully

**Output**

After confirmation, display:
```
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
```

**Advanced Usage**

- **Dry run**: `openspec-generate-changelog --all --dry-run` - Preview changes without writing
- **Custom templates**: Use project-specific changelog format via references/ templates
- **Date filters**: `openspec-generate-changelog --since 2026-01-01 --until 2026-01-31`
- **Change selection**: `openspec-generate-changelog --changes add-dark-mode,update-auth-flow`

**Guardrails**

- Follow Keep a Changelog format specification
- Handle missing proposal.md gracefully (infrastructure-only changes)
- Use concise entries (1-2 sentences for user-facing docs)
- Version tracking: follow semantic versioning when creating version headers
- Breaking changes: highlight prominently with `**BREAKING**` marker
- Link references: include issue/PR numbers when possible
- Confirm before writing: show preview and ask user

Load the corresponding skill for detailed implementation:

See `.opencode/skills/openspec-generate-changelog/SKILL.md` for:
- Detailed change discovery patterns
- Proposal parsing guidelines
- Keyword categorization algorithm
- Version management and release dates
