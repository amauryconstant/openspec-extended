# Gitmoji Examples

Emoji at start, space, then description.

## Simple Commits

```
✨ Add user authentication system
```

```
🐛 Fix memory leak in image processor
```

```
📝 Update API documentation for v2 endpoints
```

```
♻️ Refactor database connection handling
```

```
💄 Redesign login page layout
```

## With Body

```
🐛 Fix token validation edge case

The validation was failing for tokens generated during
leap seconds. Added special handling for these cases.

- Add leap second detection
- Update token parser
- Add regression tests
```

```
✨ Add dark mode support

Implements system-wide dark mode with user preference
persistence.

- Add theme toggle component
- Implement CSS variables
- Store preference in localStorage
```

## Common Emojis

| Emoji | Code | Usage |
|-------|------|-------|
| ✨ | `:sparkles:` | New feature |
| 🐛 | `:bug:` | Bug fix |
| 📝 | `:memo:` | Documentation |
| ♻️ | `:recycle:` | Refactor |
| 💄 | `:lipstick:` | UI/style |
| 🔥 | `:fire:` | Remove code/files |
| 🚀 | `:rocket:` | Deploy/release |
| 🔒 | `:lock:` | Security fix |
| ✅ | `:white_check_mark:` | Tests |
| 🔧 | `:wrench:` | Configuration |
| ⬆️ | `:arrow_up:` | Upgrade dependencies |
| ⬇️ | `:arrow_down:` | Downgrade dependencies |
| 🚨 | `:rotating_light:` | Fix lint warnings |
| 🎨 | `:art:` | Code structure |
| ⚡ | `:zap:` | Performance |
| 🗑️ | `:wastebasket:` | Deprecate code |
| 📦 | `:package:` | Build/package |
| 👷 | `:construction_worker:` | CI/CD |
| 📌 | `:pushpin:` | Pin dependencies |
| 🔖 | `:bookmark:` | Release/version |

## Combined with Conventional

Some projects use both:

```
✨ feat: add user dashboard
```

```
🐛 fix(auth): resolve session timeout
```

## Breaking Changes

```
🔥 Remove deprecated API endpoints

The following endpoints have been removed:
- /api/v1/users (use /api/v2/users)
- /api/v1/auth (use /api/v2/auth)

Migration deadline: 2024-03-01
```

## Anti-Patterns

```
❌ ✨Add feature (no space after emoji)
❌ ✨ Added feature (past tense)
❌ ✨ add feature (lowercase start)
❌ ✨ Add feature. (period at end)
❌ 🐛 Fix stuff (too vague)
```
