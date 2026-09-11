# Audit Procedure

Project-internal design tooling for OpenSpec-extended. Compares the
OpenSpec core against the extension to surface integration drift and
gaps. Not shipped in the binary; lives outside the orchestrator/skills
trees.

## When to run

- **Pre-release**: before cutting a tag, capture the current state and
  review the report.
- **After bumping the OpenSpec core subtree**: run `mise run sync-core` first, then
  run the audit to confirm the orchestrator still honors every new core
  contract.
- **Periodically (quarterly)**: catch slow drift between docs and code.

## Workflow — capture-then-dispatch

Capture state once, dispatch subagents in parallel, then synthesize.
Capture is sequential. A and B run together. C and D run together
after A and B. E runs alone.

### 1. Capture (sequential, mandatory)

Resolve the upstream and local target roots from `references/targets.toml`.
Record the git HEAD hash for each. Save to `.audit/captures/<UTC-date>-captures.txt`.

### 2. Phase A — Upstream target map (parallel with B)

Compute `upstream_head = <hash>`. If `.audit/maps/<upstream_head>-upstream.md`
exists, load it and skip dispatch. Otherwise dispatch an `explore`
subagent (read access to the upstream root). Save the result keyed by
the upstream HEAD hash.

### 3. Phase B — Local target map (parallel with A)

Mirror of A for the local target, keyed by `local_head`. Read also the
manifest path from the config.

### 4. Phase C — Diff (parallel with D; depends on A + B)

Dispatch an `explore` subagent with both maps as input. Apply the diff
patterns in `references/diff-patterns.md`.

### 5. Phase D — Quality eval (parallel with C; depends on A + B)

Dispatch one `explore` subagent per category listed in
`references/quality-categories.md`.

### 6. Phase E — Synthesize (depends on C + D)

Combine findings. Assign severity using `references/severity-rubric.md`.
Build the report following `references/output-template.md`. Save to
`.audit/reports/<UTC-date>-audit.md`.

## Severity tiers

CRITICAL → HIGH → MEDIUM → LOW.

| Tier | Definition |
|------|------------|
| CRITICAL | Core contract surface that the orchestrator or skills depend on has changed without the extension adapting. |
| HIGH | A shipped resource no longer matches a documented behavior; users will hit it. |
| MEDIUM | Documentation drift; resource version skew between manifest and body. |
| LOW | Cosmetic / naming / cross-platform manifest inconsistency. |

## Targets

The two targets and their roots are declared in
`references/targets.toml`. Edit when targets or roots change.

- **Upstream** — `OpenSpec Core`, rooted at `orchestrator/core/`, HEAD tracked via `orchestrator/core/source/package.json`.
- **Local** — `OpenSpec Extended`, rooted at `orchestrator/source/`, HEAD tracked via `orchestrator/source/__init__.py`. Resources at `orchestrator/resources/` and `skills/resources/`; manifests at `orchestrator/resources/opencode/manifest.toml` and `skills/resources/opencode/manifest.toml`.

## Tools

Read-only filesystem analysis.

- `git log -1`, `git diff --stat`, `wc -l`, `mkdir -p`, `date -u`
- `Read`, `Grep`, `Glob`
- `Task` to dispatch `explore` subagents (`very thorough` thoroughness)

The audit never shells out to project binaries. It reads source.

## Guardrails

- Read-only. The audit returns Markdown; it never edits files.
- Cache A/B maps by HEAD hash.
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

Note: those reference files were part of the now-deleted audit skill.
A future PR may re-export them as standalone docs for use with a
`mise run audit` task; for now, treat this procedure as the
authoritative version.
