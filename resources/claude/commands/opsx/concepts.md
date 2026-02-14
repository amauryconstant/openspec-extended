---
description: Learn about OpenSpec framework - philosophy, artifacts, OPSX workflow, and ecosystem
---

Teach the OpenSpec framework: a spec-driven development approach where you agree on WHAT to build before writing code.

**Input**: No arguments required. This is an informational command.

---

**Steps**

1. **Explain the philosophy**
   - Four principles: fluid, iterative, easy, brownfield-first
   - Big picture: specs (source of truth) ↔ changes (proposed modifications)
   - Why this matters for AI-assisted development

2. **Describe the artifact system**
   - Artifact flow: proposal → specs → design → tasks → implement
   - Delta specs format (ADDED, MODIFIED, REMOVED sections)
   - Project configuration (config.yaml) for context injection

3. **Explain the OPSX workflow**
   - Complete lifecycle: explore → new → continue/ff → apply → verify → archive
   - Actions, not phases—dependencies enable, not gate
   - State transitions: BLOCKED → READY → DONE

4. **Describe the skill ecosystem**
   - Core skills: standard OPSX workflow (explore, new, apply, archive, etc.)
   - Extension skills: enhanced utilities (modify-artifacts, review-test-compliance, generate-changelog)

5. **Guide decision-making**
   - When to use OpenSpec vs. skip
   - When to update existing change vs. start new
   - Naming conventions

**Output**

Comprehensive overview with diagrams. User understands:
- OpenSpec philosophy and why it matters
- All artifact types and relationships
- OPSX lifecycle and commands
- Core vs extension skills
- When and how to use spec-driven approach

**Guardrails**

- **DO**: Reference the skill for detailed implementation
- **DO**: Use diagrams for complex concepts
- **DON'T**: Modify any files (informational only)

---

See `.claude/skills/openspec-concepts/SKILL.md` for detailed implementation with diagrams and reference documentation.
