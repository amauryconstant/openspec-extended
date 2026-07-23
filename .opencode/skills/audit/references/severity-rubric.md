# Severity Rubric

Apply in Phase E to assign severity to each finding. The tier definitions below are stable process guidance. False-positive guards and worked findings live in `rubric-examples.md` and refresh per audit.

## Tiers

| Tier | Definition | Blast radius |
|------|------------|--------------|
| CRITICAL | Silent failure · autonomous-loop break · test cements wrong behavior · production bug | Users hit it on every run; orchestrator halts or loops forever |
| HIGH | Drift · dead references · version-gated silent no-op · missing contract test · permission contradiction · agent permission vs command body mismatch | Users hit it on edge cases; certain schema or version combos break |
| MEDIUM | Doc drift · version literal mismatch · missing preflight · double-flag · duplicated constants · verbosity | Confusing or wasteful; rarely breaks |
| LOW | Terminology · redundant comment · layout polish · style nit | Cosmetic; never breaks |

## Citation discipline

- Every claim cites the file and line where the evidence was read.
- Group related findings under one header.
- No paraphrasing. Quote the actual line when ambiguity is possible.
- Use absolute paths from the configured roots in `.audit/config.toml`.
- For drift findings, cite both the source and the target: `<upstream-root>/path` ↔ `<local-root>/path`.
- Mark `UNVERIFIED` if the claim cannot be confirmed from source alone. Do not infer.

## See also

- `.audit/templates/rubric-examples.md` — current false-positive guards and worked findings, refreshed per audit.
