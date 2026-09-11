# Classic Commit Examples

No prefixes. Imperative mood. Subject ≤50 chars (72 max).

## Simple Commits

```
Add rate limiting to API endpoints
```

```
Fix authentication token expiration
```

```
Rename resources to osx-* prefix
```

```
Refactor subsystem X for readability
```

```
Release version 2.0.0
```

```
Update dependencies to latest versions
```

```
Remove deprecated legacy API methods
```

```
Enable strict mode in TypeScript config
```

## With Body

```
Fix PHASE6 workflow issues in openspec-auto

- Return error for archived changes without state.json
- Skip show_progress after PHASE6 (state deleted)
- Update logs before commit (was leaving uncommitted changes)
```

```
Add rate limiting to public API

Implement token bucket algorithm for rate limiting
API endpoints to prevent abuse.

- Add RateLimiter middleware
- Configure limits per endpoint
- Add rate limit headers to responses
- Update API documentation
```

```
Remove deprecated authentication methods

The following methods have been deprecated since v1.5:
- processOldFormat()
- legacyTransform()

Migration guide available in docs/migration.md.
```

```
Refactor database connection handling

Split the monolithic database module into separate
concerns:

- Connection pooling in pool.go
- Query building in builder.go
- Transaction management in tx.go

This improves testability and reduces coupling.
```

## Common Imperative Verbs

| Verb | Example |
|------|---------|
| Add | `Add rate limiting to API` |
| Fix | `Fix null pointer in parser` |
| Update | `Update dependencies` |
| Remove | `Remove deprecated methods` |
| Refactor | `Refactor auth module` |
| Release | `Release version 1.0.0` |
| Improve | `Improve error messages` |
| Rename | `Rename util to helpers` |
| Bump | `Bump version to 2.1.0` |
| Enable | `Enable caching by default` |
| Correct | `Correct typo in config` |
| Restructure | `Restructure src directory` |
| Replace | `Replace lodash with native` |
| Enhance | `Enhance logging output` |
| Relocate | `Relocate config files` |
| Merge | `Merge feature branch` |
| Revert | `Revert breaking change` |
| Document | `Document API endpoints` |
| Simplify | `Simplify validation logic` |
| Optimize | `Optimize query performance` |

## Subject Line Rules

1. **Capitalize first letter**: `Add` not `add`
2. **No period at end**: `Add feature` not `Add feature.`
3. **Imperative mood**: `Add` not `Added` or `Adds`
4. **Be specific**: `Fix null pointer in parser` not `Fix bug`
5. **Keep short**: ≤50 chars ideal, 72 max

## Anti-Patterns

```
❌ Added feature (past tense)
❌ Adds feature (third person)
❌ add feature (lowercase)
❌ Add feature. (period at end)
❌ Fix config (too vague)
❌ Update stuff (no substance)
❌ feat: add feature (prefix if project doesn't use one)
❌ Add feature and fix bug and update docs (too many things)
```

## Multi-Item Changes

Use bullet points in body:

```
Improve test coverage for auth module

- Add unit tests for token validation
- Add integration tests for login flow
- Mock external services in tests
- Increase coverage from 45% to 78%
```
