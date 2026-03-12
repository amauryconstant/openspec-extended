# Lib Scripts Reference

Helper scripts in `.opencode/scripts/lib/` for reliable agent operations. All output JSON.

## Primary Tool: `osc` (Python)

The `osc` tool is the primary CLI for OpenSpec change management. It replaces multiple bash scripts with a unified Python interface.

**Location**: `.opencode/scripts/lib/osc`

**Requirements**: Python 3.8+ (stdlib only, no external packages)

### Commands

```
osc <domain> <action> [args]

Domains:
  ctx         Aggregate context for a change
  git         Git status for change directory
  state       Phase and iteration state management
  iterations  Iteration history tracking
  log         Decision log management
  complete    Completion status tracking
  validate    Validation utilities
```

### Ctx Domain

```
osc ctx get <change>
```

Returns aggregated context: state, git status, artifacts, history.

### Git Domain

```
osc git get <change>
```

Returns git status for the change directory.

### State Domain

```
osc state get <change>
osc state set-phase <change> <PHASE>
osc state complete <change>
osc state transition <change> <target> <reason> [details]
osc state clear-transition <change>
```

**Transition reasons:**
- `implementation_incorrect` - Artifacts correct, code needs fixing
- `artifacts_modified` - Specs/design updated, re-implement needed
- `retry_requested` - Same phase, different approach

### Iterations Domain

```
osc iterations get <change>
osc iterations append <change> --phase <PHASE> --iteration <N> [options]
```

Options: `--summary`, `--status`, `--issues`, `--artifacts-modified`, `--decisions`, `--errors`

Also accepts JSON via stdin for backward compatibility.

### Log Domain

```
osc log get <change>
osc log append <change> --phase <PHASE> --iteration <N> [options]
```

Options: `--summary`, `--issues`, `--artifacts-modified`, `--next-steps`, `--decisions`, `--errors`

Also accepts JSON via stdin for backward compatibility.

### Complete Domain

```
osc complete check <change>
osc complete get <change>
osc complete set <change> [COMPLETE|BLOCKED] [--blocker-reason "text"]
```

### Validate Domain

```
osc validate skills
osc validate commands
osc validate change-dir <change>
osc validate archive <change>
osc validate iterations <change>
osc validate completion <change>
osc validate json <file>
```

## Output Examples

### osc state get

```json
{"phase": "PHASE1", "iteration": 2, "phase_complete": false, "change": "add-auth"}
```

### osc state transition

```json
{"success": true, "transition": {"target": "PHASE1", "reason": "implementation_incorrect"}}
```

### osc iterations get

```json
{"count": 5, "iterations": [1, 2, 3, 4, 5]}
```

### osc complete check

```json
{"exists": true}
```

### osc validate skills

```json
{"valid": true}
```

Or with errors:

```json
{"valid": false, "errors": [{"check": "skills", "message": "Missing skill: openspec-concepts"}]}
```

## Usage Patterns

### Pre-injection in commands (via `!command`)

```markdown
## Context

!`osc ctx get $1`
```

### Agent execution during phase

```bash
# Mark phase complete
osc state complete $1

# Signal transition to fix implementation
osc state transition $1 PHASE1 implementation_incorrect "ValidationPipeline missing early exit"

# Log iteration
osc iterations append $1 --phase PHASE1 --iteration 2 --summary "Fixed validation"

# Log decision
osc log append $1 --phase PHASE0 --iteration 1 --summary "Reviewed artifacts"
```

---

## Legacy Bash Scripts (Deprecated)

These scripts are still available but deprecated. Use `osc` instead.

| Script | Replaced By | Usage |
|--------|-------------|-------|
| `osc-ctx` | `osc ctx` | `osc-ctx <change>` |
| `osc-git` | `osc git` | `osc-git [change]` |
| `osc-state` | `osc state` | `osc-state <change> <action>` |
| `osc-iterations` | `osc iterations` | `osc-iterations <change> [get\|append]` |
| `osc-log` | `osc log` | `osc-log <change> [get\|append]` |
| `osc-complete` | `osc complete` | `osc-complete <change> <action>` |
| `osc-validate` | `osc validate` | `osc-validate <change> <action>` |

## Bash-Only Scripts (Not Yet Migrated)

| Script | Purpose | Usage |
|--------|---------|-------|
| `osc-baseline` | Baseline tracking | `osc-baseline <action>` |
| `osc-phase` | Phase advancement | `osc-phase <change> <action>` |
| `osc-common` | Shared functions | (sourced by other scripts) |

### osc ctx get Output

```json
{
  "change": "add-auth",
  "state": {"phase": "PHASE0", "iteration": 1, "phase_complete": false},
  "git": {"modified": [], "added": [], "untracked": [], "clean": true},
  "artifacts": {
    "proposal": {"exists": true, "size": 2048},
    "specs": {"exists": true, "count": 2},
    "design": {"exists": true, "size": 4096},
    "tasks": {"exists": true, "size": 1024}
  },
  "history": {"decision_log_entries": 3, "iterations_recorded": 1}
}
```
