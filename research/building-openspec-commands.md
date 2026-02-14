# Building OpenSpec-Style Commands

Guide for creating slash commands that follow OpenSpec patterns. Covers command/skill relationships, structure, naming conventions, and platform differences.

---

## Commands vs Skills

Understanding the distinction is essential:

| Aspect | Commands | Skills |
|--------|----------|--------|
| **Purpose** | User-invoked entry points | Implementation logic |
| **Invocation** | Via `/command-name` | Loaded into context or invoked by commands |
| **Content** | Concise workflow summary | Full implementation details |
| **Relationship** | Often delegate to skills | Contain complete instructions |

### When to Create Each

**Create a command when:**
- You want a user-facing slash command
- You need a lightweight entry point to existing functionality
- You want to provide shortcuts to skill workflows

**Create a skill when:**
- You need substantial implementation logic
- The AI needs detailed guidance for a task
- You want the instructions available in context

**Create both when:**
- You want a `/command` entry point plus detailed skill implementation
- The command serves as a shortcut to skill functionality

---

## Command File Structure

### Directory Layout

```
OpenCode:
.opencode/command/<name>.md

Claude Code:
.claude/commands/opsx/<name>.md
```

**Key difference**: OpenCode uses flat `command/` directory with full command name. Claude Code uses nested `commands/opsx/` directory with verb-only filename.

### Frontmatter Fields

```yaml
---
description: Brief description shown in slash command list
---
```

#### Field Reference

| Field | OpenCode | Claude Code | Description |
|-------|----------|-------------|-------------|
| `description` | Recommended | Recommended | Brief description for TUI/command list |
| `agent` | Optional | Optional | Which agent should execute |
| `subtask` | Optional | N/A | Force subagent invocation |
| `model` | Optional | Optional | Override model |
| `template` | Required (JSON) | N/A | Prompt template in JSON format |

**Platform differences**:
- OpenCode: Only `description` is commonly used in markdown files
- Claude Code: Supports `category`, `tags` in addition to description

### Naming Conventions

| Platform | Format | Example |
|----------|--------|---------|
| OpenCode | `opsx-<verb>.md` | `opsx-new.md`, `opsx-apply.md` |
| Claude Code | `<verb>.md` (in `commands/opsx/`) | `new.md`, `apply.md` |

**Common verbs**:
- `explore` - Think through problems
- `new` - Start something new
- `continue` - Resume work
- `ff` - Fast-forward (create all at once)
- `apply` - Implement changes
- `verify` - Validate implementation
- `archive` - Complete and store
- `sync` - Synchronize state
- `onboard` - Guided introduction

---

## Body Structure

### Recommended Sections

```markdown
[Brief opening statement - what the command does]

**IMPORTANT**: [Critical constraint, if any]

---

## Steps

1. **[Step name]**
   [Concise details]

2. **[Step name]**
   [Concise details]

---

## Output [Templates]

[Formatted examples]

---

## Guardrails

- **[DO/DON'T]**: [Constraint]
```

### Key Differences from Skills

Commands are typically:
- **More concise** - Summarize rather than detail
- **Less instructional** - Focus on workflow, not stance
- **Transition-focused** - Guide users to next commands/skills

### Section Breakdown

#### 1. Opening Statement

Single sentence stating purpose:

```markdown
Start a new change using the experimental artifact-driven approach.
```

Or with constraint:

```markdown
Enter explore mode. Think deeply. Visualize freely. Follow the conversation wherever it goes.

**IMPORTANT: Explore mode is for thinking, not implementing.** You may read files, search code, and investigate the codebase, but you must NEVER write code or implement features.
```

#### 2. Input Handling

Document argument expectations:

```markdown
**Input**: The argument after `/opsx-new` is the change name (kebab-case), OR a description of what the user wants to build.
```

With inference logic:

```markdown
**Input**: Optionally specify a change name (e.g., `/opsx-apply add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.
```

#### 3. Steps Section

Concise numbered workflow:

```markdown
**Steps**

1. **If no input provided, ask what they want to build**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."

2. **Create the change directory**
   ```bash
   openspec new change "<name>"
   ```

3. **Show the artifact status**
   ```bash
   openspec status --change "<name>"
   ```

4. **STOP and wait for user direction**
```

Note the **STOP** pattern - commands often pause to let user choose next action.

#### 4. Output Templates

Consistent formatting across commands:

```markdown
**Output**

After completing the steps, summarize:
- Change name and location
- Schema/workflow being used and its artifact sequence
- Current status (0/N artifacts complete)
- The template for the first artifact
- Prompt: "Ready to create the first artifact? Run `/opsx-continue` or just describe what this change is about and I'll draft it."
```

#### 5. Guardrails

Concise constraints:

```markdown
**Guardrails**
- Do NOT create any artifacts yet - just show the instructions
- Do NOT advance beyond showing the first artifact template
- If the name is invalid (not kebab-case), ask for a valid name
- If a change with that name already exists, suggest using `/opsx-continue` instead
```

---

## Common Patterns

### Argument Patterns

| Pattern | Example | Behavior |
|---------|---------|----------|
| **Direct name** | `/opsx-new add-dark-mode` | Use provided name directly |
| **Description** | `/opsx-new add user authentication` | Derive kebab-case name from description |
| **Empty** | `/opsx-new` | Prompt user for what they want to build |
| **Inferred** | `/opsx-apply` (after discussing "add-auth") | Use context to determine change name |

### Selection Patterns

```markdown
If a name is provided, use it. Otherwise:
- Infer from conversation context if the user mentioned a change
- Auto-select if only one active change exists
- If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select
```

### Transition Patterns

Commands guide users to next actions:

**Completion transition**:
```markdown
All tasks complete! You can archive this change with `/opsx-archive`.
```

**Continue transition**:
```markdown
Ready to create the first artifact? Run `/opsx-continue` or just describe what this change is about and I'll draft it.
```

**Error/help transition**:
```markdown
OpenSpec CLI is not installed. Install it first, then come back to `/opsx-onboard`.
```

**Graceful exit**:
```markdown
No problem! Your change is saved at `openspec/changes/<name>/`.

