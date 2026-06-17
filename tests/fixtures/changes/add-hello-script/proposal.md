# Add Hello Script

## Why

The project lacks a small, well-structured bash utility for emitting a
greeting message. Adding `scripts/hello.sh` provides a canonical example of
the project's bash conventions (argument parsing, help text, strict mode,
error handling) that future scripts can mirror.

## What Changes

- Add a new executable bash script at `scripts/hello.sh`.
- The script prints `Hello, {NAME}!` to stdout, defaulting `NAME` to `World`
  when no `--name` flag is provided.
- The script accepts `--name NAME` to customize the greeting.
- The script accepts `--help` to display usage information and exit with
  code 0.
- The script uses `set -euo pipefail` and exits with code 0 on success and
  1 on error.

## Capabilities

### New Capabilities

- `hello-script`: Command-line greeting utility that prints
  `Hello, {NAME}!` with optional `--name` and `--help` flags, written as a
  strict-mode bash script.

### Modified Capabilities

None.

## Impact

- **New file**: `scripts/hello.sh` (executable). No existing files are
  modified.
- **Conventions**: Establishes the project bash script conventions
  (shebang, strict mode, `readonly` constants, `local` variables, exit codes)
  that future scripts should follow.
- **Users**: Project contributors gain a reference bash script and a small
  reusable greeting utility.
- **Tooling**: None required. The script depends only on `bash` 4.0+, which
  is available on standard Unix-like systems.
