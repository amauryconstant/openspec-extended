# Detection Heuristics

## Priority Order

1. **Explicit config files** - Highest confidence
2. **Project documentation** - High confidence
3. **Git history patterns** - Medium confidence
4. **Default fallback** - Classic style

---

## 1. Check Config Files

```bash
# Conventional Commits / Angular
ls commitlint.config.js .commitlintrc .commitlintrc.json .commitlintrc.yaml 2>/dev/null

# Conventional Commits (standard-version, semantic-release)
ls .versionrc .versionrc.json 2>/dev/null

# Gitmoji
ls .gitmojirc .gitmojirc.json 2>/dev/null
```

---

## 2. Check Documentation

```bash
# Check for commit conventions
grep -l -i "commit" AGENTS.md CLAUDE.md CONTRIBUTING.md README.md 2>/dev/null

# Look for specific patterns
grep -E "(conventional commits|gitmoji|angular.*commit)" AGENTS.md CLAUDE.md CONTRIBUTING.md 2>/dev/null
```

---

## 3. Analyze Git History

Use the bundled script:

```bash
scripts/detect-commit-style
```

Or manually analyze last 10 commits:

```bash
git log --format="%s" -10
```

### Detection Patterns

| Pattern | Standard |
|---------|----------|
| `^(feat|fix|docs|...):` | Conventional Commits |
| `^(feat|fix|...)(scope):` | Angular |
| `^[\x{1F300}-\x{1F9FF}]` | Gitmoji |
| `^(Add|Fix|Update|...)` | Classic |

### Decision Thresholds

Require ≥3 matches to detect a standard.

| Standard | Threshold |
|----------|-----------|
| Angular | ≥3 matches + more than Conventional |
| Conventional | ≥3 matches |
| Gitmoji | ≥3 matches |
| Classic | ≥3 matches |
| Unknown | Fallback to Classic |

### Decision Tree

```
IF config file exists → Use corresponding standard
ELSE IF docs specify standard → Use specified standard
ELSE IF Angular ≥3 matches → Angular
ELSE IF Conventional ≥3 matches → Conventional
ELSE IF Gitmoji ≥3 matches → Gitmoji
ELSE IF Classic ≥3 matches → Classic
ELSE → Fallback to Classic
```

---

## Verification Patterns

After drafting, verify message matches detected standard:

| Standard | Verification Regex |
|----------|-------------------|
| Conventional | `^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\(.+\))?!?:\s.+` |
| Angular | `^(build|ci|docs|feat|fix|perf|refactor|test)\([a-z-]+\):\s.+` |
| Gitmoji | `^[\x{1F300}-\x{1F9FF}]\s.+` |
| Classic | `^[A-Z][a-z]+\s.+[^.]$` |
