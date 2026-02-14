---
description: Modify artifacts in OpenSpec changes with dependency tracking
license: MIT
metadata:
  author: openspec-extended
  version: "0.2.0"
---

Modify existing artifacts in an OpenSpec change, automatically tracking and updating dependent artifacts.

---

## Input

Optionally specify `[change-name] [artifact-id]` after `/opsx:modify`. If omitted, the AI will infer from context or prompt for selection.

**Patterns**:
| Input | Behavior |
|-------|----------|
| `/opsx:modify add-auth proposal` | Direct: use specified change and artifact |
| `/opsx:modify add-auth` | Change specified, auto-select artifact |
| `/opsx:modify` | Infer from context or prompt for both |

---

## Steps

1. **Select the change**

   If name provided: use it. Otherwise:
   - Infer from conversation context
   - Auto-select if only one active change
   - If ambiguous: run `openspec list --json` and use **Ask** to prompt

   Announce: "Using change: <name>" and how to override.

2. **Check change status**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse JSON for: schemaName, artifacts with status (done/ready/blocked).

3. **Select artifact to modify**

   If artifact ID specified: use it. Otherwise:
   - Auto-select if only one artifact has status "ready"
   - Match by name if user described content (e.g., "the requirements")
   - Prompt if multiple ready and no direction

   Present in schema order showing: ID, status, dependencies, unlocks.

4. **Get modification context**
   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```
   Extract: rules, context, template, dependencies, unlocks, outputPath.

   **Read the current artifact file** from outputPath.

5. **Determine modification mode**

   - **Mode A - Describe Changes**: User provides natural language → apply autonomously if clear, ask if ambiguous
   - **Mode B - Interactive Edit**: User references specific content → show relevant sections, apply targeted edits

   Auto-select based on input type.

6. **Apply modifications**

   Validate against `rules` from step 4:
   - Clear violations → fix automatically
   - Ambiguous violations → ask user
   - Clear intent despite violation → proceed with warning

   Use Edit tool for targeted changes, Write for complete rewrites.

7. **Handle dependent artifacts**

   Check `unlocks` array from instructions. For each dependent:
   - Read the dependent artifact
   - Analyze if modification affects it
   - Track affected artifacts

   **Decision logic**:
   - 0-1 affected: Auto-update and explain
   - 2+ affected: Show list and prompt
   - User said "cascade": Auto-update all

8. **Display summary**

---

## Output

```
## Modification Complete

**Change:** <name>
**Artifact:** <artifact-id>

### Changes Applied
- [Section]: [Action] - [Summary]

### Dependent Artifacts Updated
- [x] <artifact-id>: [Summary]

### Next Steps
- Ready to implement: `/opsx:apply <name>`
- Continue modifying: [describe next artifact]
```

---

## Guardrails

- Always read current artifact before modifying
- Check dependents before finalizing
- Use `rules` from instructions for validation (not `openspec validate`)
- Use Edit for targeted changes, Write for complete rewrites
- Prefer reasonable decisions (0-1 dependents → auto-update)
- **IMPORTANT**: `context` and `rules` are constraints for YOU, not content for the file

---

See `.claude/skills/openspec-modify-artifacts/SKILL.md` for detailed implementation logic.
