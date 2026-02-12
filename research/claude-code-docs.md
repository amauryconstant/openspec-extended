# Claude Code Documentation

Platform reference for AI coding assistant configuration. Focuses on document types (Agents, Commands, Skills, Memory) and their field definitions for use by the Germinator configuration adapter.

## Official Documentation Sources

- [Skills](https://code.claude.com/docs/en/skills.md) - Custom skills with SKILL.md format
- [Memory](https://code.claude.com/docs/en/memory.md) - Memory management with CLAUDE.md
- [Sub-agents](https://code.claude.com/docs/en/sub-agents.md) - Custom subagents
- [Settings](https://code.claude.com/docs/en/settings.md) - Configuration and permissions
- [Hooks](https://code.claude.com/docs/en/hooks) - Lifecycle hooks and event handlers
- [Plugins](https://code.claude.com/docs/en/plugins) - Plugin system and marketplace

---

## Document Types

Claude Code supports four primary document types: Skills, Agents (Subagents), Memory, and Settings.

### Skills

**File:** `.claude/skills/<name>/SKILL.md`

**Frontmatter Fields:**

| Field                    | Type    | Required    | Default        | Description                                                  |
| ------------------------ | ------- | ----------- | -------------- | ------------------------------------------------------------ |
| name                     | string  | No          | Directory name | Display name for skill, lowercase, max 64 chars              |
| description              | string  | Recommended | -              | What skill does and when to use it                           |
| version                  | string  | No          | -              | Semantic version (MAJOR.MINOR.PATCH) for tracking releases   |
| argument-hint            | string  | No          | -              | Hint shown during autocomplete, e.g., `[issue-number]`       |
| disable-model-invocation | boolean | No          | `false`        | Prevent Claude from auto-loading                             |
| user-invocable           | boolean | No          | `true`         | Set to `false` to hide from `/` menu. Default: `true`        |
| allowed-tools            | string  | No          | -              | Tools Claude can use without approval (comma-separated list) |
| model                    | string  | No          | -              | Model to use when skill is active                            |
| context                  | string  | No          | -              | Set to `fork` to run in subagent context                     |
| agent                    | string  | No          | -              | Which subagent type when `context: fork`                     |
| hooks                    | object  | No          | -              | Lifecycle hooks scoped to skill                              |

**Body:** Markdown content with skill instructions

**String Substitutions:**

- `$ARGUMENTS` - All arguments passed
- `$ARGUMENTS[N]` or `$N` - Specific argument by position (0-based index)
- `${CLAUDE_SESSION_ID}` - Current session ID

**Skill Locations (by precedence):**

1. Enterprise: Managed policy
2. Personal: `~/.claude/skills/<name>/SKILL.md`
3. Project: `.claude/skills/<name>/SKILL.md`
4. Plugin: `<plugin-root>/skills/<name>/SKILL.md` (namespaced as `plugin:name`)

**Automatic Discovery from Nested Directories:**

When working in subdirectories, Claude Code automatically discovers skills from nested `.claude/skills/` directories (e.g., `packages/frontend/.claude/skills/`).

**Supporting Files:**

Skills can include additional files in their directory:

```markdown
my-skill/
├── SKILL.md (required - overview and navigation)
├── reference.md (detailed API docs - loaded when needed)
├── examples.md (usage examples - loaded when needed)
└── scripts/
└── helper.py (utility script - executed, not loaded)
```

Reference supporting files from SKILL.md so Claude knows what each file contains and when to load it. Keep SKILL.md under 500 lines for optimal context management.

**Character Budget:**

Skill descriptions are loaded into context so Claude knows what's available. If many skills exceed the character budget (default 15,000 characters), some skills are excluded. Increase the limit with `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable. Use `/context` to check for warnings about excluded skills.

**Ultrathink Mode:**

Include the word "ultrathink" anywhere in skill content to enable extended thinking when the skill runs.

**Invocation Control:**

| Frontmatter                      | You can invoke | Claude can invoke | When loaded into context                                     |
| -------------------------------- | -------------- | ----------------- | ------------------------------------------------------------ |
| (default)                        | Yes            | Yes               | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes            | No                | Description not in context, full skill loads when you invoke |
| `user-invocable: false`          | No             | Yes               | Description always in context, full skill loads when invoked |

**Dynamic Context Injection:**

The `!`command\`` syntax runs shell commands before the skill content is sent to Claude. Command output replaces the placeholder.

**Example:**

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---
## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`
```

---

### Subagents (Agents)

**File:** `.claude/agents/<name>.md`

**Frontmatter Fields:**

| Field           | Type   | Required | Default   | Description                                                                  |
| --------------- | ------ | -------- | --------- | ---------------------------------------------------------------------------- | --------------------------------- |
| name            | string | Yes      | -         | Unique identifier, lowercase with hyphens                                    |
| description     | string | Yes      | -         | When Claude should delegate to this subagent                                 |
| tools           | string | No       | -         | Tools subagent can use (comma-separated, PascalCase)                         |
| disallowedTools | string | No       | -         | Tools to deny (comma-separated, PascalCase)                                  |
| model           | string | No       | `inherit` | Model: `sonnet`, `opus`, `haiku`, or `inherit`                               |
| permissionMode  | string | No       | -         | `default`, `acceptEdits`, `delegate`, `dontAsk`, `bypassPermissions`, `plan` |
| skills          | string | No       | -         | Skills to preload into subagent's context (comma-separated)                  |
| maxTurns        | number | No       | -         | Maximum number of agentic turns before subagent stops                        |
| mcpServers      | string | object   | No        | -                                                                            | MCP servers available to subagent |
| memory          | string | No       | -         | Persistent memory scope: `user`, `project`, or `local`                       |
| hooks           | object | No       | -         | Lifecycle hooks scoped to subagent                                           |

**Body:** Markdown content as system prompt

**Built-in Subagents:**

| Name              | Model    | Tools             | Purpose                                               |
| ----------------- | -------- | ----------------- | ----------------------------------------------------- |
| Explore           | Haiku    | Read-only only    | Fast, read-only codebase exploration                  |
| Plan              | Inherits | Read-only only    | Research for plan mode                                |
| general-purpose   | Inherits | All tools         | Complex, multi-step tasks with exploration and action |
| Bash              | Inherits | Terminal commands | Running terminal commands in separate context         |
| statusline-setup  | Sonnet   | Varies            | Configured when running `/statusline`                 |
| Claude Code Guide | Haiku    | Varies            | Answering questions about Claude Code features        |

**Subagent Execution:**

When Claude delegates to a subagent:

1. Creates isolated context window
2. Subagent inherits parent's permissions with additional restrictions
3. Subagent can optionally preload skills via `skills` field
4. Results are summarized and returned to main conversation
5. Subagents cannot spawn other subagents (prevents infinite nesting)

**Scope Hierarchy:**

1. Managed (highest)
2. User (`~/.claude/agents/`)
3. Project (`.claude/agents/`)

**Skill Preloading:**

Subagents can preload skills via the `skills` field. Preloaded skills' full content is injected at subagent startup, not just descriptions. This differs from regular session skills where only descriptions are in context initially.

---

### Memory

**Files:**

- `CLAUDE.md` (multiple locations)
- `.claude/CLAUDE.md`
- `.claude/rules/*.md`
- `CLAUDE.local.md`

**Frontmatter:** None - Pure markdown content with optional file references

**Features:**

- `@path/to/file` syntax for importing files
- Recursive imports supported (max 5 hops)
- Path-specific rules in `.claude/rules/` with `paths` frontmatter field
- Home directory expansion: `~` supported
- Relative paths resolve relative to importing file, not working directory

**Locations (by precedence):**

| Memory Type                | Location                                                                                                                                                  | Purpose                               | Shared With                |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | -------------------------- |
| **Managed policy**         | macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`<br />Linux: `/etc/claude-code/CLAUDE.md`<br />Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | Organization-wide instructions        | All users in organization  |
| **Project memory**         | `./CLAUDE.md` or `./.claude/CLAUDE.md`                                                                                                                    | Team-shared instructions              | Team via source control    |
| **Project rules**          | `./.claude/rules/*.md`                                                                                                                                    | Modular, topic-specific rules         | Team via source control    |
| **User memory**            | `~/.claude/CLAUDE.md`                                                                                                                                     | Personal preferences                  | Just you (all projects)    |
| **Project memory (local)** | `./CLAUDE.local.md`                                                                                                                                       | Personal project-specific preferences | Just you (current project) |

**Recursive Discovery:**

Claude Code reads memories recursively: starting in cwd, it recurses up to (but not including) root directory and reads any CLAUDE.md or CLAUDE.local.md files it finds. This is convenient when running Claude Code in subdirectories with memories in parent directories.

Claude also discovers CLAUDE.md nested in subtrees under current working directory. These are only included when Claude reads files in those subtrees.

**Frontmatter for `.claude/rules/*.md`:**

| Field | Type          | Required | Description                         |
| ----- | ------------- | -------- | ----------------------------------- |
| paths | array[string] | No       | Glob patterns for conditional rules |

**Glob Patterns:**

Supported patterns for `paths` field:

| Pattern             | Matches                                  |
| ------------------- | ---------------------------------------- |
| `**/*.ts`           | All TypeScript files in any directory    |
| `src/**/*`          | All files under `src/` directory         |
| `*.md`              | Markdown files in project root           |
| `src/**/*.{ts,tsx}` | Multiple extensions via brace expansion  |
| `{src,lib}/**/*.ts` | Multiple directories via brace expansion |

**Additional Directories:**

The `--add-dir` flag gives Claude access to additional directories. By default, CLAUDE.md files from these directories are not loaded. To also load memory files from additional directories, set `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`:

```bash
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ../shared-config
```

**Symlinks:**

The `.claude/rules/` directory supports symlinks for sharing rules across projects. Circular symlinks are detected and handled gracefully.

---

### Settings

**File:** `settings.json` (multiple scopes)

**Configuration Scopes:**

| Scope   | Location                             | Who it affects           | Shared with team?    |
| ------- | ------------------------------------ | ------------------------ | -------------------- |
| Managed | System-level `managed-settings.json` | All users on machine     | Yes (deployed by IT) |
| User    | `~/.claude/settings.json`            | You, across all projects | No                   |
| Project | `.claude/settings.json`              | All collaborators        | Yes (committed)      |
| Local   | `.claude/settings.local.json`        | You, in this repository  | No (gitignored)      |

**Precedence:**

1. Managed (highest) - cannot be overridden
2. Command line arguments
3. Local
4. Project
5. User (lowest)

**Permission Settings:**

| Field       | Type          | Description                              |
| ----------- | ------------- | ---------------------------------------- |
| permissions | object        | Permission configuration (see below)     |
| allow       | array[string] | Permission rules to allow                |
| ask         | array[string] | Permission rules to ask for confirmation |
| deny        | array[string] | Permission rules to deny                 |
| defaultMode | string        | Default permission mode                  |

---

## Hooks

**File:** `.claude/hooks/hooks.json` (in plugins) or via `hooks` field in skills/agents/settings

**Lifecycle Events:**

Hooks fire at specific points during Claude Code's lifecycle:

| Event                | When it fires                                        | Matcher Support     |
| -------------------- | ---------------------------------------------------- | ------------------- |
| `SessionStart`       | When a session begins or resumes                     | Session source type |
| `UserPromptSubmit`   | When you submit a prompt, before Claude processes it | No                  |
| `PreToolUse`         | Before a tool call executes. Can block it            | Tool name           |
| `PermissionRequest`  | When a permission dialog appears                     | Tool name           |
| `PostToolUse`        | After a tool call succeeds                           | Tool name           |
| `PostToolUseFailure` | After a tool call fails                              | Tool name           |
| `Notification`       | When Claude Code sends a notification                | Notification type   |
| `SubagentStart`      | When a subagent is spawned                           | Agent type          |
| `SubagentStop`       | When a subagent finishes                             | Agent type          |
| `Stop`               | When Claude finishes responding                      | No                  |
| `PreCompact`         | Before context compaction                            | Compaction trigger  |
| `SessionEnd`         | When a session terminates                            | Session end reason  |

**Configuration Format:**

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "Bash|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/script.sh",
            "timeout": 30,
            "statusMessage": "Running hook..."
          }
        ]
      }
    ]
  }
}
```

**Hook Locations:**

| Location                                 | Scope                     | Shareable                      |
| ---------------------------------------- | ------------------------- | ------------------------------ |
| `~/.claude/settings.json`                | All your projects         | No, local to your machine      |
| `.claude/settings.json`                  | Single project            | Yes, can be committed to repo  |
| `.claude/settings.local.json`            | Single project            | No, gitignored                 |
| Managed policy settings                  | Organization-wide         | Yes, admin-controlled          |
| Plugin `hooks/hooks.json`                | When plugin is enabled    | Yes, bundled with plugin       |
| Skill or agent frontmatter (hooks field) | While component is active | Yes, defined in component file |

**Hook Types:**

| Type      | Description                                                                                  |
| --------- | -------------------------------------------------------------------------------------------- |
| `command` | Execute shell commands. Receives JSON input on stdin, communicates via exit codes and stdout |
| `prompt`  | Send prompt to LLM for single-turn evaluation. Uses `$ARGUMENTS` placeholder for input JSON  |
| `agent`   | Spawn subagent that can use tools like Read, Grep, and Glob to verify conditions             |

**Common Hook Fields:**

| Field           | Required | Default   | Description                                                                      |
| --------------- | -------- | --------- | -------------------------------------------------------------------------------- |
| `type`          | yes      | -         | `"command"`, `"prompt"`, or `"agent"`                                            |
| `timeout`       | no       | 600/30/60 | Seconds before canceling. Defaults: 600 for command, 30 for prompt, 60 for agent |
| `statusMessage` | no       | -         | Custom spinner message displayed while hook runs                                 |
| `once`          | no       | -         | If `true`, runs only once per session then is removed (skills only)              |

**Command Hook Fields:**

| Field     | Required | Description                                    |
| --------- | -------- | ---------------------------------------------- |
| `command` | yes      | Shell command to execute                       |
| `async`   | no       | If `true`, runs in background without blocking |

**Prompt/Agent Hook Fields:**

| Field    | Required | Description                                                                       |
| -------- | -------- | --------------------------------------------------------------------------------- |
| `prompt` | yes      | Prompt text to send to model. Use `$ARGUMENTS` as placeholder for hook input JSON |
| `model`  | no       | Model to use for evaluation. Defaults to a fast model                             |

**Environment Variables:**

- `$CLAUDE_PROJECT_DIR`: Project root directory (wrap in quotes for paths with spaces)
- `${CLAUDE_PLUGIN_ROOT}`: Plugin's root directory for bundled scripts
- `$CLAUDE_CODE_REMOTE`: Set to `"true"` in remote web environments

**Exit Code Behavior:**

| Exit Code | Effect                                                                        |
| --------- | ----------------------------------------------------------------------------- |
| `0`       | Success. Claude Code parses stdout for JSON output fields (decision control)  |
| `2`       | Blocking error. stderr shown to Claude, action blocked (varies by event type) |
| Other     | Non-blocking error. stderr shown in verbose mode, execution continues         |

---

## Plugins

**File:** `.claude-plugin/plugin.json`

**Plugin Structure:**

```markdown
my-plugin/
├── .claude-plugin/
│ └── plugin.json # Required: plugin manifest
├── commands/ # Default command location
├── agents/ # Custom agent definitions
├── skills/ # Agent Skills (SKILL.md files)
├── hooks/ # Hook configurations (hooks.json)
├── .mcp.json # MCP server definitions
├── .lsp.json # LSP server configurations
└── scripts/ # Hook and utility scripts
```

**Plugin Manifest Fields:**

| Field         | Type          | Required    | Description                                                                                              |
| ------------- | ------------- | ----------- | -------------------------------------------------------------------------------------------------------- |
| `name`        | string        | Yes         | Unique identifier (kebab-case, no spaces). Skills are prefixed with this (e.g., `/my-plugin:skill-name`) |
| `version`     | string        | Yes         | Semantic version (MAJOR.MINOR.PATCH) for tracking releases                                               |
| `description` | string        | Recommended | Brief explanation of plugin purpose, shown in plugin manager                                             |
| `author`      | object        | No          | Author information (name, email, url)                                                                    |
| `homepage`    | string        | No          | Documentation URL                                                                                        |
| `repository`  | string        | No          | Source code URL                                                                                          |
| `license`     | string        | No          | License identifier (e.g., "MIT", "Apache-2.0")                                                           |
| `keywords`    | array[string] | No          | Discovery tags for marketplace                                                                           |

**Component Path Fields:**

| Field          | Type   | Description |
| -------------- | ------ | ----------- | ------------------------------------------------------------------------------- |
| `commands`     | string | array       | Additional command files/directories (relative to plugin root, start with `./`) |
| `agents`       | string | array       | Additional agent files (relative to plugin root, start with `./`)               |
| `skills`       | string | array       | Additional skill directories (relative to plugin root, start with `./`)         |
| `hooks`        | string | object      | Hook config path (relative to plugin root) or inline configuration              |
| `mcpServers`   | string | object      | MCP config path (relative to plugin root) or inline configuration               |
| `lspServers`   | string | object      | LSP config path (relative to plugin root) or inline configuration               |
| `outputStyles` | string | array       | Additional output style files/directories                                       |

**Plugin Scopes:**

| Scope     | Settings file                 | Use case                                       |
| --------- | ----------------------------- | ---------------------------------------------- |
| `user`    | `~/.claude/settings.json`     | Personal plugins available across all projects |
| `project` | `.claude/settings.json`       | Team plugins shared via version control        |
| `local`   | `.claude/settings.local.json` | Project-specific plugins, gitignored           |
| `managed` | `managed-settings.json`       | Managed plugins (read-only, update only)       |

**Skill Naming in Plugins:**

- Plugin skills are namespaced: `/plugin-name:skill-name`
- Prevents conflicts when multiple plugins have skills with same name
- To change namespace prefix, update `name` field in `plugin.json`

**Migration from Standalone:**

Standalone configuration (`.claude/` directory) can be converted to plugin structure:

1. Create plugin directory with `.claude-plugin/plugin.json` manifest
2. Copy existing `commands/`, `agents/`, `skills/`, `hooks/` to plugin root
3. Migrate hooks from settings files to `hooks/hooks.json`
4. Test with `--plugin-dir ./my-plugin`

---

## CLI Arguments

**Configuration-Relevant Flags:**

| Flag                | Description                                                               |
| ------------------- | ------------------------------------------------------------------------- |
| `--allowedTools`    | Tools Claude can use without approval (comma-separated or multiple flags) |
| `--disallowedTools` | Tools to explicitly deny (comma-separated or multiple flags)              |
| `--tools`           | Combined tool allow/deny list in JSON format                              |
| `--model`           | Override model selection for current session                              |
| `--agent`           | Start with specific agent (subagent)                                      |

**Tool Configuration Priority:**

1. CLI flags override all other sources
2. Settings files override defaults
3. Skill/agent frontmatter applies when component is active

**Examples:**

```bash
# Allow specific tools
claude --allowedTools Bash,Read,Grep

# Disallow dangerous commands
claude --disallowedTools "Bash(rm *)" "Bash(rm -rf *)"

# JSON format for complex tool rules
claude --tools '{"Bash": {"*": "allow", "curl *": "deny"}, "Read": {"*.env": "deny"}}'

# Override model
claude --model haiku

# Start with specific subagent
claude --agent Explore
```

---

## Permission System

### Rule Syntax

`Tool` or `Tool(specifier)`

### Evaluation Order

1. Deny rules (checked first)
2. Ask rules (checked second)
3. Allow rules (checked last)

### Permission Modes

| Mode              | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| default           | Standard permission checking with prompts                    |
| acceptEdits       | Auto-accept file edits                                       |
| dontAsk           | Auto-deny permission prompts (explicitly allowed tools work) |
| bypassPermissions | Skip all permission checks                                   |
| plan              | Plan mode (read-only exploration)                            |

### Tool Names (PascalCase)

**Built-in Tools:**

- `Bash` - Execute shell commands
- `Read` - Read file contents
- `Write` - Create/overwrite files
- `Edit` - Modify files (exact string replacement)
- `Grep` - Search file contents
- `Glob` - Find files by pattern
- `List` - List directory contents
- `Patch` - Apply patch files
- `WebFetch` - Fetch web content
- `Task` - Launch subagents
- `Skill` - Load skills
- `TodoRead`, `TodoWrite` - Manage todo lists
- `Question` - Ask user questions
- `WebSearch` - Search the web
- `Notebook` - Interactive notebook execution
- `AskUserQuestion` - Ask user clarifying questions

**MCP Tools:**

Format: `mcp__<server>__<tool>`

- `mcp__memory__create_entities` - Create memory entities
- `mcp__filesystem__read_file` - Read files via filesystem server
- `mcp__github__search_repositories` - Search GitHub repositories

### Specifier Examples

- `Bash` - All bash commands
- `Bash(npm run build)` - Exact command match
- `Bash(*)` - Equivalent to Bash
- `Bash(git *)` - Git commands with any arguments
- `Read(./.env)` - Specific file
- `WebFetch(domain:example.com)` - Specific domain
- `Edit|Write` - Multiple tools
- `mcp__memory__.*` - All memory server tools

### Wildcards

- `*` matches zero or more characters
- `?` matches exactly one character
- `**` matches any number of directories

---

## Tool Configuration

### Configuration Methods

- Via `tools` field in subagent
- Via `allowed-tools` in skill frontmatter
- Via `--allowedTools` CLI flag
- Via `--disallowedTools` CLI flag
- Via `--tools` CLI flag

---

## Model Identifiers

### Format

Full model name or alias

### Aliases

| Alias        | Description                                    |
| ------------ | ---------------------------------------------- |
| `default`    | Use default model                              |
| `sonnet`     | Use Sonnet model                               |
| `opus`       | Use Opus model                                 |
| `haiku`      | Use Haiku model                                |
| `sonnet[1m]` | Use Sonnet with 1M context (extended thinking) |
| `opusplan`   | Use Opus for planning (specialized)            |
| `inherit`    | Inherit default model (default for subagents)  |

### Full Names

- `claude-sonnet-4-5-20250929` - Specific Sonnet version
- `claude-3-5-sonnet-20241022` - Sonnet 3.5
- `claude-3-opus-20240229` - Opus 3
- `claude-3-haiku-20240307` - Haiku 3

### Examples

```yaml
model: sonnet              # Alias
model: opus                # Alias
model: default             # Default model
model: sonnet[1m]          # Extended thinking
model: claude-sonnet-4-5-20250929  # Full name
model: inherit             # Inherit default
```

---

## YAML Examples

### Skill Example

```yaml
---
name: git-release
description: Create consistent releases and changelogs
disable-model-invocation: true
allowed-tools: Bash(gh *)
context: fork
agent: general-purpose
---

## What I do
- Draft release notes from merged PRs
- Propose a version bump
- Provide a copy-pasteable `gh release create` command

## When to use me
Use this when you are preparing a tagged release.
Ask clarifying questions if target versioning scheme is unclear.
```

### Subagent Example

```yaml
---
name: code-reviewer
description: Expert code review specialist. Proactively reviews code for quality, security, and maintainability.
tools: Read, Grep, Glob, Bash
model: sonnet
permissionMode: default
---

You are a senior code reviewer ensuring high standards of code quality and security.

When invoked:
1. Run git diff to see recent changes
2. Focus on modified files
3. Begin review immediately

Review checklist:
- Code is clear and readable
- Functions and variables are well-named
- No duplicated code
- Proper error handling
- No exposed secrets or API keys
- Input validation implemented
- Good test coverage
- Performance considerations addressed

Provide feedback organized by priority:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (consider improving)

Include specific examples of how to fix issues.
```

### Settings Example

```json
{
  "permissions": {
    "allow": ["Bash(npm run lint)", "Bash(npm run test *)", "Read(~/.zshrc)"],
    "deny": [
      "Bash(curl *)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  },
  "env": {
    "FOO": "bar"
  },
  "companyAnnouncements": [
    "Welcome to our team! Review our code guidelines at docs.example.com"
  ],
  "cleanupPeriodDays": 30,
  "disableAllHooks": false
}
```

---

## Validation Constraints

### Skill Names

- Lowercase letters, numbers, hyphens only
- Max 64 characters
- No consecutive hyphens
- No starting/ending with hyphen

### Subagent Names

- Lowercase letters and hyphens
- Must be unique

### Permissions

- Rule evaluation is order-dependent
- Deny rules always take precedence
- Patterns are simple wildcards (`*`, `?`)

### File Paths

- Imports support recursive loading (max 5 hops)
- Home directory expansion: `~` supported
- Relative paths resolve from importing file, not working directory

### Settings JSON

- Must be valid JSON
- Optional `$schema` field for validation support
- Settings files auto-backed up (5 most recent)
