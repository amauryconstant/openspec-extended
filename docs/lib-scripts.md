# Lib Scripts Reference

Helper scripts in `.opencode/scripts/lib/` for reliable agent operations. All output JSON.

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `osc-state` | State file CRUD + transitions | `osc-state <change> <action>` |
| `osc-ctx` | Aggregate context | `osc-ctx <change>` |
| `osc-iterations` | Iteration history | `osc-iterations <change> [get\|append]` |
| `osc-log` | Decision logging | `osc-log <change> [get\|append]` |
| `osc-git` | Git status | `osc-git [change]` |

## Usage Patterns

### Pre-injection in commands (via `!command`)

```markdown
## Context

!`osc-ctx $1`
```

### Agent execution during phase

```bash
# Mark phase complete
osc-state $1 complete

# Signal transition to fix implementation
osc-state $1 transition PHASE1 implementation_incorrect "ValidationPipeline missing early exit"

# Log iteration
echo '{"iteration":2,"phase":"IMPLEMENTATION",...}' | osc-iterations $1 append

# Log decision
echo '{"phase":"PHASE0","iteration":1,"summary":"..."}' | osc-log $1 append
```

### osc-state Actions

| Action | Description |
|--------|-------------|
| `get` | Get current state |
| `set-phase <PHASE>` | Set current phase |
| `complete` | Mark phase complete (normal advance) |
| `transition <PHASE> <reason> [details]` | Set explicit transition target |
| `clear-transition` | Clear transition field |

**Transition reasons:**
- `implementation_incorrect` - Artifacts correct, code needs fixing
- `artifacts_modified` - Specs/design updated, re-implement needed
- `retry_requested` - Same phase, different approach


## Output Examples

### osc-state

```json
{"phase":"PHASE1","iteration":2,"phase_complete":false,"change":"add-auth"}
```

### osc-state transition

```json
{"success":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}
```

### osc-ctx

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

### osc-log

Maintains:
- `decision-log.json` - Structured decision log with entries appended via JSON input
