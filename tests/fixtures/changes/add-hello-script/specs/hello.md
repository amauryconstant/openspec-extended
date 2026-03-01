# Specification: Hello Script

Version: 1.0.0

## Overview

A command-line utility that prints a greeting message with customizable name.

## Functional Requirements

### FR-01: Default Greeting
**SHALL** output "Hello, World!" when executed without any arguments.

### FR-02: Custom Name
**SHALL** accept a `--name NAME` command-line argument.
**SHALL** output "Hello, {NAME}!" where {NAME} is the provided argument value.
**SHALL** use "World" as the default name when `--name` is not provided.

### FR-03: Help Documentation
**SHALL** accept a `--help` command-line argument.
**SHALL** display usage information to stdout when `--help` is provided.
**SHALL** exit with code 0 after displaying help.

### FR-04: Exit Codes
**SHALL** exit with code 0 on successful execution.
**SHALL** exit with code 1 on error conditions.

## Non-Functional Requirements

### NFR-01: Script Location
**MUST** be located at `scripts/hello.sh` in the project root.

### NFR-02: Executable
**MUST** be executable (have execute permission).

### NFR-03: Bash Compatibility
**MUST** be compatible with Bash 4.0+.
**MUST** use `#!/usr/bin/env bash` shebang.

### NFR-04: Code Quality
**MUST** use `set -euo pipefail` strict mode.
**MUST** use `readonly` for constants.
**MUST** use `local` for function-scoped variables.

## Interface Contract

```
Usage: hello.sh [OPTIONS]

Options:
  --name NAME    Customize the greeting name
  --help         Display usage information
```

## Output Format

Single line to stdout:
```
Hello, {NAME}!
```

Where `{NAME}` defaults to "World" or is the value provided via `--name`.
