---
description: PHASE6 - Self-Reflection
agent: openspec-analyzer
subtask: true
version: "0.1.0"
---

# PHASE6: Self-Reflection

Change: $1

## MANDATORY START

1. Read `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
2. Read `openspec/changes/$1/state.json` to confirm phase is PHASE6
3. Read `openspec/changes/$1/decision-log.md` (full history) to understand the entire workflow
4. Read `openspec/changes/$1/iterations.json` to understand iteration counts per phase

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
   - List all significant assumptions from decision-log.md
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
cat > openspec/changes/$1/complete.json << 'EOF'
{
  "status": "COMPLETE",
  "with_blocker": false,
  "blocker_reason": null,
  "timestamp": "[current timestamp]"
}
EOF
```

## DECISION LOG FORMAT

Append to `openspec/changes/$1/decision-log.md`:

```markdown
## PHASE6 - SELF-REFLECTION

### Process Reflection

**1. Artifact Review Process**
[Answer with specific examples]

**2. Implementation Phase**
[Answer with specific examples]

**3. Verification Performance**
[Answer with specific examples]

**4. Assumptions Made**
[Answer with specific examples]

**5. Completion Phases**
[Answer with specific examples]

**6. Commit Behavior**
[Answer with specific examples]

**7. Workflow Improvements**
[Answer with specific examples]

**8. Future Change Improvements**
[Answer with specific examples]

### Session Summary
All phases complete. Workflow evaluation finished.

### Completion
All phases complete. Ready to signal completion.
```

## ITERATIONS.JSON FORMAT

Append to `openspec/changes/$1/iterations.json`:

```json
{
  "iteration": N,
  "phase": "SELF_REFLECTION",
  "total_phases": 7,
  "total_iterations": N,
  "reflection_completed": true,
  "notes": "Self-reflection completed"
}
```

## COMPLETION

After PHASE6 reflection:
1. Create `complete.json` with status "COMPLETE"
2. The script will validate and exit
3. State files will be cleaned up by the script
