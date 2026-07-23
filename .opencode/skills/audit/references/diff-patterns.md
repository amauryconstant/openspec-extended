# Diff Patterns

Phase C applies the patterns below to the two surface maps. Each pattern names a class of drift to look for. Specific items under each pattern are project state and refresh per audit.

## 1. Naming taxonomy drift

Look for inconsistencies between how the upstream and local surfaces name the same kinds of things.

- Slash command prefixes and display names
- Skill name prefixes
- Agent name prefixes
- Subcommand / option naming conventions
- Display tokens used in prompts

## 2. CLI flag assumptions

Verify that every CLI flag the local wrapper passes to the upstream CLI still exists in the current upstream version.

- Subprocess invocations of the upstream CLI
- Flags passed to each invocation
- Assumptions about flag behavior (mutates, returns JSON, exits non-zero on error)

## 3. JSON envelope assumptions

Verify that consumers of the upstream CLI's `--json` outputs read keys that still exist in the current upstream version.

- Every code path that parses `--json` output
- Keys assumed to be present
- Shape assumed (object vs array, nesting)

## 4. Schema drift

Verify that the local wrapper's understanding of the upstream schema matches the current schema definition.

- Schema resolution code
- Required skills per schema
- Artifact lists per schema
- Required fields per artifact

## 5. Resource manifest parity

Verify that every resource declared in the manifest is actually deployed, and that every deployed resource is declared.

- Skills declared vs shipped
- Agents declared vs shipped
- Commands declared vs shipped
- Version numbers in sync

## 6. Documentation drift

Verify that counts, version literals, and examples in user-facing documentation match the actual current state.

- README counts (skills, agents, commands, phases)
- Version literals in examples
- Install example version pins
- Doc strings that reference code paths
