---
name: osx-commit
description: Guide agents to create commits following project conventions. Detects Conventional, Angular, Gitmoji, or Classic commit styles from git history and config files.
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

Run detection script:

```bash
scripts/detect-commit-style
```

Or analyze manually:

```bash
git log --format="%s" -10
```

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

```bash
git log -1
```

## References

- `references/standards.md` - Full standards reference
- `references/detection.md` - Detection details
- `references/examples/conventional.md`
- `references/examples/angular.md`
- `references/examples/gitmoji.md`
- `references/examples/classic.md`

## Scripts

- `scripts/detect-commit-style` - Auto-detect commit standard from git history
