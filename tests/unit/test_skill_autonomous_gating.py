from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    "skill",
    ["osx-maintain-ai-docs", "osx-modify-artifacts"],
)
@pytest.mark.parametrize("platform", ["opencode", "claude"])
def test_skill_autonomous_gates_precede_questions(skill: str, platform: str) -> None:
    path = (
        Path(__file__).parents[2]
        / "resources"
        / platform
        / "skills"
        / skill
        / "SKILL.md"
    )
    text = path.read_text()
    lines = text.splitlines()
    # The ask-tool name varies by platform and form:
    #   opencode source:  {{ASK_TOOL}}  (literal token before sync-mirrors)
    #   opencode runtime: AskUserQuestion
    #   claude source:    {{ASK_TOOL}}
    #   claude runtime:   Ask
    # Match any of these so the test is token-aware.
    question_lines = [
        index
        for index, line in enumerate(lines)
        if "AskUserQuestion" in line
        or "Ask tool" in line
        or "the **`Ask`** tool" in line
        or "{{ASK_TOOL}}" in line
        # After sync-mirrors, the substituted name "Ask" is the marker.
        # Use a word boundary so we don't match unrelated lines.
        or "(`Ask`" in line
        or " `Ask`" in line
    ]
    # The skill must declare the autonomous-mode convention at the top (one
    # blockquote pointing at references/osx-mode-conventions.md, or the inline
    # gate prose). Per-step restatement is no longer required — the convention
    # is announced once and assumed thereafter.
    assert "OSX_AUTONOMOUS=1" in text, (
        f"{path} must declare the OSX_AUTONOMOUS=1 convention"
    )
    assert "auto-accept" in text.lower() or "skip" in text.lower(), (
        f"{path} must include the auto-accept/skip phrasing of the convention"
    )
    # Per-step gating only matters when the skill actually has ask-tool
    # references. Skills with no interactive prompts (e.g., fully autonomous
    # flows) declare the convention once and need no per-step checks.
    if not question_lines:
        return
    # Per-step: every ask-tool reference must be preceded (within 4 lines) by
    # either `OSX_AUTONOMOUS=1` (per-step inline gate) or the auto-accept
    # leading word.
    for index in question_lines:
        preceding = "\n".join(lines[max(0, index - 4) : index + 1])
        gated = "OSX_AUTONOMOUS=1" in preceding or "auto-accept" in preceding.lower()
        assert gated, (
            f"{path}:{index + 1} ask-tool reference must be preceded by "
            "`OSX_AUTONOMOUS=1` gating or the auto-accept leading word"
        )
