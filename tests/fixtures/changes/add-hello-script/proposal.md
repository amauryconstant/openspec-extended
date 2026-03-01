# Add Hello Script

## Summary

Add a simple `scripts/hello.sh` script that prints a greeting message with optional name customization.

## Motivation

Provide a reusable greeting utility for the project that demonstrates proper bash scripting conventions including argument parsing, help documentation, and error handling.

## Goals

- Create a well-structured bash script following project conventions
- Support basic greeting with customizable name
- Include proper help documentation
- Follow bash best practices (strict mode, error handling)

## Non-Goals

- Complex configuration file support
- Internationalization
- Multiple output formats

## Success Criteria

- [ ] Script exists at `scripts/hello.sh`
- [ ] Script is executable
- [ ] Running `./scripts/hello.sh` outputs "Hello, World!"
- [ ] Running `./scripts/hello.sh --name Alice` outputs "Hello, Alice!"
- [ ] Running `./scripts/hello.sh --help` shows usage information
- [ ] Script exits with code 0 on success
- [ ] Script follows project bash conventions (shebang, strict mode)
