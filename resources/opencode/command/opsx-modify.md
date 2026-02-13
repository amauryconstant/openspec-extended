---
description: Modify artifacts in OpenSpec changes with dependency tracking
---

Modify existing artifacts in an OpenSpec change.

**Input**: Optionally specify `[change-name] [artifact-id]`. If omitted, infer from conversation context or auto-select when unambiguous.

**Steps**

1. **Select change**
   - If name provided: use it
   - Otherwise: infer from conversation context
   - If only one active change: auto-select it
   - If multiple changes and no inference: run `openspec list --json` and use **AskUserQuestion** to let user select

   Always announce: "Using change: <name>" and how to override (e.g., `/opsx-modify <change> <artifact>`).

2. **Check change status**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse JSON to understand: schemaName, artifacts with status (done/ready/blocked), isComplete, applyRequires.

3. **Select artifact to modify**
   - If artifact ID specified: use it
   - Otherwise: auto-select if only one artifact has status "ready"
   - If user described content (e.g., "the requirements"): match by name
   - If multiple artifacts ready and no direction: use **AskUserQuestion** to prompt

   When prompting, present artifacts in schema order, showing: artifact ID, status, dependencies count, unlocks count.

4. **Get modification context**
   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```
   Parse JSON to extract: rules, context, template, dependencies, unlocks, outputPath, instruction.

   **Read the current artifact file** from `outputPath`.

5. **Display validation constraints**
   Show user: rules array, dependencies list, unlocks list.

6. **Determine modification mode**

   **Mode A - Describe Changes**: Use when user provides natural language (e.g., "Add a requirement for...", "Update design to...").
   - Parse user's description
   - Analyze current artifact content
   - Identify which sections need changes
   - Apply changes autonomously if clear
   - If ambiguous or uncertain: pause and ask for clarification using AskUserQuestion

   **Mode B - Interactive Edit**: Use when user references specific content (e.g., "Change line 42 to...", "Replace the second paragraph...").
   - Parse entire artifact file
   - Identify relevant sections based on user's edit intent
   - Show only those sections (not entire file)
   - User provides specific edit instructions
   - Apply targeted changes using Edit tool
   - If more sections need changes, repeat

   Decision: Auto-select based on input type. No explicit prompt needed.

7. **Apply modifications** based on selected mode.

8. **Validate modifications**
   Check proposed changes against `rules` array from step 4:
   1. Identify any rule violations
   2. Clear/fixable violations → Fix automatically and continue
   3. Ambiguous violations → Explain issue and ask user
   4. If user's intent is clear despite violation → Proceed with warning

   Note: Use the `rules` from instructions, do NOT run `openspec validate`.

9. **Write the updated artifact file**
   Use Edit tool for targeted changes, Write tool for complete rewrites.
   Verify file was written successfully.

10. **Handle dependent artifacts**
    From the instructions output, check `unlocks` array (reverse dependencies).

    **For each artifact in `unlocks`**:
    - Run `openspec instructions <dependent-id> --change "<name>" --json`
    - Read the dependent artifact file
    - Analyze if modification affects this dependent artifact
    - Track affected artifacts

    **Decision logic** (prefer reasonable decisions):
    - **0-1 affected**: Auto-update and explain (no prompt)
    - **2+ affected**: Show the list and prompt for confirmation
    - **User mentioned "cascade"**: Auto-update regardless of count

    **When auto-updating**:
    - Apply the same modification principles
    - Summarize changes after all updates complete
    - Mark dependent artifacts as modified

**Output**

After completion, display:
```
## Modification Complete

**Change:** <name>
**Artifact:** <artifact-id>

### Changes Applied
- [Section]: [Action] - [Summary]

### Dependent Artifacts Updated
- [✓] <artifact-id>: [Summary]

### Next Steps
- Ready to implement: `/opsx-apply <name>`
- Continue modifying: [describe next artifact]
```

**Guardrails**

- Always read current artifact before modifying
- Check dependents before finalizing changes
- Use `rules` from instructions for validation (not CLI validate command)
- Use Edit for targeted changes, Write for complete rewrites
- Prefer reasonable decisions to keep momentum (0-1 dependents → auto-update)
- Pause and ask for clarification if unable to act autonomously
- Follow schema order for artifact selection
- IMPORTANT: `context` and `rules` are constraints for YOU, not content for the file
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into artifact
  - These guide what you write, but should never appear in the output

Load the corresponding skill for detailed implementation:

See `.opencode/skills/openspec-modify-artifacts/SKILL.md` for:
- Detailed inference logic and auto-selection behavior
- Complete modification modes and workflows
- Validation against rules
- Dependent artifact cascade update logic
