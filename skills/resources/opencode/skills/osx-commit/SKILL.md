---
name: osx-commit
description: Detect the project's commit standard (Conventional / Angular / Gitmoji / Classic) and apply it. Use when the user names a style or commits in an unfamiliar repo.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  audience: orchestrator phase commits (PHASE1 / PHASE2 / PHASE3 / PHASE4 / PHASE5 / PHASE6) and ad-hoc /osx-commit invocations
  workflow: orthogonal — invoked after every orchestrated write
---

# osx-commit

Create commits that match project style.

**Input**: No positional arguments. The orchestrator invokes `/osx-commit` after every phase write (PHASE1 / PHASE2 / PHASE3 / PHASE4 / PHASE5 / PHASE6); ad-hoc `/osx-commit` invocations operate on the user's currently staged or unstaged changes. Detect the commit standard from the project, draft a subject that matches, and commit. If no standard is detected and the user invoked ad-hoc, fall back to Conventional Commits and ask via `{{ASK_TOOL}}` only when there is genuine ambiguity (multiple standards matched).

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

Follow detected standard. See Format examples below and the
`references/standards.md` reference for the full type tables.

### 7. Verify

`git log -1 --format='%s'` returns the standard's prefix shape (e.g. `feat:` for Conventional).

## Format examples

One minimal example per standard. The full per-type tables live in
`references/standards.md`.

### Conventional Commits

```
feat(api): add rate limiting endpoint

- Add token bucket middleware
- Configure limits per route

Closes #123
```

Common types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`. Body wrapped at 72 chars; lowercase
description, no trailing period; `!` before `:` marks breaking changes.

### Angular

```
fix(router): resolve lazy loading guard order

Previously, the router would incorrectly resolve guards during
lazy loading scenarios. This fix ensures guards are resolved
in the correct order for all navigation types.

- Fix guard resolution timing
- Add integration tests

Fixes #12345
```

Scope is mandatory for non-`docs` types; body required (≥20 chars)
except for `docs`. Types: `build`, `ci`, `docs`, `feat`, `fix`,
`perf`, `refactor`, `test`.

### Gitmoji

```
✨ Add user authentication system
```

```
🐛 Fix memory leak in image processor

- Clear cache after batch processing
- Add memory usage monitoring
```

Common emojis: ✨ feat, 🐛 fix, 📝 docs, ♻️ refactor, 💄 style,
🔥 remove, 🚀 deploy, 🔒 security, ✅ tests, 🔧 config.

### Classic

```
Fix PHASE6 workflow issues in openspec-auto

- Return error for archived changes without state.json
- Skip show_progress after PHASE6 (state deleted)
```

Subject ≤50 chars ideal, 72 max. Capitalize first letter, no trailing
period, imperative mood. Common verbs: Add, Fix, Update, Remove,
Refactor, Release, Improve, Rename, Bump, Enable.

## References

- `references/standards.md` — full standards reference (per-type tables, common scopes, common emojis, seven rules)
- `references/detection.md` — detection heuristics and verification regexes

## Scripts

- `scripts/detect-commit-style` — auto-detect commit standard from git history
