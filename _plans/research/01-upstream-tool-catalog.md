# Research 01 — Upstream OpenSpec Tool Catalog

**Source:** `/home/amaury/Projects/openspec-extended/orchestrator/core/source/` (vendored upstream).

**Author:** exploration agent (catalog task).

**Date:** 2026-09-14.

---

## Purpose

Complete inventory of every AI tool OpenSpec Core (`orchestrator/core/source/`) supports, how each one is wired up, and the taxonomy that ties them together. The output of this research feeds the plan in `docs/plans/upstream-parity/`.

---

## 1. Complete tool list (canonical inventory)

OpenSpec Core enumerates its tools in one place: `AI_TOOLS` in `src/core/config.ts` (lines 40-92). That list is mirrored almost verbatim into three user-facing surfaces:

- The `availableToolIds` / `--tools` help text emitted by the CLI (`src/cli/index.ts:212-218`).
- The "Tool Directory Reference" table in `docs/supported-tools.md`.
- The `init` interactive selector (`src/core/init.ts:721`).

The `--tools` flag also accepts two reserved tokens (`all`, `none`) and one retired alias (`windsurf` → `devin` — `TOOL_ID_ALIASES` in `config.ts:100-102`, applied by `resolveToolIdAlias()` at `config.ts:107`).

### 1.1 Full tool table (46 IDs, including the alias)

| # | Display name (`name`) | Tool id (`value`) | Skills root (`skillsDir`) | Legacy roots | Detection paths | `requiresIdeRestart` | `setupNote` |
|---|------------------------|-------------------|---------------------------|--------------|-----------------|----------------------|-------------|
| 1 | Amazon Q Developer | `amazon-q` | `.amazonq` | – | – | yes | – |
| 2 | Antigravity | `antigravity` | `.agents` | `[.agent]` | `[.agent, .agents/workflows]` | yes | – |
| 3 | Auggie (Augment CLI) | `auggie` | `.augment` | – | – | no | – |
| 4 | Bob Shell | `bob` | `.bob` | – | – | no | – |
| 5 | Claude Code | `claude` | `.claude` | – | – | no | – |
| 6 | Cline | `cline` | `.cline` | – | – | yes | – |
| 7 | Command Code | `command-code` | `.commandcode` | – | – | no | – |
| 8 | CodeArts | `codeartsagent` | `.codeartsdoer` | – | – | no | – |
| 9 | Codex | `codex` | `.agents` | `[.codex]` | `[.agents/skills, .codex/skills]` | no | – |
| 10 | Devin Desktop (formerly Windsurf) | `devin` | `.devin` | – | `[.devin, .windsurf]` | yes | – |
| 11 | ForgeCode | `forgecode` | `.forge` | – | – | no | – |
| 12 | CodeBuddy Code (CLI) | `codebuddy` | `.codebuddy` | – | – | no | – |
| 13 | Continue | `continue` | `.continue` | – | – | yes | – |
| 14 | CoStrict | `costrict` | `.cospec` | – | – | yes | – |
| 15 | Crush | `crush` | `.crush` | – | – | no | – |
| 16 | Cursor | `cursor` | `.cursor` | – | – | yes | – |
| 17 | Factory Droid | `factory` | `.factory` | – | – | no | – |
| 18 | Gemini CLI | `gemini` | `.gemini` | – | – | no | – |
| 19 | GitHub Copilot | `github-copilot` | `.github` | – | `[…7 paths…]` | yes | – |
| 20 | Hermes Agent | `hermes` | `.hermes` | – | `[.hermes, HERMES.md, .hermes.md]` | no | yes |
| 21 | iFlow | `iflow` | `.iflow` | – | – | no | – |
| 22 | Junie | `junie` | `.junie` | – | – | yes | – |
| 23 | Kilo Code | `kilocode` | `.kilocode` | – | – | yes | – |
| 24 | Kimi Code | `kimi` | `.kimi-code` | – | `[.kimi-code, .kimi]` | no | – |
| 25 | Kiro | `kiro` | `.kiro` | – | – | yes | – |
| 26 | Lingma | `lingma` | `.lingma` | – | – | yes | – |
| 27 | MiniMax Code | `minimax-code` | – (`globalSkillsDir: .minimax`) | – | – | no | – |
| 28 | Mistral Vibe | `vibe` | `.vibe` | – | – | no | – |
| 29 | Oh My Pi | `oh-my-pi` | `.omp` | – | – | no | – |
| 30 | OpenCode | `opencode` | `.opencode` | – | – | no | – |
| 31 | Pi | `pi` | `.pi` | – | – | no | – |
| 32 | SourceCraft Code Assistant | `codeassistant` | `.codeassistant` | – | – | – | – |
| 33 | Qoder | `qoder` | `.qoder` | – | – | yes | – |
| 34 | Qwen Code | `qwen` | `.qwen` | – | – | no | – |
| 35 | Rovo Dev CLI | `rovodev` | `.rovodev` | – | `[.rovodev/skills, .rovodev]` | no | – |
| 36 | Zoo Code | `roocode` | `.roo` | – | – | yes | – |
| 37 | Trae | `trae` | `.trae` | – | – | yes | – |
| 38 | Zed Agent | `zed` | `.agents` | – | `[.zed, .agents/skills]` | no | – |
| 39 | ZCode | `zcode` | `.zcode` | – | – | no | – |
| 40 | Shared `.agents` skills (vendor-neutral) | `agents` | `.agents` | – | `[.agents/skills]` | no | – |
| 41 (alias) | Windsurf (retired) | `windsurf` | → resolves to `devin` | – | – | – | – |

