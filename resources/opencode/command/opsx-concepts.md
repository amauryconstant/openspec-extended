---
description: Learn about OpenSpec framework for spec-driven development
---

Display OpenSpec framework overview and concepts.

**Input**: No arguments required. This is an informational command.

**Steps**

1. **Display OpenSpec overview**:
   - Spec-driven development framework: agree on WHAT to build before writing code
   - Artifacts live in repository, not tool-specific systems

2. **Show artifact types**:
   - `proposal.md`: Why and what - intent, scope, capabilities, impact
   - `specs/`: Requirements - testable GIVEN/WHEN/THEN scenarios
   - `design.md`: How to implement - context, decisions, tradeoffs
   - `tasks.md`: Implementation checklist - progress-tracked checkboxes

3. **Display directory structure** showing typical OpenSpec layout.

4. **Explain delta spec format** with example:
   ```markdown
   ### Requirement: Session Expiration
   The system SHALL expire sessions after 30 minutes.
   #### Scenario: Idle Timeout
   - GIVEN an authenticated session
   - WHEN 30 minutes pass without activity
   - THEN session is invalidated
   ```
   Sections: ADDED (new), MODIFIED (changed), REMOVED (deleted)

5. **Show when to use OpenSpec decision tree**:
   - **Yes - Use OpenSpec when**: Multi-step (3+ tasks), unclear requirements, refactors/architecture, multi-system changes, multiple sessions
   - **No - Skip when**: Single obvious fixes (1-2 lines), emergency hotfixes, pure debugging

6. **Display key points**:
   - Specs are living documents, update as you learn
   - Delta specs prevent duplication (only document what's changing)
   - Archive preserves history with date prefix
   - Main specs merge from delta on archive

**Output**

Display comprehensive overview with examples.

**Guardrails**

- Informational only - no file modifications
- Provide clear examples for each concept

Load the corresponding skill for detailed implementation:

See `.opencode/skills/openspec-concepts/SKILL.md` for:
- Mermaid diagrams for directory structure and decision tree
- Detailed explanations and examples
- Reference artifact formats
