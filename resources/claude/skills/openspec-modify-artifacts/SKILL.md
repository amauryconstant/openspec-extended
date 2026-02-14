---
name: openspec-modify-artifacts
description: Modify an existing artifact in an OpenSpec change. Use during pre-implementation review iteration (after review-artifacts feedback) or during implementation when requirements change. Supports natural language descriptions and targeted edits with dependency tracking.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec-extended
  version: "0.2.0"
---

Modify an existing artifact in an OpenSpec change with dependency-aware updates.

**IMPORTANT: `context` and `rules` from openspec instructions are constraints for YOU, not content for the artifact file.** Do NOT copy `<context>`, `<rules>`, or `<project_context>` blocks into artifacts. These guide what you write but should never appear in output.

---

## Input

Optionally specify a change name and artifact ID. If omitted, the skill will infer from context or prompt for selection.

**Arguments**: `[change-name] [artifact-id]`

**Examples**:
- `/opsx:modify add-auth` - Modify change "add-auth" (will prompt for artifact)
- `/opsx:modify add-auth proposal` - Modify proposal.md in "add-auth"
- "Fix the missing rationale in design decision 2" - Infer from context

---

## Steps

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous: run `openspec list --json` and use the **AskUserQuestion tool** to let the user select

   When showing changes, include: name, schema, status, last modified. Mark the most recently modified as "(Recommended)".

   Always announce: "Using change: <name>" and how to override (e.g., `/opsx:modify <other> <artifact>`).

2. **Check change status**

   ```bash
   openspec status --change "<name>" --json
   ```

   Parse the JSON to understand:
   - `schemaName`: The workflow being used (e.g., "spec-driven")
   - `artifacts`: Array of artifacts with status (done/ready/blocked)
   - `isComplete`: Whether all artifacts are done

3. **Select artifact to modify**

   If an artifact ID is specified, use it. Otherwise:
   - If only one artifact has status "ready": auto-select it
   - If user described content (e.g., "the requirements", "the design"): match by name
   - If multiple artifacts ready and no direction: use the **AskUserQuestion tool** to prompt

   When prompting, present artifacts in schema order, showing:
   - Artifact ID
   - Status (done/ready/blocked)
   - Dependencies count
   - Unlocks count

4. **Get modification context**

   ```bash
   openspec instructions <artifact-id> --change "<name>" --json
   ```

   Parse the JSON to extract:
   - `rules`: Validation rules for this artifact (constraints for you)
   - `context`: Project background (constraints for you)
   - `template`: Expected structure
   - `dependencies`: Artifacts this artifact depends on
   - `unlocks`: Artifacts that depend on this one
   - `outputPath`: Where the artifact file is located
   - `instruction`: Schema-specific guidance

   **Read the current artifact file** from `outputPath`.

5. **Detect workflow scenario**

   Check conversation context for review feedback:
   - If user references review-artifacts output or specific issue numbers → **Review Iteration Mode**
   - If user describes new requirements or changes discovered during coding → **Amendment Mode**

   **Review Iteration Mode**:
   - Focus on specific issues identified in review
   - Validate fixes against the review criteria
   - After modification, suggest re-running review-artifacts

    **Amendment Mode**:
    - Focus on capturing requirement changes
    - Consider impact on existing implementation
    - After modification, suggest running `/opsx:apply <name>`

6. **Display validation constraints**

   Show the user:
   - `rules` array (as constraints, not content)
   - `dependencies` list (what this artifact relies on)
   - `unlocks` list (what artifacts depend on this)

7. **Determine modification mode**

   **Mode A: Describe Changes** - Use when user provides natural language:
   - "Add a requirement for..."
   - "Update the design to..."
   - "Remove this section..."

   **Mode B: Interactive Edit** - Use when user references specific content:
   - "Change line 42 to..."
   - "Replace the second paragraph..."
   - "Update the authentication section..."

   Auto-select based on input type. No explicit prompt needed.

8. **Apply modifications**

   **Mode A (Describe Changes)**:
   - Parse user's description
   - Analyze current artifact content
   - Identify which sections need changes
   - Apply changes autonomously if clear
    - If ambiguous: pause and ask for clarification using **AskUserQuestion tool**

   **Mode B (Interactive Edit)**:
   - Parse entire artifact file
   - Identify relevant sections based on user's edit intent
   - Show only those sections (not the entire file)
   - User provides specific edit instructions
   - Apply targeted changes using Edit tool
   - If more sections need changes, repeat

9. **Validate modifications**

   Check proposed changes against:
   
   a) The `rules` array from step 4 (structural/format requirements)
   
   b) **If in Review Iteration Mode**: The specific issues from review-artifacts feedback
   
   c) **If in Amendment Mode**: Backward compatibility with implementation

   Handle validation results:
   - Clear/fixable violations → Fix automatically and continue
   - Ambiguous violations → Explain issue and ask user
   - If user's intent is clear despite violation → Proceed with warning

   Note: Use `rules` from instructions. Do NOT run `openspec validate`.

10. **Write the updated artifact file**

    Use Edit tool for targeted changes, Write tool for complete rewrites. Verify the file was written successfully.

11. **Handle dependent artifacts**

    From the instructions output, check the `unlocks` array (reverse dependencies).

    **For each artifact in `unlocks`**:
    - Run `openspec instructions <dependent-id> --change "<name>" --json`
    - Read the dependent artifact file
    - Analyze if the modification affects this dependent artifact
    - Track affected artifacts

     **Decision logic** (prefer reasonable decisions):
     - **Single dependent affected**: Auto-update and explain (no prompt)
     - **Multiple dependents affected**: Show the list and prompt for confirmation
     - **User mentioned "cascade"**: Auto-update regardless of count

12. **Show success summary**

    Display:
    - Which artifact was modified
    - Changes applied (summary)
    - Dependent artifacts updated
    - Context-aware next steps based on scenario

---

## Output

**On Success**:

```
## Modification Complete

**Change:** <name>
**Artifact:** <artifact-id>
**Mode:** [Review Iteration / Amendment]

### Changes Applied
- [Section]: [Action] - [Summary]

### Dependent Artifacts Updated
- [x] <artifact-id>: [Summary]

### Next Steps
**Pre-implementation review:**
- Continue with: [next flagged artifact if any]
- Verify fixes: `/opsx:review <name>`
- Ready to implement: `/opsx:apply <name>` after review passes

**Implementation phase:**
- Sync changes: `/opsx:apply <name>`
- Check tests: [affected test files if known]
```

**On Pause (Ambiguous Input)**:

```
## Modification Paused

**Issue:** <description of ambiguity>

**Options:**
1. <option 1>
2. <option 2>
3. Describe differently

What would you like to do?
```

---

## Guardrails

- Always read current artifact before modifying
- Check dependents before finalizing changes
- Use `rules` from instructions for validation (not CLI validate command)
- Use Edit for targeted changes, Write for complete rewrites
- Prefer reasonable decisions to keep momentum (0-1 dependents → auto-update)
- Pause and ask for clarification if unable to act autonomously
- Follow schema order for artifact selection
- Never copy `context`, `rules`, or `project_context` blocks into artifact files
