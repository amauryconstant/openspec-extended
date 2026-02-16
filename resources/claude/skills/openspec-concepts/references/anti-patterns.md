# OpenSpec Anti-Patterns

Common mistakes AI agents and humans make when working with OpenSpec, organized by workflow phase.

---

## Workflow Anti-Patterns

### 1. Creating Artifacts Out of Order

**Problem**: Attempting to create `tasks.md` before `specs/` and `design.md` exist.

**Why it fails**: The dependency graph enforces order. `tasks` requires both `specs` and `design`.

**Solution**: Always run `openspec status --change "<name>" --json` first. Only create artifacts with `status: "ready"`.

```bash
# Check what's ready
openspec status --change "add-dark-mode" --json

# Output shows:
# {"artifacts": [{"id": "tasks", "status": "blocked", "requires": ["specs", "design"]}]}
```

---

### 2. Guessing Change Names

**Problem**: Assuming which change to work on without confirming with the user.

**Example**:
```
# BAD: AI assumes
"Working on add-dark-mode..."

# GOOD: AI confirms
"Found 2 active changes. Which should I work on?"
```

**Solution**: Use `openspec list --json` + AskUserQuestion tool. Always let the user select unless only one change exists.

**Exception**: If user explicitly says "continue with add-dark-mode", use that name.

---

### 3. Treating Artifacts as Write-Once

**Problem**: Creating artifacts and never updating them, even when implementation reveals issues.

**Why it's wrong**: OpenSpec is iterative. The philosophy is "learn as you build, refine as you go."

**Solution**: During `/opsx:apply`, if you discover:
- Design approach won't work → Update `design.md` and continue
- Scope needs adjustment → Update `proposal.md`
- Requirements misunderstood → Update `specs/`

---

### 4. Skipping Spec Updates

**Problem**: Implementing changes but not updating delta specs to reflect them.

**Consequence**: Archive produces incorrect source of truth. Future changes build on wrong assumptions.

**Solution**: Any code change that affects behavior should have corresponding spec updates. Use `openspec-review-test-compliance` to check alignment.

---

### 5. Archiving Incomplete Work

**Problem**: Running `/opsx:archive` when tasks are incomplete or specs aren't synced.

**Solution**: Before archiving:
1. Verify all tasks are `[x]` in `tasks.md`
2. Run `openspec-review-test-compliance` (optional but recommended)
3. Run `/opsx:verify` to validate implementation
4. Let archive prompt for spec sync if needed

---

### 6. Over-Engineering Proposals

**Problem**: Writing lengthy proposals that include implementation details better suited for design.

**Bad proposal**:
```markdown
## Approach
Use React Context with localStorage persistence. Create ThemeContext.tsx
with useTheme hook. CSS variables for colors...
```

**Good proposal**:
```markdown
## Approach
Use React Context for state management with localStorage persistence.
(Design document will detail implementation.)
```

**Solution**: Proposals capture intent and scope. Design captures technical approach. Keep them separate.

---

## Spec Anti-Patterns

### 7. Vague Requirements

**Problem**: Requirements that can't be objectively verified.

**Bad**: "The system should be fast"

**Good**: "The system SHALL respond to API requests within 200ms for 95th percentile under normal load"

**Solution**: Use RFC 2119 keywords (SHALL/MUST/SHOULD) and include measurable criteria.

---

### 8. Missing Scenarios

**Problem**: Requirements without testable scenarios.

**Bad**:
```markdown
### Requirement: User Authentication
The system SHALL authenticate users.
```

**Good**:
```markdown
### Requirement: User Authentication
The system SHALL authenticate users via email and password.

#### Scenario: Valid credentials
- GIVEN a user with valid credentials
- WHEN the user submits the login form
- THEN a session token is issued
- AND the user is redirected to the dashboard

#### Scenario: Invalid credentials
- GIVEN invalid credentials
- WHEN the user submits the login form
- THEN an error message is displayed
- AND no session token is issued
```

**Solution**: Every requirement needs at least one GIVEN/WHEN/THEN scenario.

