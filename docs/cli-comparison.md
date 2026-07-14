# CLI Comparison

Pick the right tool for the job. This document maps upstream `openspec` commands to `openspec-extended` (top-level passthrough) and the `osx` sub-app (programmatic library access).

## TL;DR

| Surface | When to use | Form |
|---------|-------------|------|
| `openspec` | Standard OpenSpec workflow | Direct CLI calls |
| `openspec-extended` | Same workflow + extension skills/agents + autonomous loop | One binary, no switching |
| `openspec-extended osx` | Programmatic access to change state from scripts/CI | JSON to stdout, machine-friendly |

If you are doing manual change management the way OpenSpec intends, use `openspec-extended validate`, `openspec-extended list`, etc. They pass through unchanged. If you want to drive the autonomous loop or script against change state, use the `osx` sub-app.

## Top-Level Passthrough Matrix

All commands in the second column are passthrough wrappers around the first. Exit codes, flags, and stdout are forwarded as-is. Implementation: `source/cli.py:647-955`.

| Upstream `openspec` | `openspec-extended` passthrough | `openspec-extended osx` (programmatic) |
|---------------------|---------------------------------|----------------------------------------|
| `openspec validate <id>` | `openspec-extended validate <id>` | `openspec-extended osx validate change <id>` |
| `openspec validate --all` | `openspec-extended validate --all` | `openspec-extended osx validate all` |
| `openspec validate --type spec <id>` | `openspec-extended validate --type spec <id>` | `openspec-extended osx validate spec <id>` |
| `openspec validate --changes` | `openspec-extended validate --changes` | `openspec-extended osx validate changes` |
| `openspec validate --specs` | `openspec-extended validate --specs` | `openspec-extended osx validate specs` |
| `openspec list` | `openspec-extended list` | `openspec-extended osx state get <change>` (per-change) |
| `openspec list --specs` | `openspec-extended list --specs` | -- |
| `openspec show <id>` | `openspec-extended show <id>` | `openspec-extended osx ctx get <id>` |
| `openspec status --change <id>` | `openspec-extended status --change <id>` | `openspec-extended osx complete check <id>` |
| `openspec instructions <art>` | `openspec-extended instructions <art>` | -- |
| `openspec templates` | `openspec-extended templates` | -- |
| `openspec templates --schema <name>` | `openspec-extended templates --schema <name>` | `openspec-extended osx schema which <name>` |
| `openspec schemas` | `openspec-extended schemas` | `openspec-extended osx schema list` |
| `openspec schema <sub>` | `openspec-extended schema <sub>` | `openspec-extended osx schema which\|validate\|fork\|init` |
| `openspec init [path]` | `openspec-extended init [path]` | -- |
| `openspec update [path]` | `openspec-extended update-core [path]` | -- |
| `openspec feedback <msg>` | `openspec-extended feedback <msg>` | -- |
| `openspec completion <shell>` | `openspec-extended completion <shell>` | -- |

Most cells marked `--` mean: the upstream command has no direct programmatic equivalent in the `osx` library, because `osx` is a state/IO tool rather than an instruction-rendering tool.

## Extension-Only Commands

These exist only in `openspec-extended`. They have no upstream equivalent.

| Command | Purpose | Implementation |
|---------|---------|----------------|
| `openspec-extended install <tool>` | Copy `osx-*` skills, agents, and commands into the target platform's resource directory | `source/cli.py:526-549` |
| `openspec-extended install opencode --with-core` | Same, plus the 11 upstream `osc-*` commands | `source/cli.py:526-549` |
| `openspec-extended update <tool>` | Force-update (overwrite) extension resources | `source/cli.py:556-580` |
| `openspec-extended update-core [tool]` | Refresh upstream instruction files | `source/cli.py:926-938` |
| `openspec-extended orchestrate <change>` | Run the 7-phase autonomous loop | `source/cli.py:583-645` and `source/orchestrator/engine.py` |
| `openspec-extended osx ...` | Programmatic library access (10 domains) | `source/osx_cli.py` |

## `osx` Sub-App Domains

`openspec-extended osx <domain> <action>` exposes 10 state/IO domains. Each command outputs JSON to stdout on success and JSON to stderr on failure (with non-zero exit). Library source: `source/lib/osx.py`.

