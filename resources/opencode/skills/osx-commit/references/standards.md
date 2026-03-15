# Commit Message Standards Reference

Four major standards cover 90%+ of projects.

## Quick Reference

| Standard | Format | Prefix | Scope | Emoji | Detection |
|----------|--------|--------|-------|-------|-----------|
| Conventional | `type: desc` | Required | Optional | No | `feat:`, `fix:`, etc. |
| Angular | `type(scope): desc` | Required | Required | No | `feat(core):` pattern |
| Gitmoji | `emoji desc` | No | No | Yes | Emoji at start |
| Classic | `Verb desc` | No | No | No | Imperative verbs |

---

## 1. Conventional Commits

Most widely adopted, machine-readable format.

**Format:**
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Rules:**
- Type prefix required (lowercase)
- Colon + space after type
- `!` before `:` for breaking changes
- Lowercase description, no period
- Body wrapped at 72 chars
- Footers: `BREAKING CHANGE:`, `Fixes #123`, `Refs #456`

**Types:**

| Type | Meaning | SemVer |
|------|---------|--------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation | None |
| `style` | Formatting | None |
| `refactor` | Code change (no fix/feat) | None |
| `perf` | Performance | PATCH |
| `test` | Tests | None |
| `build` | Build system | None |
| `ci` | CI config | None |
| `chore` | Maintenance | None |

**See:** `examples/conventional.md`

---

## 2. Angular Commit Guidelines

Stricter subset of Conventional Commits.

**Format:**
```
<type>(<scope>): <short summary>

<body>

<footer>
```

**Key Differences from Conventional:**
- Scope **mandatory** for most types (except `docs`)
- Body **required** (min 20 chars) except for `docs`
- Stricter scope list (usually package names)
- Present tense imperative only

**Types:** `build`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `test`

**See:** `examples/angular.md`

---

## 3. Gitmoji

Emoji-based, popular in visual/creative projects.

**Format:**
```
<emoji> <description>

[optional body]
```

**Rules:**
- Start with emoji (or code `:emoji_name:`)
- Space after emoji
- Imperative mood description
- Can combine with conventional commits

**Common Emojis:**

| Emoji | Code | Meaning |
|-------|------|---------|
| ✨ | `:sparkles:` | New feature |
| 🐛 | `:bug:` | Bug fix |
| 📝 | `:memo:` | Documentation |
| ♻️ | `:recycle:` | Refactor |
| 💄 | `:lipstick:` | UI/style |
| 🔥 | `:fire:` | Remove code |
| 🚀 | `:rocket:` | Deploy/release |
| 🔒 | `:lock:` | Security |
| ✅ | `:white_check_mark:` | Tests |
| 🔧 | `:wrench:` | Config |

**See:** `examples/gitmoji.md`

---

## 4. Classic (cbeams Style)

Traditional style used by Linux kernel, Git itself. No prefixes.

**Format:**
```
<subject line>

[optional body]

[optional footer]
```

**The Seven Rules:**
1. Separate subject from body with blank line
2. Limit subject to 50 chars (72 max)
3. Capitalize subject line
4. No period at end of subject
5. Use imperative mood
6. Wrap body at 72 chars
7. Body explains what/why, not how

**Common Verbs:** Add, Fix, Update, Remove, Refactor, Release, Improve, Rename, Bump, Enable

**See:** `examples/classic.md`

---

## Fallback (No Clear Standard)

When detection fails, use Classic with:
- Imperative mood
- Capitalize first letter
- No trailing period
- Subject ≤50 chars, max 72
- Body wrapped at 72 chars
- Bullet points with `-`