Source excerpt — `src/core/config.ts:40-92`:

```ts
export const AI_TOOLS: AIToolOption[] = [
  { name: 'Amazon Q Developer', value: 'amazon-q', available: true, successLabel: 'Amazon Q Developer', skillsDir: '.amazonq', requiresIdeRestart: true },
  { name: 'Antigravity', value: 'antigravity', available: true, successLabel: 'Antigravity', skillsDir: '.agents', legacySkillsDirs: ['.agent'], detectionPaths: ['.agent', '.agents/workflows'], requiresIdeRestart: true },
  { name: 'Auggie (Augment CLI)', value: 'auggie', available: true, successLabel: 'Auggie', skillsDir: '.augment' },
  { name: 'Bob Shell', value: 'bob', available: true, successLabel: 'Bob Shell', skillsDir: '.bob' },
  { name: 'Claude Code', value: 'claude', available: true, successLabel: 'Claude Code', skillsDir: '.claude' },
  { name: 'Cline', value: 'cline', available: true, successLabel: 'Cline', skillsDir: '.cline', requiresIdeRestart: true },
  { name: 'Command Code', value: 'command-code', available: true, successLabel: 'Command Code', skillsDir: '.commandcode' },
  { name: 'CodeArts', value: 'codeartsagent', available: true, successLabel: 'CodeArts', skillsDir: '.codeartsdoer' },
  { name: 'Codex', value: 'codex', available: true, successLabel: 'Codex', skillsDir: '.agents', legacySkillsDirs: ['.codex'], detectionPaths: ['.agents/skills', '.codex/skills'] },
  { name: 'Devin Desktop (formerly Windsurf)', value: 'devin', available: true, successLabel: 'Devin Desktop', skillsDir: '.devin', detectionPaths: ['.devin', '.windsurf'], requiresIdeRestart: true },
  // ... (39 entries total, see source for full list) ...
];
```

### 1.2 Per-tool notes (from `docs/supported-tools.md`)

