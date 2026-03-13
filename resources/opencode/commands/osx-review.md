---
description: Review OpenSpec artifacts for quality, completeness, and consistency
license: MIT
---

## Tools Available

| Tool | Type | Usage |
|------|------|-------|
| `openspec` | Upstream CLI | `openspec <command> [options]` - npm package |
| `osx ctx` | Local script | `.opencode/scripts/lib/osx ctx get <change>` - load change context |

Review OpenSpec artifacts (proposal, design, tasks, specs) for quality and completeness.

---

## Input

Optionally specify `[change-name] [artifact-id]` after `/osx-review`. If omitted, the AI will infer from context or prompt for selection.

**Patterns**:
| Input | Behavior |
|-------|----------|
| `/osx-review add-auth proposal` | Review specific artifact in specific change |
| `/osx-review add-auth` | Review entire change (all artifacts) |
| `/osx-review` | Infer from context or prompt |

---

## Steps

1. **Select the change**

   If name provided: use it. Otherwise:
   - Infer from conversation context
   - Auto-select if only one active change
   - If ambiguous: run `openspec list --json` and use **AskUserQuestion** to prompt

   Announce: "Reviewing change: <name>" and how to override.

2. **Check status to understand schema** (Optional) 
    ```bash
    .opencode/scripts/lib/osx ctx get "<name>"
    ```
    - Parse JSON for: state (phase, iteration), artifacts with existence info.
    - Bypass if the call returns nothing or an error.

3. **Select artifact to review**

   If artifact ID specified: review that one. Otherwise:
   - Review all artifacts in schema order
   - For each artifact, read and validate

4. **Single artifact review**

   For each artifact:
   - Identify type (proposal/spec/design/tasks)
   - Read artifact file
   - Check required sections exist
   - Validate format (headers, scenario levels, checkbox format)
   - Review content quality (specificity, clarity)
   - Report issues with line numbers

5. **Cross-artifact consistency checks**

   When reviewing entire change:
   - proposal Capabilities match specs/ folder structure
   - proposal What Changes covered by tasks.md
   - design.md decisions referenced in tasks
   - All proposal Capabilities have corresponding specs

6. **Prioritize and report**

   Categories:
   - **Critical**: Must fix before archive
   - **Warning**: Should fix
   - **Suggestion**: Nice to have

---

## Output

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
- [x]/[ ] [Cross-artifact validation result]
```

---

## Guardrails

- Check schema compliance for format adherence
- Prioritize issues with clear categories
- Provide specific, actionable feedback with line numbers
- For cross-artifact checks, explain dependencies clearly

---

See `.opencode/skills/osx-review-artifacts/SKILL.md` for detailed review criteria and common issues catalog.