---

### 9. Specifying Implementation in Requirements

**Problem**: Specs describe HOW instead of WHAT.

**Bad**:
```markdown
### Requirement: Session Storage
The system SHALL use Redis to store session tokens with 30-minute TTL.
```

**Good**:
```markdown
### Requirement: Session Expiration
The system SHALL expire sessions after 30 minutes of inactivity.

(Design document specifies Redis with TTL as the implementation choice.)
```

**Solution**: Specs define behavior. Design defines implementation.

---

### 10. Forgetting REMOVED Sections

**Problem**: Removing functionality but not documenting it in delta specs.

**Consequence**: Archive doesn't remove the requirement from main specs. Source of truth becomes incorrect.

**Solution**: When deprecating or removing behavior:
```markdown
## REMOVED Requirements

### Requirement: Remember Me
(Deprecated in favor of 2FA. Users should re-authenticate each session.)
```

---

## AI Agent Anti-Patterns

### 11. Not Checking State Before Acting

**Problem**: Assuming what exists instead of checking.

**Solution**: Always run `openspec status --json` before:
- Creating artifacts
- Starting apply phase
- Archiving

---

### 12. Updating Tasks Without Implementing

**Problem**: Marking tasks complete (`[x]`) without actually implementing them.

**Solution**: Only mark `[x]` after code is written and tested. During `/opsx:apply`:
1. Implement the task
2. Verify it works
3. Then update checkbox

---

### 13. Copying Context/Rules Into Artifacts

**Problem**: Including `<context>` and `<rules>` blocks from `openspec instructions` output directly into artifact files.

**Why it's wrong**: Context and rules are guidance for YOU (the AI), not content for the artifact.

**Solution**: Use context/rules to inform how you write artifacts, but don't copy them verbatim.

---

### 14. Starting New Changes for Minor Scope Adjustments

**Problem**: Creating a new change folder when the existing change just needs scope refinement.

**Example**: "Add dark mode" change exists. You realize custom themes are out of scope for MVP.

**Wrong**: Create new "add-dark-mode-mvp" change.

**Right**: Update the existing proposal to narrow scope, continue with same change.

**Solution**: See "Update vs New Change" decision tree in main skill.

---

### 15. Ignoring Parallel Change Conflicts

**Problem**: Working on multiple changes that touch the same specs without considering merge order.

**Solution**: Use `openspec-bulk-archive` which:
- Detects spec conflicts
- Checks what's implemented in codebase
- Applies changes chronologically

---

## Naming Anti-Patterns

### 16. Generic Change Names

**Bad names**:
- `feature-1`
- `update`
- `changes`
- `wip`
- `temp`
- `fix`

**Good names**:
- `add-dark-mode`
- `fix-login-redirect`
- `optimize-product-query`
- `implement-2fa`
- `refactor-auth-module`

**Pattern**: `<verb>-<noun>-<detail>` where verb is action, noun is target.

---

## Recovery Strategies

When you realize you've made a mistake:

| Situation | Recovery |
|-----------|----------|
| Created wrong artifact | Delete file, run `/opsx:continue` to recreate |
| Wrong change name | Delete folder, create new with correct name |
| Missing spec updates | Use `openspec-modify-artifacts` to add |
| Archived prematurely | Can't undo - document in next change |
| Tasks out of sync with code | Update tasks.md to match reality, not vice versa |

---

## Quick Reference: Top 5 Workflow Mistakes

| # | Mistake | Quick Fix |
|---|---------|-----------|
| 1 | Creating out of order | Check `status --json` first |
| 2 | Guessing change name | Use `list --json` + AskUserQuestion |
| 3 | Never updating artifacts | Edit freely during apply phase |
| 4 | Vague requirements | Add measurable criteria + scenarios |
| 5 | Skipping spec sync | Always sync before/during archive |

---

## Related Documentation

- Main skill: `../SKILL.md`
- `references/cli-reference.md` - CLI commands for status and instructions
- `references/change-guidance.md` - When to update vs. start fresh
