---
name: openspec-modify-artifacts
description: Modify existing artifacts in OpenSpec changes. Use when updating specs, design, proposal, or tasks during or after change creation. Supports natural language descriptions and targeted edits with dependency tracking. Uses inference to reduce prompts when context is clear.
license: MIT
argument-hint: "[change-name] [artifact-id]"
allowed-tools: "Bash,Edit,Write,AskUserQuestion"
metadata:
  author: openspec-extended
  version: "0.1.1"
---

Modify an existing artifact in an OpenSpec change.

**Input**: Optionally specify a change name. If omitted, the skill will try to infer from conversation context or auto-select if only one active change exists.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Try to infer from conversation context if the user mentioned a change
   - If only one active change exists: auto-select it
   - If multiple active changes and no inference: run `openspec list --json` and use the **AskUserQuestion tool** to let the user select

   When showing changes, include: name, schema, status, last modified. Mark the most recently modified as "(Recommended)".

   Always announce: "Using change: <name>" and how to override (e.g., "/opsx:modify-artifact <change> <artifact>")

2. **Check change status**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used (e.g., "spec-driven")
   - `artifacts`: Array of artifacts with status (done/ready/blocked)
   - `isComplete`: Whether all artifacts are done
   - `applyRequires`: Artifacts needed before implementation

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
   - `rules`: Validation rules for this artifact
   - `context`: Project background (constraints for you - do NOT include in output)
   - `template`: Expected structure
   - `dependencies`: Artifacts this artifact depends on
   - `unlocks`: Artifacts that depend on this one
   - `outputPath`: Where the artifact file is located
   - `instruction`: Schema-specific guidance

   **Read the current artifact file** from `outputPath`.

5. **Display validation constraints**

   Show the user:
   - `rules` array (as constraints, not content)
   - `dependencies` list (what this artifact relies on)
   - `unlocks` list (what artifacts depend on this)

6. **Determine modification mode**

   **Mode A: Describe Changes** - Use when user provides natural language:
   - "Add a requirement for..."
   - "Update the design to..."
   - "Remove this section..."

   **Mode B: Interactive Edit** - Use when user references specific content:
   - "Change line 42 to..."
   - "Replace the second paragraph..."
   - "Update the authentication section..."

   Decision: Auto-select based on input type. No explicit prompt needed.

7. **Apply modifications based on mode**

   **Mode A (Describe Changes)**:
   - Parse user's description
   - Analyze current artifact content
   - Identify which sections need changes
   - Apply changes autonomously if clear
   - If ambiguous or uncertain: pause and ask for clarification using AskUserQuestion

   **Mode B (Interactive Edit)**:
   - Parse entire artifact file
   - Identify relevant sections based on user's edit intent
   - Show only those sections (not the entire file)
   - User provides specific edit instructions
   - Apply targeted changes using Edit tool
   - If more sections need changes, repeat

8. **Validate modifications**

   Check the proposed changes against the `rules` array from step 4 (`openspec instructions` output):

   1. Identify any rule violations
   2. Clear/fixable violations → Fix automatically and continue
   3. Ambiguous violations → Explain issue and ask user
   4. If user's intent is clear despite violation → Proceed with warning

   Note: Use the `rules` from instructions, do NOT run `openspec validate`.

9. **Write the updated artifact file**

   Use Edit tool for targeted changes, Write tool for complete rewrites.

   Verify the file was written successfully.

10. **Handle dependent artifacts**

     From the instructions output, check the `unlocks` array (reverse dependencies).

     **For each artifact in `unlocks`**:
     - Run `openspec instructions <dependent-id> --change "<name>" --json`
     - Read the dependent artifact file
     - Analyze if the modification affects this dependent artifact
     - Track affected artifacts

     **Decision logic** (prefer reasonable decisions):
     - **0-1 affected**: Auto-update and explain (no prompt)
     - **2+ affected**: Show the list and prompt for confirmation
     - **User mentioned "cascade"**: Auto-update regardless of count

     **When auto-updating**:
     - Apply the same modification principles
     - Summarize changes after all updates complete
     - Mark dependent artifacts as modified

11. **Show success summary**

     Display:
     - Which artifact was modified
     - Changes applied (summary)
     - Dependent artifacts updated
     - Next steps: "Run `/opsx:apply <name>` to re-sync implementation with updated artifacts" or "Continue modifying other artifacts"

**Output**

After completion, show:

```
## Modification Complete

**Change:** <name>
**Artifact:** <artifact-id>

### Changes Applied
- [Section]: [Action] - [Summary]

### Dependent Artifacts Updated
- [✓] <artifact-id>: [Summary]

### Next Steps
- Ready to implement: `/opsx:apply <name>`
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
  - Do NOT copy `<context>`, `<rules>`, `<project_context>` blocks into the artifact
  - These guide what you write, but should never appear in the output
