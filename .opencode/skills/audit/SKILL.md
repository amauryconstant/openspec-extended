---
name: audit
description: Run via /audit [scope]. Compares OpenSpec Core vs OpenSpec Extended; verifies integration is correct and up-to-date. Reads references/targets.toml; emits prioritized CRITICAL→LOW backlog.
---

# User-invocation note

OpenCode has no native `disable-model-invocation` flag for skills; unknown frontmatter fields are silently ignored. The description above is narrow on purpose so the agent does not auto-fire on natural language. Reach the skill through the `/audit` slash command.

## Targets

The two targets and their roots are declared in `references/targets.toml`. Edit that file when targets or roots change. Default:

- **Upstream** — `OpenSpec Core`, rooted at `openspec-core/`, HEAD tracked via `openspec-core/source/package.json`.
- **Local** — `OpenSpec Extended`, rooted at `source/`, HEAD tracked via `source/__init__.py`, resources at `resources/`, manifest at `resources/opencode/manifest.toml`.

## Scopes

| Scope | Phases | When to use |
|-------|--------|-------------|
| `full` (default) | Capture + A + B + (C ∥ D) + E | Periodic review, pre-release |
| `upstream` | Capture + A | Quick inventory of the upstream target |
| `local` | Capture + B | Quick inventory of the local target |
| `integration` | Capture + C | Diff-only, after a library or wrapper change (assumes recent A/B maps) |
| `skills` | Capture + B (skill/agent/command subset) + D (subset) + E | Skill/agent/command review |
| `docs` | Capture + C (doc subset) + E | Documentation drift sweep |

Pass `--refresh` to force re-dispatch of A/B even when a cached map exists.

## Tools

Read-only filesystem analysis.

- **Bash**, limited to: `git log -1`, `git diff --stat`, `wc -l`, `mkdir -p`, `date -u`.
- **Read**, **Grep**, **Glob** for filesystem analysis.
- **Task** to dispatch `explore` subagents (thoroughness: `very thorough`).

The audit never shells out to project binaries. It reads source.

## Workflow — capture-then-dispatch

Capture state once, dispatch subagents in parallel, then synthesize. Capture is sequential. A and B run together. C and D run together after A and B. E runs alone.

### 1. Capture (sequential, mandatory)

Read `references/targets.toml`. Resolve the upstream and local target roots. Record the git HEAD hash for each. Count LOC on the canonical files listed in the config. Save the result to `.audit/captures/<UTC-date>-captures.txt`.

### 2. Phase A — Upstream target map (parallel with B)

Compute `upstream_head = <hash>`. If `.audit/maps/<upstream_head>-upstream.md` exists, load it and skip dispatch. Otherwise dispatch one `explore` subagent with read access to the upstream root and `allowed_reads` from the config. The subagent fills the surface schema described in `references/diff-patterns.md` and the quality categories in `references/quality-categories.md`. Save the result keyed by the upstream HEAD hash.

### 3. Phase B — Local target map (parallel with A)

Mirror of A for the local target, keyed by `local_head`. Read also `resources_root` and `manifest` paths from the config.

### 4. Phase C — Diff (parallel with D; depends on A + B)

Dispatch one `explore` subagent with both maps as input. The subagent applies the patterns in `references/diff-patterns.md` and emits per-finding entries.

### 5. Phase D — Quality eval (parallel with C; depends on A + B)

Dispatch one `explore` subagent per category listed in `references/quality-categories.md`. Each subagent returns per-surface findings.

### 6. Phase E — Synthesize (depends on C + D)

Combine findings. Assign severity using `references/severity-rubric.md` and the anchors in `references/rubric-examples.md`. Build the report following `references/output-template.md`. Save to `.audit/reports/<UTC-date>-audit.md`. Print the same content to stdout.

## Severity tiers

CRITICAL → HIGH → MEDIUM → LOW. Definitions in `references/severity-rubric.md`. Worked anchors in `references/rubric-examples.md`.

## Guardrails

- Read-only. The audit returns Markdown; it never edits files.
- Cache A/B maps by HEAD hash. `--refresh` invalidates.
- Save the report once per UTC date. Same-date reruns overwrite; do not append.
- Capture must complete before A or B; A and B before C or D; C and D before E.
- Subagents are read-only. They return Markdown, never file changes.

## See also

- `references/targets.toml` — the two targets
- `references/diff-patterns.md`
- `references/quality-categories.md`
- `references/severity-rubric.md`
- `references/rubric-examples.md`
- `references/output-template.md`
