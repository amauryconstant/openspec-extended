---
description: Update AGENTS.md and CLAUDE.md documentation to sync with available skills
---

Maintain AI coding assistant documentation files to keep them synchronized with available skills.

**Input**: Optionally specify `[file-path]` to update specific file. If omitted, scan and update all documentation files.

**Steps**

1. **Detect documentation files**
   ```bash
   # Check for AGENTS.md
   test -f AGENTS.md && echo "AGENTS.md found" || echo "AGENTS.md not found"

   # Check for CLAUDE.md
   test -f CLAUDE.md && echo "CLAUDE.md found" || echo "CLAUDE.md not found"
   ```

   Report which files were detected.

2. **Read current documentation** for each detected file:
   - Parse skills list sections
   - Extract quick reference tables
   - Preserve existing content structure

   **Key sections to preserve**:
   - Skills Distributed (list of skills with descriptions)
   - Quick Reference (if exists)
   - Project Context / Overview
   - Any project-specific sections

3. **Scan available skills** from `.opencode/skills/openspec-*`:
   ```bash
   # List OpenSpec skills
   find .opencode/skills/openspec-* -type f -name "SKILL.md" | sort
   ```

   For each skill:
   - Parse SKILL.md frontmatter (name, description, license, version)
   - Extract skill summary
   - Build skills metadata

4. **Identify discrepancies** comparing detected skills vs. documented skills:

   **Types of discrepancies**:
   - **Missing in docs**: Skill exists but not documented
   - **Outdated entries**: Documented skill has wrong description or outdated info
   - **Orphaned entries**: Documented skill no longer exists
   - **Version mismatch**: Documented version doesn't match SKILL.md

   **Discrepancy report format**:
   ```markdown
   ## Documentation Discrepancies

   ### Missing in Documentation
   - `openspec-new-skill`: Not listed in Skills Distributed section

   ### Outdated Entries
   - `openspec-review-artifacts`: Description needs update (current: "Reviews artifacts" - should be: "Reviews artifacts for quality...")

   ### Orphaned Entries
   - `openspec-old-skill`: Documented but no longer exists
   ```

5. **Update documentation** for each discrepancy:

   **For missing skills**:
   - Add entry to Skills Distributed section
   - Follow existing format (alphabetical or grouped)
   - Include name, description, and brief purpose

   **For outdated entries**:
   - Update description to match SKILL.md frontmatter
   - Update version if specified
   - Preserve any notes or context

   **For orphaned entries**:
   - Remove entry from documentation
   - Optionally archive to "Deprecated Skills" section

6. **Validate changes** before writing:
   - Check markdown formatting
   - Verify no duplicate entries
   - Confirm skill names are links to actual skill directories
   - Ensure consistency across all documentation files

7. **Preview and confirm**:
   Show user:
   - Summary of changes (X added, Y updated, Z removed)
   - Diff view or detailed change list
   - Ask for confirmation using AskUserQuestion

8. **Write to files** if confirmed.

**Output**

After confirmation, display:
```
## Documentation Updated

**Files Modified**:
- `AGENTS.md`: X skills added, Y skills updated, Z skills removed

**Summary**:
- Skills Distributed section now reflects current state
- Quick Reference updated if applicable
- All discrepancies resolved

**Next Steps**:
- Run `openspecx init <tool>` to reinstall updated skills
- Commit changes to version control
```

**Guardrails**

- Preserve existing documentation structure (don't reorganize entire file)
- Update targeted sections only
- Add context: include brief descriptions for each skill's purpose
- Version tracking: document skill versions if specified in frontmatter
- Consistency: use same format across AGENTS.md and CLAUDE.md
- Confirm before writing: show summary and ask for confirmation
- Validate: check formatting, duplicates, skill name accuracy

Load the corresponding skill for detailed implementation:

See `.opencode/skills/openspec-maintain-ai-docs/SKILL.md` for:
- Documentation file detection patterns
- Skill metadata extraction from SKILL.md
- Discrepancy detection logic
- Dry run mode support
- Custom skills directory option