- **`windsurf` (retired)** is documented as an alias for `devin`. Rebranded 2026-06-02.
- **`codex`** is "skills-only": no command files are written; users invoke `$openspec-<skill>` (Codex does not recognize `/openspec-<skill>`). The legacy `.codex/skills` is reconciled after replacement skills are written.
- **`kimi`** is also skills-only; invocation is `/skill:openspec-<skill>`.
- **`zed`** is skills-only on `.agents/skills/`, requires Zed v1.4.2+ and worktree trust.
- **`agents`** is the vendor-neutral target; writes to `.agents/skills/`. If selected alongside Codex or Zed, OpenSpec keeps one Codex-led tree.
- **`hermes`** carries a `setupNote` because Hermes only loads skills from `~/.hermes/skills/` by default; project-local skills need an `external_dirs` entry in `~/.hermes/config.yaml`.
- **`minimax-code`** uses `globalSkillsDir` (no repo-local write); installs under `~/.minimax/skills/`.
- **`devin`** spans two agents: Devin Desktop reads `.devin/workflows/`; Devin Local does not, so skills are always written and the hint is on `/openspec-*` for both agents.
- **`rovodev`** has no slash-command surface at all — its `/skills` only manages skills, so generated content references skills by name (`$openspec-propose`) or natural-language ("use the openspec-propose skill"), never `/openspec-*`.
- **`github-copilot`** also has an **opt-in cloud-agent path**: `.github/workflows/copilot-setup-steps.yml` + `.github/agents/openspec.agent.md`, controlled by `--copilot-cloud` / `--no-copilot-cloud` and persisted to `openspec/config.yaml` (`githubCopilot.cloudAgent`).
- **`codex` and `zed` both share the `.agents` root**, requiring OpenSpec's shared-skill-target ownership marker (`.openspec-target`) so only one writer claims it.

---

## 2. Tool registry schema

The registry is `AI_TOOLS: AIToolOption[]` in `src/core/config.ts:27-38`. The exact shape:

```ts
export interface AIToolOption {
  name: string;                // Display name shown in selectors and success messages
  value: string;               // Tool id used in --tools, registry lookups, and frontmatter
  available: boolean;          // Always true in shipped list; flag retained for future gating
  successLabel?: string;       // Optional override for the label used in success/refresh lines
  skillsDir?: string;          // e.g. '.claude' — /skills suffix appended per Agent Skills spec
  legacySkillsDirs?: string[]; // Former roots scanned for detection and migrated after replacement
  globalSkillsDir?: string;    // e.g. '.minimax' — resolved from the user's home directory
  detectionPaths?: string[];   // Override skillsDir for auto-detection; any path existing triggers it
  setupNote?: string;          // Manual-setup hint printed after init/update when the tool is selected
  requiresIdeRestart?: boolean;// True when slash commands are loaded by an IDE/editor process
}
```

### 2.1 Derived / runtime fields

- `toolSupportsSkills(tool)` (`src/core/shared/skill-paths.ts:11`) returns true when either `skillsDir` or `globalSkillsDir` is set.
- `resolveToolSkillsDir(projectRoot, tool)` (`skill-paths.ts:23`) returns `<home>/<globalSkillsDir>/skills` or `<projectRoot>/<skillsDir>/skills`.
- `hasGlobalSkillTarget(tool)` (`skill-paths.ts:19`) is the boolean test for the global mode.

### 2.2 Generation control flags

- **Delivery mode** — `Delivery = 'both' | 'skills' | 'commands'` in `src/core/global-config.ts:12`. Default `'both'`. Stored in `~/.config/openspec/config.json`.
- **Profile** — `Profile = 'core' | 'custom'` (`global-config.ts:11`). `'core'` = `CORE_WORKFLOWS = ['propose', 'explore', 'apply', 'update', 'sync', 'archive']` (`profiles.ts:14`). `'custom'` = whatever `globalConfig.workflows` lists, with `sync` auto-injected if `archive`/`bulk-archive` is selected.

### 2.3 Skill templates (`OPENSPEC_SKILL_NAMES` in `config.ts:3-16`)

Same 12 names regardless of profile — profile just filters which ones are *generated*:

