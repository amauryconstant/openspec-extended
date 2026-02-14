# Review Criteria

Comprehensive review criteria for each OpenSpec artifact type.

## proposal.md Review

### Required Sections

#### Why
- Purpose: Motivation for the change
- Length: 1-2 sentences
- Content: What problem does this solve? Why now?

#### What Changes
- Purpose: Describe what will change
- Format: Bullet list
- Content: Specific about new capabilities, modifications, or removals
- Mark breaking changes: **BREAKING**

#### Capabilities
- Purpose: Link proposal to specs
- Two subsections:

**New Capabilities**:
- List capabilities being introduced
- Each becomes specs/<name>/spec.md
- Use kebab-case names (e.g., `user-auth`, `data-export`)
- Format: `<name>: <brief description>`

**Modified Capabilities**:
- Existing capabilities whose requirements are changing
- Only include if spec-level behavior changes
- Leave empty if no requirement changes
- Use existing spec names from openspec/specs/
- Format: `<existing-name>: <what requirement is changing>`

#### Impact
- Purpose: Identify affected systems
- Content: Affected code, APIs, dependencies, or systems

### Quality Checks

- Why is concise (1-2 sentences), not verbose
- Why explains problem/motivation, not just what
- What Changes uses specific verbs (add/remove/modify/refactor)
- What Changes items are concrete, not vague
- New Capabilities use valid kebab-case identifiers
- Modified Capabilities reference existing spec names exactly
- Modified Capabilities only listed for requirement-level changes
- Impact section identifies what's affected

### Anti-Patterns

❌ Vague "improve X" without specifics
- Bad: "Improve performance"
- Good: "Optimize database queries by adding indexes"

❌ Missing "Why" section
- Bad: "What Changes: Add feature X"
- Good: "Why: Users need faster data export. What Changes: Add CSV export"

❌ Inconsistent naming with specs
- Bad: proposal says `user-login`, specs folder is `user-auth`
- Good: Both use `user-auth` consistently

❌ Modified Capabilities for implementation changes
- Bad: Modified `api-client` for adding new method
- Good: Only modify when requirement behavior changes

## specs/ Review

### Format Requirements

#### Section Headers
- Use exactly `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements`
- Case-sensitive: ADDED not Added

