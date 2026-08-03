# Store Selection

Skills and commands that read from or write to a change can target a registered store instead of the local `openspec/` root. A store is a standalone OpenSpec repo registered on this machine.

## Discover registered stores

```bash
openspec store list --json
```

The response is an array of `{id, name, root, ...}`. Use `id` for the `--store` flag.

## Carry `--store <id>` on every relevant command

| Command | Takes `--store`? |
|---|---|
| `new change` | yes |
| `status` | yes |
| `instructions` | yes |
| `list` | yes |
| `show` | yes |
| `validate` | yes |
| `archive` | yes |
| `doctor` | yes |
| `context` | yes |
| `instructions archive` | yes (read-only mirror of proposal/apply variants) |

Hints printed by commands already carry the flag; keep it on follow-ups.

## Without a store

Commands act on the nearest local `openspec/` root.

## Machine-level fallback (v1.7.0+)

`openspec config set defaultStore <id>` sets a project-wide default. Status responses report `root.source: "global_default"` when used. Prefer per-command `--store` over the global default when you can — it makes the choice visible to anyone reading the audit log.

## See also

- `references/schema-agnostic-contract.md` — the contract these store-selection rules belong to.
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/references/store-selection.md
Regenerate: `mise run sync:mirrors`
-->
