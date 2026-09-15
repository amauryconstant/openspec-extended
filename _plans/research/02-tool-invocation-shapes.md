# Research 02 — Headless CLI Shapes for 12 Targeted Tools

**Purpose:** Practical engineering brief for the 12 AI tools called out as "not yet supported" by openspec-extended (which currently supports only opencode and claude). Each section captures the binary name, headless invocation shape, plan/sandbox/model flags, slash/skill prefix, and process model — distilled from upstream OpenSpec v1.13.0 documentation, vendored `orchestrator/core/source/` material, the openspec-extended codebase itself, and each vendor's current public docs as of September 2026.

**Source:** exploration agent (tool invocation task).

**Date:** 2026-09-14.

---

The openspec-extended runner contract today (`source/orchestrator/runner.py`) recognises three `RunnerKind` literals — `opencode_run`, `claude_print`, `generic_print` — and the registry in `source/tools.py` ships only `opencode` and `claude`. The 12 tools below differ along the axes `binary`, `args shape before --print`, `slash prefix`, `skill prefix`, `cross_ref_prefix`, `sandbox flag`, `model flag`, `cd flag`, and whether the tool has any headless mode at all.

---

## 1. Cursor

### Binary and headless invocation

- **Binary:** `agent` (the Cursor CLI binary, also exposed as `cursor` for the IDE-only mode). Install via `curl https://cursor.com/install -fsS | bash` on macOS/Linux/WSL.
- **Headless invocation shape:** `agent -p --force "<prompt>"` — `-p` / `--print` enables non-interactive mode; `--force` (alias `--yolo`) lets the agent apply file edits without confirmation.

### Plan-mode and sandbox flags

| Flag | Effect |
|------|--------|
| `-p`, `--print` | Non-interactive |
| `--force`, `--yolo` | Allow direct file modifications in `--print` mode |
| `--output-format text\|json\|stream-json` | Output encoding |
| `--mode agent\|plan\|ask` | Pick the running mode |
| `-w`, `--worktree [name]` | Run inside a new Git worktree |
| `--workspace <path>` | Explicit repository root |
| `-m`, `--model` | Override the default model |

### Slash/skill invocation prefix

Cursor's slash resolver uses the file-name pattern, so `.cursor/commands/opsx-<id>.md` is `/opsx-<id>`. Skills (`.cursor/skills/<name>/SKILL.md`) are matched on natural-language description, not by slash.

### Process model

Interactive TUI by default. `-p` runs a single turn and exits.

### Pitfalls

- `agent` (no `-p`) hijacks a bare `agent` subcommand into a *separate* auto-installing `cursor-agent` shim; pass exactly one absolute argv entry.
- The "glass" multi-workbench mode can open `.code-workspace` files in the Agent Window; `--classic` is the community workaround.

### Upstream OpenSpec integration

- Tool ID `cursor`; skills root `.cursor/skills/openspec-*/SKILL.md`; command root `.cursor/commands/opsx-<id>.md`.
- Slash-form: `/opsx-<id>` (flat layout).
- `requiresIdeRestart: true`.

### openspec-extended integration notes

- `runner_binary="agent"`, `runner_kind="generic_print"`, `runner_args=("--force",)`.
- `slash_prefix="osx-"`, `skill_prefix="/"`, `agent_field_transform=strip_agent_line`.
- `detect_paths=(".cursor",)`, `requires_ide_restart=True`.

---

## 2. Codex

### Binary and headless invocation

