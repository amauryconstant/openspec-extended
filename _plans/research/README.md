# Research — raw outputs from the exploration phase

This subfolder preserves the raw research outputs from the four parallel exploration agents that produced the upstream-parity plan. The plan itself lives in the parent folder (`README.md` + `pr/`) and references these files for grounding.

## Files

| File | Source agent | What it covers |
|------|--------------|----------------|
| `01-upstream-tool-catalog.md` | Agent 1 (catalog task) | Complete inventory of upstream's 39 `AI_TOOLS` entries with full field shapes, adapter taxonomy, capability model, invocation rules, and cross-references to upstream source files. |
| `02-tool-invocation-shapes.md` | Agent 2 (invocation task) | Per-tool CLI invocation shape, plan-mode flags, sandbox flags, slash/skill prefixes, process models, and integration notes for 12 targeted tools (Cursor, Codex, Kimi, Qwen, Kiro, Gemini, GitHub Copilot, Devin, Continue, Aider, Cline, Rovo Dev). |
| `03-tool-adapter-audit.md` | Agent 3 (audit task) | Field-level audit of `orchestrator/source/tools.py` against upstream `AI_TOOLS`. Documents every existing field, every missing field, and the consumer files for each. Includes per-tool classification. |
| `04-coverage-matrix.md` | Agent 4 (coverage + sequencing task) | Full coverage matrix mapping 39 tools to effort tiers (Low/Medium/High), three-tier adapter model, 7-PR sequenced rollout, critical infrastructure questions, and risks. |

## How to use this folder

These documents are **reference material**, not action items. The plan files in `../pr/` are the action items. When in doubt about a decision, check:

1. **Why this PR exists** → `../00-decisions.md`
2. **What ships in this PR** → `../pr/PR<N>-*.md`
3. **What the field does** → `../reference/adapter-field-reference.md`
4. **What the upstream shape is** → `01-upstream-tool-catalog.md` (or upstream `orchestrator/core/source/src/core/config.ts`)
5. **What the local shape is** → `03-tool-adapter-audit.md` (or local `orchestrator/source/tools.py`)

## Why preserve the raw research

1. **Reproducibility** — when a future contributor questions a design choice, the raw research explains how the choice was reached.
2. **Onboarding** — a new contributor can read these to understand the *why* behind every field, test, and registration-order decision.
3. **Drift detection** — when upstream moves (new tools, renamed tools, new detection paths), the raw research provides a baseline to diff against.

## Updating this folder

When a PR lands:

1. If the PR changed a field shape, update `03-tool-adapter-audit.md` to reflect the new field set.
2. If the PR added a new tool, update `02-tool-invocation-shapes.md` with the tool's verified CLI flags (especially if any were discovered to differ from upstream docs).
3. If the PR exposed a new upstream contract (e.g. a new capability), update `01-upstream-tool-catalog.md`.
4. If the PR shifted the coverage matrix, update `04-coverage-matrix.md`'s status table.

Each file's header (`**Date:** 2026-09-14`) should be updated to reflect the latest material change.
