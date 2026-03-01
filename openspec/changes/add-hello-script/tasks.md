# Tasks: Hello Script

## Implementation Checklist

### Setup
- [ ] Create `scripts/` directory if it does not exist

### Core Implementation
- [ ] Create `scripts/hello.sh` with proper shebang (`#!/usr/bin/env bash`)
- [ ] Add `set -euo pipefail` for strict mode
- [ ] Define `SCRIPT_NAME` and `DEFAULT_NAME` constants using `readonly`
- [ ] Implement `usage()` function that prints help to stdout

### Argument Handling
- [ ] Parse `--name` flag with following argument
- [ ] Parse `--help` flag to show usage and exit 0
- [ ] Handle unknown flags gracefully (optional: show error)

### Output
- [ ] Print greeting in format: `Hello, {NAME}!`
- [ ] Use `DEFAULT_NAME` ("World") when no `--name` provided

### Finalization
- [ ] Make script executable: `chmod +x scripts/hello.sh`
- [ ] Add `main "$@"` call at end of script

## Verification Checklist

- [ ] Test: `./scripts/hello.sh` outputs `Hello, World!`
- [ ] Test: `./scripts/hello.sh --name Alice` outputs `Hello, Alice!`
- [ ] Test: `./scripts/hello.sh --help` shows usage and exits 0
- [ ] Test: Script is executable without explicit bash command
- [ ] Test: Script exits with code 0 on success

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/hello.sh` | Main greeting script |

## Estimated Effort

Small change - single file, ~30-50 lines of code.
