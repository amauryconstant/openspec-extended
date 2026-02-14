---
name: openspec-review-artifacts
description: Review OpenSpec artifacts for feasibility, correctness, completeness, and implementation-readiness. Use BEFORE implementation to validate the plan is sound, or during artifact creation to check quality. Part of pre-implementation workflow: review-artifacts → modify-artifacts → apply.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec-extended
  version: "0.2.0"
---

Review OpenSpec artifacts for feasibility, correctness, completeness, and implementation-readiness.

**IMPORTANT: This skill is for reviewing BEFORE implementation begins.** Do not use after apply-change. For post-implementation verification, use openspec-verify-change instead.

---

## Input

Optionally specify a change name. If omitted, the skill will infer from context or prompt for selection.

**Arguments**: `[change-name] [artifact-type]`

**Examples**:
- `/opsx-review add-auth` - Review all artifacts in "add-auth"
- `/opsx-review add-auth proposal` - Review only proposal.md
- "Review the design" - Infer change from context

---

## Workflow Context

This skill is part of the **pre-implementation** review cycle:

```
[new-change] → [draft artifacts] → [review-artifacts] → [modify-artifacts] → [apply]
                                    ↑_______________|
                                       (iterate until ready)
```

**After apply**: Use `openspec-verify-change` to confirm implementation matches specs.
**After verify passes**: Use `openspec-archive-change` to finalize.

---

## Steps

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context
   - Auto-select if only one active change exists
   - If ambiguous: run `openspec list --json` and use the **AskUserQuestion tool** to let the user select

   Always announce: "Reviewing change: <name>"

2. **Check change status**

   ```bash
   openspec status --change "<name>" --json
   ```

   Parse the JSON to understand:
   - `schemaName`: The workflow being used
   - `artifacts`: Array of artifacts with their status

3. **Determine review scope**

   If an artifact type is specified, review only that artifact.
   Otherwise, review all artifacts in the change.

4. **Review each artifact**

   For each artifact, check:

   **Format Validation**:
   - All required sections present
   - Correct header levels (especially scenario headers at `####`)
   - Proper checkbox format in tasks (`- [ ]` / `- [x]`)

   **Content Quality**:
   - Specificity over vagueness
   - Clear, actionable language
   - Proper use of SHALL/MUST in specs

   **Implementation Readiness**:
   - Dependencies are available and compatible
   - Scope is achievable
   - Tasks are specific enough to know when done

5. **Check cross-artifact consistency**

   Run these alignment checks:

   **proposal → specs**:
   - New Capabilities in proposal = specs/ directory names
   - Modified Capabilities = existing spec names in openspec/specs/
   - Consistent kebab-case naming

    **specs → design**:
    - All ADDED/MODIFIED requirements addressed in design
    - REMOVED requirements with migration notes have migration plan

   **design → tasks**:
   - Decisions in design.md have corresponding tasks
   - Risks in design.md have mitigation tasks
   - Non-goals NOT in tasks.md

   **proposal → tasks**:
   - What Changes items covered by task sections
   - Impact items considered

6. **Prioritize findings**

   Classify issues by severity:
   - **Critical**: Blocks implementation, must fix before apply
   - **Warning**: Should fix, may cause issues during implementation
   - **Suggestion**: Nice to have, non-blocking improvement

7. **Generate review report**

   Present findings with actionable feedback including line numbers and specific fixes.

---

## Artifact Review Criteria

### proposal.md

| Section | Required | Common Issues |
|---------|----------|---------------|
| ## Why | Yes | Missing entirely, too vague |
| ## What Changes | Yes | "Improve X" without specifics |
| ## Capabilities | Yes | Inconsistent naming vs specs |
| ## Impact | Recommended | Missing migration considerations |

**Good example**: "Add rate limiting to API endpoints to prevent abuse"
**Bad example**: "Improve API"

### specs/

| Element | Format | Common Issues |
|---------|--------|---------------|
| Section header | `## ADDED` / `## MODIFIED` / `## REMOVED` | Wrong section names |
| Requirement | `### Requirement: <name>` | Missing colon |
| Scenario | `#### Scenario: <name>` | Using `###` instead of `####` |
| Keywords | SHALL, MUST for mandatory | Using "should" ambiguously |

**Scenario format**:
```markdown
#### Scenario: Valid credentials
- **GIVEN** a user with valid credentials
- **WHEN** user submits login form
- **THEN** a JWT token is returned
```

### design.md

| Section | Required | Common Issues |
|---------|----------|---------------|
| ## Context | Yes | Missing existing system context |
| ## Decisions | Yes | No rationale for decisions |
| Alternatives | Under `## Decisions` section | Not considering alternatives |
| ## Trade-offs | Recommended | Missing or superficial |

**Decision format**:
```markdown
### Decision 1: Use JWT for authentication

**Rationale**: Stateless, widely supported, works with microservices.

**Alternatives considered**:
- Session cookies: Requires shared state
- API keys: Less secure for user auth
```

### tasks.md

| Element | Format | Common Issues |
|---------|--------|---------------|
| Section | `## 1. <name>` | Missing numbers, wrong format |
| Task | `- [ ] Task description` | Using `*` instead of `-`, missing brackets |
| Completion | `- [x] Done task` | Wrong checkbox format |

**Correct format**:
```markdown
## 1. Backend Changes

- [ ] Add rate limiting middleware
- [ ] Update API documentation
- [ ] Add configuration for rate limits

## 2. Frontend Changes

- [ ] Add rate limit error handling
- [ ] Show retry countdown UI
```

---

## Output

**On Issues Found**:

```markdown
## Artifact Review: <change-name>

### ✅ Format: Valid
- All required sections present
- Header format correct

### ⚠️ Issues Found

#### Critical (Must Fix Before Implementation)
- **proposal.md:12**: Missing "Why" section context
  - Fix: Add 2-3 sentences explaining the business need

- **specs/auth.md:45**: Scenario uses wrong header level (### instead of ####)
  - Fix: Change to `#### Scenario: Valid credentials`

#### Warnings (Should Fix)
- **design.md:23**: Decision lacks rationale
  - Better: Add "Rationale:" explaining why this approach was chosen

#### Suggestions (Nice to Have)
- **tasks.md:8**: Consider splitting "Implement auth" into smaller tasks
  - Consider: "Add login endpoint", "Add token validation", "Add refresh flow"

### Consistency Check
- ❌ proposal Capabilities don't match specs/ structure
  - Proposal mentions "user-management" but specs/ has "users"

**Next Steps:**
- Fix critical issues: `/opsx-modify <change-name>`
- Re-review after fixes: `/opsx-review <change-name>`
```

**On All Clear**:

```markdown
## Artifact Review: <change-name>

### ✅ All Checks Passed

**Format**: All artifacts properly structured
**Content**: Clear, specific, actionable
**Consistency**: Cross-artifact alignment verified
**Readiness**: Ready for implementation

**Next Steps:**
- Start implementation: `/opsx-apply <change-name>`
```

---

## Guardrails

- Review BEFORE implementation, not after
- Be specific: include file names, line numbers, exact fixes
- Prioritize by severity: critical → warning → suggestion
- Check cross-artifact consistency, not just individual files
- Don't approve changes with critical issues
- Suggest `/opsx-modify` for fixes, don't fix yourself during review
- For post-implementation verification, use openspec-verify-change instead
