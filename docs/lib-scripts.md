# Lib Scripts Reference

Helper scripts in `.opencode/scripts/lib/` for reliable agent operations. All output JSON.

## Primary Tool: `osc` (Python)

The `osc` tool is the unified CLI for OpenSpec change management. It replaces multiple bash scripts with a unified Python interface.

**Location**: `.opencode/scripts/lib/osc`

**Requirements**: Python 3.8+ (stdlib only, no external packages)

### Commands

```
osc <domain> <action> [args]

Domains:
  baseline    Baseline tracking (commit/branch)
  ctx         Aggregate context for a change
  git         Git status for change directory
  phase       Phase advancement management
  state       Phase and iteration state management
  iterations  Iteration history tracking
  log         Decision log management
  complete    Completion status tracking
  validate    Validation utilities
```

### Baseline Domain

```
osc baseline record
osc baseline get
```

Records and retrieves baseline (commit/branch/timestamp) in `.openspec-baseline.json`.

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

### Phase Domain

```
osc phase current <change>
osc phase next <change>
osc phase advance <change>
```

- `current` - Get current phase, next phase, and iteration
- `next` - Get just the next phase name
- `advance` - Advance to next phase, reset iteration to 1

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

Options: `--summary`, `--status`, `--notes`, `--commit-hash`, `--issues`, `--artifacts-modified`, `--decisions`, `--errors`, `--extra`

Also accepts JSON via stdin for backward compatibility.

### Log Domain

```
osc log get <change>
osc log append <change> --phase <PHASE> --iteration <N> [options]
```

Options: `--summary`, `--commit-hash`, `--next-steps`, `--issues`, `--artifacts-modified`, `--decisions`, `--errors`, `--extra`

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

### osc baseline record

```json
{"commit": "abc123def456...", "branch": "main", "timestamp": "2024-01-15T10:30:00Z"}
```

### osc phase current

```json
{"phase": "PHASE1", "next": "PHASE2", "iteration": 2}
```

### osc phase advance

```json
{"phase": "PHASE2", "previous": "PHASE1", "next": "PHASE3", "iteration": 1}
```

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

# Record baseline before starting
osc baseline record

# Advance to next phase
osc phase advance $1
```

### osc ctx get Output

```json
{
  "change": "add-auth",
  "state": {"phase": "PHASE0", "iteration": 1, "phase_complete": false},
  "git": {"modified": [], "added": [], "untracked": [], "clean": true, "branch": "main"},
  "artifacts": {
    "proposal": {"exists": true, "size": 2048},
    "specs": {"exists": true, "count": 2},
    "design": {"exists": true, "size": 4096},
    "tasks": {"exists": true, "size": 1024}
  },
  "history": {"decision_log_entries": 3, "iterations_recorded": 1}
}
```
