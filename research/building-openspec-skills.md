# Building OpenSpec-Style Skills

Comprehensive guide for creating AI assistant skills following OpenSpec patterns. Covers philosophy, structure, common patterns, and platform-specific considerations.

---

## Philosophy

OpenSpec skills embody specific principles that distinguish them from generic AI instructions:

### Core Principles

| Principle | Meaning | In Practice |
|-----------|---------|-------------|
| **Fluid, not rigid** | No phase gates, work on what makes sense | Steps enable, not force progression |
| **Iterative, not waterfall** | Learn as you build, refine as you go | Allow returning to earlier artifacts |
| **Stance-based** | Adopt a consistent behavioral posture | Define the "how" of interaction |
| **Dependencies as enablers** | Show what's possible, not what's required next | Check status, don't block |

### Stance Examples

From `openspec-explore`:
- **Curious, not prescriptive** - Ask questions that emerge naturally
- **Open threads, not interrogations** - Surface multiple directions, let user choose
- **Visual** - Use ASCII diagrams liberally
- **Grounded** - Explore actual codebase, don't theorize

---

## Skill File Structure

### Directory Layout

```
OpenCode:
.opencode/skills/<skill-name>/SKILL.md

Claude Code:
.claude/skills/<skill-name>/SKILL.md
```

### Frontmatter Fields

```yaml
---
name: openspec-<action>-<noun>
description: One-line description (1-1024 chars) - what skill does and when to use
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.1.1"
---
```

#### Field Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | OpenCode: Yes, Claude: No* | string | Skill identifier (1-64 chars) |
| `description` | Yes | string | What skill does, when to use (1-1024 chars) |
| `license` | No | string | License identifier (e.g., MIT) |
| `compatibility` | No | string | Platform/runtime requirements |
| `metadata` | No | object | String-to-string map for additional info |

*Claude Code defaults to directory name if `name` omitted.

#### Platform Differences

| Aspect | OpenCode | Claude Code |
|--------|----------|-------------|
| `name` field | Required | Optional (defaults to dir name) |
| Additional fields | `license`, `compatibility`, `metadata` | `allowed-tools`, `context`, `agent`, `hooks` |
| Discovery order | 4 locations (project, global, claude-compat) | 4 locations (managed, personal, project, plugin) |

### Naming Constraints

- **Format**: `^[a-z0-9]+(-[a-z0-9]+)*$`
- **Length**: 1-64 characters
- **Rules**: lowercase, hyphens only, no leading/trailing hyphens, no consecutive hyphens
- **Convention**: `openspec-<action>-<noun>` (e.g., `openspec-new-change`, `openspec-apply-change`)

---

## Body Structure

### Recommended Sections

```markdown
[Brief opening statement - what the skill does]

**IMPORTANT**: [Critical constraint or warning, if any]

---

## [Section: Input/Stance/Context]

[Content]

---

## Steps

1. **[Step name]**
   [Details]

2. **[Step name]**
   [Details]

---

## Output [Templates/Examples]

[Formatted examples]

---

## Guardrails

- **[DO/DON'T]**: [Constraint]
```

### Section Breakdown

#### 1. Opening Statement

1-2 sentences that:
- State what the skill does
- Define when it should be used
- Set expectations for output

**Example** (from `openspec-new-change`):
> Start a new change using the experimental artifact-driven approach.

**IMPORTANT note format**:
```markdown
**IMPORTANT: Explore mode is for thinking, not implementing.** You may read files, search code, and investigate the codebase, but you must NEVER write code or implement features.
```

#### 2. Input Section

Define what the user provides and how to handle missing input:

```markdown
**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.
```

**Handling missing input**:
```markdown
1. **If no change name provided, prompt for selection**

   Run `openspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.
```

#### 3. Steps Section

Numbered workflow with:
- Clear step names
- Bash commands in code blocks
- Decision logic (IF/THEN)
- JSON parsing guidance

**Pattern**:
```markdown
1. **[Step name]**

   [Context/explanation]

   ```bash
   openspec command --option "<value>"
   ```

   [What to do with output]

   **If [condition]**:
   - [Action A]
   
   **Otherwise**:
   - [Action B]
```

**Decision tree pattern**:
```markdown
**Handle states:**
- If `state: "blocked"` (missing artifacts): show message, suggest using openspec-continue-change
- If `state: "all_done"`: congratulate, suggest archive
- Otherwise: proceed to implementation
```

#### 4. Output Templates

Provide formatted examples for different states:

```markdown
**Output On Success**

```
## [Section Title]

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** N/M tasks complete ✓

[Additional details]
```

**Output On Pause (Issue Encountered)**

