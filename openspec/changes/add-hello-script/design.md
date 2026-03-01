# Design: Hello Script

## Context

This project uses bash scripts for various utilities and automation tasks. A greeting script serves as a simple demonstration of project conventions for:
- Argument parsing patterns
- Help documentation format
- Error handling standards
- Code structure (strict mode, readonly constants, functions)

This script will be the first in the `scripts/` directory and establishes patterns for future additions.

## Overview

A simple bash script that prints a greeting message with optional name customization. The script demonstrates proper bash scripting conventions used in this project.

## Decisions

### Decision 1: Use Bash with Strict Mode

**Rationale**: Bash is universally available and strict mode (`set -euo pipefail`) catches common errors early.

**Alternatives considered**:
- Python: More verbose for simple output, requires interpreter
- Plain sh: Less features, no arrays or advanced string handling

### Decision 2: Single Output Format

**Rationale**: Keep output simple and predictable for potential piping or capture.

**Alternatives considered**:
- JSON output: Overkill for a greeting
- Multiple formats via flag: Adds complexity without clear benefit

### Decision 3: Location at scripts/hello.sh

**Rationale**: Follows common convention of placing utility scripts in a dedicated `scripts/` directory.

## Implementation Details

### Location
- Path: `scripts/hello.sh`

### Structure

```bash
#!/usr/bin/env bash
# Brief description of the script

set -euo pipefail

# Constants
readonly SCRIPT_NAME=$(basename "$0")
readonly DEFAULT_NAME="World"

# Functions
usage() { ... }
main() { ... }

main "$@"
```

### Interface

```
Usage: hello.sh [OPTIONS]

Options:
  --name NAME    Greet specific name (default: World)
  --help         Show this help message

Examples:
  hello.sh                    # Output: Hello, World!
  hello.sh --name Alice       # Output: Hello, Alice!
```

### Argument Parsing

- Parse `--name NAME` to customize greeting
- Parse `--help` to show usage
- Ignore unknown arguments (or exit with error)

### Output Format

Single line output to stdout:
```
Hello, {NAME}!
```

### Error Handling

- Exit 0 on success
- Exit 1 on error (invalid arguments, etc.)
- Error messages to stderr

### Code Quality

- Follow project bash style guide
- Use `readonly` for constants
- Use `local` for function variables
- Include brief header comment