```
openspec-explore, openspec-new-change, openspec-continue-change,
openspec-apply-change, openspec-update-change, openspec-ff-change,
openspec-sync-specs, openspec-archive-change, openspec-bulk-archive-change,
openspec-verify-change, openspec-onboard, openspec-propose
```

---

## 3. Adapter registry (per-tool command files)

Located in `src/core/command-generation/`:

- `types.ts` — interface `ToolCommandAdapter` with `toolId`, `getFilePath(id)`, optional `invocationPrefix`, and `formatFile(content)`.
- `registry.ts` — `CommandAdapterRegistry` static class.
- `generator.ts` — `generateCommand(content, adapter)` rewrites `/opsx:<id>` references in the body to the tool's invocation form, then calls `adapter.formatFile(formatted)`.
- `invocation.ts` — derives `{style, prefix}` from each adapter.
- `yaml.ts` — shared `escapeYamlValue` and `formatTagsArray`.
- `adapters/index.ts` — re-exports all 31 adapters.

The test matrix in `test/core/command-generation/invocation.test.ts:25-34` confirms the canonical split:

```ts
const NAMESPACED_TOOLS = ['claude', 'codebuddy', 'crush', 'gemini', 'lingma', 'qoder', 'zcode'];
const NON_SLASH_PREFIXES: Record<string, string> = { 'amazon-q': '@' };
```

### 3.1 Adapter inventory (31 adapters)

| # | Adapter (`toolId`) | `getFilePath(id)` | Style | Invocation prefix | Special frontmatter |
|---|--------------------|--------------------|-------|--------------------|----------------------|
| 1 | `amazon-q` | `.amazonq/prompts/opsx-<id>.md` | flat | `@` | `description:` only |
| 2 | `antigravity` | `.agents/workflows/opsx-<id>.md` | flat | `/` | `description:` only |
| 3 | `auggie` | `.augment/commands/opsx-<id>.md` | flat | `/` | `description:`, `argument-hint:` |
| 4 | `bob` | `.bob/commands/opsx-<id>.md` | flat | `/` | `description:`, `argument-hint:` |
| 5 | `claude` | `.claude/commands/opsx/<id>.md` | namespaced | `/` | `name:`, `description:`, `allowed-tools:`, `category:`, `tags:` |
| 6 | `cline` | `.clinerules/workflows/opsx-<id>.md` | flat | `/` | **No frontmatter** |
| 7 | `codebuddy` | `.codebuddy/commands/opsx/<id>.md` | namespaced | `/` | `name:`, `description:`, `argument-hint:` |
| 8 | `codeassistant` | `.codeassistant/commands/opsx-<id>.md` | flat | `/` | `description:` only |
| 9 | `command-code` | `.commandcode/commands/opsx-<id>.md` | flat | `/` | Plain markdown (no frontmatter) |
| 10 | `continue` | `.continue/prompts/opsx-<id>.prompt` | flat | `/` | `name:`, `description:`, `invokable: true` (extension `.prompt`) |
| 11 | `costrict` | `.cospec/openspec/commands/opsx-<id>.md` | flat | `/` | `description:`, `argument-hint:` |
| 12 | `crush` | `.crush/commands/opsx/<id>.md` | namespaced | `/` | `name:`, `description:`, `category:`, `tags:` |
| 13 | `cursor` | `.cursor/commands/opsx-<id>.md` | flat | `/` | `name: /opsx-<id>`, `id:`, `category:`, `description:` |
| 14 | `devin` | `.devin/workflows/opsx-<id>.md` | flat | `/` | `name:`, `description:`, `category:`, `tags:` |
| 15 | `factory` | `.factory/commands/opsx-<id>.md` | flat | `/` | `description:`, `argument-hint:` |
| 16 | `gemini` | `.gemini/commands/opsx/<id>.toml` | namespaced | `/` | **TOML** |
| 17 | `github-copilot` | `.github/prompts/opsx-<id>.prompt.md` | flat | `/` | `description:` only (extension `.prompt.md`) |
| 18 | `iflow` | `.iflow/commands/opsx-<id>.md` | flat | `/` | `name: /opsx-<id>`, `id:`, `category:`, `description:` |
| 19 | `junie` | `.junie/commands/opsx-<id>.md` | flat | `/` | `description:` only |
| 20 | `kilocode` | `.kilocode/workflows/opsx-<id>.md` | flat | `/` | Plain markdown (no frontmatter) |
| 21 | `kiro` | `.kiro/prompts/opsx-<id>.prompt.md` | flat | `/` | `description:` only (extension `.prompt.md`) |
| 22 | `lingma` | `.lingma/commands/opsx/<id>.md` | namespaced | `/` | `name:`, `description:`, `category:`, `tags:` |
| 23 | `oh-my-pi` | `.omp/commands/opsx-<id>.md` | flat | `/` | `description:` + `$@` injection |
| 24 | `opencode` | `.opencode/commands/opsx-<id>.md` | flat | `/` | `description:` + `$ARGUMENTS` injection |
| 25 | `pi` | `.pi/prompts/opsx-<id>.md` | flat | `/` | `description:` + `$@` injection |
| 26 | `codeassistant` | `.codeassistant/commands/opsx-<id>.md` | flat | (natural-lang) | `description:` only |
| 27 | `qoder` | `.qoder/commands/opsx/<id>.md` | namespaced | `/` | `name:`, `description:`, `category:`, `tags:` |
| 28 | `qwen` | `.qwen/commands/opsx-<id>.md` | flat | `/` | `description:` only (Markdown, not TOML — Qwen deprecated TOML) |
| 29 | `roocode` | `.roo/commands/opsx-<id>.md` | flat | `/` | **No frontmatter** |
| 30 | `trae` | `.trae/commands/opsx-<id>.md` | flat | `/` | `name:`, `description:` |
| 31 | `zcode` | `.zcode/commands/opsx/<id>.md` | namespaced | `/` | `name:`, `description:`, `category:`, `tags:` |

