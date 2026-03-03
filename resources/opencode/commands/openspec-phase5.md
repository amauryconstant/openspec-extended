---
description: PHASE5 - Self-Reflection
agent: openspec-analyzer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc-ctx` | `.opencode/scripts/lib/osc-ctx <change>` - load change context |
| `osc-log` | `.opencode/scripts/lib/osc-log <change> <action>` - decision log |
| `osc-iterations` | `.opencode/scripts/lib/osc-iterations <change> <action>` - iteration history |
| `osc-complete` | `.opencode/scripts/lib/osc-complete <change> <action>` - signal blocker status |

# PHASE5: Self-Reflection

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE5
3. Review full history via `osc-log get` to understand entire workflow
4. Review `history.iterations_recorded` for iteration counts per phase
5. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)

## PURPOSE

Critically evaluate the autonomous development process and identify improvements.

## REFLECTION QUESTIONS

Answer each with 2-4 sentences minimum, including specific examples:

**1. How well did the artifact review process work?**
   - Were CRITICAL issues identified accurately?
   - Did the iteration limit (5) constrain fixing important issues?
   - Should any issues have been raised earlier or later?

**2. How effective was the implementation phase?**
   - Were tasks clear and achievable?
   - Did milestone commits make sense?
   - Was test compliance review useful?

**3. How did verification perform?**
   - Did it catch important issues?
   - Were issues actionable?
   - Should any CRITICAL/WARNING issues have been caught earlier?

**4. What assumptions had to be made?**
   - List all significant assumptions from decision-log.json
   - Which caused issues later?
   - Which worked well?

**5. How did completion phases work?**
   - Were phase transitions smooth?
   - Did MAINTAIN DOCS provide value?
   - Did SYNC complete successfully?

**6. How was commit behavior?**
   - Were milestone commits made appropriately?
   - Did commit timing make sense?

**7. What would improve the workflow?**
   - Missing skills or tools?
   - Process bottlenecks?
   - Documentation improvements?

**8. What would improve for future changes?**
   - Review suggestions.md for any quick wins
   - Were any suggestions actually blockers in disguise?
   - Should any suggestions become new OpenSpec changes?
   - Artifact quality improvements?
   - Missing checkpoints?
   - Better progress tracking?

## DECISION LOG

Write reflections to file, then log:

```bash
# Write reflections (full markdown allowed)
cat > "openspec/changes/$1/reflections.md" << 'EOF'
# Self-Reflection: $1

## 1. How well did the artifact review process work?
[Answer with specific examples - 2-4 sentences]

## 2. How effective was the implementation phase?
[Answer with specific examples - 2-4 sentences]

## 3. How did verification perform?
[Answer with specific examples - 2-4 sentences]

## 4. What assumptions had to be made?
[Answer with specific examples - 2-4 sentences]

## 5. How did completion phases work?
[Answer with specific examples - 2-4 sentences]

## 6. How was commit behavior?
[Answer with specific examples - 2-4 sentences]

## 7. What would improve the workflow?
[Answer with specific examples - 2-4 sentences]

## 8. What would improve for future changes?
[Answer with specific examples - 2-4 sentences]
EOF

# Log with path reference (not inline content)
echo '{
  "phase": "SELF_REFLECTION",
  "iteration": N,
  "summary": "Self-reflection completed. Workflow evaluation finished.",
  "reflections_path": "openspec/changes/$1/reflections.md",
  "total_phases": 7,
  "total_iterations": N,
  "commit_hash": "<hash or null>",
  "next_steps": "Self-reflection complete. Proceeding to PHASE6 (ARCHIVE)."
}' | .opencode/scripts/lib/osc-log "$1" append
```

## ITERATIONS.JSON

Append entry:
```bash
echo '{
  "iteration": N,
  "phase": "SELF_REFLECTION",
  "total_phases": 7,
  "total_iterations": N,
  "reflection_completed": true,
  "commit_hash": "<hash or null>",
  "notes": "Self-reflection completed"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## MANDATORY END

Commit reflections:

```bash
git add openspec/changes/$1/reflections.md
git commit -m "Complete self-reflection for $1"
```

Record commit hash in decision log and iterations.json.

## BLOCKER HANDLING

If you encounter an unrecoverable issue that prevents progress:

```bash
echo '{
  "status": "COMPLETE",
  "with_blocker": true,
  "blocker_reason": "[Describe the specific blocking issue]",
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}' > openspec/changes/$1/complete.json
```

The orchestrator will detect this and halt the workflow.

**When to use:**
- Reflection reveals a critical issue that requires human intervention
- Workflow cannot proceed to archive due to unresolved problems

## TRANSITION

1. Log: "Self-reflection complete, proceeding to ARCHIVE"
2. Mark phase complete via `osc-state`
3. Script will advance to PHASE6 (ARCHIVE)