| Domain | Actions | Example |
|--------|---------|---------|
| `baseline` | `record`, `get` | `osx baseline record` |
| `ctx` | `get` | `osx ctx get add-auth` |
| `git` | `get` | `osx git get add-auth` |
| `phase` | `current`, `next`, `advance` | `osx phase advance add-auth` |
| `state` | `get`, `complete`, `transition`, `clear-transition`, `set-phase` | `osx state get add-auth` |
| `iterations` | `get`, `append` | `osx iterations append add-auth --phase PHASE1 --iteration 1 --summary "..."` |
| `log` | `get`, `append` | `osx log append add-auth --phase PHASE1 --iteration 1 --summary "..."` |
| `complete` | `check`, `get`, `set` | `osx complete check add-auth` |
| `validate` | `json`, `skills`, `commands`, `change-dir`, `archive`, `iterations`, `completion`, `change`, `spec`, `all`, `changes`, `specs` | `osx validate change-dir add-auth` |
| `schema` | `which`, `validate`, `fork`, `init`, `list` | `osx schema which --all` |
| `instructions` | passthrough to `openspec instructions` | `osx instructions proposal` |
| `store` | `list`, `doctor`, `register`, `unregister` | `osx store list` |

`osx` outputs:

```bash
$ openspec-extended osx state get add-auth
{"phase": "PHASE1", "iteration": 1, "phase_complete": false, "change": "add-auth"}
```

Failures are also JSON:

```bash
$ openspec-extended osx state get does-not-exist
{"error": "change_not_found", "message": "Change directory does not exist", "change": "does-not-exist"}
```

(exit code 1)

This makes `osx` safe to script: parse stdout or stderr, both are JSON.

## When to Use Which

### Manual change management

Use `openspec-extended <command>` for everything upstream OpenSpec supports. The passthrough is byte-identical to `openspec <command>` and adds the `osx-*` extension skills/agents to your project on `install`.

```bash
openspec-extended validate add-auth --json --strict
openspec-extended list
openspec-extended show add-auth --deltas-only
```

### Autonomous end-to-end implementation

Use `openspec-extended orchestrate <change>`. This drives the 7-phase loop until PHASE6 archives the change. See [Orchestrator state machine](./orchestrator-state-machine.md) for the phase model.

```bash
openspec-extended orchestrate add-auth
openspec-extended orchestrate add-auth --max-phase-iterations 20 --verbose
openspec-extended orchestrate add-auth --from-phase PHASE3
openspec-extended orchestrate add-auth --schema workspace-planning
```

### Scripting and CI

Use `openspec-extended osx ...`. JSON output, no prompt interactions, exit codes that mean something. Combine with `jq` for filtering:

```bash
openspec-extended osx validate all --strict | jq '.summary.totals.failed'
openspec-extended osx state get add-auth | jq -r '.phase'
openspec-extended osx schema which --all | jq '.[].name'
```

`osx validate ...` is the right choice for CI: it returns the same shape upstream `openspec validate --json` produces, translated by `_translate_validate_payload` (`source/lib/osx.py:1320-1394`). You can wire it into GitHub Actions or GitLab CI without parsing markdown.

### Schema exploration

Use the `osx schema` sub-app or the top-level `schema` passthrough interchangeably — both delegate to `openspec schema *`. The `osx` form gives you Python-importable wrappers (`source/lib/osx.py:1585-1679`) for use in tests and other code.

```bash
# List every schema and its source
openspec-extended schema --all --json

# Resolve which schema the project uses
openspec-extended osx schema which

# Validate a schema definition
openspec-extended osx schema validate spec-driven

# Fork spec-driven into a project-local copy you can edit
openspec-extended osx schema fork spec-driven my-flow
```

## Diff With Upstream OpenSpec

| Capability | Upstream | Extended |
|------------|----------|----------|
| Spec-driven change workflow | yes | yes (delegated) |
| Validate JSON, change-dir, completion | yes | yes (delegated) + extra `osx validate` actions |
| Multi-store (`openspec store *`) | yes | yes (delegated) + `osx store` |
| Schema resolution at runtime | partial | yes — 4-level precedence at `source/lib/osx.py:1490-1547` |
| Schema-aware phase commands | no | planned Sprint 5 |
| Autonomous 7-phase loop | no | yes — `orchestrate` |
| Resume from interrupted state | no | yes — `state.json` round-trip |
| Decision log (`decision-log.json`) | no | yes — phase-by-phase audit trail |
| Iteration budget per phase | no | yes — `DEFAULT_MAX_PHASE_ITERATIONS = 10` |
| Extension skills and agents | no | yes — 8 skills + 3 agents |
| Per-phase model selection | no | planned Sprint 7 |
| Bulk orchestration | no | planned Sprint 7 |
| Transcript replay | no | planned Sprint 7 |

## See Also

- [Troubleshooting](./troubleshooting.md)
- [Orchestrator state machine](./orchestrator-state-machine.md)
- `source/cli.py` — passthrough wrappers
- `source/osx_cli.py` — `osx` sub-app
- `source/lib/osx.py` — library implementation
- [README](../README.md) — install and quickstart