### 3.2 Tool-specific behaviour

- **`opencode`** is the only adapter that actively **rewrites the body**: `injectOpenCodeArgs()` adds `**Provided arguments**: $ARGUMENTS` after the canonical `**Input**:` heading unless a positional placeholder (`$ARGUMENTS`, `$1`, …) is already there or the workflow declares no input.
- **`command-code`** does the same body rewrite with `$ARGUMENTS`.
- **`pi`** and **`oh-my-pi`** inject `**Provided arguments**: $@` after `**Input**:`.
- **`amazon-q`** is the **only** adapter with a non-`/` invocation prefix (`'@'`).
- **`gemini`** is the **only** TOML output. Its adapter includes a full TOML escape implementation.
- **`cline`**, **`kilocode`**, **`command-code`**, **`roocode`** emit no YAML frontmatter.
- **`claude`** is the only adapter that injects `allowed-tools: Bash(openspec:*)`.
- **`continue`** is the only adapter whose frontmatter has `invokable: true` (extension `.prompt`).

### 3.3 Test matrix pinning the registry

`test/core/command-generation/adapters.test.ts` (1349 lines) and `invocation.test.ts` together enforce:
- A round-trip YAML-escape matrix that runs every registered YAML adapter against 33 hostile inputs.
- A "every adapter is classified by the file it writes" tripwire.
- A non-YAML adapter exclusion list that any new entry must consciously opt into.

---

## 4. Tools referenced in skills/init/update — deduplicated first appearance

For each distinct tool id, the first location in the source tree where it appears:

