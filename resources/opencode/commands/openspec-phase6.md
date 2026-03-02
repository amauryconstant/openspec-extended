---
description: PHASE6 - Self-Reflection
agent: openspec-analyzer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc-ctx` | `.opencode/scripts/lib/osc-ctx <change>` - load change context |
| `osc-log` | `.opencode/scripts/lib/osc-log <change> <action>` - decision log |
| `osc-iterations` | `.opencode/scripts/lib/osc-iterations <change> <action>` - iteration history |

# PHASE6: Self-Reflection

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE6
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
   - Did MAINTAIN-DOCS provide value?
   - Did SYNC complete successfully?

**6. How was commit behavior?**
   - Were milestone commits made appropriately?
   - Did commit timing make sense?

**7. What would improve the workflow?**
   - Missing skills or tools?
   - Process bottlenecks?
   - Documentation improvements?

**8. What would improve for future changes?**
   - Artifact quality improvements?
   - Missing checkpoints?
   - Better progress tracking?

## STATE FILE UPDATES

After reflection, create `complete.json`:
```bash
echo '{
  "status": "COMPLETE",
  "with_blocker": false,
  "blocker_reason": null,
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}' > openspec/changes/$1/complete.json
```

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
  "summary": "All phases complete. Workflow evaluation finished.",
  "reflections_path": "openspec/changes/$1/reflections.md",
  "total_phases": 7,
  "total_iterations": N,
  "next_steps": "All phases complete. Ready to signal completion."
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
  "notes": "Self-reflection completed"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## COMPLETION

After PHASE6 reflection:
1. Create `complete.json` with status "COMPLETE"
2. The script will validate and exit
3. State files will be cleaned up by the script
