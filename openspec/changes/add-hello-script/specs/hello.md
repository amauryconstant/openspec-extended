# Specification: Hello Script

Version: 1.0.0

## ADDED

### Requirement: Default Greeting Output

The script SHALL output a greeting message when executed.

#### Scenario: No arguments provided
- **GIVEN** the script is executed without arguments
- **WHEN** the script runs
- **THEN** output "Hello, World!" to stdout
- **AND** exit with code 0

### Requirement: Custom Name Support

The script SHALL accept a `--name NAME` argument to customize the greeting.

#### Scenario: Custom name provided
- **GIVEN** the script is executed with `--name Alice`
- **WHEN** the script runs
- **THEN** output "Hello, Alice!" to stdout
- **AND** exit with code 0

#### Scenario: Name with spaces
- **GIVEN** the script is executed with `--name "Bob Smith"`
- **WHEN** the script runs
- **THEN** output "Hello, Bob Smith!" to stdout
- **AND** exit with code 0

### Requirement: Help Documentation

The script SHALL provide usage information via `--help`.

#### Scenario: Help requested
- **GIVEN** the script is executed with `--help`
- **WHEN** the script runs
- **THEN** display usage information to stdout
- **AND** exit with code 0

### Requirement: Script Location

The script MUST be located at `scripts/hello.sh`.

### Requirement: Executable Permission

The script MUST be executable.

### Requirement: Bash Compatibility

The script MUST use `#!/usr/bin/env bash` shebang.
The script MUST be compatible with Bash 4.0+.

### Requirement: Code Quality Standards

The script MUST use `set -euo pipefail` strict mode.
The script MUST use `readonly` for constants.
The script MUST use `local` for function-scoped variables.

### Requirement: Exit Codes

#### Scenario: Successful execution
- **GIVEN** the script completes successfully
- **WHEN** the script exits
- **THEN** exit code is 0

#### Scenario: Error condition
- **GIVEN** the script encounters an error
- **WHEN** the script exits
- **THEN** exit code is 1
- **AND** error message is written to stderr
