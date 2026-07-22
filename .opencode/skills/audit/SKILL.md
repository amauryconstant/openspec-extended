---
name: audit
description: Multi-agent harmonization audit of openspec-core vs openspec-extended in this repository. Load when the user asks to audit, review, harmonize, or check integration between the openspec-core subtree and the openspec-extended code, or after a sync from upstream. Dispatches parallel explore subagents to map each surface and evaluate quality, then synthesizes a prioritized backlog with file:line references. Read-only — never modifies files.
license: MIT
metadata:
  author: openspec-extended
  version: "0.1.0"
  generatedBy: manual
---

## Tools Available

- Task tool — dispatch parallel `explore` subagents (thoroughness: "very thorough")
- Read, Grep, Glob — file-system analysis
- Bash (limited to): `git log -1`, `git diff --stat`, `git rev-parse`, `realpath`, `wc -l`, `mkdir -p`, `date -u`

The audit does not invoke `openspec` or `openspec-extended` binaries. It reads source files directly.

## Input

The command body accepts `/audit [scope]`. Scopes map to phase selection:

| Scope | Phases executed |
|-------|-----------------|
| `full` | Capture + A + B + (C ∥ D) + E |
| `upstream` | Capture + A |
| `local` | Capture + B |
| `integration` | Capture + C (assumes A and B output is recent or cached) |
| `skills` | Capture + B (skill/agent/command subset) + D (skill/agent/command subset) + E |
| `docs` | Capture + C (doc subset) + E |

Default is `full`.

## Workflow

Use the **parallel-then-sequential** pattern. Capture is sequential and must complete before any other phase. Phases A and B are independent subagents and run concurrently. Phases C and D both consume A + B output and run concurrently. Phase E synthesizes everything.

### Capture step (sequential, mandatory)

Run before any subagent. Save the output to `docs/audits/<UTC-date>-captures.txt`.

1. Resolve roots:
   - Upstream subtree: `openspec-core/`
   - Local code: `source/`, `resources/`, top-level manifests

2. Record upstream head: `git log -1 --format='%h %ad %s' --date=short openspec-core/source/package.json`

3. Record local head: `git log -1 --format='%h %ad %s' --date=short source/__init__.py`

4. Identify upstream-vs-local divergence: `git diff --stat openspec-core/source/<last-sync-ref>..HEAD -- openspec-core/source/` (read `openspec-core/AGENTS.md` for the sync mechanism and ref format)

5. Count lines per major surface area:

   ```bash
   wc -l openspec-core/source/src/cli/index.ts \
         openspec-core/source/src/core/*.ts \
         source/cli.py source/osx_cli.py source/lib/osx.py \
         source/orchestrator/engine.py source/orchestrator/runner.py
   ```

6. Run a quick `openspec --version` if available — purely informational; record as "binary version" or "binary not installed".

### Phase A — Upstream surface map (parallel with Phase B)

Dispatch one Task subagent (`subagent_type: explore`, thoroughness: "very thorough") with read access to `openspec-core/source/`. Pass it:

- The captured metadata from the Capture step
- The reference template at `references/upstream-surface.md`
- Instruction: fill every applicable section; mark sections N/A when the surface lacks that artifact
- Output requirement: return the filled template as a single Markdown block

Do not constrain the subagent's reading beyond `openspec-core/source/` and `openspec-core/AGENTS.md`. The subagent should produce a structured map, not findings.

### Phase B — Local surface map (parallel with Phase A)

Dispatch one Task subagent (`subagent_type: explore`, thoroughness: "very thorough") with read access to `source/`, `resources/`, and the manifests. Pass it:

- The captured metadata
- The reference template at `references/local-surface.md`
- Same instruction as Phase A

### Phase C — Diff & inconsistencies (sequential, depends on A + B)

Dispatch one Task subagent (`subagent_type: explore`, thoroughness: "very thorough") with read access to both trees and the A + B maps as input. The subagent applies the diff patterns listed below and emits per-finding entries.

**Diff patterns the subagent must check:**

1. **Naming drift** — every literal in skills/commands/agents (`/opsx-*`, `/osc-*`, `/osx-*`, `OPSX:`, `openspec-*`); verify against the current rename pass at `source/cli.py:353-424` and the upstream install layout at `openspec-core/.opencode/commands/`
2. **CLI flag assumptions** — every `subprocess.run(["openspec", …])` call in `source/lib/osx.py` and `source/orchestrator/engine.py`; verify each flag exists in `openspec-core/source/src/cli/index.ts`
3. **JSON shape assumptions** — every `_run_openspec_json` envelope consumer in `source/lib/osx.py`; verify keys against `openspec-core/source/docs/agent-contract.md`
4. **Schema drift** — `resolve_schema`, `required_core_skills`, `list_artifacts_for_schema` in `source/lib/osx.py:1490-1582`; verify against `openspec-core/source/schemas/spec-driven/schema.yaml`
5. **Manifest parity** — entries in `resources/opencode/manifest.toml` and `resources/claude/manifest.toml` vs files actually deployed at `resources/opencode/{skills,agents,commands}/`
6. **Doc drift** — counts in `README.md`, examples in `install.sh`, version strings in `AGENTS.md` files vs the actual current state

