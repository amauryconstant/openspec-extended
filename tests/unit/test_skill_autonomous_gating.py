from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    "skill",
    ["osx-maintain-ai-docs", "osx-modify-artifacts"],
)
@pytest.mark.parametrize("platform", ["opencode", "claude"])
def test_skill_autonomous_gates_precede_questions(skill: str, platform: str) -> None:
    path = Path(__file__).parents[2] / "resources" / platform / "skills" / skill / "SKILL.md"
    lines = path.read_text().splitlines()
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
    assert question_lines, (
        f"{path} has no ask-tool references; the convention is to gate every "
        "ask behind `OSX_AUTONOMOUS=1` and skip the prompt when set"
    )
    for index in question_lines:
        preceding = "\n".join(lines[max(0, index - 4) : index + 1])
        assert "OSX_AUTONOMOUS=1" in preceding, (
            f"{path}:{index + 1} ask-tool reference must be preceded by "
            "`OSX_AUTONOMOUS=1` gating"
        )
        assert "skip" in preceding.lower(), (
            f"{path}:{index + 1} ask-tool reference must be preceded by a "
            "`skip` clause when autonomous mode is set"
        )
