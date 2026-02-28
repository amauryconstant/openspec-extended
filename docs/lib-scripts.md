# Lib Scripts Reference

Helper scripts in `.opencode/scripts/lib/` for reliable agent operations. All output JSON.

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `osc-state` | State file CRUD | `osc-state <change> [get\|set-phase\|complete]` |
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

# Log iteration
echo '{"iteration":2,"phase":"IMPLEMENTATION",...}' | osc-iterations $1 append

# Log decision
echo '{"phase":"PHASE0","iteration":1,"summary":"..."}' | osc-log $1 append
```

## Output Examples

### osc-state

```json
{"phase":"PHASE1","iteration":2,"phase_complete":false,"change":"add-auth"}
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

Maintains both:
- `decision-log.md` - Human/agent readable markdown
- `decision-log.json` - Machine-queryable index