| Tool id | First appearance |
|---------|------------------|
| `amazon-q` | `core/command-generation/adapters/amazon-q.ts:21` |
| `antigravity` | `core/command-generation/adapters/antigravity.ts:18` |
| `auggie` | `core/command-generation/adapters/auggie.ts:17` |
| `claude` | `core/command-generation/adapters/claude.ts:18` |
| `cline` | `core/command-generation/adapters/cline.ts:16` |
| `codeartsagent` | `core/config.ts:53` (no command adapter; skills-only) |
| `codex` | `core/config.ts:54`; special-cased in `command-surface.ts:22` as `'skills-invocable'` |
| `codebuddy` | `core/command-generation/adapters/codebuddy.ts:16` |
| `codeassistant` | `core/command-generation/adapters/codeassistant.ts:18` |
| `command-code` | `core/command-generation/adapters/command-code.ts:35` |
| `continue` | `core/command-generation/adapters/continue.ts:16` |
| `costrict` | `core/command-generation/adapters/costrict.ts:16` |
| `crush` | `core/command-generation/adapters/crush.ts:16` |
| `cursor` | `core/command-generation/adapters/cursor.ts:17` |
| `devin` | `core/command-generation/adapters/devin.ts:23` |
| `factory` | `core/command-generation/adapters/factory.ts:16` |
| `forgecode` | `core/config.ts:56` (no adapter; skills-only) |
| `gemini` | `core/command-generation/adapters/gemini.ts:53` |
| `github-copilot` | `core/command-generation/adapters/github-copilot.ts:16`; `core/github-copilot/cloud-agent.ts:16` |
| `hermes` | `core/config.ts:65` (no adapter; skills-only) |
| `iflow` | `core/command-generation/adapters/iflow.ts:16` |
| `junie` | `core/command-generation/adapters/junie.ts:16` |
| `kilocode` | `core/command-generation/adapters/kilocode.ts:16` |
| `kimi` | `core/config.ts:69` (no adapter; skills-only; SKILL_INVOCATION_PREFIX `'/skill:'`) |
| `kiro` | `core/command-generation/adapters/kiro.ts:16` |
| `lingma` | `core/command-generation/adapters/lingma.ts:16` |
| `minimax-code` | `core/config.ts:72` (no adapter; global skills target) |
| `oh-my-pi` | `core/command-generation/adapters/oh-my-pi.ts:37` |
| `opencode` | `core/command-generation/adapters/opencode.ts:33` |
| `pi` | `core/command-generation/adapters/pi.ts:34` |
| `codeassistant` | `core/command-generation/adapters/codeassistant.ts:18` |
| `qoder` | `core/command-generation/adapters/qoder.ts:16` |
| `qwen` | `core/command-generation/adapters/qwen.ts:20` |
| `rovodev` | `core/config.ts:80` (no adapter; `NATURAL_LANGUAGE_SKILL_TOOLS`) |
| `roocode` | `core/command-generation/adapters/roocode.ts:16` |
| `trae` | `core/command-generation/adapters/trae.ts:16` |
| `vibe` | `core/config.ts:73` (no adapter; skills-only) |
| `windsurf` | `core/config.ts:101` (alias to `devin` only) |
| `zcode` | `core/command-generation/adapters/zcode.ts:19` |
| `zed` | `core/config.ts:83` (no adapter; skills-only via shared `.agents` root) |
| `agents` | `core/config.ts:91` (no adapter; skills-only via shared `.agents` root) |

The 10 tool ids with **no command adapter**: `codeartsagent`, `codex`, `forgecode`, `hermes`, `kimi`, `minimax-code`, `rovodev`, `vibe`, `zed`, `agents`.

---

## 5. Run / invocation shape per tool

This is the *CLI* layer — how the tool is invoked headlessly or interactively. OpenSpec Core itself does not invoke these tools; it generates skill/command files that the tool then loads.

### 5.1 Slash command shape (canonical table)