To pick up where we left off later:
- `/opsx-continue <name>` - Resume artifact creation
- `/opsx-apply <name>` - Jump to implementation (if tasks exist)
```

### Context Inference

```markdown
1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>" and how to override (e.g., `/opsx-apply <other>`).
```

### Multi-State Output

For commands with multiple possible outcomes:

```markdown
**Output On Completion**

```
## Implementation Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 7/7 tasks complete ✓

### Completed This Session
- [x] Task 1
- [x] Task 2
...

All tasks complete! You can archive this change with `/opsx-archive`.
```

**Output On Pause (Issue Encountered)**

```
## Implementation Paused

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<description of the issue>

**Options:**
1. <option 1>
2. <option 2>
3. Other approach

What would you like to do?
```
```

---

## Command/Skill Coordination

### When Commands Reference Skills

Commands often reference skills for detailed work:

```markdown
If user chooses sync, use Task tool (subagent_type: "general-purpose", prompt: "Use Skill tool to invoke openspec-sync-specs for change '<name>'. Delta spec analysis: <include the analyzed delta spec summary>"). Proceed to archive regardless of choice.
```

### When Commands Reference Other Commands

Navigation between commands:

```markdown
## Command Reference

| Command | What it does |
|---------|--------------|
| `/opsx-explore` | Think through problems (no code changes) |
| `/opsx-new <name>` | Start a new change, step by step |
| `/opsx-ff <name>` | Fast-forward: all artifacts at once |
| `/opsx-continue <name>` | Continue an existing change |
| `/opsx-apply <name>` | Implement tasks |
| `/opsx-verify <name>` | Verify implementation |
| `/opsx-archive <name>` | Archive when done |
```

---

## Platform Differences Summary

### Directory Structure

```
OpenCode:                          Claude Code:
.opencode/                         .claude/
├── command/                       └── commands/
│   ├── opsx-explore.md                └── opsx/
│   ├── opsx-new.md                        ├── explore.md
│   ├── opsx-apply.md                      ├── new.md
│   └── ...                                └── ...
└── skills/
    └── openspec-*                        
        └── SKILL.md                  (same structure)
```

### Naming

| Platform | Command Filename | User Invokes |
|----------|------------------|--------------|
| OpenCode | `opsx-new.md` | `/opsx-new` |
| Claude Code | `commands/opsx/new.md` | `/opsx:new`* |

*Claude Code uses `:` for command namespacing from directories.

### Frontmatter

| Field | OpenCode | Claude Code |
|-------|----------|-------------|
| `description` | Recommended | Recommended |
| `agent` | Optional | Optional |
| `subtask` | Optional | N/A |
| `category` | N/A | Optional |
| `tags` | N/A | Optional |

---

## Example Commands Reference

Refer to these canonical implementations in `openspec-core/.opencode/command/`:

| Command | Complexity | Key Patterns Demonstrated |
|---------|------------|---------------------------|
| `opsx-explore.md` | Stance command | Minimal structure, stance-based instructions |
| `opsx-new.md` | Entry command | Argument handling, CLI integration, STOP pattern |
| `opsx-apply.md` | Action command | State management, task iteration, multi-state output |
| `opsx-archive.md` | Completion command | Confirmation prompts, spec sync integration |
| `opsx-onboard.md` | Tutorial command | Phased teaching, EXPLAIN→DO→SHOW→PAUSE |

---

## Validation Checklist

Before finalizing a command, verify:

### Frontmatter
- [ ] `description` is concise and indicates when to use
- [ ] Platform-specific fields match requirements

### Structure
- [ ] Opening statement clearly defines purpose
- [ ] **IMPORTANT** note present if critical constraints exist
- [ ] Input handling documented
- [ ] Steps are numbered and concise
- [ ] Output templates provided for expected states
- [ ] Guardrails present with explicit constraints
- [ ] Transitions to related commands documented

### Naming
- [ ] Filename follows platform convention (`opsx-*.md` or `commands/*/*.md`)
- [ ] Verb is clear and consistent with related commands
- [ ] No conflicts with existing commands

### Platform Compatibility
- [ ] Tested on target platform
- [ ] Directory structure matches platform expectations
- [ ] Command invocation syntax documented for platform

---

## Related Resources

- **Example commands**: `openspec-core/.opencode/command/` and `openspec-core/.claude/commands/opsx/`
- **Related skills**: See `research/building-openspec-skills.md`
- **Platform docs**: `research/opencode-docs.md`, `research/claude-code-docs.md`
- **OpenSpec workflow**: OpenSpec [workflows.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md)
