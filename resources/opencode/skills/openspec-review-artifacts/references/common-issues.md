# Common Issues in OpenSpec Artifacts

Catalog of frequently occurring issues with examples and fixes.

## Top 10 Issues

### 1. Scenario Header Mismatch
**Problem**: Using `### Scenario:` instead of `#### Scenario:`
**Impact**: Specs fail silently, scenarios not parsed by apply phase
**How to detect**: Check scenario headers use exactly 4 hashtags

**Example**:
```markdown
### Scenario: User logs in  # WRONG (3 #)
- GIVEN user enters credentials
- WHEN they click login
- THEN authentication succeeds

#### Scenario: User logs in  # CORRECT (4 #)
- GIVEN user enters credentials
- WHEN they click login
- THEN authentication succeeds
```

**Fix**: Ensure all scenarios use `#### Scenario:`

---

### 2. Modified Requirements with Partial Content
**Problem**: Only showing changed text under MODIFIED Requirements
**Impact**: Original requirement details lost at archive time, main spec becomes incomplete
**How to detect**: MODIFIED section doesn't include full requirement block

**Example**:
```markdown
## MODIFIED Requirements

### Requirement: Session Timeout
The timeout is now 60 minutes.  # WRONG - only showing change

## MODIFIED Requirements

### Requirement: Session Timeout
The system SHALL expire user sessions after a period of inactivity.

#### Scenario: Idle Timeout
- GIVEN an authenticated session
- WHEN 60 minutes pass without activity
- THEN session is invalidated
# CORRECT - full requirement copied
```

**Fix**: Copy entire requirement block (from `### Requirement:` through all scenarios), then edit

---

### 3. Missing Why in Proposal
**Problem**: "What" without "Why"
**Impact**: Future reviewers can't understand motivation, makes maintenance harder
**How to detect**: proposal.md has no "## Why" section or it's empty

**Example**:
```markdown
## What Changes
- Add authentication to API

## Why
Users need secure access to data.  # CORRECT
```

**Fix**: Add 1-2 sentence "Why" section explaining problem or opportunity

---

### 4. Non-Checkbox Tasks
**Problem**: Using bullets `- ` instead of checkboxes `- [ ] `
**Impact**: apply phase can't track progress, checkboxes don't work
**How to detect**: Tasks use `- 1.1 ` or `-item` instead of `- [ ] 1.1 `

**Example**:
```markdown
## 1. Setup
- 1.1 Create database schema  # WRONG
- Add dependencies  # WRONG

## 1. Setup
- [ ] 1.1 Create database schema  # CORRECT
- [ ] 1.2 Add dependencies  # CORRECT
```

**Fix**: Use exact checkbox format `- [ ] X.Y Description`

---

### 5. Vague Task Descriptions
**Problem**: "Implement feature" without specifics
**Impact**: Can't verify completion, ambiguous scope
**How to detect**: Tasks use generic verbs without specifics

**Example**:
```markdown
- [ ] 2.1 Implement authentication  # WRONG - vague
- [ ] 2.1 Add login endpoint POST /api/auth  # CORRECT
- [ ] 2.2 Implement JWT token generation  # CORRECT
```

**Fix**: Make tasks specific with file paths, endpoints, or concrete actions

---

### 6. Inconsistent Capability Naming
**Problem**: proposal says `user-login`, specs folder is `user-auth`
**Impact**: Can't locate specs, validation fails, confusion for reviewers
**How to detect**: proposal Capabilities don't match specs/ directory names

**Example**:
```markdown
# proposal.md
## Capabilities
### New Capabilities
- user-login: Add login functionality

# Directory structure
specs/
  user-auth/  # MISMATCH - should be user-login
    spec.md
```

**Fix**: Use same kebab-case identifier throughout proposal and specs/

---

### 7. Design Missing Rationale
**Problem**: Decisions without "why X over Y?"
**Impact**: Future maintainers may repeat work, can't understand trade-offs
**How to detect**: design.md Decisions section doesn't include alternatives or rationale

**Example**:
```markdown
## Decisions

### Decision 1: Use PostgreSQL  # WRONG - no rationale

### Decision 1: Database Choice
**Decision**: Use PostgreSQL over MySQL
**Rationale**: Better JSON support and extensions ecosystem
**Trade-offs**: PostgreSQL heavier to set up  # CORRECT
```

**Fix**: Include alternatives considered for each decision with specific rationale

---

### 8. REMOVED Missing Migration
**Problem**: Removing requirements without migration guidance
**Impact**: Breaks dependent code without upgrade path, causes production issues
**How to detect**: REMOVED sections lack `**Migration**:` field

