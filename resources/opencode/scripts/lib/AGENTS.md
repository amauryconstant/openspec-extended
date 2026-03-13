# Lib Scripts Reference

Helper scripts in `.opencode/scripts/lib/` for reliable agent operations. All output JSON.

## Primary Tool: `osx` (Python)

The `osx` tool is the unified CLI for OpenSpec change management. It replaces multiple bash scripts with a unified Python interface.

**Location**: `.opencode/scripts/lib/osx`

**Requirements**: Python 3.8+ (stdlib only, no external packages)

### Commands

```
osx <domain> <action> [args]

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
osx baseline record
osx baseline get
```

Records and retrieves baseline (commit/branch/timestamp) in `.openspec-baseline.json`.

### Ctx Domain

```
osx ctx get <change>
```

Returns aggregated context: state, git status, artifacts, history.

### Git Domain

```
osx git get <change>
```

Returns git status for the change directory.

### Phase Domain

```
osx phase current <change>
osx phase next <change>
osx phase advance <change>
```

- `current` - Get current phase, next phase, and iteration
- `next` - Get just the next phase name
- `advance` - Advance to next phase, reset iteration to 1

### State Domain

```
osx state get <change>
osx state set-phase <change> <PHASE>
osx state complete <change>
osx state transition <change> <target> <reason> [details]
osx state clear-transition <change>
```

**Transition reasons:**

- `implementation_incorrect` - Artifacts correct, code needs fixing
- `artifacts_modified` - Specs/design updated, re-implement needed
- `retry_requested` - Same phase, different approach

### Iterations Domain

```
osx iterations get <change>
osx iterations append <change> --phase <PHASE> --iteration <N> [options]
```

Options: `--summary`, `--status`, `--notes`, `--commit-hash`, `--issues`, `--artifacts-modified`, `--decisions`, `--errors`, `--extra`

Also accepts JSON via stdin for backward compatibility.

### Log Domain

```
osx log get <change>
osx log append <change> --phase <PHASE> --iteration <N> [options]
```

Options: `--summary`, `--commit-hash`, `--next-steps`, `--issues`, `--artifacts-modified`, `--decisions`, `--errors`, `--extra`

Also accepts JSON via stdin for backward compatibility.

### Complete Domain

```
osx complete check <change>
osx complete get <change>
osx complete set <change> [COMPLETE|BLOCKED] [--blocker-reason "text"]
```

### Validate Domain

```
osx validate skills
osx validate commands
osx validate change-dir <change>
osx validate archive <change>
osx validate iterations <change>
osx validate completion <change>
osx validate json <file>
```

## Output Examples

### osx baseline record

```json
{
  "commit": "abc123def456...",
  "branch": "main",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### osx phase current

```json
{ "phase": "PHASE1", "next": "PHASE2", "iteration": 2 }
```

### osx phase advance

```json
{ "phase": "PHASE2", "previous": "PHASE1", "next": "PHASE3", "iteration": 1 }
```

### osx state get

```json
{
  "phase": "PHASE1",
  "iteration": 2,
  "phase_complete": false,
  "change": "add-auth"
}
```

### osx state transition

```json
{
  "success": true,
  "transition": { "target": "PHASE1", "reason": "implementation_incorrect" }
}
```

### osx iterations get

```json
{ "count": 5, "iterations": [1, 2, 3, 4, 5] }
```

### osx complete check

```json
{ "exists": true }
```

### osx validate skills

```json
{ "valid": true }
```

Or with errors:

```json
{
  "valid": false,
  "errors": [{ "check": "skills", "message": "Missing skill: osx-concepts" }]
}
```

## Usage Patterns

### Pre-injection in commands (via `!command`)

```markdown
## Context

!`osx ctx get $1`
```

### Agent execution during phase

```bash
# Mark phase complete
osx state complete $1

# Signal transition to fix implementation
osx state transition $1 PHASE1 implementation_incorrect "ValidationPipeline missing early exit"

# Log iteration
osx iterations append $1 --phase PHASE1 --iteration 2 --summary "Fixed validation"

# Log decision
osx log append $1 --phase PHASE0 --iteration 1 --summary "Reviewed artifacts"

# Record baseline before starting
osx baseline record

# Advance to next phase
osx phase advance $1
```

### osx ctx get Output

```json
{
  "change": "add-auth",
  "state": { "phase": "PHASE0", "iteration": 1, "phase_complete": false },
  "git": {
    "modified": [],
    "added": [],
    "untracked": [],
    "clean": true,
    "branch": "main"
  },
  "artifacts": {
    "proposal": { "exists": true, "size": 2048 },
    "specs": { "exists": true, "count": 2 },
    "design": { "exists": true, "size": 4096 },
    "tasks": { "exists": true, "size": 1024 }
  },
  "history": { "decision_log_entries": 3, "iterations_recorded": 1 }
}
```
