# Spec: hello-script

## ADDED Requirements

### Requirement: Default Greeting
The system SHALL output `Hello, World!` to stdout when executed without any arguments.

#### Scenario: No arguments
- **WHEN** the script is run with no arguments
- **THEN** it SHALL print `Hello, World!` to stdout
- **AND** it SHALL exit with code 0

### Requirement: Custom Name
The system SHALL accept a `--name NAME` flag and output `Hello, {NAME}!`.

#### Scenario: --name Alice
- **WHEN** run with `--name Alice`
- **THEN** it SHALL print `Hello, Alice!` to stdout
- **AND** it SHALL exit with code 0

### Requirement: Help
The system SHALL accept a `--help` flag and print usage information to stdout.

#### Scenario: --help
- **WHEN** run with `--help`
- **THEN** it SHALL print usage information to stdout
- **AND** it SHALL exit with code 0

### Requirement: Exit Codes
The system SHALL exit with code 0 on success and code 1 on invalid arguments.

#### Scenario: Invalid flag
- **WHEN** run with an unknown or malformed flag
- **THEN** it SHALL exit with code 1

### Requirement: Script Location
The script SHALL be located at `scripts/hello.sh` in the project root.

#### Scenario: File exists
- **WHEN** the project tree is inspected
- **THEN** the file `scripts/hello.sh` SHALL exist

### Requirement: Executable
The script file SHALL have the executable bit set.

#### Scenario: Executable bit set
- **WHEN** `ls -l scripts/hello.sh` is run
- **THEN** the permission bits SHALL include execute for the owner

### Requirement: Bash Compatibility
The script SHALL be compatible with Bash 4.0 or later.

#### Scenario: Runs under Bash 4.0+
- **WHEN** the script is invoked with `bash` 4.0 or later
- **THEN** it SHALL execute without syntax errors

### Requirement: Bash Strict Mode
The script SHALL use `#!/usr/bin/env bash` as its shebang and SHALL enable `set -euo pipefail` strict mode.

#### Scenario: Shebang and strict mode present
- **WHEN** the script file is read
- **THEN** the first line SHALL be `#!/usr/bin/env bash`
- **AND** the script SHALL contain `set -euo pipefail`

### Requirement: Code Quality
The script SHALL use `readonly` for module-level constants and `local` for function-scoped variables, and SHALL define separate `usage()` and `main()` functions invoked via `main "$@"`.

#### Scenario: Code quality markers present
- **WHEN** the script is read
- **THEN** it SHALL contain at least one `readonly` declaration
- **AND** it SHALL contain at least one `local` declaration
- **AND** it SHALL define `usage()` and `main()` functions
- **AND** it SHALL invoke `main "$@"` at the end