**Example**:
```markdown
### Requirement: Legacy Export
**Reason**: Replaced by new export system

**Migration**: Use new export endpoint at /api/v2/export  # CORRECT
```

**Fix**: Always include `**Migration**:` section in REMOVED requirements

---

### 9. Scenarios Not Testable
**Problem**: "User feels good using the app"
**Impact**: Can't write automated tests, can't validate implementation
**How to detect**: THEN clause uses subjective language

**Example**:
```markdown
#### Scenario: Successful Login
- GIVEN user enters valid credentials
- WHEN they click login
- THEN user feels happy with experience  # WRONG - subjective

- THEN user sees welcome screen  # CORRECT - observable
- THEN user can access protected routes  # CORRECT - testable
```

**Fix**: Use observable outcomes (THEN returns 200 OK, THEN displays X)

---

### 10. Tasks Not Ordered by Dependency
**Problem**: Implementing feature before setup
**Impact**: Wasted work, blocked progress, can't complete tasks
**How to detect**: Tasks reference files/components created in later tasks

**Example**:
```markdown
## 1. Implementation  # WRONG - tasks out of order
- [ ] 1.1 Create API endpoint using User model
- [ ] 1.2 Implement authentication service

## 2. Setup  # Should be first
- [ ] 2.1 Create User model in database

## 1. Setup  # CORRECT - setup first
- [ ] 1.1 Create User model in database

## 2. Implementation
- [ ] 2.1 Create API endpoint using User model
- [ ] 2.2 Implement authentication service
```

**Fix**: Reorder tasks so prerequisites come before dependent tasks

## How to Check Issues

### Automated Validation

Run OpenSpec's built-in validation:
```bash
openspec validate
```

This checks:
- Required sections exist
- Format requirements (headers, checkbox format)
- Schema compliance

### Manual Consistency Cross-Check

Verify artifacts align:
```bash
# 1. Check proposal Capabilities match specs/
ls openspec/changes/<name>/specs/
# Compare with proposal.md Capabilities section

# 2. Check tasks cover proposal What Changes
# Manually compare proposal What Changes with tasks.md sections

# 3. Check design decisions addressed in tasks
# Compare design.md Decisions with tasks.md
```

### Common Issue Detection Patterns

**Check for vague language**:
```bash
grep -i "improve\|enhance\|optimize\|better" proposal.md
# If results, look for specifics
```

**Check scenario header levels**:
```bash
grep -n "^### Scenario:" openspec/changes/<name>/specs/*/spec.md
# Should return empty - all scenarios should be ####
```

**Check checkbox format**:
```bash
grep -n "^- [0-9]" openspec/changes/<name>/tasks.md
# Should return empty - tasks should use "- [ ] X.Y"
```

## Prevention Checklist

### Before Starting a Change

- [ ] Research existing specs before creating proposal
- [ ] Decide if change needs design.md (cross-cutting? complex?)
- [ ] List all New and Modified Capabilities in proposal

### While Creating Artifacts

- [ ] proposal.md has Why section (1-2 sentences)
- [ ] proposal.md Capabilities use kebab-case consistently
- [ ] Each spec requirement has ≥1 scenario
- [ ] All scenarios use `#### Scenario:` (4 hashtags)
- [ ] MODIFIED requirements include full content
- [ ] REMOVED requirements have Reason and Migration
- [ ] design.md decisions include rationale ("why X over Y?")
- [ ] tasks.md uses `- [ ] X.Y` format
- [ ] Tasks are specific and verifiable

### Before Implementation (Pre-Apply)

- [ ] Run `openspec-review-artifacts` to validate artifacts
- [ ] Design decisions have clear rationale and alternatives
- [ ] Tasks are specific and achievable in one session each
- [ ] All proposal What Changes have corresponding tasks
- [ ] Specs have testable scenarios for all requirements
- [ ] No blocking technical feasibility issues

### Before Archiving

- [ ] Run `openspec validate`
- [ ] All tasks are checked `[x]`
- [ ] Implementation verified with openspec-verify-change
- [ ] proposal Capabilities match specs/ directories

## Getting Help

### Review Command

Use this skill to review artifacts:
```
Review proposal.md
Review entire change
```

### Template Reference

See template files for correct format:
```bash
# OpenSpec installation
cat /path/to/openspec/schemas/spec-driven/templates/*.md
```

### Schema Reference

See schema.yaml for requirements:
```bash
cat /path/to/openspec/schemas/spec-driven/schema.yaml
```
