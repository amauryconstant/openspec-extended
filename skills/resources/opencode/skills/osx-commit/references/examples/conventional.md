# Conventional Commits Examples

## Simple Commits

```
feat: add user authentication
```

```
fix: prevent racing of requests
```

```
docs: update API documentation
```

```
refactor: simplify validation logic
```

```
test: add unit tests for parser
```

## With Scope

```
feat(api): add rate limiting endpoint
```

```
fix(auth): correct token expiration
```

```
docs(readme): add installation steps
```

```
perf(db): optimize query performance
```

```
chore(deps): bump dependencies
```

## Breaking Changes

```
feat(api)!: remove deprecated endpoints
```

```
fix!: break existing API contract

BREAKING CHANGE: The response format has changed from
XML to JSON. Clients must update their parsers.
```

## With Body

```
feat: add user preferences panel

- Add preference storage in database
- Create settings UI component
- Add API endpoints for preferences

Closes #123
```

```
fix: resolve memory leak in image processor

The cache wasn't being properly cleared when processing
large batches of images.

- Clear cache after batch processing
- Add memory usage monitoring
- Update documentation

Fixes #456
```

## Multiple Types Reference

| Type | Example |
|------|---------|
| `feat` | `feat: add dark mode support` |
| `fix` | `fix: resolve login timeout issue` |
| `docs` | `docs: clarify configuration options` |
| `style` | `style: format code with prettier` |
| `refactor` | `refactor: extract validation logic` |
| `perf` | `perf: reduce bundle size by 20%` |
| `test` | `test: add integration tests` |
| `build` | `build: update webpack config` |
| `ci` | `ci: add github actions workflow` |
| `chore` | `chore: update gitignore` |

## Anti-Patterns

```
❌ feat: Added feature. (past tense, period)
❌ Feat: add feature (uppercase type)
❌ feat:Add feature (no space after colon)
❌ feat add feature (no colon)
❌ feature: add something (invalid type)
```
