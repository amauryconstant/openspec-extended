# OpenCode Documentation

Platform documentation for AI coding assistant configuration

## Official Documentation Sources

- [Agents](https://opencode.ai/docs/agents) - Agent configuration
- [Skills](https://opencode.ai/docs/skills) - Agent skills format
- [Permissions](https://opencode.ai/docs/permissions) - Permission system
- [Commands](https://opencode.ai/docs/commands) - Custom commands
- [Config](https://opencode.ai/docs/config) - Global configuration
- [MCP Servers](https://opencode.ai/docs/mcp-servers) - Model Context Protocol integration

---

## Document Types

### Agents

**Files:** `opencode.json` or `.opencode/agents/*.md`

**Frontmatter Fields (Markdown):**

| Field       | Type    | Required | Default | Description                                                     |
| ----------- | ------- | -------- | ------- | --------------------------------------------------------------- |
| description | string  | Yes      | -       | Brief description of what agent does (1-1024 characters)        |
| mode        | string  | No       | `all`   | `primary`, `subagent`, or `all`                                 |
| model       | string  | No       | -       | Model: `provider/model-id` format                               |
| prompt      | string  | No       | -       | System prompt file path or content                              |
| tools       | object  | No       | -       | Tools available to agent (lowercase tool names, boolean values) |
| permissions | object  | No       | -       | Permission overrides                                            |
| temperature | number  | No       | model   | Temperature (0.0-1.0)                                           |
| steps       | number  | No       | -       | Maximum agentic iterations (must be > 0)                        |
| disable     | boolean | No       | `false` | Disable agent                                                   |
| hidden      | boolean | No       | `false` | Hide from `@` autocomplete (subagents only)                     |
| top_p       | number  | No       | -       | Nucleus sampling parameter (0.0-1.0)                            |

**Body (Markdown):** Markdown content with system prompt instructions

**JSON Structure:**

```json
{
  "agent": {
    "agent-name": {
      "description": "string",
      "mode": "primary|subagent|all",
      "model": "provider/model-id",
      "prompt": "file or string",
      "tools": {
        "tool-name": true/false
      },
      "permissions": {
        "tool": "allow|ask|deny"
      },
      "temperature": 0.5,
      "steps": 10,
      "top_p": 0.9
    }
  }
}
```

**Built-in Agents:**

| Agent   | Mode     | Description                                                                |
| ------- | -------- | -------------------------------------------------------------------------- |
| Build   | primary  | Default agent with all tools enabled                                       |
| Plan    | primary  | Restricted agent for analysis and planning (edits, bash ask by default)    |
| General | subagent | General-purpose agent for research and multi-step tasks (full tool access) |
| Explore | subagent | Fast, read-only agent for exploring codebases (no file modifications)      |

---

### Skills

**Files:** `.opencode/skills/<name>/SKILL.md` or `~/.claude/skills/`

**Discovery Order:**

1. Project local: `.opencode/skills/<name>/SKILL.md` (walks up to git worktree)
2. Global OpenCode: `~/.config/opencode/skills/<name>/SKILL.md`
3. Project Claude-compatible: `.claude/skills/<name>/SKILL.md`
4. Global Claude-compatible: `~/.claude/skills/<name>/SKILL.md`

**Frontmatter Fields:**

| Field         | Type   | Required | Description                         |
| ------------- | ------ | -------- | ----------------------------------- |
| name          | string | Yes      | Skill identifier (1-64 characters)  |
| description   | string | Yes      | What skill does (1-1024 characters) |
| license       | string | No       | License identifier                  |
| compatibility | string | No       | Platform compatibility              |
| metadata      | object | No       | String-to-string map for metadata   |

**Naming Constraints:**

- 1-64 characters
- Lowercase alphanumeric with single hyphen separators
- Cannot start or end with `-`
- No consecutive `--`
- Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Must match directory name
- Must be unique across all discovery locations

**Body:** Markdown content with instructions

**Permission Configuration:**

```json
{
  "permission": {
    "skill": {
      "*": "allow",
      "pr-review": "allow",
      "internal-*": "deny",
      "experimental-*": "ask"
    }
  }
}
```

| Permission | Behavior                                  |
| ---------- | ----------------------------------------- |
| allow      | Skill loads immediately                   |
| deny       | Skill hidden from agent, access rejected  |
| ask        | User prompted for approval before loading |

---

### Commands

**Files:** `opencode.json` or `.opencode/commands/*.md`

**Frontmatter Fields (Markdown):**

| Field       | Type    | Required | Description                 |
| ----------- | ------- | -------- | --------------------------- |
| description | string  | No       | Description shown in TUI    |
| agent       | string  | No       | Which agent should execute  |
| subtask     | boolean | No       | Force subagent invocation   |
| model       | string  | No       | Override model              |
| template    | string  | Yes      | Prompt template (JSON only) |

**Body (Markdown):** Markdown content with instructions

**String Substitutions:**

- `$ARGUMENTS` - All arguments
- `$1`, `$2`, `$3` - Positional arguments
- `` `!command` `` - Shell output injection
- `@filename` - File content inclusion

**Command Override:** Custom commands can override built-in commands (e.g., `/init`, `/undo`, `/redo`, `/share`, `/help`)

---

### Memory

**Note:** OpenCode does not have a native Memory document type like Claude Code. Memory-like functionality is provided through:

- **Rules files:** `AGENTS.md` or `CLAUDE.md` in project root for project context
- **Instructions configuration:** Array of files/globs in config (e.g., `CONTRIBUTING.md`, docs files)
- **Prompt field:** Agents can reference prompt files or include prompt content directly

---

## Permissions

**Configuration:** Configured in JSON

**Permission Actions:**

- `"allow"` - Run without approval
- `"ask"` - Prompt for approval
- `"deny"` - Block the action

**Available Permissions:**

| Permission         | Matches                   | Default | Notes                                |
| ------------------ | ------------------------- | ------- | ------------------------------------ |
| read               | File path                 | allow   | `.env` files denied by default       |
| edit               | All file modifications    | allow   | Covers edit, write, patch, multiedit |
| glob               | Glob pattern              | allow   |                                      |
| grep               | Regex pattern             | allow   |                                      |
| list               | Directory path            | allow   |                                      |
| bash               | Parsed commands           | allow   |                                      |
| task               | Subagent type             | allow   |                                      |
| skill              | Skill name                | allow   |                                      |
| lsp                | Non-granular              | allow   |                                      |
| todoread           | Todo list operations      | allow   | Disabled for subagents by default    |
| todowrite          | Todo list operations      | allow   | Disabled for subagents by default    |
| webfetch           | URL                       | allow   |                                      |
| websearch          | Query                     | allow   |                                      |
| codesearch         | Query                     | allow   |                                      |
| external_directory | Paths outside working dir | ask     | Inherits workspace defaults          |
| doom_loop          | Repeated tool calls       | ask     | 3 identical calls in a row           |

**Special `.env` Rules:**

```json
{
  "permission": {
    "read": {
      "*": "allow",
      "*.env": "deny",
      "*.env.*": "deny",
      "*.env.example": "allow"
    }
  }
}
```

**Structure:**

```json
{
  "permission": {
    "bash": {
      "*": "ask",
      "git *": "allow",
      "grep *": "allow"
    },
    "edit": {
      "*.env": "deny",
      "*.mdx": "allow"
    },
    "external_directory": {
      "~/projects/personal/**": "allow"
    }
  }
}
```

**Pattern Matching:**

- Simple wildcard: `*`, `?`
- Last matching rule wins
- Home directory expansion: `~/projects/*` or `$HOME/projects/*`
- External directories inherit workspace defaults

**Agent-Specific Permissions:**

```json
{
  "agent": {
    "build": {
      "permission": {
        "edit": "ask",
        "bash": {
          "git push": "deny"
        }
      }
    }
  }
}
```

---

## Tools

**Built-in Tools (15 total):**

| Tool               | Description                                                |
| ------------------ | ---------------------------------------------------------- |
| bash               | Execute shell commands                                     |
| edit               | Modify files (covers edit, write, patch, multiedit)        |
| write              | Create/overwrite files                                     |
| read               | Read files                                                 |
| grep               | Search content using regex                                 |
| glob               | Find files by pattern                                      |
| list               | List directories                                           |
| lsp (experimental) | LSP queries (requires OPENCODE_EXPERIMENTAL_LSP_TOOL=true) |
| patch              | Apply patches                                              |
| skill              | Load skills                                                |
| todowrite          | Manage todo lists                                          |
| todoread           | Read todo lists                                            |
| webfetch           | Fetch web content                                          |
| websearch          | Web search                                                 |
| codesearch         | Code search                                                |
| question           | Ask questions                                              |

**Configuration:**

- Via `permission` object in config
- Via `tools` object in agent
- Via wildcards for MCP servers: `mymcp_*`

**Note:** Tool names are **lowercase** in OpenCode

---

## MCP Servers

**Format:** JSON or JSONC configuration in `opencode.json`

**Purpose:** Add external tools using Model Context Protocol (MCP). MCP tools are automatically available to LLM alongside built-in tools.

**Configuration Location:** Within `mcp` object in config file

```json
{
  "mcp": {
    "server-name": {
      // ... configuration
    }
  }
}
```

### Local MCP Servers

**Type:** `type: "local"`

**Purpose:** Run MCP server as a local process (command or Node module)

**Fields:**

| Field         | Type          | Required | Default | Description                                           |
| ------------- | ------------- | -------- | ------- | ----------------------------------------------------- |
| `type`        | string        | Yes      | -       | Must be `"local"`                                     |
| `command`     | array[string] | Yes      | -       | Command and arguments to run MCP server               |
| `enabled`     | boolean       | No       | `true`  | Enable or disable MCP server on startup               |
| `timeout`     | number        | No       | 5000    | Timeout in ms for fetching tools (defaults to 5000ms) |
| `environment` | object        | No       | -       | Environment variables to set when running server      |

**Example:**

```json
{
  "mcp": {
    "my-local-server": {
      "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-everything"],
      "enabled": true,
      "environment": {
        "MY_ENV_VAR": "my_env_var_value"
      }
    }
  }
}
```

### Remote MCP Servers

**Type:** `type: "remote"`

**Purpose:** Connect to MCP server over HTTP

**Fields:**

| Field     | Type    | Required | Default | Description                                           |
| --------- | ------- | -------- | ------- | ----------------------------------------------------- | ---------------------------------------------- |
| `type`    | string  | Yes      | -       | Must be `"remote"`                                    |
| `url`     | string  | Yes      | -       | URL of remote MCP server                              |
| `enabled` | boolean | No       | `true`  | Enable or disable MCP server on startup               |
| `headers` | object  | No       | -       | Headers to send with request                          |
| `oauth`   | object  | false    | No      | -                                                     | OAuth authentication configuration (see below) |
| `timeout` | number  | No       | 5000    | Timeout in ms for fetching tools (defaults to 5000ms) |

**Example:**

```json
{
  "mcp": {
    "my-remote-server": {
      "type": "remote",
      "url": "https://mcp.example.com/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer MY_API_KEY"
      }
    }
  }
}
```

### OAuth Configuration

**Purpose:** Automatic authentication for remote MCP servers using RFC 7591 Dynamic Client Registration

**OAuth Fields:**

| Field          | Type   | Required | Description                                                      |
| -------------- | ------ | -------- | ---------------------------------------------------------------- |
| `clientId`     | string | No       | OAuth client ID. If not provided, dynamic registration attempted |
| `clientSecret` | string | No       | OAuth client secret, if required by authorization server         |
| `scope`        | string | No       | OAuth scopes to request during authorization                     |

**Example with OAuth:**

```json
{
  "mcp": {
    "my-oauth-server": {
      "type": "remote",
      "url": "https://mcp.example.com/mcp",
      "oauth": {
        "clientId": "{env:MY_MCP_CLIENT_ID}",
        "clientSecret": "{env:MY_MCP_CLIENT_SECRET}",
        "scope": "tools:read tools:execute"
      }
    }
  }
}
```

**Example disabling OAuth (use API keys instead):**

```json
{
  "mcp": {
    "my-api-key-server": {
      "type": "remote",
      "url": "https://mcp.example.com/mcp",
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:MY_API_KEY}"
      }
    }
  }
}
```

### MCP Tool Management

**Global Disable:** Disable MCP tools globally in config

```json
{
  "mcp": {
    "my-mcp-server": {
      "type": "local",
      "command": ["bun", "x", "my-mcp-command"],
      "enabled": true
    }
  },
  "tools": {
    "my-mcp*": false
  }
}
```

**Glob Patterns:** Disable all tools for specific server

| Pattern   | Matches                              |
| --------- | ------------------------------------ |
| `my-mcp*` | All tools from server named "my-mcp" |

**Per-Agent Enable:** Enable MCP tools for specific agent only

```json
{
  "mcp": {
    "my-mcp": {
      "type": "local",
      "command": ["bun", "x", "my-mcp-command"],
      "enabled": true
    }
  },
  "tools": {
    "my-mcp*": false
  },
  "agent": {
    "my-agent": {
      "tools": {
        "my-mcp*": true
      }
    }
  }
}
```

---

## Models

**Format:** `provider/model-id`

**Examples:**

- `anthropic/claude-sonnet-4-5`
- `opencode/gpt-5.1-codex`
- `lmstudio/google/gemma-3n-e4b`

**Loading Priority Order (4 levels):**

1. `--model` or `-m` CLI flag
2. `model` key in OpenCode config
3. Last used model
4. First model using internal priority

**Provider Configuration:**

```json
{
  "provider": {
    "openai": {
      "options": {
        "baseURL": "https://api.openai.com/v1",
        "timeout": 600000,
        "setCacheKey": true
      },
      "models": {
        "gpt-5": {
          "id": "custom-model-id",
          "options": {
            "reasoningEffort": "high",
            "textVerbosity": "low",
            "reasoningSummary": "auto"
          }
        }
      }
    }
  }
}
```

**Provider Options:**

- `baseURL`: Custom endpoint URL
- `timeout`: Request timeout in ms (default: 300000, set to false to disable)
- `setCacheKey`: Ensure cache key always set

**Amazon Bedrock Options:**

Amazon Bedrock supports AWS-specific configuration:

```json
{
  "provider": {
    "amazon-bedrock": {
      "options": {
        "region": "us-east-1",
        "profile": "my-aws-profile",
        "endpoint": "https://bedrock-runtime.us-east-1.vpce-xxxxx.amazonaws.com"
      }
    }
  }
}
```

- `region`: AWS region for Bedrock (defaults to `AWS_REGION` env var or `us-east-1`)
- `profile`: AWS named profile from `~/.aws/credentials` (defaults to `AWS_PROFILE` env var)
- `endpoint`: Custom endpoint URL for VPC endpoints. An alias for generic `baseURL` option using AWS-specific terminology. If both are specified, `endpoint` takes precedence.

**small_model Option:**

The `small_model` option configures a separate model for lightweight tasks like title generation. By default, OpenCode tries to use a cheaper model if one is available from your provider, otherwise it falls back to your main model.

---

## Config Schema

**Format:** JSON or JSONC (JSON with Comments)

**Schema:** Defined at https://opencode.ai/config.json

### Configuration Precedence Order

Config sources are merged (not replaced) in this order (later sources override earlier ones):

1. **Remote config** (from `.well-known/opencode`) - Organizational defaults
2. **Global config** (`~/.config/opencode/opencode.json`) - User preferences
3. **Custom config** (`OPENCODE_CONFIG` env var) - Custom overrides
4. **Project config** (`opencode.json` or `opencode.jsonc` in project) - Project-specific settings
5. **`.opencode` directories** (agents/, commands/, plugins/, etc.) - Component definitions
6. **Inline config** (`OPENCODE_CONFIG_CONTENT` env var) - Runtime overrides

### Configuration Locations

| Location                           | Scope                 | Shareable                     |
| ---------------------------------- | --------------------- | ----------------------------- |
| `.well-known/opencode`             | Organization (remote) | Yes, server-provided          |
| `~/.config/opencode/opencode.json` | Global user           | No, local to machine          |
| `OPENCODE_CONFIG` env var          | Custom path           | No, user-specified            |
| `opencode.json` (project root)     | Project               | Yes, can be committed to repo |
| `opencode.jsonc` (project root)    | Project               | Yes, can be committed to repo |
| `.opencode/` directories           | Component             | Yes, can be committed to repo |
| `OPENCODE_CONFIG_CONTENT` env var  | Runtime override      | No, in-memory only            |

### Schema Sections Relevant to Document Types

| Section            | Description                                     |
| ------------------ | ----------------------------------------------- |
| agents             | Agent definitions                               |
| commands           | Custom commands                                 |
| permissions        | Permission rules                                |
| instructions       | Instruction files (CONTRIBUTING.md, etc.)       |
| models             | Provider and model configuration                |
| mcp                | MCP server configurations                       |
| tools              | Global tool overrides                           |
| tui                | TUI-specific settings                           |
| server             | Server configuration for `opencode serve`       |
| themes             | Theme configuration                             |
| agent              | Per-agent settings                              |
| default_agent      | Default agent selection                         |
| sharing            | Share feature configuration                     |
| keybinds           | Custom keybindings                              |
| formatters         | Code formatter configuration                    |
| commands           | Custom commands (CLI slash commands)            |
| compaction         | Context compaction behavior                     |
| watcher            | File watcher ignore patterns                    |
| plugins            | Plugin configuration (npm packages or paths)    |
| instructions       | Instruction files (CONTRIBUTING.md, docs/\*.md) |
| disabled_providers | Explicitly disabled providers                   |
| enabled_providers  | Allowlist of enabled providers                  |
| experimental       | Experimental features                           |

### Configuration Properties

**`$schema`** - JSON schema URL for validation

```json
{
  "$schema": "https://opencode.ai/config.json",
  ...
}
```

**`tui`** - TUI-specific settings

```json
{
  "tui": {
    "scroll_speed": 3,
    "scroll_acceleration": {
      "enabled": true
    },
    "diff_style": "auto"
  }
}
```

- `scroll_speed`: Multiplier (default: 3, min: 1)
- `scroll_acceleration.enabled`: Enable macOS-style acceleration
- `diff_style`: `"auto"` or `"stacked"`

**`server`** - Server configuration for `opencode serve`

```json
{
  "server": {
    "port": 4096,
    "hostname": "0.0.0.0",
    "mdns": true,
    "mdnsDomain": "myproject.local",
    "cors": ["http://localhost:5173"]
  }
}
```

**`tools`** - Global tool availability

```json
{
  "tools": {
    "write": false,
    "bash": false
  }
}
```

**`themes`** - Theme selection

```json
{
  "theme": "opencode"
}
```

**`keybinds`** - Custom keybindings

```json
{
  "keybinds": {}
}
```

**`formatters`** - Code formatter configuration

```json
{
  "formatter": {
    "prettier": {
      "disabled": true
    },
    "custom-prettier": {
      "command": ["npx", "prettier", "--write", "$FILE"],
      "environment": {
        "NODE_ENV": "development"
      },
      "extensions": [".js", ".ts", ".jsx", ".tsx"]
    }
  }
}
```

**`sharing`** - Share feature configuration

```json
{
  "share": "manual"
}
```

Values: `"manual"` (default), `"auto"`, `"disabled"`

**`compaction`** - Context compaction

```json
{
  "compaction": {
    "auto": true,
    "prune": true
  }
}
```

**`watcher`** - File watcher ignore patterns

```json
{
  "watcher": {
    "ignore": ["node_modules/**", "dist/**", ".git/**"]
  }
}
```

**`plugins`** - Plugin configuration

```json
{
  "plugin": ["opencode-helicone-session", "@my-org/custom-plugin"]
}
```

**`instructions`** - Instruction files

```json
{
  "instructions": [
    "CONTRIBUTING.md",
    "docs/guidelines.md",
    ".cursor/rules/*.md"
  ]
}
```

**`disabled_providers`** - Explicitly disabled providers

```json
{
  "disabled_providers": ["openai", "gemini"]
}
```

**`enabled_providers`** - Allowlist of enabled providers

```json
{
  "enabled_providers": ["anthropic", "openai"]
}
```

**`experimental`** - Experimental features

```json
{
  "experimental": {}
}
```

**Variable Substitution:**

Use `{env:VARIABLE_NAME}` for environment variables and `{file:path/to/file}` for file contents:

```json
{
  "model": "{env:OPENCODE_MODEL}",
  "provider": {
    "anthropic": {
      "apiKey": "{file:~/.secrets/opencode-key}"
    }
  }
}
```

---

## Permission System

### Permission Object Structure

OpenCode uses a **structured permission object** with tool-specific configurations:

```json
{
  "permission": {
    "bash": {
      "*": "ask",
      "git *": "allow",
      "git push *": "deny"
    }
  }
}
```

**Key Points:**

- `bash` is an **object with command keys**, not a simple string value
- Supports pattern matching with wildcards (`*`, `?`)
- Last matching rule wins
- Can have tool-specific overrides
- No wildcard support for generic permissions (cannot use `"*": "allow"` globally)

---

## Agent Modes

### Mode Values

- **primary** - Main agent you interact with directly (cycle with Tab)
- **subagent** - Specialized assistant invoked by primary or via `@` mention
- **all** - Can function as either (default if not specified)

### Built-in Agents Details

| Agent   | Mode     | Tools                         | Description                                                            |
| ------- | -------- | ----------------------------- | ---------------------------------------------------------------------- |
| Build   | primary  | All enabled                   | Default agent with all tools enabled, full access for development work |
| Plan    | primary  | Restricted                    | Analysis and planning with restrictions (edits, bash ask by default)   |
| General | subagent | All except todo               | Research and multi-step tasks, can make file changes                   |
| Explore | subagent | Read-only (no edits, no bash) | Fast codebase exploration, file patterns, content search, questions    |

---

## Validation Constraints

### Skill Names

- 1-64 characters
- Lowercase alphanumeric with single hyphen separators
- Cannot start or end with `-`
- No consecutive `--`
- Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Must match directory name
- Must be unique across all discovery locations

### Descriptions

- 1-1024 characters
- Should be specific for agent selection

### Temperature

- Range: 0.0 to 1.0
- Typical ranges:
  - 0.0-0.2: Focused/deterministic (code analysis, planning)
  - 0.3-0.5: Balanced (general development)
  - 0.6-1.0: Creative/variable (brainstorming, exploration)
- Model defaults if not specified: typically 0 for most models, 0.55 for Qwen

### Steps

- Must be > 0
- No upper limit specified
- When limit reached, agent receives system prompt to summarize and recommend remaining tasks

### Permissions

- Pattern matching with wildcards
- Last matching rule wins
- Home directory expansion supported
- External directories inherit workspace defaults

---

## YAML/JSON Examples

### Agent Example (JSON)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "build": {
      "mode": "primary",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "{file:./prompts/build.txt}",
      "tools": {
        "write": true,
        "edit": true,
        "bash": true
      }
    },
    "plan": {
      "mode": "primary",
      "model": "anthropic/claude-haiku-4-20250514",
      "tools": {
        "write": false,
        "edit": false,
        "bash": false
      }
    },
    "code-reviewer": {
      "description": "Reviews code for best practices and potential issues",
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "You are a code reviewer. Focus on security, performance, and maintainability.",
      "tools": {
        "write": false,
        "edit": false
      }
    }
  }
}
```

### Agent Example (Markdown)

```yaml
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
tools:
  write: false
  edit: false
  bash: false
permissions:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "git log*": allow
    "grep *": allow
  webfetch: deny
---

You are in code review mode. Focus on:
- Code quality and best practices
- Potential bugs and edge cases
- Performance implications
- Security considerations

Provide constructive feedback without making direct changes.
```

### Skill Example

```yaml
---
name: git-release
description: Create consistent releases and changelogs
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: github
---

## What I do
- Draft release notes from merged PRs
- Propose a version bump
- Provide a copy-pasteable `gh release create` command

## When to use me
Use this when you are preparing a tagged release.

Ask clarifying questions if the target versioning scheme is unclear.
```

### Permissions Example

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "bash": "ask",
    "edit": {
      "*.env": "deny",
      "*.mdx": "allow"
    },
    "external_directory": {
      "~/projects/personal/**": "allow"
    }
  }
}
```

---

## String Substitutions

### Commands

- `$ARGUMENTS` - All arguments
- `$1`, `$2`, `$3` - Positional arguments
- `` `!command` `` - Shell output injection
- `@filename` - File content inclusion

### File References

Use `{file:path}` syntax to include file content:

```json
{
  "prompt": "{file:./prompts/code-review.txt}"
}
```

---

## Edge Cases and Special Behaviors

### Agent Defaults

- If no `temperature` specified, uses model-specific defaults
- If no `model` specified, primary agents use global model, subagents use invoking agent's model
- If no `mode` specified, defaults to "all"

### Permission Last-Rule-Wins

Pattern matching is evaluated with the last matching rule taking precedence. Common pattern: place catch-all `*` rule first, more specific rules after.

### Skill Name Uniqueness

Skill names must be unique across all discovery locations (project `.opencode/skills/`, global `~/.config/opencode/skills/`, project `.claude/skills/`, global `~/.claude/skills/`)

### Config Merging

Configuration files are merged, not replaced. Non-conflicting settings from all configs are preserved. Later configs override earlier ones for conflicting keys only.

### Subtask Field Behavior

When `subtask: true` is set on a command, it forces subagent invocation even if the agent's `mode` is set to "primary". This prevents polluting the primary context.

### Todo Tools Default Disabled

`todoread` and `todowrite` tools are disabled for subagents by default, but can be enabled manually via permissions.

### File Hygiene

SKILL.md must be spelled in all caps. Unknown frontmatter fields in skills are silently ignored.

---

## Comparison with Claude Code

| Aspect            | Claude Code                    | OpenCode                               |
| ----------------- | ------------------------------ | -------------------------------------- |
| Tool Names        | PascalCase (`Bash`, `Read`)    | Lowercase (`bash`, `read`)             |
| Permission System | Enum (`permissionMode`)        | Object with tool-specific config       |
| Permission Values | `default`, `acceptEdits`, etc. | `allow`, `ask`, `deny`                 |
| Model Format      | Alias or full name             | `provider/model-id`                    |
| Tool Config       | Flat arrays                    | Boolean objects                        |
| Agent Modes       | Built-in types                 | `primary`, `subagent`, `all`           |
| Skills            | Optional `name` field          | Required `name` field                  |
| Additional Fields | `hooks` (lifecycle)            | `license`, `compatibility`, `metadata` |
| Temperature       | Not supported                  | Supported (0.0-1.0)                    |
| MaxSteps          | Not supported                  | `steps` supported (> 0)                |
| Hidden            | Not supported                  | Supported (boolean)                    |
| Memory            | Native document type           | Via rules files and instructions       |

---

## Validation Rules Summary

### Required Fields

- **Agent**: `description` required (JSON), optional in markdown frontmatter
- **Skill**: `name` and `description` required
- **Command**: `template` required in JSON format

### Format Constraints

- **Skill names**: `^[a-z0-9]+(-[a-z0-9]+)*$`, 1-64 chars
- **Descriptions**: 1-1024 characters
- **Temperature**: 0.0-1.0 range
- **Steps**: Must be > 0

### File Locations

- **Skills**: 4 discovery locations (project, global, Claude-compatible project, Claude-compatible global)
- **Agents**: `opencode.json` or `.opencode/agents/*.md` or `~/.config/opencode/agents/`
- **Commands**: `opencode.json` or `.opencode/commands/*.md` or `~/.config/opencode/commands/`

### Permission Pattern Matching

- Wildcards: `*` (zero or more), `?` (exactly one)
- Home directory expansion: `~` or `$HOME`
- Last matching rule wins
- External directories inherit workspace defaults

### Agent Types

- `primary`: Main agent, cycle with Tab, full tool access
- `subagent`: Specialized, invoked by primary or `@`, limited tools
- `all`: Can function as either (default)

### Tool Naming

- Built-in tools: lowercase (`bash`, `edit`, `read`, etc.)
- MCP tools: server_name_tool_name pattern
- Custom tools: filename or filename_exportname pattern

### Model Configuration

- Format: `provider/model-id`
- 4-level loading priority (CLI flag → config → last used → internal)
