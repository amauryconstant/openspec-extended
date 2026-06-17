# Tasks: Hello Script

## 1. Setup

- [ ] 1.1 Create `scripts/` directory if it does not exist

## 2. Core Implementation

- [ ] 2.1 Create `scripts/hello.sh` with proper shebang (`#!/usr/bin/env bash`)
- [ ] 2.2 Add `set -euo pipefail` for strict mode
- [ ] 2.3 Define `SCRIPT_NAME` and `DEFAULT_NAME` constants using `readonly`
- [ ] 2.4 Implement `usage()` function that prints help to stdout

## 3. Argument Handling

- [ ] 3.1 Parse `--name` flag with following argument
- [ ] 3.2 Parse `--help` flag to show usage and exit 0
- [ ] 3.3 Handle unknown flags (exit 1 with error to stderr)

## 4. Output

- [ ] 4.1 Print greeting in format: `Hello, {NAME}!`
- [ ] 4.2 Use `DEFAULT_NAME` ("World") when no `--name` provided

## 5. Finalization

- [ ] 5.1 Make script executable: `chmod +x scripts/hello.sh`
- [ ] 5.2 Add `main "$@"` call at end of script

## 6. Verification

- [ ] 6.1 Test: `./scripts/hello.sh` outputs `Hello, World!`
- [ ] 6.2 Test: `./scripts/hello.sh --name Alice` outputs `Hello, Alice!`
- [ ] 6.3 Test: `./scripts/hello.sh --help` shows usage and exits 0
- [ ] 6.4 Test: Script is executable without explicit `bash` command
- [ ] 6.5 Test: Script exits with code 0 on success
