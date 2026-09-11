# Keep a Changelog Format Specification

Based on [Keep a Changelog 1.0.0](https://keepachangelog.com/en/1.0.0/).

## File Structure

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- New feature added

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security vulnerability fixes
```

## Version Sections

```markdown
## [1.2.3] - 2024-01-15

### Added
- Dark mode support
```

**Version header format**: `## [Version] - YYYY-MM-DD`

## Categories

### Standard Categories

| Category | Description | When to Use |
|-----------|-------------|-------------|
| Added | New features | New capabilities added to the project |
| Changed | Changes in existing functionality | Modifications to existing features |
| Deprecated | Soon-to-be removed features | Features that will be removed in future versions |
| Removed | Removed features | Features removed from the project |
| Fixed | Bug fixes | Bug fixes and corrections |
| Security | Security vulnerability fixes | Security-related fixes |

### Additional Categories (Optional)

These categories can be used but are less common:

| Category | Description |
|-----------|-------------|
| Performance | Performance improvements |
| Documentation | Documentation changes |
| Breaking | Breaking changes | Use for breaking changes that require user attention |

## Entry Format

### Standard Entry

```markdown
### Added
- Add dark mode support (add-dark-mode)
```

**Components**:
- Category header (### Added/Changed/etc.)
- Hyphen prefix (-) at start of entry
- Description (1-3 sentences)
- Change reference in parentheses, optional

### Entry with Reference

```markdown
### Fixed
- Fix authentication timeout (fix-auth-timeout) [#123]
```

**Optional additions**:
- Issue/PR number in brackets or parentheses
- Link to related documentation
- Commit hash for reference

### Breaking Change Entry

```markdown
### Breaking
- **BREAKING**: API endpoint /v1/users is now /v2/users (migrate-users)
```

**Important**: Breaking changes should be:
- Prominently marked with `**BREAKING**`
- Include migration guide reference
- Explain impact clearly

## Version Formatting

### Semantic Versioning

Use [Semantic Versioning](https://semver.org/) for version numbers:

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (0.Y.0): Backwards-compatible functionality added
- **PATCH** version (0.0.Z): Backwards-compatible bug fixes

### Version Header Examples

```markdown
## [1.0.0] - 2023-01-01

## [2.0.0] - 2023-06-15

## [2.1.0] - 2023-09-30
```

### Release Date

Recommended format: `## [Version] - YYYY-MM-DD`

### Link to Release Notes

If project hosts release notes separately:

```markdown
## [1.0.0] - 2023-01-01

For full release notes, see [Release 1.0.0](https://example.com/releases/1.0.0).
```

## Transitioning Between Versions

### Moving Unreleased to Version

When releasing:

1. Create new version section header
2. Move all `## [Unreleased]` entries under new version
3. Remove empty `[Unreleased]` section
4. Update version number throughout

### Keeping Unreleased Section

If release is not yet ready:

1. Leave entries in `[Unreleased]`
2. Add note at top: "This version is not yet released"
3. Plan release date in future

## Formatting Rules

### Indentation

- Version headers: Level 2 (`##`)
- Category headers: Level 3 (`###`)
- Entries: No indentation (hyphen prefix only)

### Whitespace

- One blank line between sections
- One blank line after version header
- No trailing whitespace on entries

### Character Encoding

- UTF-8 encoding recommended
- Avoid special characters in entries
- Use plain ASCII when possible

## Examples

### Minimal Changelog

```markdown
# Changelog

## [Unreleased]
No changes yet.

### Added
- Nothing to add yet.
```

### Realistic Changelog

```markdown
# Changelog

## [1.2.0] - 2024-02-12

### Added
- Add dark mode support (add-dark-mode)
- Implement user authentication system (add-auth)
- Add export to CSV functionality (add-csv-export)

### Changed
- Update API authentication flow (update-auth-flow)
- Refactor data models for better performance (refactor-models)

### Fixed
- Fix session timeout handling (fix-session-timeout)
- Resolve authentication token refresh bug (fix-token-refresh)

### Security
- **Security**: Patch JWT token leak vulnerability (patch-jwt-leak) [CVE-2024-1234]

### Removed
- Remove legacy export feature (remove-legacy-export) - deprecated in favor of CSV export

### Breaking
- **BREAKING**: API endpoint `/v1/users` is now `/v2/users`. Migration guide: [MIGRATION-v1-to-v2]

For migration instructions, see [Migration Guide](docs/migration-v1-to-v2.md).
```

## Anti-Patterns

### What to Avoid

- Don't commit unrelated changes in same release
- Don't mix multiple releases in one version header
- Don't use vague descriptions ("various fixes", "general improvements")
- Don't forget to move unreleased entries when releasing

### What to Do

- One entry per significant change (grouping related changes is OK)
- Be specific about what changed and why
- Include migration guides for breaking changes
- Reference related issues or PRs when available

## References

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/) - Alternative approach