| File path OpenSpec writes | What the user types | Tools |
|---------------------------|---------------------|-------|
| `…/commands/opsx/<id>.*` (namespaced) | `/opsx:<id>` | Claude Code, CodeBuddy, Crush, Gemini CLI, Lingma, Qoder, ZCode |
| `…/opsx-<id>.*` (flat filename) | `/opsx-<id>` | All other adapter-backed tools except the two below |
| `.devin/workflows/opsx-<id>.md` | `/opsx-<id>` (Devin Desktop) or `/openspec-<skill>` (Devin Local) | Devin Desktop |
| `.amazonq/prompts/opsx-<id>.md` | `@opsx-<id>` | Amazon Q Developer |
| *no command files; skills only* | `/openspec-<skill>` | CodeArts, ForgeCode, Hermes, Mistral Vibe, Zed Agent, shared `.agents` target |
| *no command files* | `/skill:openspec-<skill>` | Kimi Code |
| *no command files* | `$openspec-<skill>` | Codex |

### 5.2 Adapter-driven invocation rules

```ts
export const CANONICAL_INVOCATION: CommandInvocation = { style: 'namespaced', prefix: '/' };

export function getInvocationStyleForPath(commandFilePath: string): CommandInvocationStyle {
  return path.basename(commandFilePath).startsWith('opsx-') ? 'flat' : 'namespaced';
}

export function getInvocationForAdapter(adapter: ToolCommandAdapter): CommandInvocation {
  return {
    style: getInvocationStyleForPath(adapter.getFilePath('explore')),
    prefix: adapter.invocationPrefix ?? CANONICAL_INVOCATION.prefix,
  };
}
```

### 5.3 Body rewriting (`src/utils/command-references.ts`)

When a tool's invocation differs from the canonical `/opsx:<id>`, the generator rewrites the body via `transformCommandInvocations(text, invocation)`.

### 5.4 Skill invocation prefixes

```ts
const SKILL_INVOCATION_PREFIX: Record<string, string> = {
  kimi: '/skill:',
  codex: '$',
};
```

| Tool | Skill reference rendered |
|------|--------------------------|
| `kimi` | `/skill:openspec-<skill>` |
| `codex` | `$openspec-<skill>` |
| `rovodev`, `codeassistant` | `the openspec-<skill> skill` (natural-language) |
| every other tool | `/openspec-<skill>` |

### 5.5 The Codex-vs-vendor-neutral dual tree

`src/utils/command-references.ts:116-123`:

```ts
export function transformToCodexCompatibleSkillReferences(text: string): string {
  return text.replace(/\/opsx:([a-z-]+)/g, (match, commandId: string) => {
    const skillName = COMMAND_TO_SKILL_NAME[commandId];
    return skillName === undefined
      ? match
      : `$${skillName} (Codex) or /${skillName} (other agents)`;
  });
}
```

When Codex shares `.agents/skills/` with other tools (Zed, vendor-neutral `agents`), its rendered SKILL.md files list *both* invocation forms.

### 5.6 How skill and command files reach the assistant's CLI

OpenSpec Core does **not** run the assistant CLI — it only writes the file tree the assistant then scans. The shape of how each tool's CLI is invoked (interactive vs headless) appears in two sources:

- `openspec/work/simplify-context-and-workspace-model/slices/personal-worksets/research.md:295-317` (live CLI verification notes).
- `openspec/work/simplify-context-and-workspace-model/slices/store-rename-and-guidance/dogfood-transcript.md:30` records the canonical non-interactive invocation: `claude -p "<prompt>" --dangerously-skip-permissions --max-turns 25 --output-format text`.

---

## 6. Plan mode

**OpenSpec Core does not expose a plan-mode flag for any tool.** There is no `--plan` option, no plan-mode workflow, no per-tool plan flag in any adapter or command surface. Searches in `src/` for `plan.mode`, `plan-mode`, `planMode`, `--plan`, and `planning_mode` return zero matches.