```
## [Section Title] Paused

**Issue:** <description>

**Options:**
1. <option 1>
2. <option 2>

What would you like to do?
```
```

#### 5. Guardrails Section

Explicit constraints using consistent format:

```markdown
**Guardrails**
- Keep going through tasks until done or blocked
- Always read context files before starting (from the apply instructions output)
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Update task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements - don't guess
```

**Guardrail categories**:
- **Process constraints**: What order, when to stop
- **Interaction constraints**: When to ask vs. act
- **Output constraints**: Format, content limits
- **Behavior constraints**: Stance-related do's/don'ts

---

## Common Patterns

### CLI Integration

OpenSpec skills interact with the `openspec` CLI for state management:

| Command | Purpose | Output |
|---------|---------|--------|
| `openspec list --json` | List active changes | JSON array of change names/schemas/status |
| `openspec status --change "<name>" --json` | Get artifact status | JSON with schemaName, artifacts, completion |
| `openspec instructions <artifact> --change "<name>" --json` | Get template/context | JSON with template, contextFiles, instructions |
| `openspec schemas --json` | List available schemas | JSON array of schema names/descriptions |
| `openspec new change "<name>"` | Create change directory | Creates `openspec/changes/<name>/` |
| `openspec archive "<name>"` | Archive a change | Moves to `openspec/changes/archive/` |

**JSON parsing pattern**:
```markdown
Parse the JSON to understand:
- `schemaName`: The workflow being used (e.g., "spec-driven")
- `artifacts`: List of artifacts with their status (`done` or other)
```

### User Interaction Patterns

#### Selection from Options

```markdown
Run `openspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

Show only active changes (not already archived).
Include the schema used for each change if available.

**IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.
```

#### Open-Ended Prompt

```markdown
Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
> "What change do you want to work on? Describe what you want to build or fix."
```

#### Confirmation Prompts

```markdown
**If any artifacts are not `done`:**
- Display warning listing incomplete artifacts
- Use **AskUserQuestion tool** to confirm user wants to proceed
- Proceed if user confirms
```

### State Management Patterns

#### Checking Artifact Completion

```markdown
Run `openspec status --change "<name>" --json` to check artifact completion.

**If any artifacts are not `done`:**
- Display warning listing incomplete artifacts
- Prompt user for confirmation to continue
```

#### Task Checkbox Handling

```markdown
For each pending task:
- Show which task is being worked on
- Make the code changes required
- Mark task complete in the tasks file: `- [ ]` → `- [x]`
- Continue to next task
```

#### Graceful Exit with Resume

```markdown
No problem! Your change is saved at `openspec/changes/<name>/`.

To pick up where we left off later:
- `/opsx-continue <name>` - Resume artifact creation
- `/opsx-apply <name>` - Jump to implementation (if tasks exist)

The work won't be lost. Come back whenever you're ready.
```

### Context Inference Patterns

```markdown
If a name is provided, use it. Otherwise:
- Infer from conversation context if the user mentioned a change
- Auto-select if only one active change exists
- If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

Always announce: "Using change: <name>" and how to override (e.g., `/opsx-apply <other>`).
```

---

## Example Skills Reference

Instead of inline examples, refer to these canonical implementations in `openspec-core/.opencode/skills/`:

| Skill | Complexity | Key Patterns Demonstrated |
|-------|------------|---------------------------|
| `openspec-explore` | Stance-based | Curious stance, ASCII diagrams, no fixed workflow, guardrails |
| `openspec-new-change` | Step-based | Input handling, CLI integration, stopping for user direction |
| `openspec-apply-change` | Loop-based | Task iteration, state management, pause on issues |
| `openspec-archive-change` | Decision-based | Completion checks, user confirmation, spec sync |
| `openspec-sync-specs` | Transform-based | Delta spec parsing, intelligent merging |
| `openspec-onboard` | Teaching-based | Phased tutorial, EXPLAIN→DO→SHOW→PAUSE pattern |

---

## Validation Checklist

Before finalizing a skill, verify:

### Frontmatter
- [ ] `name` follows naming convention (`openspec-*` or similar)
- [ ] `description` is actionable and indicates when to use (1-1024 chars)
- [ ] `license` specified if required by project
- [ ] `compatibility` noted if dependencies exist

### Structure
- [ ] Opening statement clearly defines purpose
- [ ] **IMPORTANT** note present if critical constraints exist
- [ ] Input handling documented (what user provides, how to handle missing)
- [ ] Steps are numbered and sequential
- [ ] Output templates provided for success/error/pause states
- [ ] Guardrails section present with explicit constraints

### Content Quality
- [ ] Bash commands are in code blocks with language specifier
- [ ] JSON parsing guidance explains which fields to use
- [ ] Decision logic uses consistent IF/THEN format
- [ ] User interaction specifies tool to use (AskUserQuestion)
- [ ] Graceful exit guidance provided where appropriate

### Platform Compatibility
- [ ] Tested on target platform (OpenCode and/or Claude Code)
- [ ] Frontmatter fields match platform requirements
- [ ] Tool references use correct casing (OpenCode: lowercase, Claude: PascalCase)

---

## Related Resources

- **Example skills**: `openspec-core/.opencode/skills/` and `openspec-core/.claude/skills/`
- **Platform docs**: `research/opencode-docs.md`, `research/claude-code-docs.md`
- **OpenSpec concepts**: `openspec-core/AGENTS.md`, OpenSpec [concepts.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md)
- **OPSX workflow**: OpenSpec [opsx.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/opsx.md)
