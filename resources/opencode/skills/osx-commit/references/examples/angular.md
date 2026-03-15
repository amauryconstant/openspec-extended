# Angular Commit Examples

Angular commits require scope for most types.

## Simple Commits (docs exception)

```
docs: fix typo in getting started guide
```

## With Scope (Required for non-docs)

```
feat(compiler): add template type checking
```

```
fix(router): correct navigation during guards
```

```
perf(core): improve change detection speed
```

```
refactor(http): simplify request handling
```

```
build(deps): update TypeScript to 5.0
```

```
ci(actions): add code coverage reporting
```

```
test(common): add tests for currency pipe
```

## With Body (Required for non-docs)

```
fix(router): resolve lazy loading guard order

Previously, the router would incorrectly resolve guards during
lazy loading scenarios. This fix ensures guards are resolved
in the correct order for all navigation types.

- Fix guard resolution timing
- Add integration tests
- Update router documentation

Fixes #12345
```

```
feat(forms): add async validator support

This change enables async validators to work with reactive
forms, allowing validation that requires server-side checks.

- Add AsyncValidator interface
- Update form control to handle promises
- Add examples to docs

Closes #6789
```

## Common Scopes

| Scope | Usage |
|-------|-------|
| `core` | Core framework |
| `common` | Common utilities |
| `compiler` | Template compiler |
| `router` | Routing system |
| `forms` | Form handling |
| `http` | HTTP client |
| `animations` | Animation system |
| `service-worker` | PWA support |
| `deps` | Dependencies |
| `zone.js` | Zone.js integration |

## Breaking Changes

```
feat(core)!: remove deprecated Renderer

BREAKING CHANGE: The deprecated Renderer class has been
removed. Use Renderer2 instead.

Migration guide: docs/migration/renderer.md
```

## Anti-Patterns

```
❌ feat: add feature (missing scope)
❌ feat(Foo): add feature (uppercase scope)
❌ Feat(core): add feature (uppercase type)
❌ feat(core): Add feature (uppercase description)
❌ feat(core): add feature. (period at end)
```