### Phase D — Surface quality eval (sequential, depends on A + B; runs in parallel with Phase C)

Dispatch one Task subagent (`subagent_type: explore`, thoroughness: "very thorough") for each of:

- **Skill quality** (8 skills): description triggering, schema-agnostic compliance, gating, AskUserQuestion appropriateness, agent permission alignment
- **Agent quality** (3 agents): `mode` field, permission blocks, temperature rationale, prompt clarity
- **Command quality** (12 commands): frontmatter description, dispatch logic, guardrails, agent routing
- **Phase quality** (PHASE0–PHASE6): command bodies vs engine dispatch in `source/orchestrator/engine.py`, permission contradictions, ordering conflicts with engine cleanup

The subagent returns per-surface findings.

### Phase E — Synthesize report (sequential, depends on C + D)

Self task (no subagent). Combine findings, apply the severity rubric at `references/severity-rubric.md`, and write the report.

1. Group findings by section (Naming, CLI, Schema, Skills, Agents, Commands, Phases, Docs).
2. Assign severity using the rubric.
3. Build the prioritized backlog table (CRITICAL → LOW).
4. Save to `docs/audits/<UTC-date>-audit.md`.
5. Print the same content to stdout.

## Severity rubric

Inline summary; full rubric and worked examples at `references/severity-rubric.md`.

| Tier | Definition |
|------|------------|
| CRITICAL | Silent failure · autonomous-loop break · test cements wrong behavior · production bug |
| HIGH | Drift · dead references · version-gated silent no-op · missing contract test · permission contradiction |
| MEDIUM | Doc drift · version literal mismatch · missing preflight · double-flag · duplicated constants |
| LOW | Terminology · redundant comment · layout polish |

## Output template

Use the **Flexible Template + Progressive Disclosure** pattern. Sections appear only when findings exist for that category.

```markdown
# Integration Audit — openspec-core vs openspec-extended — <UTC-date>

## Metadata

| openspec-core | openspec-extended |
| --- | --- |
| commit `<hash>` <date> | commit `<hash>` <date> |
| <file count> files | <file count> files |
| v<X.Y.Z> | v<A.B.C> |

## Executive Summary

- ≤10 bullets covering severity counts, top findings, blast radius
- One bullet per CRITICAL finding (filename + one-line issue)

## Key Findings (CRITICAL + HIGH only)

One paragraph per finding: file:line, issue, concrete fix, blast radius.

## Detailed Findings

### Naming & Taxonomy
### CLI / JSON / Schema Drift
### Manifest / Resource Parity
### Skill Quality
### Agent Quality
### Command Quality
### Phase Workflow Quality
### Documentation Drift

Each section: list of findings as `file:line — issue — fix` tuples, grouped by sub-area.

## Prioritized Backlog

| # | Severity | File:line | Issue | Suggested fix |
|---|----------|-----------|-------|---------------|
| 1 | CRITICAL | `lib/osx.py:1076` | `osx store register --name` should be `--id` | rename flag; update test |
| … | … | … | … | … |

## Out of Scope / Deferred

Items that look like findings but are intentional (e.g., different version domains by design, intentional prefix collision).
```

## Guardrails

- **Read-only.** No file edits.
- **No mutation during audit.** Do not run `git subtree pull`, `mise run sync-core`, `openspec update`, or any installer. Capture first; never mutate mid-audit.
- **Save once per UTC date.** Overwrite same-date report; do not append.
- **Cite file:line for every claim.** No paraphrasing. Group related findings under one header.
- **Use captured metadata, not fresh reads**, in subsequent phases — avoids race conditions between phases.
- **Respect the parallel-then-sequential structure.** Capture must complete before A or B; A and B must complete before C or D; C and D must complete before E.
- **No schema/runtime inference.** The audit reasons from source files only. If a flag cannot be verified from source, mark "UNVERIFIED" and note the gap.
- **Subagent reads only.** Subagents must not edit files, install tools, or run mutating commands.

## See Also

- `.opencode/commands/audit.md` — slash-command entry point
- `references/upstream-surface.md` — Phase A template
- `references/local-surface.md` — Phase B template
- `references/severity-rubric.md` — full severity rubric + worked examples
- `openspec-core/AGENTS.md` — how `openspec-core/source/` is synced into this repo
- `openspec-core/source/docs/agent-contract.md` — upstream JSON contract (authoritative)
- `openspec-core/source/docs/opsx.md` — upstream workflow design reference
- `AGENTS.md` (root) — naming conventions, version domains, project contract
- `source/AGENTS.md`, `source/orchestrator/AGENTS.md`, `source/lib/AGENTS.md` — local subsystem contracts
