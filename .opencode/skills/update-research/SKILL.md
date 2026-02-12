---
name: update-research
description: Maintain AI coding assistant research documentation (AGENTS.md, claude-code-docs.md, opencode-docs.md). Use when agents need to verify accuracy, check structure, ensure consistency, identify redundancies, or discover new content. Leverage AI capabilities with any available tools (Context7, fetch, etc.) - make direct decisions based on findings.
---

## Workflow

When maintaining research docs, follow this workflow:

## When to Use This Skill

This skill is for MAINTENANCE TASKS on research documentation. Use when:

1. Verifying content accuracy against official docs
2. Checking structure and formatting compliance
3. Ensuring terminology consistency
4. Identifying and consolidating redundancies
5. Discovering new relevant content from official docs

NOT for:
- Reading research docs during CLI development (use AGENTS.md index)
- Quick lookups (read files directly via AGENTS.md index)
- General project understanding (use AGENTS.md project overview)

**Advisory Invocation Patterns:**
If user request includes phrasings like:
- "update the research docs"
- "check if docs are accurate"
- "verify content against official sources"
- "maintain the research documentation"
- "review and update AGENTS.md files"

Then: **SHOULD invoke this skill** for maintenance workflow.
Otherwise: Use AGENTS.md index for direct file access.

---

### Step 1: Verify Content Accuracy

Check that research doc content matches official documentation.

**Verification strategy by content type:**

| Content Type | Recommended Approach | Why |
|--------------|---------------------|-----|
| Field definitions (frontmatter) | Context7 | Structured, easy to query |
| Permission modes/values | Fetch official docs | May include constraints or examples |
| API endpoints or URLs | Fetch official docs | Most current, includes examples |
| Recent changes/features | Fetch official docs | Context7 may lag |
| Deprecated features | Fetch official docs | Most current deprecation notices |
| Tool names or syntax | Context7 or fetch | Both work, choose most efficient |

**Available verification approaches:**
- Context7 (context7_query-docs) with libraries `/anthropics/claude-code` and `/anomalyco/opencode`
- Fetch official docs directly from URLs (see `references/official-sources.md`)
- Any other available tools that provide accurate verification

**Tool selection guidance (prefer efficiency):**
- Field definitions → Context7 (structured, faster)
- Recent changes → Fetch (most current, Context7 may lag)
- Permission details → Fetch (may include constraints)
- API endpoints/URLs → Fetch (examples included)
- Tool names/syntax → Either (choose most efficient)

**For Claude Code docs:**
Verify key sections like skill frontmatter fields, permissionMode values, subagent tools field, memory @path syntax

**For OpenCode docs:**
Verify key sections like agent frontmatter, skill naming constraints, permission object format, command template field

**Identify discrepancies:**
- Missing fields or sections
- Deprecated values or features
- New constraints or capabilities
- Incorrect field types or defaults

**Decision point:** Update research doc if outdated, incomplete, or incorrect. Use whichever verification method you find most efficient.

---

### Step 2: Check Structure and Formatting

Ensure docs follow `references/structure-standards.md` and `references/format-guide.md`.

1. Read research doc file
2. Verify heading hierarchy (H1→H2→H3)
3. Check section ordering matches `structure-standards.md`
4. Validate table format:
   - Frontmatter tables: `Field | Type | Required | Default | Description`
   - Built-in entities tables: `[Name] | [Description]`
   - All table rows start with `|`