#### Requirement Format
- Each requirement: `### Requirement: <name>` header (exactly 3 #)
- Description follows header
- Use SHALL/MUST for normative requirements
- Avoid SHOULD/MAY (non-normative)

#### Scenario Format
- Each scenario: `#### Scenario: <name>` header (exactly 4 #)
- **CRITICAL**: Using 3 hashtags causes silent failures
- Format: GIVEN/WHEN/THEN or WHEN/THEN
- Each scenario must have at least one WHEN and one THEN

#### MODIFIED Requirements
- Copy ENTIRE requirement block from existing spec
- Include from `### Requirement:` through all scenarios
- Edit to reflect new behavior
- Ensure header text matches exactly (whitespace-insensitive)

#### REMOVED Requirements
- Must include `**Reason**:` Why being removed
- Must include `**Migration**:` How to upgrade code

### Quality Checks

- Every requirement has at least one scenario
- Scenarios are specific and testable
- Scenarios use observable outcomes (THEN returns 200 OK)
- GIVEN/WHEN/THEN format is consistent
- MODIFIED requirements include full content (not just diff)
- REMOVED requirements have Reason and Migration
- SHALL/MUST used correctly
- No SHOULD/MAY in requirements

### Anti-Patterns

❌ Wrong scenario header level
- Bad: `### Scenario:` (only 3 #)
- Good: `#### Scenario:` (exactly 4 #)
- Impact: Scenarios not parsed, fail silently

❌ Partial content in MODIFIED
- Bad: Only showing changed text
- Good: Copy entire requirement, then edit
- Impact: Original details lost at archive time

❌ Scenarios not testable
- Bad: "User feels happy using the app"
- Good: "THEN user sees success message"
- Impact: Can't write automated tests

❌ SHOULD/MAY in requirements
- Bad: "The system SHOULD save data"
- Good: "The system SHALL save data"
- Rationale: Requirements must be normative

❌ Missing scenarios
- Bad: Requirement with no scenarios
- Good: Each requirement has ≥1 scenario
- Impact: Can't validate implementation

❌ Adding new concerns as MODIFIED
- Bad: MODIFIED when adding new feature
- Good: ADDED for new features, MODIFIED for behavior changes

## design.md Review

### Required Sections

#### Context
- Purpose: Background, current state, constraints
- Content: What's the situation? What limitations exist?

#### Goals / Non-Goals
- **Goals**: What this design achieves
- **Non-Goals**: What's explicitly out of scope

#### Decisions
- Key technical choices with rationale
- Format: Decision + "why X over Y?"
- Include alternatives considered for each decision

#### Risks / Trade-offs
- Known risks and limitations
- Format: [Risk] → Mitigation
- Acknowledged compromises

#### Optional Sections
- Migration Plan: Steps to deploy, rollback strategy
- Open Questions: Outstanding decisions or unknowns

### Quality Checks

- Decisions explain rationale (why X over Y?)
- Includes alternatives considered
- Rationale is specific, not generic
- Context provides relevant background
- Goals are specific and measurable
- Non-goals are clearly excluded
- Risks have mitigation strategies
- Trade-offs acknowledged

### Anti-Patterns

❌ Implementation details in design
- Bad: "Create function authenticateUser() with password arg"
- Good: "Use JWT tokens for authentication"
- Rationale: Implementation belongs in tasks.md

❌ Decisions without rationale
- Bad: "Decision: Use PostgreSQL"
- Good: "Decision: Use PostgreSQL over MySQL. Rationale: Better JSON support"
- Impact: Future maintainers can't understand reasoning

❌ Missing alternatives considered
- Bad: "Decision: Use React"
- Good: "Decision: Use React over Vue. Rationale: Better ecosystem"
- Impact: No documentation of evaluation process

❌ Generic "best practice" rationale
- Bad: "Decision: Follow best practices"
- Good: "Decision: Use standard REST endpoints. Rationale: API consistency"
- Impact: Doesn't provide real guidance

❌ Missing Non-goals
- Bad: Ambiguous scope
- Good: Clear boundary of what's excluded
- Impact: Scope creep, unclear what's included

## tasks.md Review

### Format Requirements

#### Section Structure
- Use numbered `##` headers: `## 1. Setup`, `## 2. Core Implementation`
- Group related tasks under numbered headings
- Tasks ordered by dependency

#### Checkbox Format
- Each task MUST be: `- [ ] X.Y Task description`
- Space after bracket: `[ ]` not `[]`
- Period after X.Y: `- [ ] 1.1 ` not `- [ ] 1.1`
- **CRITICAL**: Non-checkbox format breaks apply phase tracking

### Quality Checks

- Tasks are verifiable (you know when done)
- Tasks are small (complete in one session)
- Tasks ordered by dependency (what must be done first?)
- Tasks reference specific files/components
- Tasks cover all design decisions
- Tasks cover all What Changes items
- Tasks address risks from design.md

### Anti-Patterns

❌ Non-checkbox format
- Bad: `- 1.1 Create component`
- Good: `- [ ] 1.1 Create component`
- Impact: apply phase can't track progress

❌ Wrong bracket spacing
- Bad: `-[] 1.1 Create component`
- Good: `- [ ] 1.1 Create component`
- Impact: Parsing fails, checkboxes not recognized

❌ Missing period after number
- Bad: `- [ ] 1.1 Create component`
- Good: `- [ ] 1.1 Create component`
- Impact: Formatting inconsistency

❌ Vague task descriptions
- Bad: "Implement feature"
- Good: "Add user-auth endpoint POST /api/auth"
- Impact: Can't verify completion

❌ Tasks too large
- Bad: "Build authentication system"
- Good: "1.1 Create auth model, 1.2 Add login endpoint, 1.3 Add logout"
- Impact: Can't finish in one session

❌ Wrong dependency order
- Bad: Implement API before creating database schema
- Good: Create schema, then implement API
- Impact: Wasted work, blocked progress

❌ Missing numbered sections
- Bad: All tasks under "Tasks" header
- Good: "## 1. Setup, ## 2. Implementation"
- Impact: No logical grouping

## Cross-Artifact Consistency

### proposal ↔ specs
- New Capabilities in proposal = specs/ directory structure
- Modified Capabilities in proposal = existing spec names
- All proposal Capabilities have corresponding spec files

### proposal ↔ design
- design Context aligns with proposal Why
- design Decisions address proposal What Changes
- design Non-goals exclude proposal Capabilities

### design ↔ tasks
- All design Decisions have corresponding tasks
- design Risks have mitigation tasks
- design Non-goals not in tasks.md

### specs ↔ tasks
- All ADDED/MODIFIED requirements have tasks
- REMOVED requirements with Migration have migration tasks
- Scenarios covered by test tasks

### proposal ↔ tasks
- What Changes items covered by task sections
- Impact items considered in tasks

## Implementation Readiness

### Feasibility Assessment

- Are required dependencies available and compatible?
- Is the scope achievable with available team skills?
- Are there unresolved technical blockers?
- Do design decisions have viable implementation paths?

### Technical Soundness

- Do design trade-offs align with system constraints?
- Are there obvious alternative approaches missing from rationale?
- Do requirements conflict with existing architecture?
- Is the task ordering correct for dependencies?

### Completeness for Implementation

- Can a developer implement from specs alone?
- Are all edge cases covered by scenarios?
- Are error handling and failure modes specified?
- Is there enough context to start coding without questions?
