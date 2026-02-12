# Official Documentation Sources Reference

This file maps research doc sections to verification sources.

## Hardcoded Context7 Libraries

- **Claude Code**: `/anthropics/claude-code`
- **OpenCode**: `/anomalyco/opencode`

## Claude Code Sources

| Research Section     | Official URL                                  | Context7 Library        | Context7 Query           | Fetch URL                                     |
| -------------------- | --------------------------------------------- | ----------------------- | ------------------------ | --------------------------------------------- |
| Skills frontmatter   | https://code.claude.com/docs/en/skills.md     | /anthropics/claude-code | skill frontmatter fields | https://code.claude.com/docs/en/skills.md     |
| Memory import syntax | https://code.claude.com/docs/en/memory.md     | /anthropics/claude-code | memory @path syntax      | https://code.claude.com/docs/en/memory.md     |
| Subagent tools       | https://code.claude.com/docs/en/sub-agents.md | /anthropics/claude-code | subagent tools field     | https://code.claude.com/docs/en/sub-agents.md |
| Permission modes     | https://code.claude.com/docs/en/settings.md   | /anthropics/claude-code | permissionMode values    | https://code.claude.com/docs/en/settings.md   |
| Hooks              | https://code.claude.com/docs/en/hooks        | /anthropics/claude-code | lifecycle events        | https://code.claude.com/docs/en/hooks        |
| Plugins            | https://code.claude.com/docs/en/plugins      | /anthropics/claude-code | plugin manifest        | https://code.claude.com/docs/en/plugins      |
| CLI Arguments       | https://code.claude.com/docs/en/settings.md   | /anthropics/claude-code | tool configuration flags | https://code.claude.com/docs/en/settings.md   |

## OpenCode Sources

| Research Section      | Official URL                         | Context7 Library    | Context7 Query           | Fetch URL                            |
| --------------------- | ------------------------------------ | ------------------- | ------------------------ | ------------------------------------ |
| Agents frontmatter    | https://opencode.ai/docs/agents      | /anomalyco/opencode | agent frontmatter        | https://opencode.ai/docs/agents      |
| Skills naming         | https://opencode.ai/docs/skills      | /anomalyco/opencode | skill naming constraints | https://opencode.ai/docs/skills      |
| Permissions structure | https://opencode.ai/docs/permissions | /anomalyco/opencode | permission object format | https://opencode.ai/docs/permissions |
| Commands template     | https://opencode.ai/docs/commands    | /anomalyco/opencode | command template field   | https://opencode.ai/docs/commands    |
| MCP Servers         | https://opencode.ai/docs/mcp-servers | /anomalyco/opencode | server configuration   | https://opencode.ai/docs/mcp-servers |
| Configuration        | https://opencode.ai/docs/config      | /anomalyco/opencode | config schema          | https://opencode.ai/docs/config      |

## Verification Strategy

1. **Try Context7 first** - Use hardcoded library IDs
2. **Fall back to fetch** - If Context7 fails or returns outdated info
3. **Cross-reference** - Compare both sources if available
4. **Agent decision** - Report findings, let agent decide