5. Ensure code blocks have language specifiers:
   - YAML: ```yaml
   - JSON: ```json
   - Markdown: ```markdown
6. Check that `---` separators only appear after H2 sections (not after H3 or H4)

**Decision point:** Fix any structure or formatting inconsistencies found.

---

### Step 3: Check Terminology Consistency

Ensure platform-specific terms are used correctly per `references/terminology.md`.

1. Read `references/terminology.md`
2. Search research docs for potential issues (Grep or other search tools):
   - In `claude-code-docs.md`: search for "agent" (should be "subagent")
   - In `opencode-docs.md`: search for "subagent" (should be "agent")
3. Review search results with context
4. Determine if usage is incorrect or intentional:

**Intentional variations (preserve these):**
- **Mode values**: `subagent` is a valid OpenCode mode value (`primary|subagent|all`)
- **Field descriptions**: "subagent type" or "agent mode" are acceptable when describing a field's purpose
- **URLs and paths**: File names like `sub-agents.md` or `agents.md` are acceptable
- **Comparisons**: "Unlike agents, subagents..." when comparing platforms
- **Code examples**: Terminology in YAML/JSON examples reflecting target platform

**Incorrect terminology (fix these):**
- "agent" in Claude Code normal text (except URLs)
- "subagent" in OpenCode normal text (except as mode value)
- Mixed terminology in descriptions without clear purpose

**Decision point:** Fix terminology errors, preserve intentional variations.

---

### Step 4: Identify Redundancies

Review and decide on duplicate or overlapping content.

1. Read all research docs
2. Compare sections across files for similar content
3. Review overlaps and determine if consolidation is appropriate:
   - Is content truly identical or just similar?
   - Does each occurrence serve a different purpose or context?
   - Would consolidation improve clarity or reduce clutter?
   - Are there platform-specific differences that justify duplication?

**Note:** No fixed threshold - review and decide based on context.

**Decision point:** Consolidate overlapping content, rewrite to differentiate, or keep as-is.

---

### Step 5: Discover New Content

Find new sections in official docs not yet in research docs.

**Available discovery approaches:**
- Fetch official docs directly from URLs (see `references/official-sources.md`)
- Context7 queries for specific topics
- Any other available tools for content discovery

**Content priority matrix:**

| Priority | Add | Consider | Skip |
|----------|-----|----------|------|
| **Fields - Required** | Required fields for document types, constraints, new types | Optional fields with clear configuration impact | Deprecated fields, removed fields |
| **Fields - Optional** | Fields affecting transformation behavior (model, tools, permissions) | Fields with optional configuration options | UI-only fields, display-only settings |
| **Permissions/Tools** | New permission values, permission system changes | Permission constraints or edge cases | Platform-specific internal tools, tool-specific bugs |
| **Modes/Values** | New enum values, mode types, agent types | Value constraints or defaults | Experimental features, beta-only features |
| **Configuration** | Frontmatter structures, validation rules, config schemas | Less common config options, provider configurations | Session management, telemetry, cache settings, logging |
| **Syntax/Behavior** | New syntax patterns, behavior changes affecting configs | Edge cases, special behaviors | Usage examples, tutorials, user guides |
| **Document Types** | New document types (plugins, MCP servers, hooks) | Document type variants or alternatives | Standalone documentation (non-config) |
| **Cross-Platform** | Cross-platform comparisons, mappings | Platform-specific explanations within comparisons | Platform-specific marketing content |

**Review new sections for relevance:**
- Is it a core capability or edge case?
- Is it configuration details or usage guidance?
- Would it help AI agents using these research docs?
- Does it add new fields, constraints, or behaviors?

**Note:** Use subagent to extract and summarize large sections for review.

**Decision point:** Add relevant sections to research docs, skip edge cases or usage examples. Use whichever discovery method you find most efficient.

---

**Decision Tree for File Access:**

Task involves reading research docs?
→ NO (maintenance task) → Use this skill workflow
→ YES → Just reading (no maintenance)?
  → NO → Use this skill workflow
  → YES → Read files directly using AGENTS.md index

---

### Step 6: Review and Apply Changes

After completing steps 1-5.

1. Review all findings holistically
2. Prioritize by impact:
   - **Critical**: Incorrect information affecting adapter functionality
   - **Important**: Missing fields, new constraints, or deprecated features
   - **Warning**: Terminology or formatting issues
   - **Info**: New sections or nicer wording
3. Apply changes directly to research docs
4. Make context-aware tradeoff decisions

You're empowered to make decisions and update content based on your review.

---

## Reference Materials

### official-sources.md

Maps research sections to verification sources:

| Platform | Context7 Library | Official Docs |
|-----------|-------------------|----------------|
| Claude Code | `/anthropics/claude-code` | skills.md, memory.md, sub-agents.md, settings.md, hooks.md, plugins.md |
| OpenCode | `/anomalyco/opencode` | agents, skills, permissions, commands, config, mcp-servers |

### structure-standards.md

AI-optimized structure patterns:

**Section ordering:**
1. Official Documentation Sources
2. Document Types
3. Platform-specific sections (alphabetical)
4. Examples
5. Validation Constraints
6. Comparison (if applicable)

**Table format standards:**
- Frontmatter: `Field | Type | Required | Default | Description`
- Built-in entities: `[Name] | [Description]` or `[Name] | [Field 2] | ...`

**Hierarchy rules:**
- H1: Document title only
- H2: Major sections
- H3: Subsections
- H4: Details (rare, use sparingly)

### format-guide.md

Formatting rules for consistency:

**Code blocks:**
- YAML: ```yaml
- JSON: ```json
- Inline code: backticks for field names, file paths, keywords

**Separators:**
- Use `---` between major sections (after H2) only
- Never between subsections

**Lists:**
- Numbered (1., 2., 3.) for sequences
- Bulleted for groups
- Nested bullets: `  -` (two-space indent)

**Links:**
- Official docs in "Official Documentation Sources" section
- Section cross-refs: `### [Section Name]` format

### terminology.md

Platform-specific terms:

**Claude Code:**
- "subagents" (not "agents" except in URLs)
- "permissionMode" enum: `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan`
- Tools: PascalCase (`Bash`, `Read`, `Edit`, `Write`)
- Model IDs: Aliases (`sonnet`, `opus`, `haiku`) or full names

**OpenCode:**
- "agents" (not "subagents")
- Permissions object: `allow`, `ask`, `deny` values
- Tools: Lowercase (`bash`, `read`, `edit`, `write`)
- Model IDs: `provider/model-id` format
- Skill names: `^[a-z0-9]+(-[a-z0-9]+)*$` regex

---

## Important Notes

- AI drives all decisions based on context and review
- No automatic changes - you decide what to update
- Use any available tools for verification and discovery (Context7, fetch, etc.) based on what's most efficient
- Reference files are guides, not strict rules
- Adapt workflow as needed based on findings
- Make context-aware tradeoff decisions when priorities conflict
- Index regeneration: Run `scripts/regenerate-index.py` after updating research docs to update AGENTS.md index