Tools that themselves ship a plan mode (Codex's `--plan`, Claude Code's plan mode, Cursor's plan mode) are *consumed* by OpenSpec but not configured by it. Adding plan-mode awareness to OpenSpec Core would be a new feature.

---

## 7. Skills-only / skills-invocable tools (capability taxonomy)

The "command-surface capability" model is implemented in `src/core/command-surface.ts` (43 lines total). The taxonomy is intentionally narrow — three states, decided once per tool id, encoded as:

```ts
export type CommandSurfaceCapability = 'adapter-backed' | 'skills-invocable' | 'none';

export function resolveCommandSurfaceCapability(toolId: string): CommandSurfaceCapability {
  if (CommandAdapterRegistry.has(toolId)) {
    return 'adapter-backed';
  }
  if (toolId === 'codex') {
    return 'skills-invocable';
  }
  return 'none';
}
```

### 7.1 The three capabilities

| Capability | Definition | Tools (today) | What gets written |
|------------|------------|---------------|---------------------|
| `adapter-backed` | Tool has a registered `ToolCommandAdapter` → per-tool command files are generated, alongside skills | All 30 adapter-backed tools | Skills + commands (delivery = `both`) or commands only (delivery = `commands`) or skills only (delivery = `skills`) |
| `skills-invocable` | Tool has **no** command adapter, but the assistant has a documented slash form for invoking skill names directly. Only `codex` qualifies today. | `codex` only | Skills only — but the user's delivery setting is otherwise ignored: `shouldGenerateSkillsForTool` always returns true. |
| `none` | Tool has **no** command adapter and no documented slash surface | `codeartsagent`, `forgecode`, `hermes`, `kimi`, `minimax-code`, `rovodev`, `vibe`, `zed`, `agents` | Skills only (if the tool supports skills at all) |

### 7.2 The four delivery gates

```ts
export function shouldGenerateSkillsForTool(toolId, delivery) { ... }
export function shouldRemoveSkillsForTool(toolId, delivery) { ... }
export function shouldGenerateCommandsForTool(toolId, delivery) { ... }
export function shouldReconcileCommandFilesForTool(toolId, delivery) { ... }
```

### 7.3 Sub-divisions inside `none`

`src/utils/command-references.ts` adds two pieces of nuance:

- **`SKILL_INVOCATION_PREFIX`**: `kimi → '/skill:'`, `codex → '$'`, every other tool → `'/'`.
- **`NATURAL_LANGUAGE_SKILL_TOOLS`**: `new Set(['rovodev', 'codeassistant'])` — references are rewritten as English prose.

### 7.4 The shared-skill-target ownership arbitration

When several tools map to the same physical `skillsDir` (`.agents/`), only one is allowed to render the shared tree. The arbitration lives in `src/core/shared-skill-target.ts`:

- `.openspec-target` marker file written under `<skillsDir>/skills/.openspec-target`.
- `reconcileSharedSkillTargets(projectPath, tools)` picks the owner:
  1. Existing marker wins.
  2. Inferred from `$openspec-` (Codex) vs `/openspec-` (vendor-neutral) references inside the rendered skills.
  3. If a pre-marker tree exists, keep the established `agents` target instead of clobbering with Codex syntax.
  4. Otherwise prefer the **skills-native** renderer over an adapter-backed one.
  5. Codex owns when `codex` is in the preferred pool; otherwise the first by `AI_TOOLS` order.

---

## Cross-references for parity planning

- Canonical `--tools` enumeration — `src/core/config.ts:40-92`.
- Tool selection resolution — `src/core/init.ts:707-770`.
- Validation errors raised by `--tools` — `src/core/init.ts:772-796`.
- IDE-restart hint driven by `requiresIdeRestart` — `src/core/shared/ide-restart.ts`.
- Shared `.agents` ownership — `src/core/shared-skill-target.ts`.
- Body-rewrite and skill-reference transformers — `src/utils/command-references.ts`.
- Three-state capability model — `src/core/command-surface.ts`.
- `openspec init` and `openspec update` orchestration — `src/core/init.ts` and `src/core/update.ts`.
- GitHub Copilot cloud-agent — `src/core/github-copilot/cloud-agent.ts`.
- Migration between rebranded/legacy roots — `src/core/migration.ts:44-62`.
- Public docs enumerating tools — `docs/supported-tools.md`, `docs/cli.md:117`, `docs/how-commands-work.md:74-83`.

---

**End of research output 01.**
