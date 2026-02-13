---
name: openspec-concepts
description: AI agent guide to OpenSpec - framework for spec-driven development. Understand artifacts, structure, and when to use spec-driven approach.
license: MIT
argument-hint: ""
metadata:
  author: openspec-extended
  version: "0.1.1"
---

# OpenSpec for AI Agents

## What is OpenSpec?

Spec-driven development framework: agree on WHAT to build before writing code. Artifacts live in repository, not tool-specific systems.

## Why It Matters

You'll encounter OpenSpec artifacts in projects using this framework. Understanding them helps you align implementation with documented requirements.

## Artifact Types

| Artifact      | Purpose                  | Contains                            |
| ------------- | ------------------------ | ----------------------------------- |
| `proposal.md` | Why & what               | Intent, scope, capabilities, impact |
| `specs/`      | Requirements             | Testable GIVEN/WHEN/THEN scenarios  |
| `design.md`   | How to implement         | Context, decisions, tradeoffs       |
| `tasks.md`    | Implementation checklist | Progress-tracked checkboxes         |

## Directory Structure

```mermaid
graph TD
    A[openspec/] --> B[specs/]
    A --> C[changes/]

    B --> D[domain-1/]
    B --> E[domain-2/]
    B --> F[domain-3/]

    D --> D1[capability-1/]
    D --> D2[capability-2/]
    D --> D3[capability-3/]

    C --> G[change-name/]
    G --> G1[proposal.md]
    G --> G2[design.md]
    G --> G3[tasks.md]
    G --> G4[specs/]

    G4 --> H[domain-1/]
    H --> H1[capability-1/]

    C --> I[archive/]
    I --> J[2025-01-15-change-name/]
    J --> J1[proposal.md]
    J --> J2[design.md]
    J --> J3[tasks.md]
    J --> J4[specs/]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#fff4e1
    style I fill:#ffe1e1
```

## Delta Spec Format

```markdown
### Requirement: Session Expiration

The system SHALL expire sessions after 30 minutes.

#### Scenario: Idle Timeout

- GIVEN an authenticated session
- WHEN 30 minutes pass without activity
- THEN session is invalidated
```

Sections: **ADDED** (new), **MODIFIED** (changed), **REMOVED** (deleted)

## When to Read Artifacts

- Before implementing (align with specs/design)
- When uncertain about requirements
- To understand context for bug fixes

## When to Suggest Creating Artifacts

```mermaid
graph TD
    A[User requests change] --> B{Quick fix?}
    B -->|1-2 lines, obvious| C[Skip OpenSpec<br/>Just implement]
    B -->|Multi-step work| D{Emergency?}

    D -->|Hotfix, urgent| C
    D -->|No| E{Unclear requirements?}

    E -->|Yes| F[Use OpenSpec]
    E -->|No, clear scope| G{Refactor/Architecture?}

    G -->|Yes| F
    G -->|No| H{Multiple sessions?}

    H -->|Yes| F
    H -->|No| I[Optional: Consider OpenSpec<br/>if 3+ tasks]

    style C fill:#ffe1e1
    style F fill:#e1ffe1
    style I fill:#fff4e1
```

**Yes - Use OpenSpec when:**

- Multi-step implementation (3+ distinct tasks)
- Unclear requirements or multiple approaches exist
- Refactors or architectural changes
- Changes affecting multiple files/systems
- Work spanning multiple sessions

**No - Skip when:**

- Single obvious fixes (1-2 lines)
- Emergency hotfixes (document afterward)
- Pure debugging/investigation

## Key Points

- Specs are living documents, update as you learn
- Delta specs prevent duplication (only document what's changing)
- Archive preserves history with date prefix
- Main specs merge from delta on archive

See `references/artifact-formats.md` for detailed examples.
