# Quality Categories

Phase D evaluates each category below against the surface maps. Specific items under each category are project state and refresh per audit.

## 1. Skill quality

Evaluate each skill for clarity, trigger specificity, and contract compliance.

- Frontmatter fields complete and valid
- Description fires on the right prompts, not too broadly
- Steps clear and bounded
- References disclosed, not inlined
- Contract rules honored (e.g., schema-agnostic where applicable)
- Permission declarations match what the body instructs

## 2. Agent quality

Evaluate each agent for role clarity and permission consistency.

- `mode` field appropriate for dispatch context
- Permission blocks (edit, question, etc.) consistent with intended use
- Temperature rationale sensible
- Prompt clarity: role, scope, escalation path
- No permission contradictions with the commands that route to the agent

## 3. Command quality

Evaluate each slash command for dispatch and guardrail integrity.

- Frontmatter description accurate and bounded
- Body instructs clearly
- Dispatch logic correct (which agent, which flags)
- Guardrails present where the command mutates
- No dead references to skills or commands that no longer exist

## 4. Phase workflow quality

Evaluate each orchestrator phase against the engine's dispatch contract.

- Command body matches engine dispatch table
- Permission model consistent across phases that share an agent
- Ordering conflicts with engine cleanup logic
- Phase output handled correctly by the next phase or by archive
- No silent no-ops when the upstream surface is missing expected pieces
