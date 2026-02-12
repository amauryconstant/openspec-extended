---
description: Review OpenSpec artifacts for quality, completeness, and consistency
---

Review OpenSpec artifacts (proposal, design, tasks, specs) for quality and completeness.

**Input**: Optionally specify `[change-name] [artifact-id]`. If omitted, infer from context or auto-select.

**Steps**

1. **Select change**
   - If name provided: use it
   - Otherwise: infer from conversation context
   - If only one active change: auto-select it
   - If multiple changes: run `openspec list --json` and use **AskUserQuestion** to let user select

   Always announce: "Reviewing change: <name>" and how to override.

2. **Check status to understand schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse JSON for: schemaName, artifact list.

3. **Select artifact to review**
   - If artifact ID specified: use it
   - Otherwise: if only one artifact has status "ready": auto-select it
   - If user described content (e.g., "the requirements", "the design"): match by name
   - If multiple artifacts ready and no direction: show list and use **AskUserQuestion** to prompt

   When prompting, present artifacts in schema order, showing: artifact ID, status (done/ready/blocked), dependencies count, unlocks count.

4. **Single artifact review workflow**
   1. Identify artifact type (proposal/spec/design/tasks)
   2. Read artifact file
   3. Load `references/review-criteria.md` for that artifact type (from skill)
   4. Check each required section exists
   5. Validate format (headers, scenario levels, checkbox format)
   6. Review content quality (specificity, clarity)
   7. Reference `references/common-issues.md` for known problems (from skill)
   8. Report issues with actionable feedback (line numbers, examples)

5. **Entire change review workflow** (if no artifact specified)
   1. List artifacts: `openspec status --change <name> --json`
   2. Review each artifact using single artifact workflow
   3. **Cross-artifact consistency checks**:
      - proposal Capabilities match specs/ folder structure
      - proposal What Changes covered by tasks.md
      - design.md decisions referenced in tasks
      - All proposal Capabilities have corresponding specs
   4. **Schema compliance**:
      - Validate against schema.yaml requirements
      - Check template format adherence
   5. Prioritize issues: critical (blocking), warning (should fix), suggestion (nice to have)

**Consistency checks:**

- **proposal → specs**: New Capabilities in proposal = specs/ directory names, Modified Capabilities = existing spec names, use kebab-case consistently
- **specs → design**: All ADDED/MODIFIED requirements addressed in design, REMOVED requirements with Migration have migration plan in design
- **design → tasks**: Decisions in design.md have corresponding tasks, Risks in design.md have mitigation tasks, Non-goals in design.md not in tasks.md
- **proposal → tasks**: What Changes items covered by task sections, Impact items considered in tasks

**Report format**

```
## Artifact Review: [artifact-name.md]

### Format: Valid
- All required sections present
- Header format correct

### Issues Found

#### Critical (Must Fix Before Archive)
- **Line X**: [Description]
  - Fix: [Specific action]

#### Warnings (Should Fix)
- **Line X**: [Description]
  - Better: [Suggestion]

#### Suggestions (Nice to Have)
- **Line X**: [Description]
  - Consider: [Alternative]

### Consistency Check
- ✅/❌ [Cross-artifact validation result]
```

**Output**

Display report with prioritized issues.

**Guardrails**

- Check schema compliance for format adherence
- Prioritize issues with clear categories (critical/warning/suggestion)
- Provide specific, actionable feedback with line numbers
- Reference review criteria and common issues from skill

Load the corresponding skill for detailed implementation:

See `.opencode/skills/openspec-review-artifacts/SKILL.md` for:
- Detailed review criteria per artifact type
- Common issues catalog with examples
- Schema validation requirements
- Cross-artifact consistency check logic
