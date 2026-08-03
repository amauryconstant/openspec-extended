---
name: osx-commit
description: Detect the project's commit standard (Conventional / Angular / Gitmoji / Classic) and apply it. Use when the user names a style or commits in an unfamiliar repo.
license: MIT
---

# osx-commit

Create commits that match project style.

## Process

### 1. Check Documentation

```bash
grep -i "commit" AGENTS.md CONTRIBUTING.md README.md 2>/dev/null
```

If conventions are defined, follow them.

### 2. Check Config Files

```bash
ls commitlint.config.js .commitlintrc .versionrc .gitmojirc 2>/dev/null
```

### 3. Detect Standard

```bash
scripts/detect-commit-style
```

Falls back to manual `git log --format="%s" -10` only when the script is absent.

| Pattern | Standard |
|---------|----------|
| `type:` or `type(scope):` | Conventional |
| `type(scope):` (scope required) | Angular |
| Emoji at start | Gitmoji |
| Imperative verbs, no prefix | Classic |

### 4. Apply Standard

- **Conventional:** `type: description`
- **Angular:** `type(scope): description` (body required)
- **Gitmoji:** `emoji description`
- **Classic:** `Verb description` (no prefix)

### 5. Stage and Review

```bash
git add <files>
git diff --staged
```

### 6. Draft and Commit

Follow detected standard. See references for examples.

### 7. Verify

`git log -1 --format='%s'` returns the standard's prefix shape (e.g. `feat:` for Conventional).

## References

- `references/standards.md` — full standards reference
- `references/detection.md` — detection details
- `references/examples/conventional.md`
- `references/examples/angular.md`
- `references/examples/gitmoji.md`
- `references/examples/classic.md`

## Scripts

- `scripts/detect-commit-style` — auto-detect commit standard from git history
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/osx-commit/SKILL.md
Regenerate: `mise run sync:mirrors`
-->
