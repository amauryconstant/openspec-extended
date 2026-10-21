# Resource Separation

The Phase 5 split pins the contract between the two resource trees
(`orchestrator/resources/canonical/` and `skills/resources/canonical/`).
This rule documents the runtime invariants and the rationale for
shared-references ownership.

## Tree layout

```
orchestrator/resources/canonical/      # workflow side
├── manifest.toml                      # orchestrator-source manifest
├── skills/osx-workflow/...            # orchestrator-side skill
├── agents/osx-*.md                    # orchestrator-side agents
└── commands/osx-*.md                  # orchestrator-side commands

skills/resources/canonical/            # gap-filling side
├── manifest.toml                      # skills-source manifest
├── skills/osx-*/SKILL.md              # skills-side skills
└── commands/osx-*.md                  # skills-side commands
```

Two source trees, two source manifests, two deployed manifests
(`<target>/manifest.toml` for orchestrator, `<target>/skills-manifest.toml`
for skills). The two source manifests are disjoint by construction; the
runtime check `_assert_manifests_disjoint_and_prefixed` enforces it on
every deploy.

## On-disk ownership

### Shared references pool

A single canonical shared-references pool lives at
`orchestrator/resources/canonical/skills/references/`. Both side manifests
may declare `references = [...]`; deploy resolves every entry against this
one pool.

- `deploy_skills` (cli.py:373) reads from the pool by absolute path. This
  is the canonical entry point used for both orchestrator-side and
  skills-side skills.
- `_deploy_skill_mirror` (cli.py:545) reads from
  `source_base.parent / "skills" / "references"` — caller-relative.
  Used by the Claude modern-mirror path. Resolves to the same files
  because the mirror's `source_base` is always under one of the two
  canonical roots.

Two conventions coexist; both resolve to the same files. Caller-relative
makes future test fixtures easier to isolate.

### Core (`osc-*`) entries

`osc-*` resources live only on the TARGET side, never on the SOURCE
side. They are absorbed post-deploy by
`_preserve_core_tracking` (cli.py:747) when `--with-core` is enabled.
Source manifests must never declare `osc-*` entries — the runtime check
in Item A rejects them.

## Disjoint-manifest invariant

Two rules:

1. Each side's source manifest declares only `osx-*` resources.
2. The two side manifests are disjoint: no name appears on both sides.

Enforced in Python by
`orchestrator/source/cli.py:_assert_manifests_disjoint_and_prefixed`,
called from `deploy_all_resources` after both manifests are loaded.
Locks the Phase 5 parity invariant on uncommitted edits before any
deploy side-effect runs.

The committed-manifests invariant is pinned separately by
`tests/unit/test_resource_contract.py::TestManifestParity`.

## Validation

`lib/osx/__init__.py:validate_commands` walks both side manifests at validation
time:

- Orchestrator-side commands cross-checked via `PHASE_COMMANDS` against
  the deployed filesystem (`_command_resolved_for_phase`).
- Skills-side commands cross-checked via the skills-side manifest's
  `[resources.commands]` against the deployed filesystem.
- The two checks share the same resolver so per-adapter layout quirks
  (`commands_style`, `cmd_filename_strip_prefix`) apply uniformly.

The skills-side command set is small and stable today (`osx-review`,
`osx-verify-tests`); the cross-check is symmetric so future skills-side
commands get the same guarantee for free.

## Meta tag at deploy time

Every deploy writes `meta.side = "orchestrator"` or `meta.side = "skills"`
into the deployed manifest before serialization, so the deployed files
are self-describing. A reader that loads both manifests separately
(via `_load_per_side_manifests`) gets the side label from the file
path; the tag is for merged-manifest consumers and third-party tools.

## Out-of-scope (known follow-ups)

- E: split `lib/osx/` constants (`REQUIRED_SKILLS`, `REQUIRED_CORE_SKILLS`,
  `ORCHESTRATION_RESOURCE_NAMES`) into per-side sub-modules for clarity.
- F: unify `deploy_skills` and `_deploy_skill_mirror` refs-resolution
  conventions.
- G: introduce a `SIDE` enum to replace string-tuple dispatch.