- **Binary:** `codex` (OpenAI's CLI). Install via `curl -fsSL https://chatgpt.com/codex/install.sh | sh`.
- **Headless invocation shape:** `codex exec "<task>"` — `codex exec` (alias `codex e`) is the **only** documented non-interactive entry point. The flag `-p/--print` is **not** what you want.

### Plan mode and sandbox flags

| Flag | Effect |
|------|--------|
| `-s`, `--sandbox <MODE>` | `read-only` (default), `workspace-write`, `danger-full-access` |
| `-a`, `--ask-for-approval <on-request\|never>` | When the agent pauses for approval |
| `-C`, `--cd <DIR>` | Set the working directory |
| `--add-dir <path>` | Grant an extra directory write access; repeatable |
| `-m`, `--model <MODEL>` | Override model |
| `--full-auto` | **Deprecated**; use `--sandbox workspace-write` |
| `--yolo`, `--dangerously-bypass-approvals-and-sandbox` | Bypass approvals and sandboxing |
| `-c`, `--config <key=value>` | Inline TOML overrides |
| `--search` | Enable live web search |
| `--json` | JSONL output (event stream) |
| `review` | Dedicated read-only review |

### Slash/skill invocation prefix

Codex is **skills-only** in upstream OpenSpec — no command files are written. Users invoke skills as `$openspec-<skill>` (e.g. `$openspec-propose`). The form `/openspec-<skill>` is explicitly **not** recognized.

### Process model

Interactive TUI by default. `codex exec` is the headless path. `codex review` is a separate read-only review path. `codex acp` exposes ACP over stdio.

### JSONL event schema

`codex exec --json` emits one JSON object per line: `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.started`, `item.completed`, `error`.

### Exit codes

`codex exec` follows the conventions in the upstream docs; non-zero on failure.

### Upstream OpenSpec integration

- Tool ID `codex`; skills root `.agents/skills/openspec-*/SKILL.md`.
- No command files. Slash prefix `$`, skill prefix `$`, cross_ref_prefix `$`.

### openspec-extended integration notes

- `runner_binary="codex"`, `runner_kind="generic_print"`.
- `runner_args=("--sandbox", "workspace-write")` (workspace-write is the safe default for autonomous use).
- `slash_prefix="/"`, `skill_prefix="$"`, `cross_ref_prefix="$"`.
- `commands_style="skills-only"`, `shared_skills_root=True`.
- `frontmatter_extras={"source": "openspec-extended"}`.
- `detect_paths=(".agents",)` — note: zed MUST register BEFORE codex in registration order.

---

## 3. Kimi Code

### Binary and headless invocation

- **Binary:** `kimi` (MoonshotAI). Standalone Node.js-based binary.
- **Headless invocation shape:** `kimi -p "<prompt>"` — `-p` / `--prompt` runs a single prompt non-interactively and streams Assistant output to stdout.

### Plan-mode, sandbox/permission, model flags

| Flag | Effect |
|------|--------|
| `-p`, `--prompt <prompt>` | Non-interactive single prompt |
| `--output-format <text\|stream-json>` | Output format |
| `-m`, `--model <model>` | Override model |
| `--plan` | Start in Plan mode (read-only). Mutually exclusive with `-p` |
| `--yolo`, `-y` | "Ask When Needed" mode |
| `--auto` | "Never Ask" mode (no interrupts). Mutually exclusive with `--yolo` |
| `--add-dir <dir>` | Add an extra workspace dir; repeatable |
| `--skills-dir <dir>` | Replace auto-discovered skill dirs for this launch |
| `--agent <name>` / `--agent-file <path>` | Pick / load a custom agent |

### Slash / skill invocation prefix

External skills use the namespaced form: **`/skill:<name>`** (e.g. `/skill:openspec-propose`).

### Process model

Interactive TUI by default. `-p` is a single-turn non-interactive mode. Subcommands include `kimi login`, `kimi acp`, `kimi web`, `kimi doctor`, etc.

### Pitfalls

- `--continue` + `--session`; `--yolo` + `--auto`; `--prompt` + `--yolo` / `--auto` / `--plan` are mutually exclusive.
- Static deny rules remain in effect even with `--yolo`.

### Upstream OpenSpec integration

- Tool ID `kimi`; skills root `.kimi-code/skills/openspec-*/SKILL.md`. Legacy detection: `.kimi`.

### openspec-extended integration notes

- `runner_binary="kimi"`, `runner_kind="generic_print"`.
- `slash_prefix="/"`, `skill_prefix="/skill:"`, `cross_ref_prefix="/skill:"`.
- `commands_style="skills-only"`.
- `detect_paths=(".kimi-code", ".kimi")`.
- `legacy_skills_dirs=(".kimi",)` (PR6).

---

## 4. Qwen Code

### Binary and headless invocation

- **Binary:** `qwen` (Alibaba's CLI). Install via npm or the official site.
- **Headless invocation shape:** `qwen -p "<prompt>"` — `-p` / `--prompt` runs in headless mode.

### Plan-mode, sandbox, approval, model flags

| Flag | Effect |
|------|--------|
| `-p`, `--prompt <prompt>` | Run a single prompt non-interactively |
| `--output-format text\|json\|stream-json` | Output format |
| `--input-format text\|stream-json` | How stdin is interpreted |
| `--yolo`, `-y` | Auto-approve all actions (does NOT enable a sandbox) |
| `--approval-mode plan\|default\|auto-edit\|auto\|yolo` | Per-run approval mode. `plan` is read-only |
| `--include-directories <list>` | Extra dirs to include |
| `--model`, `-m` | Override the model |
| `--safe-mode` | Disable all customizations |
| `--continue` / `--resume [sessionId]` | Resume previous sessions |
| `--max-session-turns` | Cap user/model/tool turns. Exit 53 on overrun |

### Slash / skill invocation prefix

Qwen Code's interactive commands are **built-in skills** that appear as `/<name>`. External skills follow the same convention — `/<skill-name>`.

### Process model

Interactive TUI by default. `-p` is the headless single-prompt mode.

### Pitfalls

- `Learning` output style is skipped in headless runs.
- `--yolo` does **not** enable a sandbox.

### Upstream OpenSpec integration

- Tool ID `qwen`; skills root `.qwen/skills/openspec-*/SKILL.md`; command root `.qwen/commands/opsx-<id>.md` (Markdown frontmatter only — Qwen deprecated TOML).

### openspec-extended integration notes

- `runner_binary="qwen"`, `runner_kind="generic_print"`.
- `commands_ext="md"` (Qwen Code uses Markdown, not TOML despite what upstream docs suggest).
- `slash_prefix="osx-"`, `skill_prefix="/"`.

---

## 5. Kiro

### Binary and headless invocation

- **Binary:** `kiro-cli` (AWS's agentic CLI, formerly Amazon Q Developer CLI). Install via `curl -fsSL https://cli.kiro.dev/install | bash`.
- **Headless invocation shape:** `kiro-cli chat --no-interactive "<prompt>"`.

### Plan-mode, trust, model flags

| Flag | Effect |
|------|--------|
| `--no-interactive` | Run non-interactively |
| `--agent-engine v1\|v2\|v3` | Pick agent engine |
| `--output-format stream-json` | JSONL events (V2/V3) |
| `--trust-all-tools` | Auto-approve every tool call |
| `--trust-tools=<categories>` | Approve specific categories |
| `--require-mcp-startup` | Fail fast if any MCP server can't connect |

### Slash / skill invocation prefix

In interactive mode, Kiro recognises `/`-prefixed commands (slash menu). Headless mode has no slash surface — instructions are passed directly.

### Process model

Interactive TUI by default. Headless single-turn via `chat --no-interactive`. ACP mode available.

### Pitfalls

- `--output-format stream-json` requires V2 or V3.
- API key authentication only available for paid subscribers.

### Upstream OpenSpec integration

- Tool ID `kiro`; skills root `.kiro/skills/openspec-*/SKILL.md`; command root `.kiro/prompts/opsx-<id>.prompt.md`.

### openspec-extended integration notes

- `runner_binary="kiro-cli"`, `runner_kind="generic_print"`.
- `commands_dir="prompts"`, `commands_ext="prompt.md"`.
- `runner_args=("--trust-all-tools",)` (auto-approve for write phases).
- `slash_prefix="osx-"`, `skill_prefix="/"`, `requires_ide_restart=True`.

---

## 6. Gemini CLI

### Binary and headless invocation

- **Binary:** `gemini` (Google's open-source CLI). Install via `npm install -g @google/gemini-cli`.
- **Headless invocation shape:** `gemini -p "<prompt>"` — `-p` / `--prompt` runs in non-interactive mode.

### Plan-mode, sandbox, model flags

| Flag | Effect |
|------|--------|
| `-p`, `--prompt "<query>"` | Non-interactive mode |
| `--output-format text\|json\|stream-json` | Output format |
| `-m`, `--model <MODEL>` | Model selector |
| `--include-directories <list>` | Add extra workspace directories |
| `--yolo` | **Auto-approve all actions** (no permission prompts). **No sandbox implied.** |
| `--sandbox` | Run in a sandboxed environment (separate from `--yolo`) |
| `--approval-mode plan\|default\|auto-edit\|auto\|yolo` | Per-run approval mode |
| `--resume [sessionId]` | Resume previous session |

### Slash / skill invocation prefix

Gemini CLI's built-in commands are slash-form (`/help`, `/chat`, `/memory`, `/clear`, etc.). Skills are matched on user intent; no first-class slash form.

### Process model

Interactive TUI by default; auto-detects headless when stdin/stdout is redirected or `-p` is passed.

### Pitfalls

- `--yolo` does **not** enable a sandbox.

### Upstream OpenSpec integration

- Tool ID `gemini`; skills root `.gemini/skills/openspec-*/SKILL.md`; command root `.gemini/commands/opsx/<id>.toml` (TOML, namespaced).

### openspec-extended integration notes

- `runner_binary="gemini"`, `runner_kind="generic_print"`.
- `runner_args=("--yolo",)` (auto-approve for write phases).
- `commands_ext="toml"`, `commands_style="namespaced"`, `commands_dir="commands/opsx"`.
- `slash_prefix="osx:"` (namespaced layout).
- TOML frontmatter needs proper escape (control chars, CR/LF, lone CRs, quote runs, trailing backslashes).

---

## 7. GitHub Copilot

### Binary and headless invocation

- **Binary:** `copilot` (the standalone Copilot CLI). Install via `curl -fsSL https://gh.io/copilot-install | bash`.
- **Headless invocation shape:** The new agentic Copilot CLI does **not** ship a stable `--print`/`exec` subcommand as of writing. The interactive TUI is the primary surface.

### Slash / skill invocation prefix

The Copilot CLI uses `/`-prefixed slash commands (`/login`, `/model`, `/mcp`, etc.). Prompt files (`.github/prompts/*.prompt.md`) are recognized as custom slash commands in VS Code / JetBrains / Visual Studio IDE extensions — but the Copilot CLI does **not** currently consume these files directly.

### Cloud coding agent

A separate, opt-in flow:

1. `.github/workflows/copilot-setup-steps.yml` — installs `@fission-ai/openspec` in the agent's environment.
2. `.github/agents/openspec.agent.md` — describes how the agent should drive OpenSpec.

Selected with `openspec init --copilot-cloud` (or removed with `--no-copilot-cloud`).

### Process model

Interactive TUI (Copilot CLI) or asynchronous cloud agent (GitHub Actions workflow).

### Pitfalls

- The CLI does **not** read `.github/prompts/*.prompt.md` (only IDE extensions do).

### Upstream OpenSpec integration

- Tool ID `github-copilot`; skills root `.github/skills/openspec-*/SKILL.md`; command root `.github/prompts/opsx-<id>.prompt.md`.

### openspec-extended integration notes

- GitHub Copilot is the **weakest fit** for autonomous driver: no stable headless mode. Surface the cloud agent workflow; do not rely on the local CLI as primary.
- `runner_binary="copilot"`, `runner_kind="generic_print"`.
- `commands_ext="prompt.md"`, `commands_dir="prompts"`.
- `slash_prefix="osx-"`, `skill_prefix="/"`, `requires_ide_restart=True`.
- `detect_paths=(7 paths including 3 file-typed)`.
- `setup_note="Local CLI does not read these files; use the IDE for prompt invocation."`.

---

## 8. Devin Desktop

### Tool reality (important nuance)

Devin has **two distinct products**: Devin (cloud) and Devin CLI (formerly Windsurf CLI). The Devin CLI is what the orchestrator can drive.

### Binary and headless invocation

- **Binary:** `devin` (Devin CLI).
- **Headless invocation shape:** `devin -p "prompt words"` or `devin --print [PROMPT]`.

### Plan-mode, sandbox, model flags

| Flag | Effect |
|------|--------|
| `-p`, `--print [PROMPT]` | Single-turn mode; print response and exit |
| `-c`, `--continue` | Resume the most recent session in cwd |
| `-r`, `--resume <SESSION_ID>` | Resume a specific session |
| `-m`, `--model <MODEL>` | Set the model for this session |
| `--permission-mode <MODE>` | `normal`, `accept-edits`, `smart`, `dangerous`/`yolo`, `autonomous` |
| `--sandbox` | Run with OS-level process sandboxing |
| `--respect-workspace-trust [true\|false]` | Respect workspace trust; defaults `true` |
| `--prompt-file <FILE>` | Load the initial prompt from a file |

### Slash / skill invocation prefix

Slash commands inside the interactive REPL include `/plan`, `/ask`, `/bypass` (aliases `/yolo`, `/dangerous`), etc.

### Process model

Interactive REPL by default. `-p` is single-turn print-and-exit.

### Pitfalls

- `--print` in an untrusted directory fails; pass `--respect-workspace-trust false` in CI.
- Smart mode is rolling out gradually.
- Autonomous mode is **only** available with `--sandbox`.

### Upstream OpenSpec integration

- Tool ID `devin` (alias `windsurf`); skills root `.devin/skills/openspec-*/SKILL.md`; command root `.devin/workflows/opsx-<id>.md`.

### openspec-extended integration notes

- `runner_binary="devin"`, `runner_kind="generic_print"`.
- `runner_args=("--permission-mode", "bypass")` (write phases); use `plan` for read-only phases.
- `commands_dir="workflows"`, `commands_ext="md"`.
- `slash_prefix="osx-"`, `skill_prefix="/"`, `requires_ide_restart=True`.
- `detect_paths=(".devin", ".windsurf")`.
- `legacy_skills_dirs=(".windsurf",)` (PR6).

---

## 9. Continue

### Binary and headless invocation

- Continue is primarily a **VS Code / JetBrains extension**, not a standalone CLI. No widely-shipped Continue CLI today.
- For prompt files, Continue reads `.continue/prompts/opsx-<id>.prompt` with frontmatter `name`, `description`, `invokable: true`.

### Process model

IDE extension. No subprocess pattern suitable for openspec-extended's 7-phase driver.

### Pitfalls

- **No documented headless CLI**.

### Upstream OpenSpec integration

- Tool ID `continue`; skills root `.continue/skills/openspec-*/SKILL.md`; command root `.continue/prompts/opsx-<id>.prompt`.

### openspec-extended integration notes

- **Do not add a `continue` adapter to `REGISTRY` for runner dispatch.** Continue has no binary to spawn.
- `commands_dir="prompts"`, `commands_ext="prompt"`, `commands_style="flat"`.
- `runner_binary=""` (empty; preflight probe skips).
- `setup_note="Continue reads these files only inside the VS Code / JetBrains extension; there is no headless CLI."`.

---

## 10. Aider

### Reality check (important)

**Aider is NOT in upstream OpenSpec's `AI_TOOLS` list.** No `aider` row in `config.ts`, no Aider-specific adapter.

### Binary and headless invocation

- **Binary:** `aider` (Python package).
- **Headless invocation shape:** `aider --message "make a script that prints hello" hello.js`.

### Slash / skill invocation prefix

In-chat slash commands (`/add`, `/drop`, `/model`, `/help`, etc.) — Aider-specific.

### Process model

Interactive REPL with readline-style input by default.

### Pitfalls

- Aider auto-commits every successful change unless `--no-auto-commits`.
- Aider does not consume Agent Skills.

### openspec-extended integration notes

- **Skip.** Aider is fundamentally a different product.
- Two paths: (a) skip entirely; (b) bridge via `aider --message "..."` — but Aider doesn't read `.aider/skills/`. Not in scope.

---

## 11. Cline

### Binary and headless invocation

- **Binary:** `cline` (the standalone CLI).
- **Headless invocation shape:** `cline --json "refactor this module"` — headless mode triggered by `--json`, when stdin is piped, or when stdout is redirected.

### Plan-mode, sandbox, model flags

| Flag | Effect |
|------|--------|
| `-p`, `--plan` | Start in Plan mode |
| `--auto-approve <boolean>` | Global tool auto-approval (`true`/`false`, default `true`) |
| `-m`, `--model <model>` | Override model |
| `-P`, `--provider <id>` | Override provider |
| `-c`, `--cwd <path>` | Set working directory |
| `--json` | Newline-delimited JSON output |
| `--thinking <level>` | `none\|low\|medium\|high\|xhigh` |

### Slash / skill invocation prefix

In interactive mode: `/newtask`, `/smol`, `/newrule`, `/deep-planning`, etc. Any enabled skill is triggered via `/<skill-name>`.

### Process model

Interactive TUI by default; headless mode auto-engages for `--json`, piped stdin, or redirected stdout.

### Pitfalls

- `--auto-approve true` will modify files and run commands without further prompts.

### Upstream OpenSpec integration

- Tool ID `cline`; skills root `.cline/skills/openspec-*/SKILL.md`; command root `.clinerules/workflows/opsx-<id>.md` (Markdown header, no frontmatter).

### openspec-extended integration notes

- `runner_binary="cline"`, `runner_kind="generic_print"`.
- `runner_args=("--json", "--auto-approve", "true")`.
- `slash_prefix="osx-"`, `skill_prefix="/"`, `requires_ide_restart=True`.

---

## 12. Rovo Dev CLI

### Binary and headless invocation

- **Binary:** `acli rovodev` (Atlassian CLI — Rovo Dev is shipped through the `acli` command tree, not as a standalone binary).
- **Headless invocation shape:** `acli rovodev run "<instruction>"` — runs a single instruction non-interactively. Without an argument, `acli rovodev run` starts the interactive TUI. Use `acli rovodev run --yolo` for unattended execution.

### Slash / skill invocation prefix

Rovo Dev has no slash surface for skills — references are rewritten as natural-language prose ("use the openspec-propose skill").

### Process model

Interactive TUI by default; headless via `acli rovodev run`.

### openspec-extended integration notes

- `runner_binary="acli"`, `runner_kind="generic_print"`.
- `runner_args=("rovodev", "run", "--yolo")`.
- `slash_prefix=""` (natural-language refs).
- `commands_style="skills-only"`.
- `setup_note="Rovo Dev CLI is invoked as `acli rovodev run --yolo \"<prompt>\"` — not as a standalone binary."`.

---

## Summary: integration effort ranking

From lowest to highest integration effort:

1. **forgecode** — pure skills-only, no quirks.
2. **kimi** — skills-only with `/skill:` prefix; needs `cross_ref_prefix` (already supported).
3. **cursor** — generic_print with `--force` flag; straightforward.
4. **qwen** — generic_print; `.toml` extension needs PR4 plumbing.
5. **gemini** — generic_print with `--yolo`; `.toml` extension needs PR4 plumbing; namespaced layout.
6. **devin** — generic_print with permission-mode flag; multi-path detection including legacy `.windsurf`.
7. **kiro** — generic_print with `--trust-all-tools`; `.prompt.md` extension needs PR4 plumbing; `prompts/` subdir.
8. **cline** — generic_print with `--json --auto-approve true`; straightforward flags.
9. **codex** — skills-only; `$` prefix; `frontmatter_extras`; shared `.agents` root.
10. **github-copilot** — weak fit (no stable CLI); file-typed detection paths; multi-path.
11. **hermes** — only needs `setup_note`; multi-path detection with files.
12. **codeassistant** — natural-language skill refs; empty `slash_prefix`.

Plus:
- **antigravity** — needs `legacy_skills_dirs=(".agent",)`; multi-path detection.
- **minimax-code** — the only Heavy adapter; `global_skills_dir`.
- **aider** — skip entirely (not in upstream).
