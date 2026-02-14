---
description: Generate changelogs in Keep a Changelog format from archived OpenSpec changes
---

Generate changelogs from archived OpenSpec changes in Keep a Changelog format.

**IMPORTANT**: This is an AI-guided workflow. It does not use CLI flags. All filtering is done through user interaction.

---

## Input

No arguments required. The AI will guide you through scope selection.

---

## Steps

1. **Discover archived changes**
   ```bash
   find openspec/changes/archive -type d -name "????-??-??-*" | sort
   ```
   
   Change directory format: `YYYY-MM-DD-<change-name>/`

2. **Prompt for scope selection**

   If multiple archived changes exist, use **Ask** to ask:
   - All archived changes
   - Changes since a specific date
   - Specific changes by name

   Present options with counts (e.g., "12 changes from 2025-01-15 to 2026-02-14").

3. **Parse proposal files**

   For each selected change, read `proposal.md` and extract:
   - **## Summary** → Changelog entry summary
   - **## Proposed Change** → Change details and categorization

4. **Categorize changes**

   Analyze "## Proposed Change" section for keywords:

   | Category | Keywords |
   |----------|----------|
   | Added | add, create, introduce, new, implement |
   | Changed | modify, update, change, refactor, improve |
   | Fixed | fix, bug, resolve, correct, error |
   | Removed | remove, delete, deprecate, drop |
   | Breaking | BREAKING, break, incompatible, major |
   | Security | security, vulnerability, CVE, patch |

   Multi-category: Use most significant (Security > Breaking > Fixed > others).

5. **Generate changelog entries**

   Format: `- <description> (<change-name>)`

   Example:
   ```markdown
   ### Added
   - Add dark mode support (add-dark-mode)

   ### Fixed
   - Fix session timeout handling (fix-session-timeout)

   ### Breaking
   - **BREAKING**: API endpoint /v1/users is now /v2/users (migrate-users)
   ```

6. **Preview and confirm**

   Show user:
   - Number of changes processed
   - Categorization summary (X Added, Y Changed, Z Fixed)
   - Preview of generated entries

   Use **Ask** to confirm before writing.

7. **Update or create CHANGELOG.md**

   If exists:
   - Detect current version from `## [Version]` headers
   - Add new entries to `## [Unreleased]` section
   
   If not exists:
   - Create new file with Keep a Changelog header
   - Start with `## [Unreleased]`

   Use Write tool for new files, Edit for updates.

---

## Output

```
## Changelog Generated

**Changes Processed**: 12
- Added: 5
- Changed: 3
- Fixed: 3
- Removed: 1

**Preview**:

## [Unreleased]

### Added
- Add dark mode support (add-dark-mode)
- Implement user authentication (add-user-auth)

### Fixed
- Fix session timeout (fix-session-timeout)

**Output File**: CHANGELOG.md
```

---

## Guardrails

- Follow Keep a Changelog format specification
- Handle missing proposal.md gracefully (infrastructure-only changes)
- Use concise entries (1-2 sentences)
- Breaking changes: highlight with `**BREAKING**` marker
- Link references: include issue/PR numbers when available
- Confirm before writing: always show preview and ask user
- Preserve existing changelog content when updating

---

See `.claude/skills/openspec-generate-changelog/SKILL.md` for detailed categorization algorithm and version management.
