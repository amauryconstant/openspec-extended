# Design: Hello Script

## Context

The project currently has no utility for emitting a standardized greeting
message. Adding `scripts/hello.sh` introduces a small, well-structured bash
script that doubles as a reference implementation of the project's bash
conventions: shebang form, strict mode, `readonly` constants, `local`
function variables, argument parsing, help text, and exit-code policy. The
script must be self-contained (no external dependencies beyond `bash`) and
must run on any POSIX-style shell environment with Bash 4.0+.

## Goals / Non-Goals

**Goals:**

- Produce a self-contained, executable `scripts/hello.sh` that prints
  `Hello, {NAME}!` to stdout.
- Default the name to `World` when no `--name` is provided.
- Accept `--name NAME` to customize the greeting.
- Accept `--help` to print usage information to stdout and exit 0.
- Exit 0 on success, exit 1 on invalid arguments.
- Use `#!/usr/bin/env bash`, `set -euo pipefail`, `readonly` for
  module-level constants, and `local` for function-scoped variables.
- Define separate `usage()` and `main()` functions, invoked via `main "$@"`
  at the end of the script.

**Non-Goals:**

- Configuration file support.
- Internationalization or locale handling.
- Multiple output formats (JSON, YAML, etc.).
- Logging, verbose mode, or diagnostic flags.
- Packaging, installation, or distribution.
- A `--version` flag.

## Decisions

- **Shebang `#!/usr/bin/env bash`**: Use `env` to resolve `bash` from
  `PATH` rather than hard-coding `/bin/bash`. This allows portability
  across distributions where `bash` may live in different paths
  (`/bin/bash`, `/usr/bin/bash`, `/usr/local/bin/bash`).
- **Strict mode `set -euo pipefail`**: Fail fast on errors, unset
  variables, and broken pipes. This matches project bash conventions and
  prevents silent failures during argument parsing or output.
- **Module-level `readonly` constants**: `SCRIPT_NAME` (derived from
  `${BASH_SOURCE[0]##*/}`) and `DEFAULT_NAME="World"` are declared
  `readonly` to prevent accidental reassignment and to make intent
  explicit.
- **Separate `usage()` and `main()` functions**: Decompose the script into
  discrete, testable functions. `usage()` writes help to stdout and is
  safe to call without coupling to the caller's exit-code policy. `main`
  handles argument parsing and delegates to `usage` for `--help`.
- **Invocation via `main "$@"`**: Single entry point at the bottom of the
  script forwards all arguments unmodified. The `$@` quoting preserves
  arguments with spaces.
- **Exit-code policy**: Exit 0 for success and for `--help` (a successful
  invocation). Exit 1 for invalid or unknown arguments. Error messages
  flow to stderr, normal output to stdout.
- **Unknown flag is an error**: An unknown flag exits 1 rather than being
  silently ignored, so callers learn about mistakes immediately.

## Risks / Trade-offs

- **Strict-mode interaction with argument parsing** → Mitigation: keep
  argument parsing simple (small `while/case` loop, no `[[ -z $(cmd) ]]`
  patterns). The reference script is intentionally minimal.
- **No automated tests in this change** → Mitigation: PHASE2 manually
  exercises each spec scenario. A future change can add a `tests/`
  harness once more scripts adopt this pattern.
- **`env` shebang assumes `bash` is on `PATH`** → Mitigation: this is
  true on every supported platform for this project. The alternative
  (`#!/bin/bash`) breaks on systems where bash lives elsewhere.
- **Single-file script** → Trade-off: simpler distribution, but no shared
  library for argument parsing across future scripts. A future refactor
  can extract a `lib/parse-args.bash` if duplication becomes a problem.
