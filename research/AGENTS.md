# Research Documentation

Platform capability reference for AI agents building the configuration adapter.

---

## Purpose

Factual overview of Claude Code and OpenCode platform capabilities. These documents serve as a shortcut for AI agents to understand platform-specific features, field formats, and constraints without consulting official documentation.

---

## Files

### Platform Capabilities
- **claude-code-docs.md** - Claude Code capabilities (skills, subagents, memory, settings, permissions)
- **opencode-docs.md** - OpenCode capabilities (agents, skills, permissions, commands, tools)

### Building Skills & Commands
- **building-openspec-skills.md** - Guide for creating OpenSpec-style AI assistant skills
- **building-openspec-commands.md** - Guide for creating OpenSpec-style slash commands

### OpenSpec Core Reference (from [upstream docs](https://github.com/Fission-AI/OpenSpec/tree/main/docs))
- **openspec-opsx.md** - OPSX workflow overview (fluid, iterative approach vs legacy)
- **openspec-concepts.md** - Core philosophy, specs, changes, delta specs, schemas, archive
- **openspec-workflows.md** - Workflow patterns (explore, quick feature, parallel changes)
- **openspec-commands.md** - AI slash commands (`/opsx:new`, `/opsx:apply`, `/opsx:archive`, etc.)
- **openspec-cli.md** - CLI reference (`openspec init`, `openspec list`, `openspec validate`, etc.)

---

## Usage Guidelines

1. **Reference only** - Consult when building/adapting platform adapters or validating configurations
2. **Factual content** - Documents contain objective platform information, no recommendations
3. **Cross-reference** - Compare capabilities when designing transformation logic
4. **Validation** - Use documented constraints for field validation schemas

---

## Notes

- Documents are concise overviews, not implementation guidance
- When in doubt, verify against official documentation sources linked in each file
- Claude Code is the source format for transformations